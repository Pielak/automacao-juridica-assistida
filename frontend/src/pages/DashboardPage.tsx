import React, { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCases } from '../hooks/useCases';
import { useDocuments } from '../hooks/useDocuments';
import { DataTable, type ColumnDef } from '../components/ui/DataTable';
import type { CaseSummary } from '../hooks/useCases';
import type { DocumentSummary } from '../hooks/useDocuments';

// ============================================================================
// DashboardPage — Página principal do portal jurídico
// Exibe resumo de processos, documentos recentes, análises pendentes e KPIs.
// ============================================================================

/* ---------------------------------------------------------------------------
 * Tipos auxiliares
 * --------------------------------------------------------------------------- */

/** Card de KPI exibido no topo do dashboard. */
interface KpiCardProps {
  /** Rótulo descritivo do indicador */
  label: string;
  /** Valor numérico ou textual */
  value: string | number;
  /** Ícone ou emoji representativo */
  icon: string;
  /** Cor de destaque (classes Tailwind) */
  accentClass?: string;
}

/* ---------------------------------------------------------------------------
 * Componentes internos
 * --------------------------------------------------------------------------- */

/**
 * Card individual de KPI.
 * Exibe um indicador-chave de desempenho com ícone, rótulo e valor.
 */
function KpiCard({ label, value, icon, accentClass = 'bg-blue-50 text-blue-700' }: KpiCardProps) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex items-center gap-3">
        <span
          className={`flex h-10 w-10 items-center justify-center rounded-full text-lg ${accentClass}`}
          aria-hidden="true"
        >
          {icon}
        </span>
        <div>
          <p className="text-sm font-medium text-gray-500">{label}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
        </div>
      </div>
    </div>
  );
}

/**
 * Skeleton de carregamento para os cards de KPI.
 */
function KpiSkeleton() {
  return (
    <div className="animate-pulse rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-full bg-gray-200" />
        <div className="space-y-2">
          <div className="h-3 w-20 rounded bg-gray-200" />
          <div className="h-6 w-12 rounded bg-gray-200" />
        </div>
      </div>
    </div>
  );
}

/**
 * Componente de estado vazio para seções sem dados.
 */
function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 bg-gray-50 py-12 text-center">
      <span className="text-4xl" aria-hidden="true">📋</span>
      <p className="mt-2 text-sm text-gray-500">{message}</p>
    </div>
  );
}

/**
 * Componente de estado de erro com opção de retry.
 */
function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
      <span className="text-3xl" aria-hidden="true">⚠️</span>
      <p className="mt-2 text-sm text-red-700">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
        >
          Tentar novamente
        </button>
      )}
    </div>
  );
}

/* ---------------------------------------------------------------------------
 * Definições de colunas para as tabelas
 * --------------------------------------------------------------------------- */

/** Colunas da tabela de casos/processos recentes. */
const caseColumns: ColumnDef<CaseSummary>[] = [
  {
    key: 'title',
    header: 'Título',
    sortable: true,
    render: (row) => (
      <span className="font-medium text-gray-900">{row.title}</span>
    ),
  },
  {
    key: 'status',
    header: 'Status',
    sortable: true,
    render: (row) => <StatusBadge status={row.status} />,
  },
  {
    key: 'description',
    header: 'Descrição',
    sortable: false,
    render: (row) => (
      <span className="line-clamp-1 text-sm text-gray-500">
        {row.description || '—'}
      </span>
    ),
  },
];

/** Colunas da tabela de documentos recentes. */
const documentColumns: ColumnDef<DocumentSummary>[] = [
  {
    key: 'title',
    header: 'Título',
    sortable: true,
    render: (row) => (
      <span className="font-medium text-gray-900">{row.title}</span>
    ),
  },
  {
    key: 'filename',
    header: 'Arquivo',
    sortable: true,
    render: (row) => (
      <span className="text-sm text-gray-600">{row.filename}</span>
    ),
  },
  {
    key: 'status',
    header: 'Status',
    sortable: true,
    render: (row) => <StatusBadge status={row.status} />,
  },
  {
    key: 'size_bytes',
    header: 'Tamanho',
    sortable: true,
    render: (row) => (
      <span className="text-sm text-gray-500">{formatFileSize(row.size_bytes)}</span>
    ),
  },
  {
    key: 'created_at',
    header: 'Criado em',
    sortable: true,
    render: (row) => (
      <span className="text-sm text-gray-500">{formatDate(row.created_at)}</span>
    ),
  },
];

/* ---------------------------------------------------------------------------
 * Utilitários
 * --------------------------------------------------------------------------- */

/**
 * Formata bytes em representação legível (KB, MB, GB).
 * @param bytes - Tamanho em bytes
 */
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  const size = (bytes / Math.pow(1024, i)).toFixed(1);
  return `${size} ${units[i]}`;
}

/**
 * Formata string ISO em data legível pt-BR.
 * @param isoString - Data em formato ISO 8601
 */
function formatDate(isoString: string): string {
  try {
    return new Intl.DateTimeFormat('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(isoString));
  } catch {
    return isoString;
  }
}

/** Mapeamento de status para cores de badge. */
const STATUS_COLORS: Record<string, string> = {
  active: 'bg-green-100 text-green-800',
  ativo: 'bg-green-100 text-green-800',
  pending: 'bg-yellow-100 text-yellow-800',
  pendente: 'bg-yellow-100 text-yellow-800',
  analysis: 'bg-blue-100 text-blue-800',
  analise: 'bg-blue-100 text-blue-800',
  closed: 'bg-gray-100 text-gray-800',
  encerrado: 'bg-gray-100 text-gray-800',
  error: 'bg-red-100 text-red-800',
  erro: 'bg-red-100 text-red-800',
  processing: 'bg-purple-100 text-purple-800',
  processando: 'bg-purple-100 text-purple-800',
  uploaded: 'bg-indigo-100 text-indigo-800',
};

/**
 * Badge visual para status de caso ou documento.
 */
function StatusBadge({ status }: { status: string }) {
  const colorClass = STATUS_COLORS[status.toLowerCase()] ?? 'bg-gray-100 text-gray-800';
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${colorClass}`}
    >
      {status}
    </span>
  );
}

/* ---------------------------------------------------------------------------
 * Componente principal — DashboardPage
 * --------------------------------------------------------------------------- */

/**
 * Página de Dashboard principal do portal jurídico.
 *
 * Exibe:
 * - KPIs resumidos (total de casos, documentos, análises pendentes, etc.)
 * - Tabela de processos/casos recentes
 * - Tabela de documentos recentes
 *
 * Utiliza os hooks `useCases` e `useDocuments` para buscar dados da API.
 */
export default function DashboardPage() {
  const navigate = useNavigate();

  // -------------------------------------------------------------------------
  // Busca de dados
  // -------------------------------------------------------------------------

  // TODO: Os hooks useCases e useDocuments podem expor variantes de listagem
  // (ex.: useCasesList, useDocumentsList). Ajustar chamadas conforme API real.
  const {
    data: casesData,
    isLoading: casesLoading,
    isError: casesError,
    refetch: refetchCases,
  } = useCases();

  const {
    data: documentsData,
    isLoading: documentsLoading,
    isError: documentsError,
    refetch: refetchDocuments,
  } = useDocuments();

  // -------------------------------------------------------------------------
  // Derivação de KPIs
  // -------------------------------------------------------------------------

  const cases: CaseSummary[] = useMemo(() => {
    if (!casesData) return [];
    // TODO: Ajustar conforme shape real da resposta paginada da API
    return Array.isArray(casesData) ? casesData : (casesData as any).items ?? [];
  }, [casesData]);

  const documents: DocumentSummary[] = useMemo(() => {
    if (!documentsData) return [];
    return Array.isArray(documentsData) ? documentsData : (documentsData as any).items ?? [];
  }, [documentsData]);

  const kpis = useMemo(() => {
    const totalCases = cases.length;
    const activeCases = cases.filter(
      (c) => c.status.toLowerCase() === 'active' || c.status.toLowerCase() === 'ativo',
    ).length;
    const pendingAnalysis = cases.filter(
      (c) =>
        c.status.toLowerCase() === 'pending' ||
        c.status.toLowerCase() === 'pendente' ||
        c.status.toLowerCase() === 'analysis' ||
        c.status.toLowerCase() === 'analise',
    ).length;
    const totalDocuments = documents.length;

    return { totalCases, activeCases, pendingAnalysis, totalDocuments };
  }, [cases, documents]);

  // Documentos recentes — últimos 5 ordenados por data de criação
  const recentDocuments = useMemo(() => {
    return [...documents]
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .slice(0, 5);
  }, [documents]);

  // Casos recentes — últimos 5
  const recentCases = useMemo(() => {
    // TODO: Ordenar por updated_at quando disponível no CaseSummary
    return cases.slice(0, 5);
  }, [cases]);

  // -------------------------------------------------------------------------
  // Estado global de carregamento
  // -------------------------------------------------------------------------

  const isLoading = casesLoading || documentsLoading;

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <div className="mx-auto max-w-7xl space-y-8 px-4 py-6 sm:px-6 lg:px-8">
      {/* Cabeçalho */}
      <header>
        <h1 className="text-2xl font-bold tracking-tight text-gray-900 sm:text-3xl">
          Painel de Controle
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Visão geral dos seus processos, documentos e análises.
        </p>
      </header>

      {/* KPIs */}
      <section aria-label="Indicadores-chave de desempenho">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {isLoading ? (
            <>
              <KpiSkeleton />
              <KpiSkeleton />
              <KpiSkeleton />
              <KpiSkeleton />
            </>
          ) : (
            <>
              <KpiCard
                label="Total de Processos"
                value={kpis.totalCases}
                icon="📁"
                accentClass="bg-blue-50 text-blue-700"
              />
              <KpiCard
                label="Processos Ativos"
                value={kpis.activeCases}
                icon="⚡"
                accentClass="bg-green-50 text-green-700"
              />
              <KpiCard
                label="Análises Pendentes"
                value={kpis.pendingAnalysis}
                icon="🔍"
                accentClass="bg-yellow-50 text-yellow-700"
              />
              <KpiCard
                label="Documentos"
                value={kpis.totalDocuments}
                icon="📄"
                accentClass="bg-purple-50 text-purple-700"
              />
            </>
          )}
        </div>
      </section>

      {/* Processos Recentes */}
      <section aria-label="Processos recentes">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Processos Recentes</h2>
          <button
            type="button"
            onClick={() => navigate('/cases')}
            className="text-sm font-medium text-blue-600 hover:text-blue-800 focus:outline-none focus:underline"
          >
            Ver todos →
          </button>
        </div>

        <div className="mt-3">
          {casesError ? (
            <ErrorState
              message="Não foi possível carregar os processos. Verifique sua conexão e tente novamente."
              onRetry={() => refetchCases()}
            />
          ) : casesLoading ? (
            <div className="animate-pulse space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="h-12 rounded bg-gray-100" />
              ))}
            </div>
          ) : recentCases.length === 0 ? (
            <EmptyState message="Nenhum processo encontrado. Crie seu primeiro processo para começar." />
          ) : (
            <DataTable<CaseSummary>
              columns={caseColumns}
              data={recentCases}
              keyExtractor={(row) => row.id}
            />
          )}
        </div>
      </section>

      {/* Documentos Recentes */}
      <section aria-label="Documentos recentes">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Documentos Recentes</h2>
          <button
            type="button"
            onClick={() => navigate('/documents')}
            className="text-sm font-medium text-blue-600 hover:text-blue-800 focus:outline-none focus:underline"
          >
            Ver todos →
          </button>
        </div>

        <div className="mt-3">
          {documentsError ? (
            <ErrorState
              message="Não foi possível carregar os documentos. Verifique sua conexão e tente novamente."
              onRetry={() => refetchDocuments()}
            />
          ) : documentsLoading ? (
            <div className="animate-pulse space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="h-12 rounded bg-gray-100" />
              ))}
            </div>
          ) : recentDocuments.length === 0 ? (
            <EmptyState message="Nenhum documento encontrado. Faça upload do seu primeiro documento." />
          ) : (
            <DataTable<DocumentSummary>
              columns={documentColumns}
              data={recentDocuments}
              keyExtractor={(row) => row.id}
            />
          )}
        </div>
      </section>
    </div>
  );
}
