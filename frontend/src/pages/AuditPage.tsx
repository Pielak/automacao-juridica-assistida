import React, { useState, useCallback, useMemo } from 'react';
import { DataTable } from '@/components/ui/DataTable';
import {
  useAuditLogs,
  useAuditActions,
  type AuditLogLevel,
  type AuditAction,
  type AuditLogEntry,
  type AuditLogFilters,
} from '@/hooks/useAudit';

// ============================================================================
// AuditPage — Página de auditoria (admin)
// Exibe trilha de logs com filtros por usuário, entidade, período e nível.
// ============================================================================

/** Opções de nível de severidade para o filtro. */
const LEVEL_OPTIONS: { label: string; value: AuditLogLevel | '' }[] = [
  { label: 'Todos os níveis', value: '' },
  { label: 'Informação', value: 'info' },
  { label: 'Aviso', value: 'warning' },
  { label: 'Erro', value: 'error' },
  { label: 'Crítico', value: 'critical' },
];

/** Mapeamento de nível para classes de estilo (Tailwind). */
const LEVEL_BADGE_CLASSES: Record<AuditLogLevel, string> = {
  info: 'bg-blue-100 text-blue-800',
  warning: 'bg-yellow-100 text-yellow-800',
  error: 'bg-red-100 text-red-800',
  critical: 'bg-red-200 text-red-900 font-bold',
};

/** Mapeamento de nível para rótulo em PT-BR. */
const LEVEL_LABELS: Record<AuditLogLevel, string> = {
  info: 'Informação',
  warning: 'Aviso',
  error: 'Erro',
  critical: 'Crítico',
};

/** Estado inicial dos filtros. */
const INITIAL_FILTERS: AuditFilterState = {
  userId: '',
  entityType: '',
  entityId: '',
  action: '',
  level: '',
  startDate: '',
  endDate: '',
};

/** Tipagem interna do estado de filtros do formulário. */
interface AuditFilterState {
  userId: string;
  entityType: string;
  entityId: string;
  action: string;
  level: AuditLogLevel | '';
  startDate: string;
  endDate: string;
}

/**
 * Página de auditoria administrativa.
 * Permite visualizar, filtrar e paginar registros de auditoria do sistema.
 */
export default function AuditPage(): React.ReactElement {
  // ---------------------------------------------------------------------------
  // Estado local
  // ---------------------------------------------------------------------------
  const [filters, setFilters] = useState<AuditFilterState>(INITIAL_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<AuditFilterState>(INITIAL_FILTERS);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);

  // ---------------------------------------------------------------------------
  // Query de dados — usa o hook de auditoria
  // ---------------------------------------------------------------------------
  const queryFilters: AuditLogFilters = useMemo(() => {
    const f: AuditLogFilters = {
      page,
      page_size: pageSize,
    };
    if (appliedFilters.userId) f.user_id = appliedFilters.userId;
    if (appliedFilters.entityType) f.entity_type = appliedFilters.entityType;
    if (appliedFilters.entityId) f.entity_id = appliedFilters.entityId;
    if (appliedFilters.action) f.action = appliedFilters.action as AuditAction;
    if (appliedFilters.level) f.level = appliedFilters.level as AuditLogLevel;
    if (appliedFilters.startDate) f.start_date = appliedFilters.startDate;
    if (appliedFilters.endDate) f.end_date = appliedFilters.endDate;
    return f;
  }, [appliedFilters, page, pageSize]);

  const {
    data: auditData,
    isLoading,
    isError,
    error,
    isFetching,
  } = useAuditLogs(queryFilters);

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  /** Atualiza um campo do formulário de filtros. */
  const handleFilterChange = useCallback(
    (field: keyof AuditFilterState) =>
      (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        setFilters((prev) => ({ ...prev, [field]: e.target.value }));
      },
    [],
  );

  /** Aplica os filtros e volta para a primeira página. */
  const handleApplyFilters = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      setPage(1);
      setAppliedFilters({ ...filters });
    },
    [filters],
  );

  /** Limpa todos os filtros. */
  const handleClearFilters = useCallback(() => {
    setFilters(INITIAL_FILTERS);
    setAppliedFilters(INITIAL_FILTERS);
    setPage(1);
  }, []);

  /** Navega para uma página específica. */
  const handlePageChange = useCallback((newPage: number) => {
    setPage(newPage);
  }, []);

  // ---------------------------------------------------------------------------
  // Definição de colunas para o DataTable
  // ---------------------------------------------------------------------------
  const columns = useMemo(
    () => [
      {
        key: 'timestamp',
        header: 'Data/Hora',
        sortable: true,
        render: (entry: AuditLogEntry) => (
          <span className="text-sm text-gray-700 whitespace-nowrap">
            {new Date(entry.timestamp).toLocaleString('pt-BR', {
              dateStyle: 'short',
              timeStyle: 'medium',
            })}
          </span>
        ),
      },
      {
        key: 'level',
        header: 'Nível',
        sortable: true,
        render: (entry: AuditLogEntry) => (
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
              LEVEL_BADGE_CLASSES[entry.level] ?? 'bg-gray-100 text-gray-800'
            }`}
          >
            {LEVEL_LABELS[entry.level] ?? entry.level}
          </span>
        ),
      },
      {
        key: 'action',
        header: 'Ação',
        sortable: true,
        render: (entry: AuditLogEntry) => (
          <span className="text-sm font-mono bg-gray-50 px-1.5 py-0.5 rounded">
            {entry.action}
          </span>
        ),
      },
      {
        key: 'user_id',
        header: 'Usuário',
        sortable: true,
        render: (entry: AuditLogEntry) => (
          <span className="text-sm text-gray-700">
            {entry.user_email ?? entry.user_id ?? '—'}
          </span>
        ),
      },
      {
        key: 'entity_type',
        header: 'Entidade',
        sortable: true,
        render: (entry: AuditLogEntry) => (
          <span className="text-sm text-gray-600">
            {entry.entity_type
              ? `${entry.entity_type}${entry.entity_id ? ` #${entry.entity_id}` : ''}`
              : '—'}
          </span>
        ),
      },
      {
        key: 'description',
        header: 'Descrição',
        sortable: false,
        render: (entry: AuditLogEntry) => (
          <span className="text-sm text-gray-600 max-w-xs truncate block" title={entry.description}>
            {entry.description ?? '—'}
          </span>
        ),
      },
      {
        key: 'ip_address',
        header: 'IP',
        sortable: false,
        render: (entry: AuditLogEntry) => (
          <span className="text-xs font-mono text-gray-500">
            {entry.ip_address ?? '—'}
          </span>
        ),
      },
    ],
    [],
  );

  // ---------------------------------------------------------------------------
  // Cálculos de paginação
  // ---------------------------------------------------------------------------
  const totalItems = auditData?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
  const items: AuditLogEntry[] = auditData?.items ?? [];

  // ---------------------------------------------------------------------------
  // Renderização
  // ---------------------------------------------------------------------------
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Cabeçalho da página */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-2xl font-bold text-gray-900">Trilha de Auditoria</h1>
          <p className="mt-1 text-sm text-gray-500">
            Visualize e filtre os registros de auditoria do sistema.
          </p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6 space-y-6">
        {/* ----------------------------------------------------------------- */}
        {/* Painel de Filtros                                                  */}
        {/* ----------------------------------------------------------------- */}
        <form
          onSubmit={handleApplyFilters}
          className="bg-white rounded-lg shadow-sm border border-gray-200 p-5"
        >
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Filtros</h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Usuário */}
            <div>
              <label htmlFor="filter-userId" className="block text-sm font-medium text-gray-700 mb-1">
                ID do Usuário
              </label>
              <input
                id="filter-userId"
                type="text"
                placeholder="Ex: uuid do usuário"
                value={filters.userId}
                onChange={handleFilterChange('userId')}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              />
            </div>

            {/* Tipo de Entidade */}
            <div>
              <label htmlFor="filter-entityType" className="block text-sm font-medium text-gray-700 mb-1">
                Tipo de Entidade
              </label>
              <input
                id="filter-entityType"
                type="text"
                placeholder="Ex: document, user"
                value={filters.entityType}
                onChange={handleFilterChange('entityType')}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              />
            </div>

            {/* ID da Entidade */}
            <div>
              <label htmlFor="filter-entityId" className="block text-sm font-medium text-gray-700 mb-1">
                ID da Entidade
              </label>
              <input
                id="filter-entityId"
                type="text"
                placeholder="Ex: uuid da entidade"
                value={filters.entityId}
                onChange={handleFilterChange('entityId')}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              />
            </div>

            {/* Ação */}
            <div>
              <label htmlFor="filter-action" className="block text-sm font-medium text-gray-700 mb-1">
                Ação
              </label>
              <input
                id="filter-action"
                type="text"
                placeholder="Ex: login, document_create"
                value={filters.action}
                onChange={handleFilterChange('action')}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              />
            </div>

            {/* Nível */}
            <div>
              <label htmlFor="filter-level" className="block text-sm font-medium text-gray-700 mb-1">
                Nível
              </label>
              <select
                id="filter-level"
                value={filters.level}
                onChange={handleFilterChange('level')}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              >
                {LEVEL_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Data Início */}
            <div>
              <label htmlFor="filter-startDate" className="block text-sm font-medium text-gray-700 mb-1">
                Data Início
              </label>
              <input
                id="filter-startDate"
                type="date"
                value={filters.startDate}
                onChange={handleFilterChange('startDate')}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              />
            </div>

            {/* Data Fim */}
            <div>
              <label htmlFor="filter-endDate" className="block text-sm font-medium text-gray-700 mb-1">
                Data Fim
              </label>
              <input
                id="filter-endDate"
                type="date"
                value={filters.endDate}
                onChange={handleFilterChange('endDate')}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Botões de ação dos filtros */}
          <div className="mt-4 flex items-center gap-3">
            <button
              type="submit"
              className="inline-flex items-center rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
            >
              Aplicar Filtros
            </button>
            <button
              type="button"
              onClick={handleClearFilters}
              className="inline-flex items-center rounded-md bg-white px-4 py-2 text-sm font-medium text-gray-700 border border-gray-300 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
            >
              Limpar Filtros
            </button>
            {isFetching && (
              <span className="text-sm text-gray-400 animate-pulse">Carregando...</span>
            )}
          </div>
        </form>

        {/* ----------------------------------------------------------------- */}
        {/* Indicadores de estado                                              */}
        {/* ----------------------------------------------------------------- */}
        {isError && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
            <strong>Erro ao carregar registros de auditoria.</strong>
            {error instanceof Error && <span className="ml-1">{error.message}</span>}
          </div>
        )}

        {/* ----------------------------------------------------------------- */}
        {/* Resumo e Tabela                                                    */}
        {/* ----------------------------------------------------------------- */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          {/* Barra de resumo */}
          <div className="px-5 py-3 border-b border-gray-200 flex items-center justify-between">
            <span className="text-sm text-gray-600">
              {isLoading
                ? 'Carregando registros...'
                : `${totalItems} registro${totalItems !== 1 ? 's' : ''} encontrado${totalItems !== 1 ? 's' : ''}`}
            </span>
            <span className="text-xs text-gray-400">
              Página {page} de {totalPages}
            </span>
          </div>

          {/* Tabela de dados */}
          {isLoading ? (
            <div className="flex items-center justify-center py-16">
              <div className="flex flex-col items-center gap-2">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600" />
                <span className="text-sm text-gray-500">Carregando registros de auditoria...</span>
              </div>
            </div>
          ) : items.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-gray-400">
              <svg
                className="h-12 w-12 mb-3"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m5.231 13.481L15 17.25m-4.5-15H5.625c-.621 0-1.125.504-1.125 1.125v16.5c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9zm3.75 11.625a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z"
                />
              </svg>
              <p className="text-sm">Nenhum registro de auditoria encontrado.</p>
              <p className="text-xs mt-1">Ajuste os filtros e tente novamente.</p>
            </div>
          ) : (
            <DataTable
              columns={columns}
              data={items}
              // TODO: Verificar se DataTable aceita prop `rowKey` ou similar para chave única — usar entry.id
            />
          )}

          {/* Paginação */}
          {totalPages > 1 && (
            <div className="px-5 py-3 border-t border-gray-200 flex items-center justify-between">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => handlePageChange(page - 1)}
                className="inline-flex items-center rounded-md bg-white px-3 py-1.5 text-sm font-medium text-gray-700 border border-gray-300 shadow-sm hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Anterior
              </button>

              <div className="flex items-center gap-1">
                {generatePageNumbers(page, totalPages).map((p, idx) =>
                  p === '...' ? (
                    <span key={`ellipsis-${idx}`} className="px-2 text-gray-400 text-sm">
                      …
                    </span>
                  ) : (
                    <button
                      key={p}
                      type="button"
                      onClick={() => handlePageChange(p as number)}
                      className={`min-w-[2rem] rounded-md px-2 py-1 text-sm font-medium transition-colors ${
                        p === page
                          ? 'bg-blue-600 text-white'
                          : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      {p}
                    </button>
                  ),
                )}
              </div>

              <button
                type="button"
                disabled={page >= totalPages}
                onClick={() => handlePageChange(page + 1)}
                className="inline-flex items-center rounded-md bg-white px-3 py-1.5 text-sm font-medium text-gray-700 border border-gray-300 shadow-sm hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Próxima
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Utilitários
// =============================================================================

/**
 * Gera uma lista de números de página para exibição na paginação,
 * incluindo reticências quando necessário.
 *
 * @param current - Página atual.
 * @param total - Total de páginas.
 * @returns Array de números de página ou '...' para reticências.
 */
function generatePageNumbers(
  current: number,
  total: number,
): (number | '...')[] {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }

  const pages: (number | '...')[] = [];

  // Sempre mostra a primeira página
  pages.push(1);

  if (current > 3) {
    pages.push('...');
  }

  // Páginas ao redor da atual
  const start = Math.max(2, current - 1);
  const end = Math.min(total - 1, current + 1);

  for (let i = start; i <= end; i++) {
    pages.push(i);
  }

  if (current < total - 2) {
    pages.push('...');
  }

  // Sempre mostra a última página
  pages.push(total);

  return pages;
}
