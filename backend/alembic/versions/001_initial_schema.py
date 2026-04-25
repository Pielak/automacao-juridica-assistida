"""Migration inicial: criação das tabelas principais do sistema.

Tabelas criadas:
- users: Usuários do sistema com suporte a RBAC e MFA
- cases: Casos/processos jurídicos
- documents: Documentos associados a casos
- analyses: Análises de documentos via IA (Claude/Anthropic)
- audit_logs: Logs de auditoria para compliance e rastreabilidade
- chat_sessions: Sessões de chat com assistente IA

Revision ID: 001
Revises: -
Create Date: 2024-01-01 00:00:00.000000

Projeto: Automação Jurídica Assistida
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# Identificadores da revisão Alembic
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Aplica a migration: cria todas as tabelas do schema inicial."""

    # ──────────────────────────────────────────────
    # Tipos ENUM customizados
    # ──────────────────────────────────────────────
    user_role_enum = postgresql.ENUM(
        "admin",
        "advogado",
        "estagiario",
        "cliente",
        name="user_role",
        create_type=True,
    )

    user_status_enum = postgresql.ENUM(
        "active",
        "inactive",
        "suspended",
        "pending_verification",
        name="user_status",
        create_type=True,
    )

    case_status_enum = postgresql.ENUM(
        "draft",
        "active",
        "archived",
        "closed",
        "suspended",
        name="case_status",
        create_type=True,
    )

    document_status_enum = postgresql.ENUM(
        "pending",
        "processing",
        "analyzed",
        "error",
        "archived",
        name="document_status",
        create_type=True,
    )

    analysis_status_enum = postgresql.ENUM(
        "queued",
        "processing",
        "completed",
        "failed",
        "cancelled",
        name="analysis_status",
        create_type=True,
    )

    analysis_type_enum = postgresql.ENUM(
        "summary",
        "risk_assessment",
        "clause_extraction",
        "legal_opinion",
        "datajud_enrichment",
        "custom",
        name="analysis_type",
        create_type=True,
    )

    audit_action_enum = postgresql.ENUM(
        "create",
        "read",
        "update",
        "delete",
        "login",
        "logout",
        "login_failed",
        "export",
        "analysis_requested",
        "analysis_completed",
        "document_uploaded",
        "document_downloaded",
        "permission_changed",
        name="audit_action",
        create_type=True,
    )

    chat_session_status_enum = postgresql.ENUM(
        "active",
        "closed",
        "archived",
        name="chat_session_status",
        create_type=True,
    )

    # ──────────────────────────────────────────────
    # Tabela: users
    # Usuários do sistema com autenticação JWT + MFA
    # ──────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Identificador único do usuário (UUID v4)",
        ),
        sa.Column(
            "email",
            sa.String(255),
            nullable=False,
            unique=True,
            comment="E-mail do usuário, utilizado como login",
        ),
        sa.Column(
            "hashed_password",
            sa.String(255),
            nullable=False,
            comment="Hash bcrypt da senha do usuário",
        ),
        sa.Column(
            "full_name",
            sa.String(255),
            nullable=False,
            comment="Nome completo do usuário",
        ),
        sa.Column(
            "oab_number",
            sa.String(20),
            nullable=True,
            comment="Número de registro na OAB (quando aplicável)",
        ),
        sa.Column(
            "role",
            user_role_enum,
            nullable=False,
            server_default="estagiario",
            comment="Papel do usuário no sistema (RBAC)",
        ),
        sa.Column(
            "status",
            user_status_enum,
            nullable=False,
            server_default="pending_verification",
            comment="Status atual da conta do usuário",
        ),
        sa.Column(
            "mfa_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Indica se MFA (TOTP) está habilitado",
        ),
        sa.Column(
            "mfa_secret",
            sa.String(255),
            nullable=True,
            comment="Segredo TOTP criptografado para MFA",
        ),
        sa.Column(
            "last_login_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Data/hora do último login bem-sucedido",
        ),
        sa.Column(
            "failed_login_attempts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Contador de tentativas de login falhas consecutivas",
        ),
        sa.Column(
            "locked_until",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Data/hora até quando a conta está bloqueada por tentativas falhas",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="Data/hora de criação do registro",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="Data/hora da última atualização do registro",
        ),
        comment="Usuários do sistema com autenticação, RBAC e suporte a MFA",
    )

    # Índices para users
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])
    op.create_index("ix_users_status", "users", ["status"])
    op.create_index("ix_users_oab_number", "users", ["oab_number"], unique=True, postgresql_where=sa.text("oab_number IS NOT NULL"))

    # ──────────────────────────────────────────────
    # Tabela: cases
    # Casos/processos jurídicos
    # ──────────────────────────────────────────────
    op.create_table(
        "cases",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Identificador único do caso (UUID v4)",
        ),
        sa.Column(
            "title",
            sa.String(500),
            nullable=False,
            comment="Título descritivo do caso",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Descrição detalhada do caso",
        ),
        sa.Column(
            "case_number",
            sa.String(50),
            nullable=True,
            unique=True,
            comment="Número do processo judicial (formato CNJ quando aplicável)",
        ),
        sa.Column(
            "court",
            sa.String(255),
            nullable=True,
            comment="Tribunal/vara responsável pelo processo",
        ),
        sa.Column(
            "subject_area",
            sa.String(100),
            nullable=True,
            comment="Área do direito (ex: trabalhista, cível, penal)",
        ),
        sa.Column(
            "status",
            case_status_enum,
            nullable=False,
            server_default="draft",
            comment="Status atual do caso no sistema",
        ),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            comment="ID do usuário responsável pelo caso",
        ),
        sa.Column(
            "client_name",
            sa.String(255),
            nullable=True,
            comment="Nome do cliente associado ao caso",
        ),
        sa.Column(
            "client_document",
            sa.String(20),
            nullable=True,
            comment="CPF ou CNPJ do cliente (mascarado)",
        ),
        sa.Column(
            "datajud_synced_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Data/hora da última sincronização com DataJud",
        ),
        sa.Column(
            "metadata_",
            postgresql.JSONB(),
            nullable=True,
            server_default=sa.text("'{}'"),
            comment="Metadados adicionais do caso em formato JSON",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="Data/hora de criação do registro",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="Data/hora da última atualização do registro",
        ),
        comment="Casos e processos jurídicos gerenciados no sistema",
    )

    # Índices para cases
    op.create_index("ix_cases_owner_id", "cases", ["owner_id"])
    op.create_index("ix_cases_status", "cases", ["status"])
    op.create_index("ix_cases_case_number", "cases", ["case_number"], unique=True, postgresql_where=sa.text("case_number IS NOT NULL"))
    op.create_index("ix_cases_subject_area", "cases", ["subject_area"])
    op.create_index("ix_cases_created_at", "cases", ["created_at"])

    # ──────────────────────────────────────────────
    # Tabela: documents
    # Documentos associados a casos
    # ──────────────────────────────────────────────
    op.create_table(
        "documents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Identificador único do documento (UUID v4)",
        ),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
            comment="ID do caso ao qual o documento pertence",
        ),
        sa.Column(
            "uploaded_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            comment="ID do usuário que realizou o upload",
        ),
        sa.Column(
            "filename",
            sa.String(500),
            nullable=False,
            comment="Nome original do arquivo enviado",
        ),
        sa.Column(
            "storage_path",
            sa.String(1000),
            nullable=False,
            comment="Caminho no storage onde o arquivo está armazenado",
        ),
        sa.Column(
            "mime_type",
            sa.String(100),
            nullable=False,
            comment="Tipo MIME do arquivo (ex: application/pdf)",
        ),
        sa.Column(
            "file_size_bytes",
            sa.BigInteger(),
            nullable=False,
            comment="Tamanho do arquivo em bytes",
        ),
        sa.Column(
            "file_hash_sha256",
            sa.String(64),
            nullable=False,
            comment="Hash SHA-256 do conteúdo do arquivo para verificação de integridade",
        ),
        sa.Column(
            "status",
            document_status_enum,
            nullable=False,
            server_default="pending",
            comment="Status atual do documento no pipeline de processamento",
        ),
        sa.Column(
            "document_type",
            sa.String(100),
            nullable=True,
            comment="Tipo do documento jurídico (ex: petição, contrato, sentença)",
        ),
        sa.Column(
            "page_count",
            sa.Integer(),
            nullable=True,
            comment="Número de páginas do documento (quando aplicável)",
        ),
        sa.Column(
            "extracted_text",
            sa.Text(),
            nullable=True,
            comment="Texto extraído do documento via OCR ou parsing",
        ),
        sa.Column(
            "virus_scan_passed",
            sa.Boolean(),
            nullable=True,
            comment="Resultado da varredura antivírus (null = não verificado)",
        ),
        sa.Column(
            "virus_scan_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Data/hora da varredura antivírus",
        ),
        sa.Column(
            "metadata_",
            postgresql.JSONB(),
            nullable=True,
            server_default=sa.text("'{}'"),
            comment="Metadados adicionais do documento em formato JSON",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="Data/hora de criação do registro (upload)",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="Data/hora da última atualização do registro",
        ),
        comment="Documentos jurídicos associados a casos, com rastreamento de integridade",
    )

    # Índices para documents
    op.create_index("ix_documents_case_id", "documents", ["case_id"])
    op.create_index("ix_documents_uploaded_by_id", "documents", ["uploaded_by_id"])
    op.create_index("ix_documents_status", "documents", ["status"])
    op.create_index("ix_documents_mime_type", "documents", ["mime_type"])
    op.create_index("ix_documents_file_hash_sha256", "documents", ["file_hash_sha256"])
    op.create_index("ix_documents_created_at", "documents", ["created_at"])

    # ──────────────────────────────────────────────
    # Tabela: analyses
    # Análises de documentos realizadas via IA
    # ──────────────────────────────────────────────
    op.create_table(
        "analyses",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Identificador único da análise (UUID v4)",
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
            comment="ID do documento analisado",
        ),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
            comment="ID do caso associado (desnormalizado para consultas rápidas)",
        ),
        sa.Column(
            "requested_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            comment="ID do usuário que solicitou a análise",
        ),
        sa.Column(
            "analysis_type",
            analysis_type_enum,
            nullable=False,
            comment="Tipo de análise solicitada",
        ),
        sa.Column(
            "status",
            analysis_status_enum,
            nullable=False,
            server_default="queued",
            comment="Status atual da análise no pipeline",
        ),
        sa.Column(
            "prompt_template",
            sa.String(100),
            nullable=True,
            comment="Identificador do template de prompt utilizado",
        ),
        sa.Column(
            "input_tokens",
            sa.Integer(),
            nullable=True,
            comment="Quantidade de tokens de entrada consumidos pela API Anthropic",
        ),
        sa.Column(
            "output_tokens",
            sa.Integer(),
            nullable=True,
            comment="Quantidade de tokens de saída gerados pela API Anthropic",
        ),
        sa.Column(
            "model_used",
            sa.String(100),
            nullable=True,
            comment="Modelo da Anthropic utilizado (ex: claude-3-sonnet)",
        ),
        sa.Column(
            "result",
            postgresql.JSONB(),
            nullable=True,
            comment="Resultado estruturado da análise em formato JSON",
        ),
        sa.Column(
            "result_summary",
            sa.Text(),
            nullable=True,
            comment="Resumo textual do resultado da análise",
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
            comment="Mensagem de erro caso a análise tenha falhado",
        ),
        sa.Column(
            "retry_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Número de tentativas de reprocessamento",
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Data/hora de início do processamento",
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Data/hora de conclusão do processamento",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="Data/hora de criação do registro (solicitação)",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="Data/hora da última atualização do registro",
        ),
        comment="Análises de documentos jurídicos realizadas via IA (Anthropic Claude)",
    )

    # Índices para analyses
    op.create_index("ix_analyses_document_id", "analyses", ["document_id"])
    op.create_index("ix_analyses_case_id", "analyses", ["case_id"])
    op.create_index("ix_analyses_requested_by_id", "analyses", ["requested_by_id"])
    op.create_index("ix_analyses_status", "analyses", ["status"])
    op.create_index("ix_analyses_analysis_type", "analyses", ["analysis_type"])
    op.create_index("ix_analyses_created_at", "analyses", ["created_at"])

    # ──────────────────────────────────────────────
    # Tabela: audit_logs
    # Logs de auditoria para compliance e rastreabilidade
    # ──────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Identificador único do registro de auditoria (UUID v4)",
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            comment="ID do usuário que realizou a ação (null para ações do sistema)",
        ),
        sa.Column(
            "action",
            audit_action_enum,
            nullable=False,
            comment="Tipo de ação registrada",
        ),
        sa.Column(
            "resource_type",
            sa.String(100),
            nullable=False,
            comment="Tipo do recurso afetado (ex: user, case, document, analysis)",
        ),
        sa.Column(
            "resource_id",
            sa.String(255),
            nullable=True,
            comment="ID do recurso afetado pela ação",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Descrição legível da ação realizada",
        ),
        sa.Column(
            "changes",
            postgresql.JSONB(),
            nullable=True,
            comment="Detalhes das alterações realizadas (before/after)",
        ),
        sa.Column(
            "ip_address",
            sa.String(45),
            nullable=True,
            comment="Endereço IP de origem da requisição (IPv4 ou IPv6)",
        ),
        sa.Column(
            "user_agent",
            sa.String(500),
            nullable=True,
            comment="User-Agent do navegador/cliente HTTP",
        ),
        sa.Column(
            "request_id",
            sa.String(100),
            nullable=True,
            comment="ID de correlação da requisição HTTP para rastreamento",
        ),
        sa.Column(
            "session_id",
            sa.String(255),
            nullable=True,
            comment="ID da sessão do usuário no momento da ação",
        ),
        sa.Column(
            "metadata_",
            postgresql.JSONB(),
            nullable=True,
            server_default=sa.text("'{}'"),
            comment="Metadados adicionais do evento de auditoria",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="Data/hora do evento de auditoria",
        ),
        comment="Logs de auditoria imutáveis para compliance LGPD e rastreabilidade",
    )

    # Índices para audit_logs — otimizados para consultas de auditoria
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_resource_type", "audit_logs", ["resource_type"])
    op.create_index("ix_audit_logs_resource_id", "audit_logs", ["resource_id"])
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    # Índice composto para consultas frequentes de auditoria por recurso
    op.create_index(
        "ix_audit_logs_resource_lookup",
        "audit_logs",
        ["resource_type", "resource_id", "created_at"],
    )

    # ──────────────────────────────────────────────
    # Tabela: chat_sessions
    # Sessões de chat com assistente IA
    # ──────────────────────────────────────────────
    op.create_table(
        "chat_sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Identificador único da sessão de chat (UUID v4)",
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            comment="ID do usuário proprietário da sessão",
        ),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cases.id", ondelete="SET NULL"),
            nullable=True,
            comment="ID do caso associado à sessão (opcional)",
        ),
        sa.Column(
            "title",
            sa.String(500),
            nullable=True,
            comment="Título da sessão de chat (gerado automaticamente ou pelo usuário)",
        ),
        sa.Column(
            "status",
            chat_session_status_enum,
            nullable=False,
            server_default="active",
            comment="Status atual da sessão de chat",
        ),
        sa.Column(
            "model_used",
            sa.String(100),
            nullable=True,
            comment="Modelo da Anthropic utilizado na sessão",
        ),
        sa.Column(
            "system_prompt",
            sa.Text(),
            nullable=True,
            comment="System prompt customizado para a sessão",
        ),
        sa.Column(
            "messages",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'"),
            comment="Histórico de mensagens da sessão em formato JSON",
        ),
        sa.Column(
            "total_input_tokens",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Total acumulado de tokens de entrada na sessão",
        ),
        sa.Column(
            "total_output_tokens",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Total acumulado de tokens de saída na sessão",
        ),
        sa.Column(
            "message_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Contador de mensagens na sessão",
        ),
        sa.Column(
            "context_documents",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=True,
            comment="IDs dos documentos utilizados como contexto na sessão",
        ),
        sa.Column(
            "metadata_",
            postgresql.JSONB(),
            nullable=True,
            server_default=sa.text("'{}'"),
            comment="Metadados adicionais da sessão de chat",
        ),
        sa.Column(
            "last_message_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Data/hora da última mensagem na sessão",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="Data/hora de criação da sessão",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="Data/hora da última atualização do registro",
        ),
        comment="Sessões de chat com assistente IA para consultas jurídicas",
    )

    # Índices para chat_sessions
    op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"])
    op.create_index("ix_chat_sessions_case_id", "chat_sessions", ["case_id"])
    op.create_index("ix_chat_sessions_status", "chat_sessions", ["status"])
    op.create_index("ix_chat_sessions_created_at", "chat_sessions", ["created_at"])
    op.create_index("ix_chat_sessions_last_message_at", "chat_sessions", ["last_message_at"])

    # ──────────────────────────────────────────────
    # Função e triggers para updated_at automático
    # ──────────────────────────────────────────────
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # Aplica trigger de updated_at em todas as tabelas que possuem a coluna
    for table_name in ["users", "cases", "documents", "analyses", "chat_sessions"]:
        op.execute(
            f"""
            CREATE TRIGGER trigger_update_{table_name}_updated_at
                BEFORE UPDATE ON {table_name}
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
            """
        )


def downgrade() -> None:
    """Reverte a migration: remove todas as tabelas e tipos ENUM criados."""

    # Remove triggers primeiro
    for table_name in ["users", "cases", "documents", "analyses", "chat_sessions"]:
        op.execute(f"DROP TRIGGER IF EXISTS trigger_update_{table_name}_updated_at ON {table_name};")

    # Remove a função de trigger
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")

    # Remove tabelas na ordem inversa de dependência
    op.drop_table("chat_sessions")
    op.drop_table("audit_logs")
    op.drop_table("analyses")
    op.drop_table("documents")
    op.drop_table("cases")
    op.drop_table("users")

    # Remove tipos ENUM
    op.execute("DROP TYPE IF EXISTS chat_session_status;")
    op.execute("DROP TYPE IF EXISTS audit_action;")
    op.execute("DROP TYPE IF EXISTS analysis_type;")
    op.execute("DROP TYPE IF EXISTS analysis_status;")
    op.execute("DROP TYPE IF EXISTS document_status;")
    op.execute("DROP TYPE IF EXISTS case_status;")
    op.execute("DROP TYPE IF EXISTS user_status;")
    op.execute("DROP TYPE IF EXISTS user_role;")
