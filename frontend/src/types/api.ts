/**
 * @module api
 * @description Tipos e interfaces TypeScript espelhando os DTOs do backend FastAPI.
 * Inclui definições para User, Case, Document, Analysis e Chat.
 * Todos os tipos seguem a convenção de nomenclatura do backend (snake_case nos campos)
 * para facilitar a serialização/deserialização direta com a API REST.
 */

// ============================================================================
// Enums
// ============================================================================

/** Status possíveis de um usuário no sistema */
export enum UserStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  SUSPENDED = 'suspended',
  PENDING_VERIFICATION = 'pending_verification',
}

/** Papéis disponíveis no sistema RBAC */
export enum UserRole {
  ADMIN = 'admin',
  LAWYER = 'lawyer',
  ANALYST = 'analyst',
  VIEWER = 'viewer',
}

/** Status do ciclo de vida de um caso jurídico */
export enum CaseStatus {
  DRAFT = 'draft',
  ACTIVE = 'active',
  IN_ANALYSIS = 'in_analysis',
  PENDING_REVIEW = 'pending_review',
  CLOSED = 'closed',
  ARCHIVED = 'archived',
}

/** Tipos de documento suportados pelo sistema */
export enum DocumentType {
  PETITION = 'petition',
  CONTRACT = 'contract',
  COURT_DECISION = 'court_decision',
  LEGAL_OPINION = 'legal_opinion',
  POWER_OF_ATTORNEY = 'power_of_attorney',
  EVIDENCE = 'evidence',
  DATAJUD = 'datajud',
  OTHER = 'other',
}

/** Status do documento conforme state machine do backend */
export enum DocumentStatus {
  UPLOADED = 'uploaded',
  PROCESSING = 'processing',
  PROCESSED = 'processed',
  ANALYSIS_PENDING = 'analysis_pending',
  ANALYZED = 'analyzed',
  ERROR = 'error',
  ARCHIVED = 'archived',
}

/** Status de uma análise de IA */
export enum AnalysisStatus {
  QUEUED = 'queued',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
}

/** Tipo de análise realizada pela IA */
export enum AnalysisType {
  SUMMARY = 'summary',
  RISK_ASSESSMENT = 'risk_assessment',
  CLAUSE_REVIEW = 'clause_review',
  LEGAL_RESEARCH = 'legal_research',
  DOCUMENT_COMPARISON = 'document_comparison',
  DATAJUD_ENRICHMENT = 'datajud_enrichment',
}

/** Papel de uma mensagem no chat */
export enum ChatMessageRole {
  USER = 'user',
  ASSISTANT = 'assistant',
  SYSTEM = 'system',
}

// ============================================================================
// Tipos Utilitários
// ============================================================================

/** Identificador UUID como string */
export type UUID = string;

/** Timestamp ISO 8601 como string */
export type ISODateTime = string;

// ============================================================================
// User — DTOs de Usuário
// ============================================================================

/** Representação base de um usuário */
export interface UserBase {
  /** E-mail do usuário (único no sistema) */
  email: string;
  /** Nome completo do usuário */
  full_name: string;
  /** Papel do usuário no sistema RBAC */
  role: UserRole;
}

/** Payload para criação de usuário */
export interface UserCreate extends UserBase {
  /** Senha em texto plano (será hasheada no backend) */
  password: string;
  /** Número OAB (obrigatório para advogados) */
  oab_number?: string;
}

/** Payload para atualização parcial de usuário */
export interface UserUpdate {
  full_name?: string;
  email?: string;
  role?: UserRole;
  status?: UserStatus;
  oab_number?: string;
}

/** Resposta completa de usuário retornada pela API */
export interface UserResponse extends UserBase {
  id: UUID;
  status: UserStatus;
  oab_number: string | null;
  mfa_enabled: boolean;
  created_at: ISODateTime;
  updated_at: ISODateTime;
  last_login_at: ISODateTime | null;
}

/** Resumo de usuário para listagens e referências */
export interface UserSummary {
  id: UUID;
  full_name: string;
  email: string;
  role: UserRole;
}

// ============================================================================
// Auth — DTOs de Autenticação
// ============================================================================

/** Payload de login */
export interface LoginRequest {
  email: string;
  password: string;
  /** Código TOTP para MFA (quando habilitado) */
  mfa_code?: string;
}

/** Resposta de autenticação com tokens JWT */
export interface AuthTokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
  expires_in: number;
  /** Indica se MFA é necessário para completar o login */
  mfa_required: boolean;
}

/** Payload para refresh de token */
export interface RefreshTokenRequest {
  refresh_token: string;
}

// ============================================================================
// Case — DTOs de Caso Jurídico
// ============================================================================

/** Campos base de um caso jurídico */
export interface CaseBase {
  /** Título descritivo do caso */
  title: string;
  /** Descrição detalhada do caso */
  description: string;
  /** Número do processo (formato CNJ quando aplicável) */
  case_number: string | null;
  /** Área do direito */
  legal_area: string | null;
  /** Tribunal ou vara responsável */
  court: string | null;
}

/** Payload para criação de caso */
export interface CaseCreate extends CaseBase {
  /** IDs dos advogados responsáveis */
  assigned_lawyer_ids?: UUID[];
  /** Tags para categorização */
  tags?: string[];
}

/** Payload para atualização parcial de caso */
export interface CaseUpdate {
  title?: string;
  description?: string;
  case_number?: string | null;
  legal_area?: string | null;
  court?: string | null;
  status?: CaseStatus;
  assigned_lawyer_ids?: UUID[];
  tags?: string[];
}

/** Resposta completa de caso retornada pela API */
export interface CaseResponse extends CaseBase {
  id: UUID;
  status: CaseStatus;
  created_by: UserSummary;
  assigned_lawyers: UserSummary[];
  tags: string[];
  document_count: number;
  analysis_count: number;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

/** Resumo de caso para listagens */
export interface CaseSummary {
  id: UUID;
  title: string;
  case_number: string | null;
  status: CaseStatus;
  legal_area: string | null;
  document_count: number;
  updated_at: ISODateTime;
}

// ============================================================================
// Document — DTOs de Documento
// ============================================================================

/** Metadados de upload de documento */
export interface DocumentUploadMeta {
  /** ID do caso ao qual o documento pertence */
  case_id: UUID;
  /** Tipo do documento */
  document_type: DocumentType;
  /** Título descritivo (opcional, usa nome do arquivo se omitido) */
  title?: string;
  /** Descrição adicional */
  description?: string;
  /** Tags para categorização */
  tags?: string[];
}

/** Payload para atualização de metadados do documento */
export interface DocumentUpdate {
  title?: string;
  description?: string;
  document_type?: DocumentType;
  tags?: string[];
}

/** Resposta completa de documento retornada pela API */
export interface DocumentResponse {
  id: UUID;
  case_id: UUID;
  title: string;
  description: string | null;
  document_type: DocumentType;
  status: DocumentStatus;
  /** Nome original do arquivo */
  original_filename: string;
  /** Tipo MIME do arquivo */
  mime_type: string;
  /** Tamanho do arquivo em bytes */
  file_size: number;
  /** Hash SHA-256 do arquivo para verificação de integridade */
  file_hash: string;
  tags: string[];
  uploaded_by: UserSummary;
  /** Número de análises realizadas neste documento */
  analysis_count: number;
  created_at: ISODateTime;
  updated_at: ISODateTime;
  processed_at: ISODateTime | null;
}

/** Resumo de documento para listagens */
export interface DocumentSummary {
  id: UUID;
  title: string;
  document_type: DocumentType;
  status: DocumentStatus;
  original_filename: string;
  file_size: number;
  created_at: ISODateTime;
}

// ============================================================================
// Analysis — DTOs de Análise de IA
// ============================================================================

/** Payload para solicitar uma nova análise */
export interface AnalysisCreate {
  /** ID do documento a ser analisado */
  document_id: UUID;
  /** Tipo de análise desejada */
  analysis_type: AnalysisType;
  /** Instruções adicionais para a IA (prompt customizado) */
  custom_instructions?: string;
  /** IDs de documentos adicionais para contexto (ex: comparação) */
  context_document_ids?: UUID[];
}

/** Item de risco identificado pela análise */
export interface RiskItem {
  /** Nível de severidade do risco */
  severity: 'low' | 'medium' | 'high' | 'critical';
  /** Descrição do risco identificado */
  description: string;
  /** Trecho do documento relacionado ao risco */
  excerpt: string | null;
  /** Recomendação de mitigação */
  recommendation: string | null;
}

/** Resultado estruturado de uma análise */
export interface AnalysisResult {
  /** Resumo executivo da análise */
  summary: string;
  /** Pontos-chave identificados */
  key_points: string[];
  /** Riscos identificados (quando aplicável) */
  risks: RiskItem[];
  /** Recomendações gerais */
  recommendations: string[];
  /** Dados adicionais específicos do tipo de análise */
  metadata: Record<string, unknown>;
  /** Confiança geral da análise (0.0 a 1.0) */
  confidence_score: number;
}

/** Resposta completa de análise retornada pela API */
export interface AnalysisResponse {
  id: UUID;
  document_id: UUID;
  case_id: UUID;
  analysis_type: AnalysisType;
  status: AnalysisStatus;
  custom_instructions: string | null;
  /** Resultado da análise (null enquanto não concluída) */
  result: AnalysisResult | null;
  /** Mensagem de erro (quando status = FAILED) */
  error_message: string | null;
  /** Modelo de IA utilizado */
  model_used: string | null;
  /** Tokens de entrada consumidos */
  input_tokens: number | null;
  /** Tokens de saída consumidos */
  output_tokens: number | null;
  requested_by: UserSummary;
  context_document_ids: UUID[];
  created_at: ISODateTime;
  updated_at: ISODateTime;
  completed_at: ISODateTime | null;
}

/** Resumo de análise para listagens */
export interface AnalysisSummary {
  id: UUID;
  analysis_type: AnalysisType;
  status: AnalysisStatus;
  confidence_score: number | null;
  created_at: ISODateTime;
  completed_at: ISODateTime | null;
}

// ============================================================================
// Chat — DTOs de Chat com IA
// ============================================================================

/** Mensagem individual de chat */
export interface ChatMessage {
  id: UUID;
  role: ChatMessageRole;
  content: string;
  /** Referências a documentos citados na mensagem */
  document_references: DocumentReference[];
  created_at: ISODateTime;
}

/** Referência a um trecho de documento citado no chat */
export interface DocumentReference {
  document_id: UUID;
  document_title: string;
  /** Trecho relevante do documento */
  excerpt: string;
  /** Número da página (quando disponível) */
  page_number: number | null;
}

/** Payload para criar uma nova sessão de chat */
export interface ChatSessionCreate {
  /** ID do caso associado ao chat */
  case_id: UUID;
  /** Título da sessão de chat */
  title?: string;
  /** IDs de documentos para contexto inicial */
  context_document_ids?: UUID[];
}

/** Payload para enviar uma mensagem no chat */
export interface ChatMessageCreate {
  /** Conteúdo da mensagem do usuário */
  content: string;
  /** IDs de documentos adicionais para contexto */
  context_document_ids?: UUID[];
}

/** Resposta completa de sessão de chat */
export interface ChatSessionResponse {
  id: UUID;
  case_id: UUID;
  title: string;
  created_by: UserSummary;
  context_document_ids: UUID[];
  messages: ChatMessage[];
  message_count: number;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

/** Resumo de sessão de chat para listagens */
export interface ChatSessionSummary {
  id: UUID;
  title: string;
  case_id: UUID;
  message_count: number;
  /** Prévia da última mensagem */
  last_message_preview: string | null;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

// ============================================================================
// Audit — DTOs de Auditoria
// ============================================================================

/** Registro de auditoria */
export interface AuditLogEntry {
  id: UUID;
  /** Usuário que realizou a ação */
  user_id: UUID;
  user_email: string;
  /** Ação realizada */
  action: string;
  /** Recurso afetado (ex: 'document', 'case', 'analysis') */
  resource_type: string;
  /** ID do recurso afetado */
  resource_id: UUID | null;
  /** Detalhes adicionais da ação */
  details: Record<string, unknown> | null;
  /** Endereço IP de origem */
  ip_address: string;
  /** User-Agent do navegador */
  user_agent: string;
  created_at: ISODateTime;
}

// ============================================================================
// Respostas Paginadas e Genéricas
// ============================================================================

/** Resposta paginada genérica da API */
export interface PaginatedResponse<T> {
  /** Lista de itens da página atual */
  items: T[];
  /** Total de itens disponíveis */
  total: number;
  /** Página atual (1-indexed) */
  page: number;
  /** Itens por página */
  page_size: number;
  /** Total de páginas */
  total_pages: number;
  /** Indica se há próxima página */
  has_next: boolean;
  /** Indica se há página anterior */
  has_previous: boolean;
}

/** Resposta de erro padrão da API */
export interface ApiErrorResponse {
  /** Mensagem de erro legível */
  detail: string;
  /** Código de erro interno (para rastreamento) */
  error_code?: string;
  /** Erros de validação por campo (quando aplicável) */
  field_errors?: FieldError[];
}

/** Erro de validação de campo individual */
export interface FieldError {
  /** Caminho do campo com erro (ex: 'body.email') */
  field: string;
  /** Mensagem de erro do campo */
  message: string;
  /** Tipo de erro de validação */
  error_type: string;
}

/** Resposta genérica de sucesso para operações sem retorno de dados */
export interface SuccessResponse {
  /** Mensagem de confirmação */
  message: string;
  /** Indica sucesso da operação */
  success: boolean;
}

// ============================================================================
// Parâmetros de Query Comuns
// ============================================================================

/** Parâmetros de paginação padrão */
export interface PaginationParams {
  page?: number;
  page_size?: number;
}

/** Parâmetros de ordenação */
export interface SortParams {
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

/** Parâmetros de busca e filtro para casos */
export interface CaseFilterParams extends PaginationParams, SortParams {
  status?: CaseStatus;
  legal_area?: string;
  search?: string;
  assigned_lawyer_id?: UUID;
  created_after?: ISODateTime;
  created_before?: ISODateTime;
}

/** Parâmetros de busca e filtro para documentos */
export interface DocumentFilterParams extends PaginationParams, SortParams {
  case_id?: UUID;
  document_type?: DocumentType;
  status?: DocumentStatus;
  search?: string;
  uploaded_after?: ISODateTime;
  uploaded_before?: ISODateTime;
}

/** Parâmetros de busca e filtro para análises */
export interface AnalysisFilterParams extends PaginationParams, SortParams {
  case_id?: UUID;
  document_id?: UUID;
  analysis_type?: AnalysisType;
  status?: AnalysisStatus;
  created_after?: ISODateTime;
  created_before?: ISODateTime;
}
