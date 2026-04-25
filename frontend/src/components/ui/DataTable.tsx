import React, { useState, useMemo, useCallback } from 'react';

// ============================================================================
// DataTable — Componente de tabela de dados com paginação, sorting e filtros
// Responsivo, tipado e reutilizável para o portal jurídico.
// ============================================================================

/** Direção de ordenação */
type SortDirection = 'asc' | 'desc' | null;

/** Estado de ordenação ativo */
interface SortState {
  columnKey: string;
  direction: SortDirection;
}

/** Definição de uma coluna da tabela */
export interface ColumnDef<T> {
  /** Chave única da coluna (deve corresponder a uma propriedade de T ou ser um id customizado) */
  key: string;
  /** Rótulo exibido no cabeçalho */
  header: string;
  /** Função de renderização customizada para a célula */
  render?: (row: T, rowIndex: number) => React.ReactNode;
  /** Se a coluna é ordenável (padrão: true) */
  sortable?: boolean;
  /** Se a coluna é filtrável (padrão: false) */
  filterable?: boolean;
  /** Placeholder do campo de filtro */
  filterPlaceholder?: string;
  /** Largura customizada (ex: '200px', '20%') */
  width?: string;
  /** Classe CSS adicional para a célula */
  className?: string;
  /** Alinhamento do conteúdo */
  align?: 'left' | 'center' | 'right';
}

/** Opções de paginação */
export interface PaginationOptions {
  /** Página atual (base 1) */
  page: number;
  /** Itens por página */
  pageSize: number;
  /** Total de itens (para paginação server-side) */
  totalItems?: number;
  /** Opções de tamanho de página disponíveis */
  pageSizeOptions?: number[];
}

/** Propriedades do componente DataTable */
export interface DataTableProps<T> {
  /** Dados a serem exibidos */
  data: T[];
  /** Definição das colunas */
  columns: ColumnDef<T>[];
  /** Função para extrair a chave única de cada linha */
  rowKey: (row: T, index: number) => string | number;
  /** Opções de paginação (se omitido, exibe todos os dados) */
  pagination?: PaginationOptions;
  /** Callback quando a paginação muda */
  onPaginationChange?: (page: number, pageSize: number) => void;
  /** Callback quando a ordenação muda (para server-side sorting) */
  onSortChange?: (columnKey: string, direction: SortDirection) => void;
  /** Callback quando os filtros mudam (para server-side filtering) */
  onFilterChange?: (filters: Record<string, string>) => void;
  /** Se a ordenação/filtro é feita no servidor (desabilita client-side) */
  serverSide?: boolean;
  /** Estado de carregamento */
  loading?: boolean;
  /** Mensagem quando não há dados */
  emptyMessage?: string;
  /** Classe CSS adicional para o container */
  className?: string;
  /** Renderizar ações por linha */
  rowActions?: (row: T, rowIndex: number) => React.ReactNode;
  /** Callback ao clicar em uma linha */
  onRowClick?: (row: T, rowIndex: number) => void;
  /** Título da tabela (acessibilidade) */
  caption?: string;
}

/**
 * Ícone de seta para indicar direção de ordenação.
 * Componente interno auxiliar.
 */
function SortIcon({ direction }: { direction: SortDirection }) {
  if (direction === 'asc') {
    return (
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 20 20"
        fill="currentColor"
        className="datatable-sort-icon"
        width={16}
        height={16}
        aria-hidden="true"
      >
        <path
          fillRule="evenodd"
          d="M10 3a.75.75 0 01.55.24l3.25 3.5a.75.75 0 11-1.1 1.02L10 4.852 7.3 7.76a.75.75 0 01-1.1-1.02l3.25-3.5A.75.75 0 0110 3z"
          clipRule="evenodd"
        />
      </svg>
    );
  }
  if (direction === 'desc') {
    return (
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 20 20"
        fill="currentColor"
        className="datatable-sort-icon"
        width={16}
        height={16}
        aria-hidden="true"
      >
        <path
          fillRule="evenodd"
          d="M10 17a.75.75 0 01-.55-.24l-3.25-3.5a.75.75 0 111.1-1.02L10 15.148l2.7-2.908a.75.75 0 111.1 1.02l-3.25 3.5A.75.75 0 0110 17z"
          clipRule="evenodd"
        />
      </svg>
    );
  }
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className="datatable-sort-icon datatable-sort-icon--neutral"
      width={16}
      height={16}
      aria-hidden="true"
      style={{ opacity: 0.3 }}
    >
      <path d="M10 3l3.25 3.5H6.75L10 3zM10 17l-3.25-3.5h6.5L10 17z" />
    </svg>
  );
}

/**
 * DataTable — Componente genérico de tabela de dados.
 *
 * Suporta paginação (client-side e server-side), ordenação por coluna,
 * filtros por coluna, responsividade via scroll horizontal e ações por linha.
 *
 * @example
 * ```tsx
 * <DataTable
 *   data={documentos}
 *   columns={[
 *     { key: 'titulo', header: 'Título', sortable: true, filterable: true },
 *     { key: 'status', header: 'Status', render: (row) => <Badge>{row.status}</Badge> },
 *     { key: 'criadoEm', header: 'Criado em', sortable: true },
 *   ]}
 *   rowKey={(row) => row.id}
 *   pagination={{ page: 1, pageSize: 10 }}
 *   emptyMessage="Nenhum documento encontrado."
 * />
 * ```
 */
export function DataTable<T extends Record<string, unknown>>({
  data,
  columns,
  rowKey,
  pagination,
  onPaginationChange,
  onSortChange,
  onFilterChange,
  serverSide = false,
  loading = false,
  emptyMessage = 'Nenhum registro encontrado.',
  className = '',
  rowActions,
  onRowClick,
  caption,
}: DataTableProps<T>) {
  // -------------------------------------------------------------------------
  // Estado interno
  // -------------------------------------------------------------------------
  const [sortState, setSortState] = useState<SortState | null>(null);
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [internalPage, setInternalPage] = useState<number>(pagination?.page ?? 1);
  const [internalPageSize, setInternalPageSize] = useState<number>(pagination?.pageSize ?? 10);

  // Sincroniza página externa quando controlada
  const currentPage = pagination ? pagination.page : internalPage;
  const currentPageSize = pagination ? pagination.pageSize : internalPageSize;
  const pageSizeOptions = pagination?.pageSizeOptions ?? [5, 10, 20, 50];

  // -------------------------------------------------------------------------
  // Filtros (client-side)
  // -------------------------------------------------------------------------
  const handleFilterChange = useCallback(
    (columnKey: string, value: string) => {
      const newFilters = { ...filters, [columnKey]: value };
      if (!value) {
        delete newFilters[columnKey];
      }
      setFilters(newFilters);
      onFilterChange?.(newFilters);

      // Volta para a primeira página ao filtrar
      if (!pagination) {
        setInternalPage(1);
      } else {
        onPaginationChange?.(1, currentPageSize);
      }
    },
    [filters, onFilterChange, pagination, onPaginationChange, currentPageSize],
  );

  // -------------------------------------------------------------------------
  // Ordenação
  // -------------------------------------------------------------------------
  const handleSort = useCallback(
    (columnKey: string) => {
      let newDirection: SortDirection;

      if (sortState?.columnKey === columnKey) {
        // Ciclo: asc -> desc -> null
        if (sortState.direction === 'asc') {
          newDirection = 'desc';
        } else if (sortState.direction === 'desc') {
          newDirection = null;
        } else {
          newDirection = 'asc';
        }
      } else {
        newDirection = 'asc';
      }

      const newState: SortState | null = newDirection
        ? { columnKey, direction: newDirection }
        : null;

      setSortState(newState);
      onSortChange?.(columnKey, newDirection);
    },
    [sortState, onSortChange],
  );

  // -------------------------------------------------------------------------
  // Dados processados (client-side filtering + sorting + pagination)
  // -------------------------------------------------------------------------
  const processedData = useMemo(() => {
    if (serverSide) {
      return data;
    }

    let result = [...data];

    // Aplicar filtros client-side
    const activeFilters = Object.entries(filters).filter(([, v]) => v.trim() !== '');
    if (activeFilters.length > 0) {
      result = result.filter((row) =>
        activeFilters.every(([key, filterValue]) => {
          const cellValue = row[key];
          if (cellValue == null) return false;
          return String(cellValue)
            .toLowerCase()
            .includes(filterValue.toLowerCase());
        }),
      );
    }

    // Aplicar ordenação client-side
    if (sortState?.direction) {
      const { columnKey, direction } = sortState;
      result.sort((a, b) => {
        const aVal = a[columnKey];
        const bVal = b[columnKey];

        if (aVal == null && bVal == null) return 0;
        if (aVal == null) return direction === 'asc' ? -1 : 1;
        if (bVal == null) return direction === 'asc' ? 1 : -1;

        if (typeof aVal === 'string' && typeof bVal === 'string') {
          const comparison = aVal.localeCompare(bVal, 'pt-BR', { sensitivity: 'base' });
          return direction === 'asc' ? comparison : -comparison;
        }

        if (typeof aVal === 'number' && typeof bVal === 'number') {
          return direction === 'asc' ? aVal - bVal : bVal - aVal;
        }

        // Fallback: comparação por string
        const comparison = String(aVal).localeCompare(String(bVal), 'pt-BR');
        return direction === 'asc' ? comparison : -comparison;
      });
    }

    return result;
  }, [data, filters, sortState, serverSide]);

  // -------------------------------------------------------------------------
  // Paginação
  // -------------------------------------------------------------------------
  const totalItems = serverSide
    ? (pagination?.totalItems ?? data.length)
    : processedData.length;

  const totalPages = Math.max(1, Math.ceil(totalItems / currentPageSize));

  const paginatedData = useMemo(() => {
    if (serverSide) {
      return processedData;
    }
    const start = (currentPage - 1) * currentPageSize;
    return processedData.slice(start, start + currentPageSize);
  }, [processedData, currentPage, currentPageSize, serverSide]);

  const handlePageChange = useCallback(
    (newPage: number) => {
      const clampedPage = Math.max(1, Math.min(newPage, totalPages));
      if (pagination) {
        onPaginationChange?.(clampedPage, currentPageSize);
      } else {
        setInternalPage(clampedPage);
      }
    },
    [totalPages, pagination, onPaginationChange, currentPageSize],
  );

  const handlePageSizeChange = useCallback(
    (newSize: number) => {
      if (pagination) {
        onPaginationChange?.(1, newSize);
      } else {
        setInternalPageSize(newSize);
        setInternalPage(1);
      }
    },
    [pagination, onPaginationChange],
  );

  // -------------------------------------------------------------------------
  // Colunas com ações (se definido)
  // -------------------------------------------------------------------------
  const hasActions = !!rowActions;
  const hasFilterableColumns = columns.some((col) => col.filterable);

  // -------------------------------------------------------------------------
  // Geração de páginas para o paginador
  // -------------------------------------------------------------------------
  const pageNumbers = useMemo(() => {
    const pages: (number | 'ellipsis')[] = [];
    const maxVisible = 5;

    if (totalPages <= maxVisible + 2) {
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      pages.push(1);

      const start = Math.max(2, currentPage - 1);
      const end = Math.min(totalPages - 1, currentPage + 1);

      if (start > 2) {
        pages.push('ellipsis');
      }

      for (let i = start; i <= end; i++) {
        pages.push(i);
      }

      if (end < totalPages - 1) {
        pages.push('ellipsis');
      }

      pages.push(totalPages);
    }

    return pages;
  }, [totalPages, currentPage]);

  // -------------------------------------------------------------------------
  // Estilos inline (para independência de framework CSS)
  // TODO: Migrar para Tailwind CSS classes quando design tokens forem definidos (G005 ADR)
  // -------------------------------------------------------------------------
  const styles = {
    container: {
      width: '100%',
      overflowX: 'auto' as const,
      border: '1px solid #e2e8f0',
      borderRadius: '8px',
      backgroundColor: '#ffffff',
    },
    table: {
      width: '100%',
      borderCollapse: 'collapse' as const,
      fontSize: '14px',
    },
    th: {
      padding: '12px 16px',
      textAlign: 'left' as const,
      fontWeight: 600,
      fontSize: '13px',
      color: '#4a5568',
      backgroundColor: '#f7fafc',
      borderBottom: '2px solid #e2e8f0',
      whiteSpace: 'nowrap' as const,
      userSelect: 'none' as const,
    },
    thSortable: {
      cursor: 'pointer',
    },
    td: {
      padding: '12px 16px',
      borderBottom: '1px solid #edf2f7',
      color: '#2d3748',
    },
    trClickable: {
      cursor: 'pointer',
    },
    trHover: {
      backgroundColor: '#f7fafc',
    },
    filterInput: {
      width: '100%',
      padding: '6px 8px',
      marginTop: '4px',
      fontSize: '12px',
      border: '1px solid #e2e8f0',
      borderRadius: '4px',
      outline: 'none',
    },
    pagination: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '12px 16px',
      borderTop: '1px solid #e2e8f0',
      flexWrap: 'wrap' as const,
      gap: '8px',
      fontSize: '13px',
      color: '#4a5568',
    },
    pageButton: {
      padding: '4px 10px',
      border: '1px solid #e2e8f0',
      borderRadius: '4px',
      backgroundColor: '#ffffff',
      cursor: 'pointer',
      fontSize: '13px',
      color: '#4a5568',
    },
    pageButtonActive: {
      backgroundColor: '#3182ce',
      color: '#ffffff',
      borderColor: '#3182ce',
    },
    pageButtonDisabled: {
      opacity: 0.5,
      cursor: 'not-allowed',
    },
    loadingOverlay: {
      position: 'relative' as const,
      opacity: 0.6,
      pointerEvents: 'none' as const,
    },
    emptyRow: {
      textAlign: 'center' as const,
      padding: '32px 16px',
      color: '#a0aec0',
      fontStyle: 'italic' as const,
    },
    select: {
      padding: '4px 8px',
      border: '1px solid #e2e8f0',
      borderRadius: '4px',
      fontSize: '13px',
      color: '#4a5568',
      backgroundColor: '#ffffff',
    },
  } as const;

  // -------------------------------------------------------------------------
  // Renderização
  // -------------------------------------------------------------------------
  const totalColSpan = columns.length + (hasActions ? 1 : 0);

  return (
    <div
      className={`datatable-container ${className}`}
      style={styles.container}
      role="region"
      aria-label={caption ?? 'Tabela de dados'}
    >
      {loading && (
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'rgba(255,255,255,0.7)',
            zIndex: 10,
            borderRadius: '8px',
          }}
          aria-live="polite"
          aria-busy="true"
        >
          <span>Carregando...</span>
        </div>
      )}

      <div style={loading ? styles.loadingOverlay : { position: 'relative' as const }}>
        <table style={styles.table} aria-label={caption ?? 'Tabela de dados'}>
          {caption && <caption style={{ display: 'none' }}>{caption}</caption>}

          {/* Cabeçalho */}
          <thead>
            <tr>
              {columns.map((col) => {
                const isSortable = col.sortable !== false;
                const isCurrentSort = sortState?.columnKey === col.key;
                const currentDirection = isCurrentSort ? sortState?.direction ?? null : null;

                return (
                  <th
                    key={col.key}
                    style={{
                      ...styles.th,
                      ...(isSortable ? styles.thSortable : {}),
                      width: col.width,
                      textAlign: col.align ?? 'left',
                    }}
                    onClick={isSortable ? () => handleSort(col.key) : undefined}
                    aria-sort={
                      isCurrentSort && currentDirection
                        ? currentDirection === 'asc'
                          ? 'ascending'
                          : 'descending'
                        : 'none'
                    }
                    tabIndex={isSortable ? 0 : undefined}
                    onKeyDown={
                      isSortable
                        ? (e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault();
                              handleSort(col.key);
                            }
                          }
                        : undefined
                    }
                  >
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                        justifyContent: col.align === 'right' ? 'flex-end' : col.align === 'center' ? 'center' : 'flex-start',
                      }}
                    >
                      <span>{col.header}</span>
                      {isSortable && <SortIcon direction={currentDirection} />}
                    </div>
                  </th>
                );
              })}
              {hasActions && (
                <th style={{ ...styles.th, textAlign: 'center', width: '120px' }}>
                  Ações
                </th>
              )}
            </tr>

            {/* Linha de filtros */}
            {hasFilterableColumns && (
              <tr>
                {columns.map((col) => (
                  <th key={`filter-${col.key}`} style={{ padding: '4px 8px', backgroundColor: '#f7fafc' }}>
                    {col.filterable ? (
                      <input
                        type="text"
                        placeholder={col.filterPlaceholder ?? `Filtrar ${col.header.toLowerCase()}...`}
                        value={filters[col.key] ?? ''}
                        onChange={(e) => handleFilterChange(col.key, e.target.value)}
                        style={styles.filterInput}
                        aria-label={`Filtrar por ${col.header}`}
                      />
                    ) : null}
                  </th>
                ))}
                {hasActions && <th style={{ backgroundColor: '#f7fafc' }} />}
              </tr>
            )}
          </thead>

          {/* Corpo */}
          <tbody>
            {paginatedData.length === 0 ? (
              <tr>
                <td colSpan={totalColSpan} style={styles.emptyRow}>
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              paginatedData.map((row, rowIndex) => {
                const key = rowKey(row, rowIndex);
                const globalIndex = (currentPage - 1) * currentPageSize + rowIndex;

                return (
                  <tr
                    key={key}
                    onClick={onRowClick ? () => onRowClick(row, globalIndex) : undefined}
                    style={onRowClick ? styles.trClickable : undefined}
                    onMouseEnter={(e) => {
                      (e.currentTarget as HTMLElement).style.backgroundColor = '#f7fafc';
                    }}
                    onMouseLeave={(e) => {
                      (e.currentTarget as HTMLElement).style.backgroundColor = '';
                    }}
                    tabIndex={onRowClick ? 0 : undefined}
                    onKeyDown={
                      onRowClick
                        ? (e) => {
                            if (e.key === 'Enter') {
                              onRowClick(row, globalIndex);
                            }
                          }
                        : undefined
                    }
                    role={onRowClick ? 'button' : undefined}
                  >
                    {columns.map((col) => (
                      <td
                        key={`${key}-${col.key}`}
                        style={{
                          ...styles.td,
                          textAlign: col.align ?? 'left',
                        }}
                        className={col.className}
                      >
                        {col.render
                          ? col.render(row, globalIndex)
                          : row[col.key] != null
                            ? String(row[col.key])
                            : '—'}
                      </td>
                    ))}
                    {hasActions && (
                      <td style={{ ...styles.td, textAlign: 'center' }}>
                        {rowActions!(row, globalIndex)}
                      </td>
                    )}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Paginação */}
      {pagination !== undefined && (
        <div style={styles.pagination}>
          {/* Info */}
          <div>
            Exibindo{' '}
            <strong>
              {totalItems === 0 ? 0 : (currentPage - 1) * currentPageSize + 1}
            </strong>
            {' '}a{' '}
            <strong>
              {Math.min(currentPage * currentPageSize, totalItems)}
            </strong>
            {' '}de <strong>{totalItems}</strong> registros
          </div>

          {/* Controles de página */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <button
              type="button"
              style={{
                ...styles.pageButton,
                ...(currentPage <= 1 ? styles.pageButtonDisabled : {}),
              }}
              disabled={currentPage <= 1}
              onClick={() => handlePageChange(currentPage - 1)}
              aria-label="Página anterior"
            >
              ‹
            </button>

            {pageNumbers.map((pageNum, idx) =>
              pageNum === 'ellipsis' ? (
                <span key={`ellipsis-${idx}`} style={{ padding: '4px 6px' }}>
                  …
                </span>
              ) : (
                <button
                  key={pageNum}
                  type="button"
                  style={{
                    ...styles.pageButton,
                    ...(pageNum === currentPage ? styles.pageButtonActive : {}),
                  }}
                  onClick={() => handlePageChange(pageNum)}
                  aria-label={`Ir para página ${pageNum}`}
                  aria-current={pageNum === currentPage ? 'page' : undefined}
                >
                  {pageNum}
                </button>
              ),
            )}

            <button
              type="button"
              style={{
                ...styles.pageButton,
                ...(currentPage >= totalPages ? styles.pageButtonDisabled : {}),
              }}
              disabled={currentPage >= totalPages}
              onClick={() => handlePageChange(currentPage + 1)}
              aria-label="Próxima página"
            >
              ›
            </button>
          </div>

          {/* Seletor de tamanho de página */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <label htmlFor="datatable-page-size">Itens por página:</label>
            <select
              id="datatable-page-size"
              value={currentPageSize}
              onChange={(e) => handlePageSizeChange(Number(e.target.value))}
              style={styles.select}
            >
              {pageSizeOptions.map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}
    </div>
  );
}

export default DataTable;
