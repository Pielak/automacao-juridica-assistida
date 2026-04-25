import React, { useState, useCallback } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { Button } from '../components/ui/Button';
import { DataTable, type ColumnDefinition } from '../components/ui/DataTable';
import {
  useAnalysisList,
  useAnalysisDetail,
  useRequestAnalysis,
  type AnalysisSummary,
  type RequestAnalysisPayload,
} from '../hooks/useAnalysis';

// ============================================================================
// AnalysisPage — Página de Análises IA
// Permite solicitar novas análises, visualizar resultados e histórico por caso.
// ============================================================================

/** Mapeamento de status para labels legíveis em PT-BR */
const STATUS_LABELS: Record<string, string> = {
  pending: 'Pendente',
  processing: 'Processando',
  completed: 'Concluída',
  failed: 'Falhou',
};

/** Mapeamento de status para classes CSS de badge */
const STATUS_STYLES: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  processing: 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
};

/**
 * Componente de badge de status da análise.
 * Exibe o status com cores contextuais.
 */
const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const label = STATUS_LABELS[status] ?? status;
  const style = STATUS_STYLES[status] ?? 'bg-gray-100 text-gray-800';

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${style}`}
    >
      {label}
    </span>
  );
};

/**
 * Formulário para solicitar uma nova análise de IA.
 * Coleta o ID do documento (opcional) e tipo de análise.
 */
const RequestAnalysisForm: React.FC<{
  caseId: string;
  onSuccess: () => void;
}> = ({ caseId, onSuccess }) => {
  const [documentId, setDocumentId] = useState('');
  const [analysisType, setAnalysisType] = useState('general');

  const requestAnalysis = useRequestAnalysis();

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();

      const payload: RequestAnalysisPayload = {
        caseId,
        ...(documentId.trim() ? { documentId: documentId.trim() } : {}),
        // TODO: Verificar campos adicionais aceitos pelo payload (analysisType, etc.)
        // quando a interface completa de RequestAnalysisPayload estiver disponível.
      } as RequestAnalysisPayload;

      requestAnalysis.mutate(payload, {
        onSuccess: () => {
          setDocumentId('');
          setAnalysisType('general');
          onSuccess();
        },
      });
    },
    [caseId, documentId, analysisType, requestAnalysis, onSuccess],
  );

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm"
    >
      <h2 className="mb-4 text-lg font-semibold text-gray-900">
        Solicitar Nova Análise
      </h2>

      <div className="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
        {/* ID do Documento (opcional) */}
        <div>
          <label
            htmlFor="documentId"
            className="mb-1 block text-sm font-medium text-gray-700"
          >
            ID do Documento (opcional)
          </label>
          <input
            id="documentId"
            type="text"
            value={documentId}
            onChange={(e) => setDocumentId(e.target.value)}
            placeholder="Ex.: doc-abc-123"
            className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        {/* Tipo de Análise */}
        <div>
          <label
            htmlFor="analysisType"
            className="mb-1 block text-sm font-medium text-gray-700"
          >
            Tipo de Análise
          </label>
          <select
            id="analysisType"
            value={analysisType}
            onChange={(e) => setAnalysisType(e.target.value)}
            className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="general">Análise Geral</option>
            <option value="risk">Análise de Risco</option>
            <option value="summary">Resumo Jurídico</option>
            <option value="precedent">Busca de Precedentes</option>
          </select>
        </div>
      </div>

      {/* Mensagem de erro */}
      {requestAnalysis.isError && (
        <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
          Erro ao solicitar análise. Por favor, tente novamente.
        </div>
      )}

      {/* Mensagem de sucesso */}
      {requestAnalysis.isSuccess && (
        <div className="mb-4 rounded-md bg-green-50 p-3 text-sm text-green-700">
          Análise solicitada com sucesso! Acompanhe o progresso abaixo.
        </div>
      )}

      <Button
        type="submit"
        variant="primary"
        loading={requestAnalysis.isPending}
        disabled={requestAnalysis.isPending}
      >
        Solicitar Análise
      </Button>
    </form>
  );
};

/**
 * Painel de detalhe de uma análise selecionada.
 * Exibe os resultados completos retornados pela IA.
 */
const AnalysisDetailPanel: React.FC<{
  analysisId: string;
  onClose: () => void;
}> = ({ analysisId, onClose }) => {
  const { data: analysis, isLoading, isError } = useAnalysisDetail(analysisId);

  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
          <span className="ml-3 text-sm text-gray-600">
            Carregando detalhes da análise…
          </span>
        </div>
      </div>
    );
  }

  if (isError || !analysis) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6">
        <p className="text-sm text-red-700">
          Não foi possível carregar os detalhes da análise.
        </p>
        <Button variant="secondary" size="sm" onClick={onClose} className="mt-3">
          Fechar
        </Button>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">
          Detalhes da Análise
        </h2>
        <Button variant="secondary" size="sm" onClick={onClose}>
          Fechar
        </Button>
      </div>

      <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div>
          <span className="text-xs font-medium uppercase text-gray-500">
            ID
          </span>
          <p className="text-sm text-gray-900">{analysis.id}</p>
        </div>
        <div>
          <span className="text-xs font-medium uppercase text-gray-500">
            Status
          </span>
          <div className="mt-0.5">
            <StatusBadge status={analysis.status} />
          </div>
        </div>
        <div>
          <span className="text-xs font-medium uppercase text-gray-500">
            Criado em
          </span>
          <p className="text-sm text-gray-900">
            {new Date(analysis.createdAt).toLocaleString('pt-BR')}
          </p>
        </div>
      </div>

      {/* Resultado da análise */}
      {analysis.result && (
        <div className="mt-4">
          <h3 className="mb-2 text-sm font-semibold text-gray-700">
            Resultado
          </h3>
          <div className="max-h-96 overflow-y-auto rounded-md bg-gray-50 p-4 text-sm leading-relaxed text-gray-800 whitespace-pre-wrap">
            {typeof analysis.result === 'string'
              ? analysis.result
              : JSON.stringify(analysis.result, null, 2)}
          </div>
        </div>
      )}

      {/* TODO: Exibir metadados adicionais (tokens consumidos, modelo utilizado, etc.)
         quando a interface AnalysisDetail completa estiver disponível. */}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Definição das colunas da tabela de histórico
// ---------------------------------------------------------------------------

const buildColumns = (
  onSelect: (id: string) => void,
): ColumnDefinition<AnalysisSummary>[] => [
  {
    key: 'id',
    header: 'ID',
    sortable: true,
    render: (row) => (
      <button
        type="button"
        onClick={() => onSelect(row.id)}
        className="text-blue-600 underline hover:text-blue-800"
        title="Ver detalhes da análise"
      >
        {row.id.slice(0, 8)}…
      </button>
    ),
  },
  {
    key: 'status',
    header: 'Status',
    sortable: true,
    render: (row) => <StatusBadge status={row.status} />,
  },
  {
    key: 'createdAt',
    header: 'Data de Criação',
    sortable: true,
    render: (row) => new Date(row.createdAt).toLocaleString('pt-BR'),
  },
  // TODO: Adicionar coluna "Tipo" quando o campo estiver disponível em AnalysisSummary.
];

// ============================================================================
// Componente principal da página
// ============================================================================

/**
 * AnalysisPage — Página principal de análises assistidas por IA.
 *
 * Funcionalidades:
 * - Solicitar nova análise para um caso jurídico
 * - Visualizar histórico de análises do caso
 * - Inspecionar detalhes e resultados de uma análise específica
 *
 * Rota esperada: `/cases/:caseId/analysis`
 */
const AnalysisPage: React.FC = () => {
  // ---------------------------------------------------------------------------
  // Parâmetros de rota e estado local
  // ---------------------------------------------------------------------------
  const { caseId } = useParams<{ caseId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();

  /** ID da análise selecionada para exibição de detalhes */
  const selectedAnalysisId = searchParams.get('analysisId');

  // ---------------------------------------------------------------------------
  // Queries
  // ---------------------------------------------------------------------------
  const {
    data: analysisList,
    isLoading: isListLoading,
    isError: isListError,
    refetch: refetchList,
  } = useAnalysisList(caseId ?? '');

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  /** Seleciona uma análise para exibir detalhes */
  const handleSelectAnalysis = useCallback(
    (analysisId: string) => {
      setSearchParams({ analysisId });
    },
    [setSearchParams],
  );

  /** Fecha o painel de detalhes */
  const handleCloseDetail = useCallback(() => {
    setSearchParams({});
  }, [setSearchParams]);

  /** Callback pós-solicitação de análise com sucesso */
  const handleAnalysisRequested = useCallback(() => {
    refetchList();
  }, [refetchList]);

  // ---------------------------------------------------------------------------
  // Colunas da tabela (memoizadas com base no handler)
  // ---------------------------------------------------------------------------
  const columns = React.useMemo(
    () => buildColumns(handleSelectAnalysis),
    [handleSelectAnalysis],
  );

  // ---------------------------------------------------------------------------
  // Validação de parâmetros
  // ---------------------------------------------------------------------------
  if (!caseId) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8">
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
          <p className="text-sm text-red-700">
            Caso jurídico não identificado. Verifique a URL e tente novamente.
          </p>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      {/* Cabeçalho da página */}
      <header className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          Análises Assistidas por IA
        </h1>
        <p className="mt-1 text-sm text-gray-600">
          Caso: <span className="font-medium text-gray-800">{caseId}</span>
        </p>
      </header>

      {/* Formulário de solicitação */}
      <section className="mb-8">
        <RequestAnalysisForm
          caseId={caseId}
          onSuccess={handleAnalysisRequested}
        />
      </section>

      {/* Painel de detalhes (condicional) */}
      {selectedAnalysisId && (
        <section className="mb-8">
          <AnalysisDetailPanel
            analysisId={selectedAnalysisId}
            onClose={handleCloseDetail}
          />
        </section>
      )}

      {/* Histórico de análises */}
      <section>
        <h2 className="mb-4 text-lg font-semibold text-gray-900">
          Histórico de Análises
        </h2>

        {isListLoading && (
          <div className="flex items-center justify-center py-12">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
            <span className="ml-3 text-sm text-gray-600">
              Carregando histórico…
            </span>
          </div>
        )}

        {isListError && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-6">
            <p className="text-sm text-red-700">
              Erro ao carregar o histórico de análises.
            </p>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => refetchList()}
              className="mt-3"
            >
              Tentar novamente
            </Button>
          </div>
        )}

        {!isListLoading && !isListError && analysisList && (
          <>
            {analysisList.length === 0 ? (
              <div className="rounded-lg border border-gray-200 bg-gray-50 p-8 text-center">
                <p className="text-sm text-gray-600">
                  Nenhuma análise encontrada para este caso. Solicite a primeira
                  análise acima.
                </p>
              </div>
            ) : (
              <DataTable<AnalysisSummary>
                columns={columns}
                data={analysisList}
              />
            )}
          </>
        )}
      </section>
    </div>
  );
};

export default AnalysisPage;
