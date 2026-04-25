"""Rotas de auditoria — Automação Jurídica Assistida.

Endpoints para consulta da trilha de auditoria do sistema.
Acesso restrito a administradores (admin only).

Endpoints:
    GET /audit/logs — Lista eventos de auditoria com filtros por entidade,
                      usuário e período.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Dependências internas (peers declarados)
# ---------------------------------------------------------------------------
from backend.src.api.dependencies import (
    get_current_user,
    get_db_session,
)
from backend.src.application.use_cases.audit_use_cases import (
    AuditLogFilters,
    AuditLogResult,
    ListAuditLogsUseCase,
)

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(
    prefix="/audit",
    tags=["Auditoria"],
    responses={
        401: {"description": "Não autenticado"},
        403: {"description": "Acesso negado — somente administradores"},
    },
)


# ---------------------------------------------------------------------------
# Schemas de resposta (Pydantic v2)
# ---------------------------------------------------------------------------


class AuditLogEntryResponse(BaseModel):
    """Representação de um registro individual da trilha de auditoria."""

    id: UUID = Field(..., description="Identificador único do evento de auditoria")
    entity_type: str = Field(..., description="Tipo da entidade afetada (ex: document, user)")
    entity_id: Optional[str] = Field(None, description="Identificador da entidade afetada")
    action: str = Field(..., description="Ação realizada (ex: create, update, delete, access)")
    user_id: Optional[UUID] = Field(None, description="Identificador do usuário que executou a ação")
    user_email: Optional[str] = Field(None, description="E-mail do usuário que executou a ação")
    details: Optional[dict[str, Any]] = Field(
        None, description="Detalhes adicionais do evento em formato livre"
    )
    ip_address: Optional[str] = Field(None, description="Endereço IP de origem da requisição")
    created_at: datetime = Field(..., description="Data e hora do evento (UTC)")

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    """Resposta paginada da listagem de eventos de auditoria."""

    items: list[AuditLogEntryResponse] = Field(
        default_factory=list, description="Lista de registros de auditoria"
    )
    total: int = Field(..., description="Total de registros encontrados")
    page: int = Field(..., description="Página atual")
    page_size: int = Field(..., description="Quantidade de itens por página")
    pages: int = Field(..., description="Total de páginas disponíveis")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_admin(current_user: Any) -> None:
    """Verifica se o usuário corrente possui perfil de administrador.

    Raises:
        HTTPException: 403 caso o usuário não seja administrador.
    """
    # O objeto `current_user` retornado por `get_current_user` deve expor
    # um atributo `role` (ou equivalente). Ajuste o nome do atributo
    # conforme a implementação concreta do modelo de usuário.
    user_role: Optional[str] = getattr(current_user, "role", None)
    if user_role is None:
        user_role = getattr(current_user, "profile", None)

    if user_role not in ("admin", "administrator", "superadmin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Somente administradores podem consultar a trilha de auditoria.",
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/logs",
    response_model=AuditLogListResponse,
    summary="Listar eventos de auditoria",
    description=(
        "Retorna a trilha de auditoria do sistema com suporte a filtros por "
        "tipo de entidade, identificador de usuário e intervalo de datas. "
        "Acesso restrito a administradores."
    ),
    status_code=status.HTTP_200_OK,
)
async def list_audit_logs(
    # --- Filtros ---
    entity_type: Optional[str] = Query(
        None,
        description="Filtrar por tipo de entidade (ex: document, user, analysis)",
        examples=["document"],
    ),
    entity_id: Optional[str] = Query(
        None,
        description="Filtrar por identificador específico da entidade",
    ),
    user_id: Optional[UUID] = Query(
        None,
        description="Filtrar por identificador do usuário que executou a ação",
    ),
    action: Optional[str] = Query(
        None,
        description="Filtrar por tipo de ação (ex: create, update, delete, access)",
        examples=["create"],
    ),
    start_date: Optional[datetime] = Query(
        None,
        description="Início do período de busca (ISO 8601, UTC)",
        examples=["2024-01-01T00:00:00Z"],
    ),
    end_date: Optional[datetime] = Query(
        None,
        description="Fim do período de busca (ISO 8601, UTC)",
        examples=["2024-12-31T23:59:59Z"],
    ),
    # --- Paginação ---
    page: int = Query(
        1,
        ge=1,
        description="Número da página (inicia em 1)",
    ),
    page_size: int = Query(
        20,
        ge=1,
        le=100,
        description="Quantidade de registros por página (máx. 100)",
    ),
    # --- Dependências injetadas ---
    current_user: Any = Depends(get_current_user),
    db_session: Any = Depends(get_db_session),
) -> AuditLogListResponse:
    """Lista eventos de auditoria com filtros opcionais.

    Somente usuários com perfil de administrador podem acessar este endpoint.
    Os resultados são paginados e ordenados do mais recente para o mais antigo.

    Args:
        entity_type: Tipo da entidade para filtro.
        entity_id: ID da entidade para filtro.
        user_id: ID do usuário executor para filtro.
        action: Tipo de ação para filtro.
        start_date: Data/hora inicial do período.
        end_date: Data/hora final do período.
        page: Página desejada.
        page_size: Itens por página.
        current_user: Usuário autenticado (injetado).
        db_session: Sessão do banco de dados (injetada).

    Returns:
        AuditLogListResponse com os registros encontrados e metadados de paginação.

    Raises:
        HTTPException 403: Usuário não é administrador.
        HTTPException 422: Parâmetros de consulta inválidos.
    """
    # Verificação de autorização — admin only
    _require_admin(current_user)

    # Validação de intervalo de datas
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A data de início não pode ser posterior à data de fim.",
        )

    # Monta filtros para o use case
    # TODO: Confirmar se AuditLogFilters é o dataclass correto exportado
    # por audit_use_cases.py. Caso o nome ou campos difiram, ajustar aqui.
    filters = AuditLogFilters(
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=str(user_id) if user_id else None,
        action=action,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )

    # TODO: Obter instância do use case via factory de dependências quando
    # disponível (ex: get_list_audit_logs_use_case em dependencies.py).
    # Por ora, instanciamos diretamente passando a sessão do banco.
    use_case = ListAuditLogsUseCase(db_session=db_session)

    try:
        result: AuditLogResult = await use_case.execute(filters)
    except Exception as exc:
        # Log estruturado do erro (structlog recomendado na stack)
        # TODO: Substituir por structlog quando configurado globalmente.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao consultar a trilha de auditoria. Tente novamente mais tarde.",
        ) from exc

    # Calcula total de páginas
    total = result.total if hasattr(result, "total") else 0
    pages = max(1, -(-total // page_size))  # ceil division sem import math

    # Monta resposta
    items = [
        AuditLogEntryResponse(
            id=entry.id,
            entity_type=entry.entity_type,
            entity_id=getattr(entry, "entity_id", None),
            action=entry.action,
            user_id=getattr(entry, "user_id", None),
            user_email=getattr(entry, "user_email", None),
            details=getattr(entry, "details", None),
            ip_address=getattr(entry, "ip_address", None),
            created_at=entry.created_at,
        )
        for entry in (result.items if hasattr(result, "items") else [])
    ]

    return AuditLogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )
