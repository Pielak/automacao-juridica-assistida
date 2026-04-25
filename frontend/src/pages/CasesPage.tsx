import React, { useState, useCallback, useMemo } from 'react';
import {
  useCases,
  useCreateCase,
  useUpdateCase,
  useDeleteCase,
  type CaseSummary,
  type CreateCasePayload,
  type UpdateCasePayload,
} from '../hooks/useCases';
import { DataTable, type ColumnDefinition } from '../components/ui/DataTable';
import { Modal } from '../components/ui/Modal';
import { Button } from '../components/ui/Button';

// ============================================================================
// CasesPage — Página principal de gestão de processos jurídicos
// Funcionalidades: listagem com filtros (tribunal, status), criação, edição,
// visualização de detalhes e exclusão de casos.
// ============================================================================

/** Opções de status disponíveis para filtragem */
const STATUS_OPTIONS: { label: string; value: string }[] = [
  { label: 'Todos', value: '' },
  { label: 'Ativo', value: 'active' },
  { label: 'Arquivado', value: 'archived' },
  { label: 'Em andamento', value: 'in_progress' },
  { label: 'Concluído', value: 'concluded' },
  { label: 'Suspenso', value: 'suspended' },
];

/** Opções de tribunal disponíveis para filtragem */
const COURT_OPTIONS: { label: string; value: string }[] = [
  { label: 'Todos', value: '' },
  { label: 'STF', value: 'STF' },
  { label: 'STJ', value: 'STJ' },
  { label: 'TRF-1', value: 'TRF-1' },
  { label: 'TRF-2', value: 'TRF-2' },
  { label: 'TRF-3', value: 'TRF-3' },
  { label: 'TRF-4', value: 'TRF-4' },
  { label: 'TRF-5', value: 'TRF-5' },
  { label: 'TJSP', value: 'TJSP' },
  { label: 'TJRJ', value: 'TJRJ' },
  { label: 'TJMG', value: 'TJMG' },
  // TODO: Carregar lista completa de tribunais via endpoint /api/courts
];

/** Estado do formulário de criação/edição de caso */
interface CaseFormState {
  title: string;
  description: string;
  court: string;
  clientName: string;
  caseNumber: string;
}

/** Estado inicial do formulário */
const INITIAL_FORM_STATE: CaseFormState = {
  title: '',
  description: '',
  court: '',
  clientName: '',
  caseNumber: '',
};

/**
 * Página de processos jurídicos.
 * Exibe listagem paginada com filtros por tribunal e status,
 * permite operações CRUD e visualização de detalhes.
 */
export const CasesPage: React.FC = () => {
  // ---------------------------------------------------------------------------
  // Estado de filtros
  // ---------------------------------------------------------------------------
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [courtFilter, setCourtFilter] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [page, setPage] = useState<number>(1);
  const pageSize = 20;

  // ---------------------------------------------------------------------------
  // Estado de modais
  // ---------------------------------------------------------------------------
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [selectedCase, setSelectedCase] = useState<CaseSummary | null>(null);
  const [formState, setFormState] = useState<CaseFormState>(INITIAL_FORM_STATE);
  const [formErrors, setFormErrors] = useState<Partial<Record<keyof CaseFormState, string>>>({});

  // ---------------------------------------------------------------------------
  // Queries e mutations (hooks do domínio)
  // ---------------------------------------------------------------------------
  const casesQuery = useCases({
    status: statusFilter || undefined,
    court: courtFilter || undefined,
    search: searchTerm || undefined,
    page,
    pageSize,
  });

  const createMutation = useCreateCase();
  const updateMutation = useUpdateCase();
  const deleteMutation = useDeleteCase();

  // ---------------------------------------------------------------------------
  // Definição de colunas da tabela
  // ---------------------------------------------------------------------------
  const columns: ColumnDefinition<CaseSummary>[] = useMemo(
    () => [
      {
        key: 'caseNumber',
        header: 'Nº do Processo',
        sortable: true,
        render: (row: CaseSummary) => (
          <span className="font-mono text-sm">{row.caseNumber ?? '—'}</span>
        ),
      },
      {
        key: 'title',
        header: 'Título',
        sortable: true,
        render: (row: CaseSummary) => (
          <button
            type="button"
            className="text-blue-700 underline hover:text-blue-900 text-left"
            onClick={() => handleOpenDetail(row)}
            aria-label={`Ver detalhes do caso ${row.title}`}
          >
            {row.title}
          </button>
        ),
      },
      {
        key: 'clientName',
        header: 'Cliente',
        sortable: true,
        render: (row: CaseSummary) => row.clientName ?? '—',
      },
      {
        key: 'court',
        header: 'Tribunal',
        sortable: true,
        render: (row: CaseSummary) => row.court ?? '—',
      },
      {
        key: 'status',
        header: 'Status',
        sortable: true,
        render: (row: CaseSummary) => <StatusBadge status={row.status} />,
      },
      {
        key: 'createdAt',
        header: 'Criado em',
        sortable: true,
        render: (row: CaseSummary) => formatDate(row.createdAt),
      },
      {
        key: 'actions',
        header: 'Ações',
        sortable: false,
        render: (row: CaseSummary) => (
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => handleOpenEdit(row)}
              aria-label={`Editar caso ${row.title}`}
            >
              Editar
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={() => handleOpenDelete(row)}
              aria-label={`Excluir caso ${row.title}`}
            >
              Excluir
            </Button>
          </div>
        ),
      },
    ],
    [],
  );

  // ---------------------------------------------------------------------------
  // Handlers de modal
  // ---------------------------------------------------------------------------

  /** Abre modal de criação com formulário limpo */
  const handleOpenCreate = useCallback(() => {
    setFormState(INITIAL_FORM_STATE);
    setFormErrors({});
    setIsCreateModalOpen(true);
  }, []);

  /** Abre modal de edição preenchendo o formulário com dados do caso */
  const handleOpenEdit = useCallback((caseItem: CaseSummary) => {
    setSelectedCase(caseItem);
    setFormState({
      title: caseItem.title,
      description: caseItem.description ?? '',
      court: caseItem.court ?? '',
      clientName: caseItem.clientName ?? '',
      caseNumber: caseItem.caseNumber ?? '',
    });
    setFormErrors({});
    setIsEditModalOpen(true);
  }, []);

  /** Abre modal de detalhes */
  const handleOpenDetail = useCallback((caseItem: CaseSummary) => {
    setSelectedCase(caseItem);
    setIsDetailModalOpen(true);
  }, []);

  /** Abre modal de confirmação de exclusão */
  const handleOpenDelete = useCallback((caseItem: CaseSummary) => {
    setSelectedCase(caseItem);
    setIsDeleteModalOpen(true);
  }, []);

  // ---------------------------------------------------------------------------
  // Validação do formulário
  // ---------------------------------------------------------------------------
  const validateForm = useCallback((): boolean => {
    const errors: Partial<Record<keyof CaseFormState, string>> = {};

    if (!formState.title.trim()) {
      errors.title = 'O título é obrigatório.';
    } else if (formState.title.trim().length < 3) {
      errors.title = 'O título deve ter pelo menos 3 caracteres.';
    }

    if (!formState.description.trim()) {
      errors.description = 'A descrição é obrigatória.';
    }

    if (!formState.clientName.trim()) {
      errors.clientName = 'O nome do cliente é obrigatório.';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  }, [formState]);

  // ---------------------------------------------------------------------------
  // Handlers de submit
  // ---------------------------------------------------------------------------

  /** Submete criação de novo caso */
  const handleCreateSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!validateForm()) return;

      const payload: CreateCasePayload = {
        title: formState.title.trim(),
        description: formState.description.trim(),
        court: formState.court || undefined,
        clientName: formState.clientName.trim(),
        caseNumber: formState.caseNumber.trim() || undefined,
      };

      createMutation.mutate(payload, {
        onSuccess: () => {
          setIsCreateModalOpen(false);
          setFormState(INITIAL_FORM_STATE);
        },
      });
    },
    [formState, validateForm, createMutation],
  );

  /** Submete atualização de caso existente */
  const handleEditSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!selectedCase || !validateForm()) return;

      const payload: UpdateCasePayload = {
        id: selectedCase.id,
        title: formState.title.trim(),
        description: formState.description.trim(),
        court: formState.court || undefined,
        clientName: formState.clientName.trim(),
        caseNumber: formState.caseNumber.trim() || undefined,
      };

      updateMutation.mutate(payload, {
        onSuccess: () => {
          setIsEditModalOpen(false);
          setSelectedCase(null);
        },
      });
    },
    [formState, selectedCase, validateForm, updateMutation],
  );

  /** Confirma exclusão de caso */
  const handleDeleteConfirm = useCallback(() => {
    if (!selectedCase) return;

    deleteMutation.mutate(selectedCase.id, {
      onSuccess: () => {
        setIsDeleteModalOpen(false);
        setSelectedCase(null);
      },
    });
  }, [selectedCase, deleteMutation]);

  // ---------------------------------------------------------------------------
  // Handler genérico de campo do formulário
  // ---------------------------------------------------------------------------
  const handleFieldChange = useCallback(
    (field: keyof CaseFormState) =>
      (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
        setFormState((prev) => ({ ...prev, [field]: e.target.value }));
        // Limpa erro do campo ao digitar
        setFormErrors((prev) => ({ ...prev, [field]: undefined }));
      },
    [],
  );

  // ---------------------------------------------------------------------------
  // Handlers de filtro
  // ---------------------------------------------------------------------------
  const handleStatusFilterChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      setStatusFilter(e.target.value);
      setPage(1);
    },
    [],
  );

  const handleCourtFilterChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      setCourtFilter(e.target.value);
      setPage(1);
    },
    [],
  );

  const handleSearchChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setSearchTerm(e.target.value);
      setPage(1);
    },
    [],
  );

  const handleClearFilters = useCallback(() => {
    setStatusFilter('');
    setCourtFilter('');
    setSearchTerm('');
    setPage(1);
  }, []);

  // ---------------------------------------------------------------------------
  // Dados da tabela
  // ---------------------------------------------------------------------------
  const cases: CaseSummary[] = casesQuery.data?.items ?? [];
  const totalItems = casesQuery.data?.total ?? 0;
  const isLoading = casesQuery.isLoading;
  const isError = casesQuery.isError;

  const hasActiveFilters = statusFilter || courtFilter || searchTerm;

  // ---------------------------------------------------------------------------
  // Renderização
  // ---------------------------------------------------------------------------
  return (
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      {/* Cabeçalho da página */}
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Processos</h1>
          <p className="mt-1 text-sm text-gray-600">
            Gerencie seus processos jurídicos, aplique filtros e acompanhe o andamento.
          </p>
        </div>
        <Button variant="primary" size="md" onClick={handleOpenCreate}>
          + Novo Processo
        </Button>
      </div>

      {/* Barra de filtros */}
      <section
        aria-label="Filtros de processos"
        className="mb-6 rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
      >
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {/* Busca textual */}
          <div>
            <label htmlFor="search" className="mb-1 block text-sm font-medium text-gray-700">
              Buscar
            </label>
            <input
              id="search"
              type="text"
              placeholder="Título, nº do processo ou cliente..."
              value={searchTerm}
              onChange={handleSearchChange}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* Filtro de status */}
          <div>
            <label htmlFor="status-filter" className="mb-1 block text-sm font-medium text-gray-700">
              Status
            </label>
            <select
              id="status-filter"
              value={statusFilter}
              onChange={handleStatusFilterChange}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Filtro de tribunal */}
          <div>
            <label htmlFor="court-filter" className="mb-1 block text-sm font-medium text-gray-700">
              Tribunal
            </label>
            <select
              id="court-filter"
              value={courtFilter}
              onChange={handleCourtFilterChange}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {COURT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Botão limpar filtros */}
          <div className="flex items-end">
            <Button
              variant="secondary"
              size="md"
              onClick={handleClearFilters}
              disabled={!hasActiveFilters}
              className="w-full"
            >
              Limpar Filtros
            </Button>
          </div>
        </div>
      </section>

      {/* Estado de erro */}
      {isError && (
        <div
          role="alert"
          className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800"
        >
          <p className="font-medium">Erro ao carregar processos.</p>
          <p className="mt-1 text-sm">
            Não foi possível obter a lista de processos. Tente novamente mais tarde.
          </p>
          <Button
            variant="secondary"
            size="sm"
            className="mt-2"
            onClick={() => casesQuery.refetch()}
          >
            Tentar novamente
          </Button>
        </div>
      )}

      {/* Tabela de processos */}
      <section aria-label="Lista de processos">
        <DataTable<CaseSummary>
          columns={columns}
          data={cases}
          loading={isLoading}
          emptyMessage="Nenhum processo encontrado."
          pagination={{
            currentPage: page,
            pageSize,
            totalItems,
            onPageChange: setPage,
          }}
          rowKeyExtractor={(row) => row.id}
        />
      </section>

      {/* Resumo de resultados */}
      {!isLoading && !isError && (
        <p className="mt-2 text-sm text-gray-500">
          {totalItems === 0
            ? 'Nenhum resultado encontrado.'
            : `Exibindo ${cases.length} de ${totalItems} processo(s).`}
        </p>
      )}

      {/* ================================================================== */}
      {/* Modal: Criar Processo                                              */}
      {/* ================================================================== */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Novo Processo"
        description="Preencha os dados para cadastrar um novo processo jurídico."
      >
        <form onSubmit={handleCreateSubmit} noValidate>
          <CaseFormFields
            formState={formState}
            formErrors={formErrors}
            onFieldChange={handleFieldChange}
          />
          <div className="mt-6 flex justify-end gap-3">
            <Button
              variant="secondary"
              size="md"
              type="button"
              onClick={() => setIsCreateModalOpen(false)}
            >
              Cancelar
            </Button>
            <Button
              variant="primary"
              size="md"
              type="submit"
              loading={createMutation.isPending}
            >
              Criar Processo
            </Button>
          </div>
          {createMutation.isError && (
            <p className="mt-3 text-sm text-red-600" role="alert">
              Erro ao criar processo. Verifique os dados e tente novamente.
            </p>
          )}
        </form>
      </Modal>

      {/* ================================================================== */}
      {/* Modal: Editar Processo                                             */}
      {/* ================================================================== */}
      <Modal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        title="Editar Processo"
        description="Atualize os dados do processo jurídico."
      >
        <form onSubmit={handleEditSubmit} noValidate>
          <CaseFormFields
            formState={formState}
            formErrors={formErrors}
            onFieldChange={handleFieldChange}
          />
          <div className="mt-6 flex justify-end gap-3">
            <Button
              variant="secondary"
              size="md"
              type="button"
              onClick={() => setIsEditModalOpen(false)}
            >
              Cancelar
            </Button>
            <Button
              variant="primary"
              size="md"
              type="submit"
              loading={updateMutation.isPending}
            >
              Salvar Alterações
            </Button>
          </div>
          {updateMutation.isError && (
            <p className="mt-3 text-sm text-red-600" role="alert">
              Erro ao atualizar processo. Verifique os dados e tente novamente.
            </p>
          )}
        </form>
      </Modal>

      {/* ================================================================== */}
      {/* Modal: Detalhes do Processo                                        */}
      {/* ================================================================== */}
      <Modal
        isOpen={isDetailModalOpen}
        onClose={() => setIsDetailModalOpen(false)}
        title="Detalhes do Processo"
      >
        {selectedCase && (
          <div className="space-y-4">
            <DetailRow label="Nº do Processo" value={selectedCase.caseNumber ?? '—'} />
            <DetailRow label="Título" value={selectedCase.title} />
            <DetailRow label="Descrição" value={selectedCase.description ?? '—'} />
            <DetailRow label="Cliente" value={selectedCase.clientName ?? '—'} />
            <DetailRow label="Tribunal" value={selectedCase.court ?? '—'} />
            <DetailRow
              label="Status"
              value={<StatusBadge status={selectedCase.status} />}
            />
            <DetailRow label="Criado em" value={formatDate(selectedCase.createdAt)} />
            <DetailRow label="Atualizado em" value={formatDate(selectedCase.updatedAt)} />
          </div>
        )}
        <div className="mt-6 flex justify-end">
          <Button
            variant="secondary"
            size="md"
            onClick={() => setIsDetailModalOpen(false)}
          >
            Fechar
          </Button>
        </div>
      </Modal>

      {/* ================================================================== */}
      {/* Modal: Confirmar Exclusão                                          */}
      {/* ================================================================== */}
      <Modal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        title="Confirmar Exclusão"
        description="Esta ação não pode ser desfeita."
      >
        <p className="text-sm text-gray-700">
          Tem certeza que deseja excluir o processo{' '}
          <strong>{selectedCase?.title}</strong>? Todos os dados associados serão
          permanentemente removidos.
        </p>
        <div className="mt-6 flex justify-end gap-3">
          <Button
            variant="secondary"
            size="md"
            type="button"
            onClick={() => setIsDeleteModalOpen(false)}
          >
            Cancelar
          </Button>
          <Button
            variant="danger"
            size="md"
            onClick={handleDeleteConfirm}
            loading={deleteMutation.isPending}
          >
            Excluir Processo
          </Button>
        </div>
        {deleteMutation.isError && (
          <p className="mt-3 text-sm text-red-600" role="alert">
            Erro ao excluir processo. Tente novamente.
          </p>
        )}
      </Modal>
    </main>
  );
};

// =============================================================================
// Componentes auxiliares internos
// =============================================================================

/** Props do formulário de caso reutilizado em criação e edição */
interface CaseFormFieldsProps {
  formState: CaseFormState;
  formErrors: Partial<Record<keyof CaseFormState, string>>;
  onFieldChange: (
    field: keyof CaseFormState,
  ) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => void;
}

/**
 * Campos do formulário de caso, reutilizados nos modais de criação e edição.
 */
const CaseFormFields: React.FC<CaseFormFieldsProps> = ({
  formState,
  formErrors,
  onFieldChange,
}) => (
  <div className="space-y-4">
    {/* Título */}
    <div>
      <label htmlFor="case-title" className="mb-1 block text-sm font-medium text-gray-700">
        Título <span className="text-red-500">*</span>
      </label>
      <input
        id="case-title"
        type="text"
        value={formState.title}
        onChange={onFieldChange('title')}
        placeholder="Ex.: Ação de Indenização — João Silva"
        className={`w-full rounded-md border px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-1 ${
          formErrors.title
            ? 'border-red-400 focus:border-red-500 focus:ring-red-500'
            : 'border-gray-300 focus:border-blue-500 focus:ring-blue-500'
        }`}
        aria-invalid={!!formErrors.title}
        aria-describedby={formErrors.title ? 'case-title-error' : undefined}
      />
      {formErrors.title && (
        <p id="case-title-error" className="mt-1 text-xs text-red-600" role="alert">
          {formErrors.title}
        </p>
      )}
    </div>

    {/* Descrição */}
    <div>
      <label htmlFor="case-description" className="mb-1 block text-sm font-medium text-gray-700">
        Descrição <span className="text-red-500">*</span>
      </label>
      <textarea
        id="case-description"
        rows={3}
        value={formState.description}
        onChange={onFieldChange('description')}
        placeholder="Descreva brevemente o processo..."
        className={`w-full rounded-md border px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-1 ${
          formErrors.description
            ? 'border-red-400 focus:border-red-500 focus:ring-red-500'
            : 'border-gray-300 focus:border-blue-500 focus:ring-blue-500'
        }`}
        aria-invalid={!!formErrors.description}
        aria-describedby={formErrors.description ? 'case-description-error' : undefined}
      />
      {formErrors.description && (
        <p id="case-description-error" className="mt-1 text-xs text-red-600" role="alert">
          {formErrors.description}
        </p>
      )}
    </div>

    {/* Nome do cliente */}
    <div>
      <label htmlFor="case-client" className="mb-1 block text-sm font-medium text-gray-700">
        Cliente <span className="text-red-500">*</span>
      </label>
      <input
        id="case-client"
        type="text"
        value={formState.clientName}
        onChange={onFieldChange('clientName')}
        placeholder="Nome completo do cliente"
        className={`w-full rounded-md border px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-1 ${
          formErrors.clientName
            ? 'border-red-400 focus:border-red-500 focus:ring-red-500'
            : 'border-gray-300 focus:border-blue-500 focus:ring-blue-500'
        }`}
        aria-invalid={!!formErrors.clientName}
        aria-describedby={formErrors.clientName ? 'case-client-error' : undefined}
      />
      {formErrors.clientName && (
        <p id="case-client-error" className="mt-1 text-xs text-red-600" role="alert">
          {formErrors.clientName}
        </p>
      )}
    </div>

    {/* Número do processo */}
    <div>
      <label htmlFor="case-number" className="mb-1 block text-sm font-medium text-gray-700">
        Nº do Processo
      </label>
      <input
        id="case-number"
        type="text"
        value={formState.caseNumber}
        onChange={onFieldChange('caseNumber')}
        placeholder="Ex.: 0000000-00.0000.0.00.0000"
        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
      />
    </div>

    {/* Tribunal */}
    <div>
      <label htmlFor="case-court" className="mb-1 block text-sm font-medium text-gray-700">
        Tribunal
      </label>
      <select
        id="case-court"
        value={formState.court}
        onChange={onFieldChange('court')}
        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
      >
        <option value="">Selecione o tribunal</option>
        {COURT_OPTIONS.filter((opt) => opt.value !== '').map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  </div>
);

/** Props para linha de detalhe */
interface DetailRowProps {
  label: string;
  value: React.ReactNode;
}

/** Linha de exibição de detalhe no modal de visualização */
const DetailRow: React.FC<DetailRowProps> = ({ label, value }) => (
  <div className="flex flex-col sm:flex-row sm:gap-4">
    <dt className="text-sm font-medium text-gray-500 sm:w-40 sm:flex-shrink-0">{label}</dt>
    <dd className="mt-1 text-sm text-gray-900 sm:mt-0">{value}</dd>
  </div>
);

/** Mapeamento de status para cores do badge */
const STATUS_COLORS: Record<string, string> = {
  active: 'bg-green-100 text-green-800',
  in_progress: 'bg-blue-100 text-blue-800',
  concluded: 'bg-gray-100 text-gray-800',
  archived: 'bg-yellow-100 text-yellow-800',
  suspended: 'bg-red-100 text-red-800',
};

/** Mapeamento de status para labels em PT-BR */
const STATUS_LABELS: Record<string, string> = {
  active: 'Ativo',
  in_progress: 'Em andamento',
  concluded: 'Concluído',
  archived: 'Arquivado',
  suspended: 'Suspenso',
};

/** Badge visual para status do processo */
const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const colorClass = STATUS_COLORS[status] ?? 'bg-gray-100 text-gray-800';
  const label = STATUS_LABELS[status] ?? status;

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${colorClass}`}
    >
      {label}
    </span>
  );
};

// =============================================================================
// Utilitários
// =============================================================================

/**
 * Formata uma string de data ISO para o formato brasileiro (dd/mm/aaaa).
 * Retorna '—' caso o valor seja nulo ou indefinido.
 */
function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '—';
  try {
    return new Intl.DateTimeFormat('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    }).format(new Date(dateStr));
  } catch {
    return '—';
  }
}

export default CasesPage;
