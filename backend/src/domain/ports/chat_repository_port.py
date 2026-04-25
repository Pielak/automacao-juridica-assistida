"""Porta (interface abstrata) para o repositório de chat.

Define o contrato que qualquer implementação concreta de repositório
de chat deve seguir, conforme os princípios de Clean Architecture
(Ports & Adapters). A camada de domínio depende apenas desta interface,
nunca de implementações concretas de infraestrutura.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Protocol, runtime_checkable

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Entidades de domínio leves (value objects / DTOs internos do domínio)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ChatSession:
    """Representa uma sessão de chat entre o usuário e o assistente jurídico."""

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime
    is_archived: bool = False
    metadata: dict | None = field(default=None)


@dataclass(frozen=True)
class ChatMessage:
    """Representa uma mensagem individual dentro de uma sessão de chat."""

    id: uuid.UUID
    session_id: uuid.UUID
    role: str  # "user" | "assistant" | "system"
    content: str
    created_at: datetime
    token_count: int | None = None
    model: str | None = None
    metadata: dict | None = field(default=None)


# ---------------------------------------------------------------------------
# Porta do repositório
# ---------------------------------------------------------------------------

@runtime_checkable
class ChatRepositoryPort(Protocol):
    """Interface abstrata (Protocol) para o repositório de chat.

    Toda implementação concreta — seja via SQLAlchemy, repositório
    em memória para testes, ou qualquer outro adaptador — deve
    satisfazer este contrato.
    """

    # -------------------------------------------------------------------
    # Operações de sessão
    # -------------------------------------------------------------------

    async def create_session(
        self,
        user_id: uuid.UUID,
        title: str,
        metadata: dict | None = None,
    ) -> ChatSession:
        """Cria uma nova sessão de chat para o usuário.

        Args:
            user_id: Identificador único do usuário proprietário.
            title: Título descritivo da sessão.
            metadata: Dados adicionais opcionais (ex.: contexto do documento).

        Returns:
            A sessão de chat recém-criada.

        Raises:
            RepositoryError: Em caso de falha na persistência.
        """
        ...

    async def get_session_by_id(
        self,
        session_id: uuid.UUID,
    ) -> ChatSession | None:
        """Recupera uma sessão de chat pelo seu identificador.

        Args:
            session_id: Identificador único da sessão.

        Returns:
            A sessão encontrada ou ``None`` se não existir.
        """
        ...

    async def list_sessions_by_user(
        self,
        user_id: uuid.UUID,
        *,
        include_archived: bool = False,
        offset: int = 0,
        limit: int = 50,
    ) -> list[ChatSession]:
        """Lista as sessões de chat de um usuário com paginação.

        Args:
            user_id: Identificador único do usuário.
            include_archived: Se ``True``, inclui sessões arquivadas.
            offset: Deslocamento para paginação.
            limit: Quantidade máxima de registros retornados.

        Returns:
            Lista ordenada por data de atualização (mais recente primeiro).
        """
        ...

    async def update_session(
        self,
        session_id: uuid.UUID,
        *,
        title: str | None = None,
        is_archived: bool | None = None,
        metadata: dict | None = None,
    ) -> ChatSession | None:
        """Atualiza campos de uma sessão existente.

        Apenas os campos fornecidos (não ``None``) serão atualizados.

        Args:
            session_id: Identificador único da sessão.
            title: Novo título, se fornecido.
            is_archived: Novo estado de arquivamento, se fornecido.
            metadata: Novos metadados, se fornecidos.

        Returns:
            A sessão atualizada ou ``None`` se não encontrada.
        """
        ...

    async def delete_session(
        self,
        session_id: uuid.UUID,
    ) -> bool:
        """Remove permanentemente uma sessão e todas as suas mensagens.

        Args:
            session_id: Identificador único da sessão.

        Returns:
            ``True`` se a sessão foi removida, ``False`` se não existia.
        """
        ...

    async def count_sessions_by_user(
        self,
        user_id: uuid.UUID,
        *,
        include_archived: bool = False,
    ) -> int:
        """Conta o total de sessões de um usuário.

        Args:
            user_id: Identificador único do usuário.
            include_archived: Se ``True``, inclui sessões arquivadas na contagem.

        Returns:
            Número total de sessões.
        """
        ...

    # -------------------------------------------------------------------
    # Operações de mensagem
    # -------------------------------------------------------------------

    async def add_message(
        self,
        session_id: uuid.UUID,
        role: str,
        content: str,
        *,
        token_count: int | None = None,
        model: str | None = None,
        metadata: dict | None = None,
    ) -> ChatMessage:
        """Adiciona uma mensagem a uma sessão de chat.

        Args:
            session_id: Identificador da sessão à qual a mensagem pertence.
            role: Papel do autor (``user``, ``assistant`` ou ``system``).
            content: Conteúdo textual da mensagem.
            token_count: Contagem de tokens consumidos (para controle de custo).
            model: Identificador do modelo de IA utilizado (ex.: ``claude-3-sonnet``).
            metadata: Dados adicionais opcionais.

        Returns:
            A mensagem recém-criada.

        Raises:
            RepositoryError: Se a sessão não existir ou houver falha na persistência.
        """
        ...

    async def get_messages_by_session(
        self,
        session_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[ChatMessage]:
        """Recupera as mensagens de uma sessão com paginação.

        Args:
            session_id: Identificador da sessão.
            offset: Deslocamento para paginação.
            limit: Quantidade máxima de mensagens retornadas.

        Returns:
            Lista de mensagens ordenadas cronologicamente (mais antiga primeiro).
        """
        ...

    async def get_last_messages(
        self,
        session_id: uuid.UUID,
        count: int = 10,
    ) -> list[ChatMessage]:
        """Recupera as últimas N mensagens de uma sessão.

        Útil para construir o contexto de prompt enviado à API da Anthropic,
        respeitando limites de janela de contexto.

        Args:
            session_id: Identificador da sessão.
            count: Número máximo de mensagens a retornar.

        Returns:
            Lista de mensagens ordenadas cronologicamente (mais antiga primeiro).
        """
        ...

    async def count_messages_by_session(
        self,
        session_id: uuid.UUID,
    ) -> int:
        """Conta o total de mensagens em uma sessão.

        Args:
            session_id: Identificador da sessão.

        Returns:
            Número total de mensagens na sessão.
        """
        ...

    async def get_total_tokens_by_session(
        self,
        session_id: uuid.UUID,
    ) -> int:
        """Calcula o total de tokens consumidos em uma sessão.

        Essencial para controle de custos e respeito aos limites
        da API da Anthropic.

        Args:
            session_id: Identificador da sessão.

        Returns:
            Soma dos tokens de todas as mensagens da sessão.
        """
        ...

    async def delete_messages_by_session(
        self,
        session_id: uuid.UUID,
    ) -> int:
        """Remove todas as mensagens de uma sessão (limpa o histórico).

        Args:
            session_id: Identificador da sessão.

        Returns:
            Número de mensagens removidas.
        """
        ...
