import { useQuery, keepPreviousData } from '@tanstack/react-query';
import type { UseQueryOptions } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

/* ---------------------------------------------------------------------------
 * Tipos
 * --------------------------------------------------------------------------- */

/** Níveis de severidade possíveis para um registro de auditoria. */
export type AuditLogLevel = 'info' | 'warning' | 'error' | 'critical';

/** Categorias de ação rastreadas pelo sistema de auditoria. */
export type AuditAction =
  | 'login'
  | 'logout'
  | 'create'
  | 'read'
  | 'update'
  | 'delete'
  | 'upload'
  | 'download'
  | 'analysis_request'
  | 'analysis_complete'
  | 'chat_message'
  | 'permission_change'
  | string; // permite extensão futura

/**
 * Representa um único registro de auditoria retornado pela API.
 */
export interface AuditLog {
  /** Identificador único do registro. */
  id: string;
  /** Data/hora em que o evento ocorreu (ISO 8601). */
  timestamp: string;
  /** ID do usuário que realizou a ação. */
  user_id: string;
  /** Nome de exibição do usuário (pode vir populado via join no backend). */
  user_name?: string;
  /** Ação executada. */
  action: AuditAction;
  /** Módulo/recurso afetado (ex.: "documents", "users"). */
  resource: string;
  /** ID do recurso afetado, quando aplicável. */
  resource_id?: string;
  /** Nível de severidade do evento. */
  level: AuditLogLevel;
  /** Endereço IP de origem da requisição. */
  ip_address?: string;
  /** Detalhes adicionais em formato livre. */
  details?: Record<string, unknown>;
}

/**
 * Resposta paginada da API de logs de auditoria.
 */
export interface AuditLogsResponse {
  /** Lista de registros da página atual. */
  items: AuditLog[];
  /** Número total de registros que atendem aos filtros. */
  total: number;
  /** Página atual (base 1). */
  page: number;
  /** Quantidade de itens por página. */
  page_size: number;
  /** Total de páginas disponíveis. */
  total_pages: number;
}

/**
 * Filtros disponíveis para consulta de logs de auditoria.
 */
export interface AuditLogFilters {
  /** Página desejada (base 1). @default 1 */
  page?: number;
  /** Itens por página. @default 20 */
  page_size?: number;
  /** Filtrar por ID de usuário específico. */
  user_id?: string;
  /** Filtrar por tipo de ação. */
  action?: AuditAction;
  /** Filtrar por módulo/recurso. */
  resource?: string;
  /** Filtrar por nível de severidade. */
  level?: AuditLogLevel;
  /** Data/hora inicial do intervalo (ISO 8601). */
  date_from?: string;
  /** Data/hora final do intervalo (ISO 8601). */
  date_to?: string;
  /** Busca textual livre (pesquisa em detalhes, nome de usuário, etc.). */
  search?: string;
  /** Campo para ordenação. @default "timestamp" */
  sort_by?: string;
  /** Direção da ordenação. @default "desc" */
  sort_order?: 'asc' | 'desc';
}

/* ---------------------------------------------------------------------------
 * Constantes
 * --------------------------------------------------------------------------- */

/** Prefixo da query key para invalidação seletiva. */
const AUDIT_QUERY_KEY_PREFIX = 'audit-logs' as const;

/** Endpoint da API de auditoria. */
const AUDIT_ENDPOINT = '/audit/logs';

/** Tempo padrão de stale (5 minutos) — logs de auditoria não mudam com frequência. */
const DEFAULT_STALE_TIME = 5 * 60 * 1000;

/* ---------------------------------------------------------------------------
 * Funções auxiliares
 * --------------------------------------------------------------------------- */

/**
 * Constrói a query key determinística a partir dos filtros fornecidos.
 * Garante que o TanStack Query faça cache e refetch corretamente
 * quando qualquer filtro mudar.
 *
 * @param filters - Filtros ativos para a consulta.
 * @returns Tupla estável para uso como queryKey.
 */
export function buildAuditQueryKey(filters: AuditLogFilters = {}): readonly [string, AuditLogFilters] {
  return [AUDIT_QUERY_KEY_PREFIX, filters] as const;
}

/**
 * Remove chaves com valor `undefined` ou string vazia dos filtros
 * para não enviar query params desnecessários à API.
 */
function cleanParams(filters: AuditLogFilters): Record<string, string | number> {
  const cleaned: Record<string, string | number> = {};

  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== null && value !== '') {
      cleaned[key] = value;
    }
  }

  return cleaned;
}

/**
 * Busca logs de auditoria na API com os filtros e paginação informados.
 *
 * @param filters - Filtros e parâmetros de paginação.
 * @returns Resposta paginada com os logs de auditoria.
 */
async function fetchAuditLogs(filters: AuditLogFilters): Promise<AuditLogsResponse> {
  const params = cleanParams({
    page: filters.page ?? 1,
    page_size: filters.page_size ?? 20,
    sort_by: filters.sort_by ?? 'timestamp',
    sort_order: filters.sort_order ?? 'desc',
    ...filters,
  });

  const response = await apiClient.get<AuditLogsResponse>(AUDIT_ENDPOINT, { params });
  return response.data;
}

/* ---------------------------------------------------------------------------
 * Hooks
 * --------------------------------------------------------------------------- */

/**
 * Hook principal para consulta de logs de auditoria com filtros e paginação.
 *
 * Utiliza `keepPreviousData` para manter os dados da página anterior
 * visíveis enquanto a próxima página é carregada, proporcionando
 * uma experiência de navegação suave.
 *
 * @example
 * ```tsx
 * const { data, isLoading, isError } = useAuditLogs({
 *   page: 1,
 *   page_size: 20,
 *   action: 'login',
 *   date_from: '2024-01-01T00:00:00Z',
 * });
 * ```
 *
 * @param filters - Filtros e paginação desejados.
 * @param options - Opções adicionais do TanStack Query (opcional).
 * @returns Resultado da query com dados paginados de auditoria.
 */
export function useAuditLogs(
  filters: AuditLogFilters = {},
  options?: Partial<UseQueryOptions<AuditLogsResponse, Error>>,
) {
  return useQuery<AuditLogsResponse, Error>({
    queryKey: buildAuditQueryKey(filters),
    queryFn: () => fetchAuditLogs(filters),
    staleTime: DEFAULT_STALE_TIME,
    placeholderData: keepPreviousData,
    retry: 2,
    ...options,
  });
}

/**
 * Hook para buscar um único registro de auditoria pelo ID.
 *
 * @example
 * ```tsx
 * const { data: log } = useAuditLogById('abc-123');
 * ```
 *
 * @param logId - ID do registro de auditoria.
 * @param options - Opções adicionais do TanStack Query (opcional).
 * @returns Resultado da query com o registro individual.
 */
export function useAuditLogById(
  logId: string | undefined,
  options?: Partial<UseQueryOptions<AuditLog, Error>>,
) {
  return useQuery<AuditLog, Error>({
    queryKey: [AUDIT_QUERY_KEY_PREFIX, 'detail', logId] as const,
    queryFn: async () => {
      const response = await apiClient.get<AuditLog>(`${AUDIT_ENDPOINT}/${logId}`);
      return response.data;
    },
    enabled: !!logId,
    staleTime: DEFAULT_STALE_TIME,
    retry: 2,
    ...options,
  });
}

/**
 * Hook para obter as opções de filtro disponíveis (valores distintos de
 * action, resource, level, etc.) para popular dropdowns de filtro na UI.
 *
 * @example
 * ```tsx
 * const { data: filterOptions } = useAuditFilterOptions();
 * // filterOptions?.actions → ['login', 'logout', 'create', ...]
 * ```
 *
 * @param options - Opções adicionais do TanStack Query (opcional).
 * @returns Resultado da query com as opções de filtro.
 */
export interface AuditFilterOptions {
  /** Ações distintas registradas. */
  actions: AuditAction[];
  /** Recursos/módulos distintos registrados. */
  resources: string[];
  /** Níveis de severidade disponíveis. */
  levels: AuditLogLevel[];
}

export function useAuditFilterOptions(
  options?: Partial<UseQueryOptions<AuditFilterOptions, Error>>,
) {
  return useQuery<AuditFilterOptions, Error>({
    queryKey: [AUDIT_QUERY_KEY_PREFIX, 'filter-options'] as const,
    queryFn: async () => {
      // TODO: Confirmar endpoint exato com o backend. Assumindo GET /audit/logs/filter-options
      const response = await apiClient.get<AuditFilterOptions>(
        `${AUDIT_ENDPOINT}/filter-options`,
      );
      return response.data;
    },
    staleTime: 10 * 60 * 1000, // 10 minutos — opções mudam raramente
    retry: 1,
    ...options,
  });
}
