import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryOptions,
  type UseMutationOptions,
} from '@tanstack/react-query';
import { apiClient } from '../lib/api-client';
import type { AxiosError } from 'axios';

/* ---------------------------------------------------------------------------
 * Tipos do domínio "Caso Jurídico"
 * --------------------------------------------------------------------------- */

/** Representação resumida de um caso retornado em listagens. */
export interface CaseSummary {
  id: string;
  title: string;
  description: string;
  status: string;
  client_name: string;
  created_at: string;
  updated_at: string;
}

/** Representação completa de um caso (detalhe). */
export interface CaseDetail extends CaseSummary {
  documents_count: number;
  analyses_count: number;
  notes: string | null;
  tags: string[];
  /** Metadados adicionais específicos do domínio jurídico. */
  metadata: Record<string, unknown> | null;
}

/** Payload para criação de um novo caso. */
export interface CreateCasePayload {
  title: string;
  description: string;
  client_name: string;
  notes?: string | null;
  tags?: string[];
  metadata?: Record<string, unknown> | null;
}

/** Payload para atualização parcial de um caso existente. */
export interface UpdateCasePayload {
  title?: string;
  description?: string;
  client_name?: string;
  status?: string;
  notes?: string | null;
  tags?: string[];
  metadata?: Record<string, unknown> | null;
}

/** Resposta paginada padrão da API. */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

/** Parâmetros de filtro e paginação para listagem de casos. */
export interface ListCasesParams {
  page?: number;
  page_size?: number;
  search?: string;
  status?: string;
  ordering?: string;
}

/** Estrutura padrão de erro da API. */
export interface ApiErrorResponse {
  detail: string;
}

/* ---------------------------------------------------------------------------
 * Chaves de query centralizadas
 * --------------------------------------------------------------------------- */

/** Chaves de cache do TanStack Query para o módulo de casos. */
export const caseKeys = {
  /** Raiz — utilizada para invalidação ampla. */
  all: ['cases'] as const,
  /** Lista com filtros aplicados. */
  lists: () => [...caseKeys.all, 'list'] as const,
  /** Lista filtrada por parâmetros específicos. */
  list: (params: ListCasesParams) => [...caseKeys.lists(), params] as const,
  /** Detalhes de um caso individual. */
  details: () => [...caseKeys.all, 'detail'] as const,
  /** Detalhe de um caso específico pelo ID. */
  detail: (id: string) => [...caseKeys.details(), id] as const,
} as const;

/* ---------------------------------------------------------------------------
 * Endpoint base
 * --------------------------------------------------------------------------- */

const CASES_ENDPOINT = '/cases';

/* ---------------------------------------------------------------------------
 * Hooks
 * --------------------------------------------------------------------------- */

/**
 * Hook para listar casos jurídicos com paginação e filtros.
 *
 * @param params - Parâmetros de filtro e paginação.
 * @param options - Opções adicionais do TanStack Query.
 * @returns Query com a lista paginada de casos.
 *
 * @example
 * ```tsx
 * const { data, isLoading } = useListCases({ page: 1, search: 'trabalhista' });
 * ```
 */
export function useListCases(
  params: ListCasesParams = {},
  options?: Omit<
    UseQueryOptions<PaginatedResponse<CaseSummary>, AxiosError<ApiErrorResponse>>,
    'queryKey' | 'queryFn'
  >,
) {
  return useQuery<PaginatedResponse<CaseSummary>, AxiosError<ApiErrorResponse>>({
    queryKey: caseKeys.list(params),
    queryFn: async () => {
      const response = await apiClient.get<PaginatedResponse<CaseSummary>>(
        CASES_ENDPOINT,
        { params },
      );
      return response.data;
    },
    staleTime: 1000 * 60 * 2, // 2 minutos — dados de listagem podem ser levemente stale
    ...options,
  });
}

/**
 * Hook para obter os detalhes de um caso jurídico específico.
 *
 * @param id - Identificador único do caso.
 * @param options - Opções adicionais do TanStack Query.
 * @returns Query com os detalhes completos do caso.
 *
 * @example
 * ```tsx
 * const { data: caseDetail } = useCase('uuid-do-caso');
 * ```
 */
export function useCase(
  id: string,
  options?: Omit<
    UseQueryOptions<CaseDetail, AxiosError<ApiErrorResponse>>,
    'queryKey' | 'queryFn'
  >,
) {
  return useQuery<CaseDetail, AxiosError<ApiErrorResponse>>({
    queryKey: caseKeys.detail(id),
    queryFn: async () => {
      const response = await apiClient.get<CaseDetail>(
        `${CASES_ENDPOINT}/${id}`,
      );
      return response.data;
    },
    enabled: !!id,
    staleTime: 1000 * 60 * 5, // 5 minutos — detalhe muda com menos frequência
    ...options,
  });
}

/**
 * Hook para criar um novo caso jurídico.
 *
 * Após criação bem-sucedida, invalida automaticamente as listas de casos
 * para que a UI reflita o novo registro.
 *
 * @param options - Opções adicionais do TanStack Query Mutation.
 * @returns Mutation para criação de caso.
 *
 * @example
 * ```tsx
 * const createCase = useCreateCase();
 * createCase.mutate({ title: 'Novo Caso', description: '...', client_name: 'João' });
 * ```
 */
export function useCreateCase(
  options?: Omit<
    UseMutationOptions<CaseDetail, AxiosError<ApiErrorResponse>, CreateCasePayload>,
    'mutationFn'
  >,
) {
  const queryClient = useQueryClient();

  return useMutation<CaseDetail, AxiosError<ApiErrorResponse>, CreateCasePayload>({
    mutationFn: async (payload) => {
      const response = await apiClient.post<CaseDetail>(
        CASES_ENDPOINT,
        payload,
      );
      return response.data;
    },
    onSuccess: (data, variables, context) => {
      // Invalida todas as listas para refletir o novo caso
      queryClient.invalidateQueries({ queryKey: caseKeys.lists() });

      // Pré-popula o cache de detalhe com os dados retornados
      queryClient.setQueryData(caseKeys.detail(data.id), data);

      options?.onSuccess?.(data, variables, context);
    },
    onError: options?.onError,
    onSettled: options?.onSettled,
    ...options,
  });
}

/**
 * Hook para atualizar um caso jurídico existente.
 *
 * Após atualização bem-sucedida, invalida as listas e atualiza o cache
 * de detalhe do caso modificado.
 *
 * @param options - Opções adicionais do TanStack Query Mutation.
 * @returns Mutation para atualização de caso.
 *
 * @example
 * ```tsx
 * const updateCase = useUpdateCase();
 * updateCase.mutate({ id: 'uuid', data: { title: 'Título Atualizado' } });
 * ```
 */
export function useUpdateCase(
  options?: Omit<
    UseMutationOptions<
      CaseDetail,
      AxiosError<ApiErrorResponse>,
      { id: string; data: UpdateCasePayload }
    >,
    'mutationFn'
  >,
) {
  const queryClient = useQueryClient();

  return useMutation<
    CaseDetail,
    AxiosError<ApiErrorResponse>,
    { id: string; data: UpdateCasePayload }
  >({
    mutationFn: async ({ id, data }) => {
      const response = await apiClient.patch<CaseDetail>(
        `${CASES_ENDPOINT}/${id}`,
        data,
      );
      return response.data;
    },
    onSuccess: (data, variables, context) => {
      // Invalida listas para refletir possíveis mudanças de status/título
      queryClient.invalidateQueries({ queryKey: caseKeys.lists() });

      // Atualiza o cache de detalhe com os dados frescos
      queryClient.setQueryData(caseKeys.detail(variables.id), data);

      options?.onSuccess?.(data, variables, context);
    },
    onError: options?.onError,
    onSettled: options?.onSettled,
    ...options,
  });
}

/**
 * Hook para excluir um caso jurídico.
 *
 * Após exclusão bem-sucedida, invalida as listas e remove o cache
 * de detalhe do caso excluído.
 *
 * @param options - Opções adicionais do TanStack Query Mutation.
 * @returns Mutation para exclusão de caso.
 *
 * @example
 * ```tsx
 * const deleteCase = useDeleteCase();
 * deleteCase.mutate('uuid-do-caso');
 * ```
 */
export function useDeleteCase(
  options?: Omit<
    UseMutationOptions<void, AxiosError<ApiErrorResponse>, string>,
    'mutationFn'
  >,
) {
  const queryClient = useQueryClient();

  return useMutation<void, AxiosError<ApiErrorResponse>, string>({
    mutationFn: async (id) => {
      await apiClient.delete(`${CASES_ENDPOINT}/${id}`);
    },
    onSuccess: (_data, id, context) => {
      // Invalida todas as listas
      queryClient.invalidateQueries({ queryKey: caseKeys.lists() });

      // Remove o cache de detalhe do caso excluído
      queryClient.removeQueries({ queryKey: caseKeys.detail(id) });

      options?.onSuccess?.(_data, id, context);
    },
    onError: options?.onError,
    onSettled: options?.onSettled,
    ...options,
  });
}
