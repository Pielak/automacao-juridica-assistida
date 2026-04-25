import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { AxiosError } from 'axios';
import { apiClient } from '../lib/api-client';

/* ---------------------------------------------------------------------------
 * Tipos
 * --------------------------------------------------------------------------- */

/** Representação resumida de um documento retornado pela API. */
export interface DocumentSummary {
  id: string;
  title: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  status: string;
  created_at: string;
  updated_at: string;
}

/** Resposta paginada da listagem de documentos. */
export interface PaginatedDocuments {
  items: DocumentSummary[];
  total: number;
  page: number;
  page_size: number;
}

/** Parâmetros opcionais para listagem de documentos. */
export interface ListDocumentsParams {
  page?: number;
  page_size?: number;
  search?: string;
  status?: string;
  ordering?: string;
}

/** Payload para upload de documento. */
export interface UploadDocumentPayload {
  /** Arquivo selecionado pelo usuário. */
  file: File;
  /** Título opcional — se omitido, o backend pode derivar do nome do arquivo. */
  title?: string;
}

/** Resposta do upload de documento. */
export interface UploadDocumentResponse {
  id: string;
  title: string;
  filename: string;
  status: string;
  created_at: string;
}

/** Estrutura padrão de erro da API. */
export interface ApiErrorDetail {
  detail: string;
}

/* ---------------------------------------------------------------------------
 * Chaves de cache (query keys)
 * --------------------------------------------------------------------------- */

/**
 * Fábrica de query keys para o domínio de documentos.
 * Segue convenção recomendada pelo TanStack Query para invalidação granular.
 */
export const documentKeys = {
  /** Chave raiz — invalida tudo relacionado a documentos. */
  all: ['documents'] as const,
  /** Chave para listagens (aceita filtros). */
  lists: () => [...documentKeys.all, 'list'] as const,
  /** Chave para uma listagem específica com parâmetros. */
  list: (params: ListDocumentsParams) => [...documentKeys.lists(), params] as const,
  /** Chave para detalhes de um documento individual. */
  details: () => [...documentKeys.all, 'detail'] as const,
  /** Chave para detalhe de um documento específico. */
  detail: (id: string) => [...documentKeys.details(), id] as const,
} as const;

/* ---------------------------------------------------------------------------
 * Endpoints
 * --------------------------------------------------------------------------- */

const DOCUMENTS_ENDPOINT = '/documents';

/* ---------------------------------------------------------------------------
 * Hook: useListDocuments
 * --------------------------------------------------------------------------- */

/**
 * Hook para listar documentos com paginação, busca e filtros.
 *
 * @param params - Parâmetros de listagem (página, busca, status, ordenação).
 * @returns Query do TanStack Query com dados paginados de documentos.
 *
 * @example
 * ```tsx
 * const { data, isLoading, error } = useListDocuments({ page: 1, page_size: 20 });
 * ```
 */
export function useListDocuments(params: ListDocumentsParams = {}) {
  return useQuery<PaginatedDocuments, AxiosError<ApiErrorDetail>>({
    queryKey: documentKeys.list(params),
    queryFn: async () => {
      const response = await apiClient.get<PaginatedDocuments>(DOCUMENTS_ENDPOINT, {
        params: {
          page: params.page ?? 1,
          page_size: params.page_size ?? 20,
          ...(params.search ? { search: params.search } : {}),
          ...(params.status ? { status: params.status } : {}),
          ...(params.ordering ? { ordering: params.ordering } : {}),
        },
      });
      return response.data;
    },
    staleTime: 30_000, // 30 segundos — documentos não mudam com alta frequência
    placeholderData: (previousData) => previousData, // mantém dados anteriores durante refetch
  });
}

/* ---------------------------------------------------------------------------
 * Hook: useUploadDocument
 * --------------------------------------------------------------------------- */

/**
 * Hook para upload de um novo documento.
 *
 * Envia o arquivo via `multipart/form-data` e invalida automaticamente
 * o cache de listagem após sucesso.
 *
 * @returns Mutation do TanStack Query para upload de documento.
 *
 * @example
 * ```tsx
 * const upload = useUploadDocument();
 * upload.mutate({ file: selectedFile, title: 'Petição Inicial' });
 * ```
 */
export function useUploadDocument() {
  const queryClient = useQueryClient();

  return useMutation<UploadDocumentResponse, AxiosError<ApiErrorDetail>, UploadDocumentPayload>({
    mutationFn: async (payload) => {
      const formData = new FormData();
      formData.append('file', payload.file);

      if (payload.title) {
        formData.append('title', payload.title);
      }

      const response = await apiClient.post<UploadDocumentResponse>(
        DOCUMENTS_ENDPOINT,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        },
      );

      return response.data;
    },
    onSuccess: () => {
      // Invalida todas as listagens para refletir o novo documento
      queryClient.invalidateQueries({ queryKey: documentKeys.lists() });
    },
  });
}

/* ---------------------------------------------------------------------------
 * Hook: useDeleteDocument
 * --------------------------------------------------------------------------- */

/**
 * Hook para exclusão de um documento.
 *
 * Remove o documento pelo ID e invalida automaticamente o cache de listagem
 * e o detalhe do documento excluído.
 *
 * @returns Mutation do TanStack Query para exclusão de documento.
 *
 * @example
 * ```tsx
 * const remove = useDeleteDocument();
 * remove.mutate('uuid-do-documento');
 * ```
 */
export function useDeleteDocument() {
  const queryClient = useQueryClient();

  return useMutation<void, AxiosError<ApiErrorDetail>, string>({
    mutationFn: async (documentId) => {
      await apiClient.delete(`${DOCUMENTS_ENDPOINT}/${documentId}`);
    },
    onSuccess: (_data, documentId) => {
      // Invalida listagens para refletir a remoção
      queryClient.invalidateQueries({ queryKey: documentKeys.lists() });
      // Remove o cache de detalhe do documento excluído
      queryClient.removeQueries({ queryKey: documentKeys.detail(documentId) });
    },
  });
}
