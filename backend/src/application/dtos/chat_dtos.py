"""DTOs (Data Transfer Objects) para o módulo de chat.

Define os schemas Pydantic para requisições e respostas
relacionados às sessões de chat e mensagens com o assistente
jurídico baseado em IA (Claude/Anthropic).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatRole(str, Enum):
    """Papel do autor da mensagem no chat."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessageType(str, Enum):
    """Tipo de conteúdo da mensagem."""

    TEXT = "text"
    DOCUMENT_REFERENCE = "document_reference"
    ANALYSIS_RESULT = "analysis_result"


# ---------------------------------------------------------------------------
# Request DTOs
# ---------------------------------------------------------------------------


class ChatSessionCreateRequest(BaseModel):
    """DTO para criação de uma nova sessão de chat."""

    model_config = ConfigDict(strict=True)

    title: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Título opcional da sessão de chat. Se não informado, será gerado automaticamente.",
    )
    document_id: Optional[UUID] = Field(
        default=None,
        description="ID do documento associado à sessão, caso o chat seja contextualizado a um documento específico.",
    )
    context_metadata: Optional[dict] = Field(
        default=None,
        description="Metadados adicionais de contexto para a sessão (ex.: área jurídica, tipo de processo).",
    )


class ChatMessageRequest(BaseModel):
    """DTO para envio de uma mensagem do usuário ao assistente."""

    model_config = ConfigDict(strict=True)

    session_id: UUID = Field(
        ...,
        description="ID da sessão de chat à qual a mensagem pertence.",
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Conteúdo textual da mensagem enviada pelo usuário.",
    )
    message_type: ChatMessageType = Field(
        default=ChatMessageType.TEXT,
        description="Tipo de conteúdo da mensagem.",
    )
    document_ids: Optional[list[UUID]] = Field(
        default=None,
        description="Lista de IDs de documentos referenciados na mensagem para contextualização.",
    )
    include_history: bool = Field(
        default=True,
        description="Se verdadeiro, inclui o histórico da sessão como contexto para o assistente.",
    )
    max_tokens: Optional[int] = Field(
        default=None,
        ge=1,
        le=4096,
        description="Número máximo de tokens na resposta do assistente. Se não informado, usa o padrão do sistema.",
    )
    temperature: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Temperatura de geração (0.0 = determinístico, 1.0 = criativo). Se não informado, usa o padrão do sistema.",
    )


class ChatHistoryRequest(BaseModel):
    """DTO para consulta do histórico de mensagens de uma sessão."""

    model_config = ConfigDict(strict=True)

    session_id: UUID = Field(
        ...,
        description="ID da sessão de chat cujo histórico será consultado.",
    )
    page: int = Field(
        default=1,
        ge=1,
        description="Número da página para paginação do histórico.",
    )
    page_size: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Quantidade de mensagens por página.",
    )
    order: str = Field(
        default="asc",
        pattern="^(asc|desc)$",
        description="Ordenação das mensagens: 'asc' (mais antigas primeiro) ou 'desc' (mais recentes primeiro).",
    )


# ---------------------------------------------------------------------------
# Response DTOs
# ---------------------------------------------------------------------------


class ChatMessageResponse(BaseModel):
    """DTO de resposta representando uma mensagem individual no chat."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(
        ...,
        description="Identificador único da mensagem.",
    )
    session_id: UUID = Field(
        ...,
        description="ID da sessão de chat à qual a mensagem pertence.",
    )
    role: ChatRole = Field(
        ...,
        description="Papel do autor da mensagem (user, assistant, system).",
    )
    content: str = Field(
        ...,
        description="Conteúdo textual da mensagem.",
    )
    message_type: ChatMessageType = Field(
        default=ChatMessageType.TEXT,
        description="Tipo de conteúdo da mensagem.",
    )
    document_ids: Optional[list[UUID]] = Field(
        default=None,
        description="IDs de documentos referenciados na mensagem.",
    )
    token_count: Optional[int] = Field(
        default=None,
        description="Quantidade de tokens consumidos pela mensagem.",
    )
    model_used: Optional[str] = Field(
        default=None,
        description="Identificador do modelo de IA utilizado para gerar a resposta (ex.: claude-3-5-sonnet).",
    )
    latency_ms: Optional[int] = Field(
        default=None,
        description="Latência em milissegundos da chamada à API de IA (apenas para mensagens do assistente).",
    )
    created_at: datetime = Field(
        ...,
        description="Data e hora de criação da mensagem.",
    )


class ChatSessionResponse(BaseModel):
    """DTO de resposta representando uma sessão de chat."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(
        ...,
        description="Identificador único da sessão de chat.",
    )
    user_id: UUID = Field(
        ...,
        description="ID do usuário proprietário da sessão.",
    )
    title: Optional[str] = Field(
        default=None,
        description="Título da sessão de chat.",
    )
    document_id: Optional[UUID] = Field(
        default=None,
        description="ID do documento associado à sessão, se houver.",
    )
    context_metadata: Optional[dict] = Field(
        default=None,
        description="Metadados de contexto da sessão.",
    )
    message_count: int = Field(
        default=0,
        ge=0,
        description="Quantidade total de mensagens na sessão.",
    )
    total_tokens_used: int = Field(
        default=0,
        ge=0,
        description="Total de tokens consumidos na sessão.",
    )
    is_active: bool = Field(
        default=True,
        description="Indica se a sessão está ativa ou foi encerrada.",
    )
    created_at: datetime = Field(
        ...,
        description="Data e hora de criação da sessão.",
    )
    updated_at: datetime = Field(
        ...,
        description="Data e hora da última atualização da sessão.",
    )
    last_message_at: Optional[datetime] = Field(
        default=None,
        description="Data e hora da última mensagem na sessão.",
    )


class ChatSessionDetailResponse(ChatSessionResponse):
    """DTO de resposta detalhada de uma sessão, incluindo mensagens recentes."""

    recent_messages: list[ChatMessageResponse] = Field(
        default_factory=list,
        description="Lista das mensagens mais recentes da sessão.",
    )


class ChatSessionListResponse(BaseModel):
    """DTO de resposta para listagem paginada de sessões de chat."""

    model_config = ConfigDict(from_attributes=True)

    items: list[ChatSessionResponse] = Field(
        ...,
        description="Lista de sessões de chat do usuário.",
    )
    total: int = Field(
        ...,
        ge=0,
        description="Número total de sessões encontradas.",
    )
    page: int = Field(
        ...,
        ge=1,
        description="Página atual.",
    )
    page_size: int = Field(
        ...,
        ge=1,
        description="Tamanho da página.",
    )
    has_next: bool = Field(
        ...,
        description="Indica se existe uma próxima página.",
    )


class ChatMessageListResponse(BaseModel):
    """DTO de resposta para listagem paginada de mensagens de uma sessão."""

    model_config = ConfigDict(from_attributes=True)

    items: list[ChatMessageResponse] = Field(
        ...,
        description="Lista de mensagens da sessão.",
    )
    total: int = Field(
        ...,
        ge=0,
        description="Número total de mensagens na sessão.",
    )
    page: int = Field(
        ...,
        ge=1,
        description="Página atual.",
    )
    page_size: int = Field(
        ...,
        ge=1,
        description="Tamanho da página.",
    )
    has_next: bool = Field(
        ...,
        description="Indica se existe uma próxima página.",
    )


class ChatUsageStatsResponse(BaseModel):
    """DTO de resposta com estatísticas de uso do chat pelo usuário."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID = Field(
        ...,
        description="ID do usuário.",
    )
    total_sessions: int = Field(
        default=0,
        ge=0,
        description="Total de sessões de chat criadas.",
    )
    active_sessions: int = Field(
        default=0,
        ge=0,
        description="Total de sessões ativas.",
    )
    total_messages_sent: int = Field(
        default=0,
        ge=0,
        description="Total de mensagens enviadas pelo usuário.",
    )
    total_tokens_consumed: int = Field(
        default=0,
        ge=0,
        description="Total de tokens consumidos em todas as sessões.",
    )
    period_start: Optional[datetime] = Field(
        default=None,
        description="Início do período de apuração das estatísticas.",
    )
    period_end: Optional[datetime] = Field(
        default=None,
        description="Fim do período de apuração das estatísticas.",
    )
