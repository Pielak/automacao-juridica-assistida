"""Rotas da API para o módulo de chat jurídico assistido.

Define os endpoints REST para gerenciamento de sessões de chat e mensagens:
- POST /chat/sessions — Iniciar nova sessão de chat
- POST /chat/messages — Enviar mensagem e obter resposta do LLM
- GET /chat/sessions/{session_id}/history — Consultar histórico de mensagens

Todos os endpoints exigem autenticação JWT e seguem os princípios
de Clean Architecture, dependendo apenas de use cases injetados
via dependências do FastAPI.
"""

from __future__ import annotations

import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.src.api.dependencies import (
    get_current_user,
    get_chat_use_cases,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(
    prefix="/chat",
    tags=["Chat Jurídico"],
    responses={
        401: {"description": "Não autenticado — token JWT ausente ou inválido."},
        403: {"description": "Sem permissão para acessar este recurso."},
    },
)

# ---------------------------------------------------------------------------
# Schemas de request / response (Pydantic v2)
# ---------------------------------------------------------------------------


class CreateSessionRequest(BaseModel):
    """Payload para criação de uma nova sessão de chat."""

    title: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Título opcional da sessão de chat. Se não informado, será gerado automaticamente.",
        examples=["Análise de contrato de locação"],
    )
    document_id: Optional[uuid.UUID] = Field(
        default=None,
        description="ID do documento jurídico associado à sessão, se houver.",
    )
    context_metadata: Optional[dict] = Field(
        default=None,
        description="Metadados adicionais de contexto para a sessão (ex.: área do direito, tipo de análise).",
    )


class SessionResponse(BaseModel):
    """Representação de uma sessão de chat na resposta da API."""

    id: uuid.UUID = Field(description="Identificador único da sessão.")
    title: Optional[str] = Field(description="Título da sessão.")
    document_id: Optional[uuid.UUID] = Field(description="ID do documento associado.")
    user_id: uuid.UUID = Field(description="ID do usuário proprietário da sessão.")
    created_at: str = Field(description="Data/hora de criação (ISO 8601).")
    is_active: bool = Field(description="Indica se a sessão está ativa.")

    model_config = {"from_attributes": True}


class SendMessageRequest(BaseModel):
    """Payload para envio de mensagem em uma sessão de chat."""

    session_id: uuid.UUID = Field(
        description="ID da sessão de chat onde a mensagem será enviada.",
    )
    content: str = Field(
        min_length=1,
        max_length=10_000,
        description="Conteúdo da mensagem do usuário.",
        examples=["Quais são as cláusulas abusivas neste contrato?"],
    )


class MessageResponse(BaseModel):
    """Representação de uma mensagem individual na resposta da API."""

    id: uuid.UUID = Field(description="Identificador único da mensagem.")
    session_id: uuid.UUID = Field(description="ID da sessão à qual pertence.")
    role: str = Field(
        description="Papel do autor da mensagem: 'user' ou 'assistant'.",
        examples=["user", "assistant"],
    )
    content: str = Field(description="Conteúdo textual da mensagem.")
    created_at: str = Field(description="Data/hora de criação (ISO 8601).")
    token_count: Optional[int] = Field(
        default=None,
        description="Quantidade de tokens consumidos pela mensagem (quando disponível).",
    )

    model_config = {"from_attributes": True}


class SendMessageResponse(BaseModel):
    """Resposta ao envio de mensagem — contém a mensagem do usuário e a resposta do LLM."""

    user_message: MessageResponse = Field(
        description="Mensagem enviada pelo usuário.",
    )
    assistant_message: MessageResponse = Field(
        description="Resposta gerada pelo assistente jurídico (LLM).",
    )


class ChatHistoryResponse(BaseModel):
    """Histórico completo de mensagens de uma sessão de chat."""

    session: SessionResponse = Field(description="Dados da sessão.")
    messages: list[MessageResponse] = Field(
        default_factory=list,
        description="Lista de mensagens ordenadas cronologicamente.",
    )
    total: int = Field(description="Total de mensagens na sessão.")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Iniciar nova sessão de chat",
    description=(
        "Cria uma nova sessão de chat jurídico assistido por IA. "
        "Opcionalmente pode ser vinculada a um documento previamente carregado."
    ),
)
async def create_session(
    payload: CreateSessionRequest,
    current_user=Depends(get_current_user),
    chat_use_cases=Depends(get_chat_use_cases),
) -> SessionResponse:
    """Cria uma nova sessão de chat para o usuário autenticado.

    Args:
        payload: Dados para criação da sessão.
        current_user: Usuário autenticado via JWT.
        chat_use_cases: Instância dos use cases de chat (injetada).

    Returns:
        SessionResponse com os dados da sessão criada.

    Raises:
        HTTPException 422: Dados de entrada inválidos.
        HTTPException 500: Erro interno ao criar a sessão.
    """
    logger.info(
        "Criando nova sessão de chat",
        user_id=str(current_user.id),
        document_id=str(payload.document_id) if payload.document_id else None,
    )

    try:
        # TODO: Verificar assinatura exata do método no chat_use_cases.
        # A chamada abaixo assume que `create_session` aceita os parâmetros
        # user_id, title, document_id e context_metadata conforme definido
        # em backend/src/application/use_cases/chat_use_cases.py.
        session = await chat_use_cases.create_session(
            user_id=current_user.id,
            title=payload.title,
            document_id=payload.document_id,
            context_metadata=payload.context_metadata,
        )
    except ValueError as exc:
        logger.warning(
            "Erro de validação ao criar sessão de chat",
            user_id=str(current_user.id),
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Dados inválidos para criação da sessão: {exc}",
        ) from exc
    except Exception as exc:
        logger.error(
            "Erro inesperado ao criar sessão de chat",
            user_id=str(current_user.id),
            error=str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao criar sessão de chat. Tente novamente mais tarde.",
        ) from exc

    logger.info(
        "Sessão de chat criada com sucesso",
        session_id=str(session.id),
        user_id=str(current_user.id),
    )

    return SessionResponse(
        id=session.id,
        title=session.title,
        document_id=session.document_id,
        user_id=session.user_id,
        created_at=session.created_at.isoformat() if hasattr(session.created_at, "isoformat") else str(session.created_at),
        is_active=session.is_active,
    )


@router.post(
    "/messages",
    response_model=SendMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enviar mensagem no chat",
    description=(
        "Envia uma mensagem do usuário em uma sessão de chat existente "
        "e retorna a resposta gerada pelo assistente jurídico (LLM Anthropic Claude)."
    ),
)
async def send_message(
    payload: SendMessageRequest,
    current_user=Depends(get_current_user),
    chat_use_cases=Depends(get_chat_use_cases),
) -> SendMessageResponse:
    """Envia mensagem e obtém resposta do LLM.

    O use case orquestra:
    1. Validação da sessão e permissões do usuário.
    2. Persistência da mensagem do usuário.
    3. Chamada ao LLM (Anthropic Claude) com contexto da sessão.
    4. Persistência da resposta do assistente.
    5. Registro de auditoria e contagem de tokens.

    Args:
        payload: Dados da mensagem (session_id + conteúdo).
        current_user: Usuário autenticado via JWT.
        chat_use_cases: Instância dos use cases de chat (injetada).

    Returns:
        SendMessageResponse com a mensagem do usuário e a resposta do assistente.

    Raises:
        HTTPException 404: Sessão não encontrada.
        HTTPException 403: Sessão não pertence ao usuário.
        HTTPException 422: Dados de entrada inválidos.
        HTTPException 503: Serviço de IA indisponível.
        HTTPException 500: Erro interno.
    """
    logger.info(
        "Enviando mensagem no chat",
        user_id=str(current_user.id),
        session_id=str(payload.session_id),
        content_length=len(payload.content),
    )

    try:
        # TODO: Verificar assinatura exata do método `send_message` no chat_use_cases.
        # Espera-se que retorne um objeto/tupla com a mensagem do usuário e a do assistente.
        result = await chat_use_cases.send_message(
            session_id=payload.session_id,
            user_id=current_user.id,
            content=payload.content,
        )
    except LookupError as exc:
        logger.warning(
            "Sessão de chat não encontrada",
            session_id=str(payload.session_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessão de chat não encontrada.",
        ) from exc
    except PermissionError as exc:
        logger.warning(
            "Acesso negado à sessão de chat",
            session_id=str(payload.session_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para enviar mensagens nesta sessão.",
        ) from exc
    except ConnectionError as exc:
        logger.error(
            "Serviço de IA indisponível",
            session_id=str(payload.session_id),
            error=str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="O serviço de inteligência artificial está temporariamente indisponível. Tente novamente em alguns instantes.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Dados inválidos: {exc}",
        ) from exc
    except Exception as exc:
        logger.error(
            "Erro inesperado ao processar mensagem de chat",
            session_id=str(payload.session_id),
            user_id=str(current_user.id),
            error=str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao processar sua mensagem. Tente novamente mais tarde.",
        ) from exc

    # TODO: Ajustar mapeamento conforme estrutura real retornada pelo use case.
    # Assume-se que `result` possui atributos `user_message` e `assistant_message`.
    user_msg = result.user_message
    assistant_msg = result.assistant_message

    logger.info(
        "Mensagem processada com sucesso",
        session_id=str(payload.session_id),
        user_message_id=str(user_msg.id),
        assistant_message_id=str(assistant_msg.id),
    )

    return SendMessageResponse(
        user_message=MessageResponse(
            id=user_msg.id,
            session_id=user_msg.session_id,
            role=user_msg.role,
            content=user_msg.content,
            created_at=user_msg.created_at.isoformat() if hasattr(user_msg.created_at, "isoformat") else str(user_msg.created_at),
            token_count=getattr(user_msg, "token_count", None),
        ),
        assistant_message=MessageResponse(
            id=assistant_msg.id,
            session_id=assistant_msg.session_id,
            role=assistant_msg.role,
            content=assistant_msg.content,
            created_at=assistant_msg.created_at.isoformat() if hasattr(assistant_msg.created_at, "isoformat") else str(assistant_msg.created_at),
            token_count=getattr(assistant_msg, "token_count", None),
        ),
    )


@router.get(
    "/sessions/{session_id}/history",
    response_model=ChatHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Consultar histórico de mensagens",
    description=(
        "Retorna o histórico completo de mensagens de uma sessão de chat, "
        "ordenado cronologicamente. Suporta paginação via offset e limit."
    ),
)
async def get_session_history(
    session_id: uuid.UUID,
    offset: int = Query(
        default=0,
        ge=0,
        description="Número de mensagens a pular (para paginação).",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Quantidade máxima de mensagens a retornar (entre 1 e 200).",
    ),
    current_user=Depends(get_current_user),
    chat_use_cases=Depends(get_chat_use_cases),
) -> ChatHistoryResponse:
    """Retorna o histórico de mensagens de uma sessão de chat.

    Args:
        session_id: Identificador único da sessão.
        offset: Deslocamento para paginação.
        limit: Limite de mensagens por página.
        current_user: Usuário autenticado via JWT.
        chat_use_cases: Instância dos use cases de chat (injetada).

    Returns:
        ChatHistoryResponse com dados da sessão e lista de mensagens.

    Raises:
        HTTPException 404: Sessão não encontrada.
        HTTPException 403: Sessão não pertence ao usuário.
    """
    logger.info(
        "Consultando histórico de chat",
        session_id=str(session_id),
        user_id=str(current_user.id),
        offset=offset,
        limit=limit,
    )

    try:
        # TODO: Verificar assinatura exata do método `get_session_history` no chat_use_cases.
        history = await chat_use_cases.get_session_history(
            session_id=session_id,
            user_id=current_user.id,
            offset=offset,
            limit=limit,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessão de chat não encontrada.",
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acessar esta sessão de chat.",
        ) from exc
    except Exception as exc:
        logger.error(
            "Erro ao consultar histórico de chat",
            session_id=str(session_id),
            user_id=str(current_user.id),
            error=str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao consultar histórico. Tente novamente mais tarde.",
        ) from exc

    # TODO: Ajustar mapeamento conforme estrutura real retornada pelo use case.
    # Assume-se que `history` possui atributos `session` e `messages`.
    session = history.session
    messages = history.messages

    logger.info(
        "Histórico de chat retornado com sucesso",
        session_id=str(session_id),
        total_messages=len(messages),
    )

    return ChatHistoryResponse(
        session=SessionResponse(
            id=session.id,
            title=session.title,
            document_id=session.document_id,
            user_id=session.user_id,
            created_at=session.created_at.isoformat() if hasattr(session.created_at, "isoformat") else str(session.created_at),
            is_active=session.is_active,
        ),
        messages=[
            MessageResponse(
                id=msg.id,
                session_id=msg.session_id,
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at.isoformat() if hasattr(msg.created_at, "isoformat") else str(msg.created_at),
                token_count=getattr(msg, "token_count", None),
            )
            for msg in messages
        ],
        total=getattr(history, "total", len(messages)),
    )
