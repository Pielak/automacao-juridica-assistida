"""Models SQLAlchemy para sessões de chat e mensagens — Automação Jurídica Assistida.

Define os modelos `ChatSession` e `ChatMessage` que representam o histórico
de interações dos usuários com a IA (Claude/Anthropic). Cada sessão agrupa
uma conversa completa, e cada mensagem registra o conteúdo trocado entre
o usuário e o assistente, incluindo metadados de tokens e modelo utilizado.

Exemplo de uso:
    from backend.src.infrastructure.database.models.chat_session import (
        ChatSession,
        ChatMessage,
    )

    # Criar uma nova sessão de chat
    session = ChatSession(
        user_id=user_id,
        title="Análise de contrato de locação",
    )

    # Adicionar uma mensagem à sessão
    message = ChatMessage(
        session_id=session.id,
        role="user",
        content="Quais são as cláusulas abusivas neste contrato?",
    )
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Classe base declarativa do SQLAlchemy.

    Caso o projeto já possua uma Base compartilhada em outro módulo,
    substitua esta importação pela Base centralizada.
    """

    # TODO: Substituir por import da Base centralizada do projeto quando disponível.
    # Exemplo: from backend.src.infrastructure.database.base import Base
    pass


class MessageRole(str, enum.Enum):
    """Enum que representa o papel do autor de uma mensagem no chat.

    Valores:
        USER: Mensagem enviada pelo usuário.
        ASSISTANT: Resposta gerada pela IA.
        SYSTEM: Mensagem de sistema (prompt de contexto, instruções).
    """

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatSessionStatus(str, enum.Enum):
    """Enum que representa o status de uma sessão de chat.

    Valores:
        ACTIVE: Sessão ativa, aceitando novas mensagens.
        ARCHIVED: Sessão arquivada pelo usuário.
        DELETED: Sessão marcada para exclusão (soft delete).
    """

    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class ChatSession(Base):
    """Model que representa uma sessão de chat com a IA.

    Cada sessão pertence a um usuário e agrupa uma conversa completa,
    incluindo título, status, metadados de contexto e referências
    opcionais a documentos jurídicos analisados.

    Attributes:
        id: Identificador único da sessão (UUID v4).
        user_id: ID do usuário proprietário da sessão.
        title: Título descritivo da sessão de chat.
        status: Status atual da sessão (active, archived, deleted).
        model_name: Nome do modelo de IA utilizado (ex: claude-3-sonnet).
        system_prompt: Prompt de sistema utilizado para contextualizar a IA.
        context_metadata: Metadados adicionais de contexto em formato JSON.
        document_id: Referência opcional ao documento jurídico em análise.
        total_tokens_used: Total acumulado de tokens consumidos na sessão.
        message_count: Contagem de mensagens na sessão (cache desnormalizado).
        last_message_at: Timestamp da última mensagem enviada.
        created_at: Timestamp de criação do registro.
        updated_at: Timestamp da última atualização do registro.
        is_active: Flag de soft delete (False = logicamente excluído).
    """

    __tablename__ = "chat_sessions"
    __table_args__ = (
        Index("ix_chat_sessions_user_id_status", "user_id", "status"),
        Index("ix_chat_sessions_user_id_created_at", "user_id", "created_at"),
        Index(
            "ix_chat_sessions_user_id_last_message",
            "user_id",
            "last_message_at",
        ),
        {"comment": "Sessões de chat dos usuários com a IA assistente jurídica"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único da sessão de chat",
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID do usuário proprietário da sessão",
    )

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        default="Nova conversa",
        comment="Título descritivo da sessão de chat",
    )

    status: Mapped[ChatSessionStatus] = mapped_column(
        Enum(ChatSessionStatus, name="chat_session_status", native_enum=True),
        nullable=False,
        default=ChatSessionStatus.ACTIVE,
        comment="Status atual da sessão",
    )

    model_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default="claude-3-sonnet-20240229",
        comment="Nome/versão do modelo de IA utilizado",
    )

    system_prompt: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Prompt de sistema para contextualização da IA",
    )

    context_metadata: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
        comment="Metadados adicionais de contexto (área jurídica, tags, etc.)",
    )

    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Referência opcional ao documento jurídico em análise",
    )

    total_tokens_used: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total acumulado de tokens consumidos na sessão",
    )

    message_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Contagem de mensagens na sessão (cache desnormalizado)",
    )

    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp da última mensagem enviada",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp de criação do registro",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp da última atualização",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Flag de soft delete (False = logicamente excluído)",
    )

    # --- Relacionamentos ---

    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at.asc()",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """Representação textual da sessão de chat."""
        return (
            f"<ChatSession(id={self.id!r}, user_id={self.user_id!r}, "
            f"title={self.title!r}, status={self.status!r}, "
            f"messages={self.message_count})>"
        )


class ChatMessage(Base):
    """Model que representa uma mensagem individual dentro de uma sessão de chat.

    Registra o conteúdo trocado entre o usuário e o assistente de IA,
    incluindo metadados de consumo de tokens, latência e possíveis erros.

    Attributes:
        id: Identificador único da mensagem (UUID v4).
        session_id: ID da sessão de chat à qual a mensagem pertence.
        role: Papel do autor da mensagem (user, assistant, system).
        content: Conteúdo textual da mensagem.
        input_tokens: Quantidade de tokens de entrada consumidos (para respostas da IA).
        output_tokens: Quantidade de tokens de saída gerados (para respostas da IA).
        model_name: Modelo específico utilizado para gerar esta resposta.
        latency_ms: Latência em milissegundos da chamada à API da IA.
        error_message: Mensagem de erro caso a geração tenha falhado.
        metadata_extra: Metadados adicionais da mensagem em formato JSON.
        parent_message_id: Referência opcional à mensagem pai (para threads).
        created_at: Timestamp de criação do registro.
        is_active: Flag de soft delete.
    """

    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_messages_session_id_created_at", "session_id", "created_at"),
        Index("ix_chat_messages_session_id_role", "session_id", "role"),
        {
            "comment": "Mensagens individuais das sessões de chat com a IA assistente jurídica"
        },
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único da mensagem",
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID da sessão de chat à qual a mensagem pertence",
    )

    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, name="message_role", native_enum=True),
        nullable=False,
        comment="Papel do autor da mensagem (user, assistant, system)",
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Conteúdo textual da mensagem",
    )

    input_tokens: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        default=None,
        comment="Tokens de entrada consumidos (respostas da IA)",
    )

    output_tokens: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        default=None,
        comment="Tokens de saída gerados (respostas da IA)",
    )

    model_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default=None,
        comment="Modelo específico utilizado para gerar esta resposta",
    )

    latency_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        default=None,
        comment="Latência em milissegundos da chamada à API da IA",
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="Mensagem de erro caso a geração tenha falhado",
    )

    metadata_extra: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
        comment="Metadados adicionais da mensagem (fontes citadas, confiança, etc.)",
    )

    parent_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_messages.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
        comment="Referência opcional à mensagem pai (para threads de conversa)",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp de criação do registro",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Flag de soft delete (False = logicamente excluído)",
    )

    # --- Relacionamentos ---

    session: Mapped["ChatSession"] = relationship(
        "ChatSession",
        back_populates="messages",
    )

    parent_message: Mapped["ChatMessage | None"] = relationship(
        "ChatMessage",
        remote_side="ChatMessage.id",
        foreign_keys=[parent_message_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """Representação textual da mensagem de chat."""
        content_preview = (
            self.content[:50] + "..." if self.content and len(self.content) > 50 else self.content
        )
        return (
            f"<ChatMessage(id={self.id!r}, session_id={self.session_id!r}, "
            f"role={self.role!r}, content={content_preview!r})>"
        )

    @property
    def total_tokens(self) -> int | None:
        """Retorna o total de tokens consumidos pela mensagem.

        Returns:
            Soma de input_tokens e output_tokens, ou None se ambos forem nulos.
        """
        if self.input_tokens is None and self.output_tokens is None:
            return None
        return (self.input_tokens or 0) + (self.output_tokens or 0)
