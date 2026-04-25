import React, { useState, useCallback, useMemo } from 'react';
import { FileUpload } from '../components/ui/FileUpload';
import { DataTable, type ColumnDefinition } from '../components/ui/DataTable';
import {
  useDocuments,
  useUploadDocument,
  useDeleteDocument,
  useDownloadDocument,
  type DocumentSummary,
} from '../hooks/useDocuments';

// ============================================================================
// DocumentsPage — Página principal de gestão de documentos jurídicos
// Permite upload, listagem por caso, preview, download e exclusão.
// ============================================================================

/** Status visuais mapeados para badges coloridos */
const STATUS_LABELS: Record<string, { label: string; className: string }> = {
  pending: { label: 'Pendente', className: 'bg-yellow-100 text-yellow-800' },
  processing: { label: 'Processando', className: 'bg-blue-100 text-blue-800' },
  completed: { label: 'Concluído', className: 'bg-green-100 text-green-800' },
  error: { label: 'Erro', className: 'bg-red-100 text-red-800' },
  archived: { label: 'Arquivado', className: 'bg-gray-100 text-gray-600' },
};

/**
 * Formata bytes em unidade legível (KB, MB, GB).
 * @param bytes - Tamanho em bytes
 * @returns String formatada, ex: "2.5 MB"
 */
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  const size = bytes / Math.pow(1024, i);
  return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

/**
 * Formata data ISO em formato brasileiro dd/mm/aaaa HH:mm.
 * @param isoDate - String de data ISO 8601
 * @returns Data formatada em pt-BR
 */
function formatDate(isoDate: string): string {
  try {
    return new Intl.DateTimeFormat('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(isoDate));
  } catch {
    return isoDate;
  }
}

/** Tipos MIME que suportam preview inline */
const PREVIEWABLE_TYPES = new Set([
  'application/pdf',
  'image/png',
  'image/jpeg',
]);

/**
 * Componente de badge de status do documento.
 */
function StatusBadge({ status }: { status: string }) {
  const config = STATUS_LABELS[status] ?? {
    label: status,
    className: 'bg-gray-100 text-gray-800',
  };
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${config.className}`}
    >
      {config.label}
    </span>
  );
}

/**
 * Modal simples de preview de documento.
 */
function PreviewModal({
  document,
  previewUrl,
  onClose,
}: {
  document: DocumentSummary;
  previewUrl: string;
  onClose: () => void;
}) {
  const isImage = document.mime_type.startsWith('image/');
  const isPdf = document.mime_type === 'application/pdf';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={`Preview de ${document.title}`}
    >
      <div
        className="relative max-h-[90vh] w-full max-w-4xl overflow-auto rounded-lg bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Cabeçalho */}
        <div className="flex items-center justify-between border-b px-6 py-4">
          <h3 className="text-lg font-semibold text-gray-900 truncate">
            {document.title}
          </h3>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
            aria-label="Fechar preview"
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Conteúdo */}
        <div className="p-6">
          {isPdf && (
            <iframe
              src={previewUrl}
              title={`Preview: ${document.title}`}
              className="h-[70vh] w-full rounded border"
            />
          )}
          {isImage && (
            <img
              src={previewUrl}
              alt={document.title}
              className="mx-auto max-h-[70vh] rounded object-contain"
            />
          )}
          {!isPdf && !isImage && (
            <div className="flex flex-col items-center justify-center py-12 text-gray-500">
              <svg className="mb-4 h-16 w-16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p>Preview não disponível para este tipo de arquivo.</p>
              <p className="text-sm text-gray-400 mt-1">{document.mime_type}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Modal de confirmação de exclusão.
 */
function DeleteConfirmModal({
  document,
  onConfirm,
  onCancel,
  isDeleting,
}: {
  document: DocumentSummary;
  onConfirm: () => void;
  onCancel: () => void;
  isDeleting: boolean;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onCancel}
      role="dialog"
      aria-modal="true"
      aria-label="Confirmar exclusão"
    >
      <div
        className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-red-100">
            <svg className="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900">Confirmar exclusão</h3>
        </div>

        <p className="mb-2 text-gray-600">
          Tem certeza que deseja excluir o documento?
        </p>
        <p className="mb-6 rounded bg-gray-50 px-3 py-2 text-sm font-medium text-gray-800">
          {document.title} ({document.filename})
        </p>

        <div className="flex justify-end gap-3">
          <button
            onClick={onCancel}
            disabled={isDeleting}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            Cancelar
          </button>
          <button
            onClick={onConfirm}
            disabled={isDeleting}
            className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 transition-colors disabled:opacity-50"
          >
            {isDeleting ? 'Excluindo...' : 'Excluir'}
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * DocumentsPage — Página principal de gestão de documentos.
 *
 * Funcionalidades:
 * - Upload de documentos jurídicos (PDF, DOC, DOCX, imagens)
 * - Listagem com paginação, ordenação e filtro por caso
 * - Preview inline para PDFs e imagens
 * - Download de documentos
 * - Exclusão com confirmação
 *
 * @returns Componente React da página de documentos
 */
export default function DocumentsPage() {
  // ---------------------------------------------------------------------------
  // Estado local
  // ---------------------------------------------------------------------------
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [caseFilter, setCaseFilter] = useState<string>('');
  const [previewDoc, setPreviewDoc] = useState<DocumentSummary | null>(null);
  const [deleteDoc, setDeleteDoc] = useState<DocumentSummary | null>(null);
  const [notification, setNotification] = useState<{
    type: 'success' | 'error';
    message: string;
  } | null>(null);

  // ---------------------------------------------------------------------------
  // Hooks de dados (peers)
  // ---------------------------------------------------------------------------
  const {
    data: documents,
    isLoading,
    isError,
    error,
    refetch,
  } = useDocuments({ caseId: caseFilter || undefined });

  const uploadMutation = useUploadDocument();
  const deleteMutation = useDeleteDocument();
  const downloadMutation = useDownloadDocument();

  // ---------------------------------------------------------------------------
  // Notificação temporária
  // ---------------------------------------------------------------------------
  const showNotification = useCallback(
    (type: 'success' | 'error', message: string) => {
      setNotification({ type, message });
      setTimeout(() => setNotification(null), 5000);
    },
    [],
  );

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  /** Callback de upload de arquivos vindo do FileUpload */
  const handleFilesAccepted = useCallback(
    (files: File[]) => {
      files.forEach((file) => {
        uploadMutation.mutate(
          { file, caseId: caseFilter || undefined },
          {
            onSuccess: () => {
              showNotification('success', `"${file.name}" enviado com sucesso.`);
              refetch();
            },
            onError: (err) => {
              const message =
                (err as Error)?.message ?? 'Erro desconhecido ao enviar arquivo.';
              showNotification('error', `Falha ao enviar "${file.name}": ${message}`);
            },
          },
        );
      });
      setIsUploadOpen(false);
    },
    [uploadMutation, caseFilter, showNotification, refetch],
  );

  /** Inicia download de um documento */
  const handleDownload = useCallback(
    (doc: DocumentSummary) => {
      downloadMutation.mutate(
        { documentId: doc.id, filename: doc.filename },
        {
          onError: () => {
            showNotification('error', `Falha ao baixar "${doc.filename}".`);
          },
        },
      );
    },
    [downloadMutation, showNotification],
  );

  /** Confirma exclusão de documento */
  const handleDeleteConfirm = useCallback(() => {
    if (!deleteDoc) return;
    deleteMutation.mutate(
      { documentId: deleteDoc.id },
      {
        onSuccess: () => {
          showNotification('success', `"${deleteDoc.filename}" excluído com sucesso.`);
          setDeleteDoc(null);
          refetch();
        },
        onError: () => {
          showNotification('error', `Falha ao excluir "${deleteDoc.filename}".`);
          setDeleteDoc(null);
        },
      },
    );
  }, [deleteDoc, deleteMutation, showNotification, refetch]);

  /** Abre preview se o tipo for suportado */
  const handlePreview = useCallback((doc: DocumentSummary) => {
    if (PREVIEWABLE_TYPES.has(doc.mime_type)) {
      setPreviewDoc(doc);
    }
  }, []);

  // ---------------------------------------------------------------------------
  // Definição de colunas da DataTable
  // ---------------------------------------------------------------------------
  const columns: ColumnDefinition<DocumentSummary>[] = useMemo(
    () => [
      {
        key: 'title',
        header: 'Título',
        sortable: true,
        render: (doc) => (
          <div className="min-w-0">
            <p className="truncate font-medium text-gray-900" title={doc.title}>
              {doc.title}
            </p>
            <p className="truncate text-xs text-gray-500" title={doc.filename}>
              {doc.filename}
            </p>
          </div>
        ),
      },
      {
        key: 'mime_type',
        header: 'Tipo',
        sortable: true,
        render: (doc) => {
          const ext = doc.filename.split('.').pop()?.toUpperCase() ?? doc.mime_type;
          return <span className="text-sm text-gray-600">{ext}</span>;
        },
      },
      {
        key: 'size_bytes',
        header: 'Tamanho',
        sortable: true,
        render: (doc) => (
          <span className="text-sm text-gray-600">{formatFileSize(doc.size_bytes)}</span>
        ),
      },
      {
        key: 'status',
        header: 'Status',
        sortable: true,
        render: (doc) => <StatusBadge status={doc.status} />,
      },
      {
        key: 'created_at',
        header: 'Criado em',
        sortable: true,
        render: (doc) => (
          <span className="text-sm text-gray-600">{formatDate(doc.created_at)}</span>
        ),
      },
      {
        key: 'actions' as keyof DocumentSummary,
        header: 'Ações',
        sortable: false,
        render: (doc) => (
          <div className="flex items-center gap-1">
            {/* Preview */}
            {PREVIEWABLE_TYPES.has(doc.mime_type) && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handlePreview(doc);
                }}
                className="rounded p-1.5 text-gray-500 hover:bg-gray-100 hover:text-blue-600 transition-colors"
                title="Visualizar documento"
                aria-label={`Visualizar ${doc.title}`}
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
              </button>
            )}

            {/* Download */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleDownload(doc);
              }}
              className="rounded p-1.5 text-gray-500 hover:bg-gray-100 hover:text-green-600 transition-colors"
              title="Baixar documento"
              aria-label={`Baixar ${doc.title}`}
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
            </button>

            {/* Excluir */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                setDeleteDoc(doc);
              }}
              className="rounded p-1.5 text-gray-500 hover:bg-red-50 hover:text-red-600 transition-colors"
              title="Excluir documento"
              aria-label={`Excluir ${doc.title}`}
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        ),
      },
    ],
    [handlePreview, handleDownload],
  );

  // ---------------------------------------------------------------------------
  // URL de preview (construída a partir do ID do documento)
  // ---------------------------------------------------------------------------
  // TODO: Ajustar a URL de preview conforme endpoint real da API (ex: /api/documents/:id/preview)
  const previewUrl = previewDoc
    ? `/api/documents/${previewDoc.id}/preview`
    : '';

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      {/* Notificação flutuante */}
      {notification && (
        <div
          className={`fixed right-4 top-4 z-50 max-w-sm rounded-lg p-4 shadow-lg transition-all ${
            notification.type === 'success'
              ? 'bg-green-50 text-green-800 border border-green-200'
              : 'bg-red-50 text-red-800 border border-red-200'
          }`}
          role="alert"
        >
          <div className="flex items-start gap-3">
            <span className="text-sm font-medium">{notification.message}</span>
            <button
              onClick={() => setNotification(null)}
              className="ml-auto -mr-1 -mt-1 rounded p-1 hover:bg-black/5"
              aria-label="Fechar notificação"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* Cabeçalho da página */}
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Documentos</h1>
          <p className="mt-1 text-sm text-gray-500">
            Gerencie os documentos jurídicos do sistema.
          </p>
        </div>
        <button
          onClick={() => setIsUploadOpen(true)}
          className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Enviar documento
        </button>
      </div>

      {/* Filtro por caso */}
      <div className="mb-6 flex flex-col gap-4 rounded-lg border border-gray-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center">
        <label
          htmlFor="case-filter"
          className="text-sm font-medium text-gray-700 whitespace-nowrap"
        >
          Filtrar por caso:
        </label>
        <input
          id="case-filter"
          type="text"
          value={caseFilter}
          onChange={(e) => setCaseFilter(e.target.value)}
          placeholder="Digite o ID ou número do caso..."
          className="w-full max-w-md rounded-md border border-gray-300 px-3 py-2 text-sm placeholder-gray-400 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        {caseFilter && (
          <button
            onClick={() => setCaseFilter('')}
            className="text-sm text-blue-600 hover:text-blue-800 transition-colors"
          >
            Limpar filtro
          </button>
        )}
      </div>

      {/* Área de upload (colapsável) */}
      {isUploadOpen && (
        <div className="mb-6 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">Enviar documentos</h2>
            <button
              onClick={() => setIsUploadOpen(false)}
              className="rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
              aria-label="Fechar área de upload"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <FileUpload
            onFilesAccepted={handleFilesAccepted}
            multiple={true}
            disabled={uploadMutation.isPending}
          />
          {uploadMutation.isPending && (
            <div className="mt-4 flex items-center gap-2 text-sm text-blue-600">
              <svg
                className="h-4 w-4 animate-spin"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
              Enviando arquivo(s)...
            </div>
          )}
        </div>
      )}

      {/* Estado de carregamento */}
      {isLoading && (
        <div className="flex items-center justify-center py-16">
          <div className="flex flex-col items-center gap-3">
            <svg
              className="h-8 w-8 animate-spin text-blue-600"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
            <p className="text-sm text-gray-500">Carregando documentos...</p>
          </div>
        </div>
      )}

      {/* Estado de erro */}
      {isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
          <svg
            className="mx-auto mb-3 h-10 w-10 text-red-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"
            />
          </svg>
          <p className="mb-2 font-medium text-red-800">
            Erro ao carregar documentos
          </p>
          <p className="mb-4 text-sm text-red-600">
            {(error as Error)?.message ?? 'Ocorreu um erro inesperado.'}
          </p>
          <button
            onClick={() => refetch()}
            className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 transition-colors"
          >
            Tentar novamente
          </button>
        </div>
      )}

      {/* Tabela de documentos */}
      {!isLoading && !isError && documents && (
        <>
          {documents.length === 0 ? (
            <div className="rounded-lg border border-gray-200 bg-white py-16 text-center">
              <svg
                className="mx-auto mb-4 h-12 w-12 text-gray-300"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              <p className="mb-1 text-lg font-medium text-gray-900">
                Nenhum documento encontrado
              </p>
              <p className="mb-6 text-sm text-gray-500">
                {caseFilter
                  ? 'Nenhum documento encontrado para este caso. Tente outro filtro.'
                  : 'Comece enviando seu primeiro documento jurídico.'}
              </p>
              {!caseFilter && (
                <button
                  onClick={() => setIsUploadOpen(true)}
                  className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  Enviar documento
                </button>
              )}
            </div>
          ) : (
            <div className="rounded-lg border border-gray-200 bg-white shadow-sm overflow-hidden">
              <DataTable<DocumentSummary>
                columns={columns}
                data={documents}
                keyExtractor={(doc) => doc.id}
                onRowClick={handlePreview}
                emptyMessage="Nenhum documento encontrado."
              />
            </div>
          )}
        </>
      )}

      {/* Modal de preview */}
      {previewDoc && (
        <PreviewModal
          document={previewDoc}
          previewUrl={previewUrl}
          onClose={() => setPreviewDoc(null)}
        />
      )}

      {/* Modal de confirmação de exclusão */}
      {deleteDoc && (
        <DeleteConfirmModal
          document={deleteDoc}
          onConfirm={handleDeleteConfirm}
          onCancel={() => setDeleteDoc(null)}
          isDeleting={deleteMutation.isPending}
        />
      )}
    </div>
  );
}