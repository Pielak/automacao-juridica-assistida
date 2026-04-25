import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { UseMutationOptions, UseQueryOptions } from '@tanstack/react-query';
import { apiClient } from '../lib/api-client';

/* ---------------------------------------------------------------------------
 * Tipos
 * --------------------------------------------------------------------------- */

/** Payload para solicitar uma nova análise de documento/caso. */
export interface RequestAnalysisPayload {
  /** Identificador do caso jurídico. */
  caseId: string;
  /** Identificador do documento a ser analisado (opcional se análise for do caso inteiro). */
  documentId?: string;
  /** Tipo de análise solicitada. */
  analysisType: 'summary' | 'risk' | 'precedent' | 'full';
  /** Instruções adicionais em linguagem natural para a IA. */
  additionalInstructions?: string;
}

/** Status possíveis de uma análise. */
export type AnalysisStatus = 'pending' | 'processing' | 'completed' | 'failed';

/** Representação de uma análise retornada pela API. */
export interface Analysis {
  id: string;
  caseId: string;
  documentId?: string;
  analysisType: 'summary' | 'risk' | 'precedent' | 'full';
  status: AnalysisStatus;
  /** Resultado textual da análise (disponível quando status === 'completed'). */
  result?: string;
  /** Metadados adicionais retornados pela IA (ex.: score de risco, referências). */
  metadata?: Record<string, unknown>;
  /** Mensagem de erro caso status === 'failed'. */
  errorMessage?: string;
  createdAt: string;
  updatedAt: string;
}

/** Resposta paginada de análises de um caso. */
export interface CaseAnalysesResponse {
  items: Analysis[];
  total: number;
  page: number;
  pageSize: number;
}

/** Parâmetros de consulta para listagem de análises de um caso. */
export interface CaseAnalysesParams {
  caseId: string;
  page?: number;
  pageSize?: number;
  status?: AnalysisStatus;
  analysisType?: Analysis['analysisType'];
}

/* ---------------------------------------------------------------------------
 * Chaves de query (query keys)
 * --------------------------------------------------------------------------- */

export const analysisKeys = {
  /** Raiz de todas as queries de análise. */
  all: ['analyses'] as const,
  /** Detalhes de uma análise específica. */
  detail: (analysisId: string) => [...analysisKeys.all, 'detail', analysisId] as const,
  /** Lista de análises de um caso, com filtros opcionais. */
  byCase: (params: CaseAnalysesParams) => [...analysisKeys.all, 'case', params] as const,
};

/* ---------------------------------------------------------------------------
 * Hooks
 * --------------------------------------------------------------------------- */

/**
 * Hook para solicitar uma nova análise de documento/caso.
 *
 * Utiliza `useMutation` do TanStack Query para enviar a requisição ao backend
 * e invalida automaticamente as queries relacionadas ao caso após sucesso.
 *
 * @example
 * ```tsx
 * const { mutate: requestAnalysis, isPending } = useRequestAnalysis();
 * requestAnalysis({ caseId: '123', analysisType: 'full' });
 * ```
 */
export function useRequestAnalysis(
  options?: Omit<
    UseMutationOptions<Analysis, Error, RequestAnalysisPayload>,
    'mutationFn'
  >,
) {
  const queryClient = useQueryClient();

  return useMutation<Analysis, Error, RequestAnalysisPayload>({
    mutationFn: async (payload) => {
      const response = await apiClient.post<Analysis>('/analyses', payload);
      return response.data;
    },
    onSuccess: (data, variables, context) => {
      // Invalida a lista de análises do caso para refletir a nova análise.
      queryClient.invalidateQueries({
        queryKey: analysisKeys.all,
      });

      // Propaga callback do consumidor, se fornecido.
      options?.onSuccess?.(data, variables, context);
    },
    onError: options?.onError,
    onSettled: options?.onSettled,
    ...options,
  });
}

/**
 * Hook para obter o resultado de uma análise específica.
 *
 * Realiza polling automático enquanto a análise estiver em andamento
 * (`pending` ou `processing`), verificando a cada 3 segundos.
 *
 * @param analysisId - Identificador único da análise.
 * @param options - Opções adicionais do `useQuery`.
 *
 * @example
 * ```tsx
 * const { data: analysis, isLoading } = useAnalysisResult('abc-123');
 * ```
 */
export function useAnalysisResult(
  analysisId: string | undefined,
  options?: Omit<
    UseQueryOptions<Analysis, Error, Analysis, ReturnType<typeof analysisKeys.detail>>,
    'queryKey' | 'queryFn'
  >,
) {
  return useQuery<Analysis, Error, Analysis, ReturnType<typeof analysisKeys.detail>>({
    queryKey: analysisKeys.detail(analysisId ?? ''),
    queryFn: async () => {
      const response = await apiClient.get<Analysis>(`/analyses/${analysisId}`);
      return response.data;
    },
    enabled: !!analysisId,
    /**
     * Polling automático: enquanto a análise não estiver concluída ou com erro,
     * refaz a consulta a cada 3 segundos para atualizar o status.
     */
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'pending' || status === 'processing') {
        return 3_000;
      }
      return false;
    },
    /** Mantém dados anteriores durante refetch para evitar flicker na UI. */
    placeholderData: (previousData) => previousData,
    ...options,
  });
}

/**
 * Hook para listar análises de um caso jurídico específico.
 *
 * Suporta paginação e filtros por status e tipo de análise.
 *
 * @param params - Parâmetros de consulta (caseId obrigatório, filtros opcionais).
 * @param options - Opções adicionais do `useQuery`.
 *
 * @example
 * ```tsx
 * const { data, isLoading } = useCaseAnalyses({
 *   caseId: '123',
 *   page: 1,
 *   pageSize: 10,
 *   status: 'completed',
 * });
 * ```
 */
export function useCaseAnalyses(
  params: CaseAnalysesParams,
  options?: Omit<
    UseQueryOptions<
      CaseAnalysesResponse,
      Error,
      CaseAnalysesResponse,
      ReturnType<typeof analysisKeys.byCase>
    >,
    'queryKey' | 'queryFn'
  >,
) {
  const { caseId, page = 1, pageSize = 20, status, analysisType } = params;

  return useQuery<
    CaseAnalysesResponse,
    Error,
    CaseAnalysesResponse,
    ReturnType<typeof analysisKeys.byCase>
  >({
    queryKey: analysisKeys.byCase(params),
    queryFn: async () => {
      const response = await apiClient.get<CaseAnalysesResponse>(
        `/cases/${caseId}/analyses`,
        {
          params: {
            page,
            page_size: pageSize,
            ...(status ? { status } : {}),
            ...(analysisType ? { analysis_type: analysisType } : {}),
          },
        },
      );
      return response.data;
    },
    enabled: !!caseId,
    /** Mantém dados anteriores durante navegação de página para UX fluida. */
    placeholderData: (previousData) => previousData,
    ...options,
  });
}
