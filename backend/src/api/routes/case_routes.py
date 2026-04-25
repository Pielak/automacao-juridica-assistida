"""Rotas da API para o módulo de casos/processos jurídicos.

Implementa os endpoints CRUD para gerenciamento de processos cíveis
no sistema de Automação Jurídica Assistida:
- GET    /cases      — Listagem paginada com filtros
- GET    /cases/{id} — Detalhamento de um caso específico
- POST   /cases      — Criação de novo caso
- PUT    /cases/{id} — Atualização de caso existente
- DELETE /cases/{id} — Remoção lógica de caso

Segue Clean Architecture: os endpoints dependem apenas de use cases
injetados via dependencies, sem acoplamento direto a repositórios
ou infraestrutura.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.src.api.dependencies import (
    get_current_user,
    get_create_case_use_case,
    get_delete_case_use_case,
    get_get_case_use_case,
    get_list_cases_use_case,
    get_update_case_use_case,
)
from backend.src.application.use_cases.case_use_cases import (
    CreateCaseUseCase,
    DeleteCaseUseCase,
    GetCaseUseCase,
    ListCasesUseCase,
    UpdateCaseUseCase,
)

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/cases",
    tags=["Casos / Processos"],
    responses={
        401: {"description": "Não autenticado"},
        403: {"description": "Sem permissão para acessar este recurso"},
    },
)


# ---------------------------------------------------------------------------
# Schemas de request / response (Pydantic v2)
# ---------------------------------------------------------------------------


class CaseCreateRequest(BaseModel):
    """Schema de criação de um novo caso/processo."""

    title: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Título descritivo do caso/processo",
        examples=["Ação de Indenização — João vs. Empresa X"],
    )
    case_number: Optional[str] = Field(
        None,
        max_length=50,
        description="Número do processo no tribunal (formato CNJ, se disponível)",
        examples=["0001234-56.2024.8.26.0100"],
    )
    description: Optional[str] = Field(
        None,
        max_length=5000,
        description="Descrição detalhada do caso",
    )
    case_type: Optional[str] = Field(
        None,
        max_length=100,
        description="Tipo/natureza do processo (ex.: cível, trabalhista, tributário)",
        examples=["cível"],
    )
    court: Optional[str] = Field(
        None,
        max_length=255,
        description="Tribunal ou vara responsável",
        examples=["1ª Vara Cível — Foro Central — São Paulo/SP"],
    )
    plaintiff: Optional[str] = Field(
        None,
        max_length=255,
        description="Nome do autor/requerente",
    )
    defendant: Optional[str] = Field(
        None,
        max_length=255,
        description="Nome do réu/requerido",
    )
    metadata: Optional[dict[str, Any]] = Field(
        None,
        description="Metadados adicionais do caso em formato livre",
    )


class CaseUpdateRequest(BaseModel):
    """Schema de atualização parcial de um caso/processo."""

    title: Optional[str] = Field(
        None,
        min_length=3,
        max_length=255,
        description="Título descritivo do caso/processo",
    )
    case_number: Optional[str] = Field(
        None,
        max_length=50,
        description="Número do processo no tribunal",
    )
    description: Optional[str] = Field(
        None,
        max_length=5000,
        description="Descrição detalhada do caso",
    )
    case_type: Optional[str] = Field(
        None,
        max_length=100,
        description="Tipo/natureza do processo",
    )
    court: Optional[str] = Field(
        None,
        max_length=255,
        description="Tribunal ou vara responsável",
    )
    plaintiff: Optional[str] = Field(
        None,
        max_length=255,
        description="Nome do autor/requerente",
    )
    defendant: Optional[str] = Field(
        None,
        max_length=255,
        description="Nome do réu/requerido",
    )
    status: Optional[str] = Field(
        None,
        max_length=50,
        description="Status do caso (ex.: ativo, arquivado, suspenso)",
    )
    metadata: Optional[dict[str, Any]] = Field(
        None,
        description="Metadados adicionais do caso",
    )


class CaseResponse(BaseModel):
    """Schema de resposta para um caso/processo."""

    id: UUID = Field(..., description="Identificador único do caso")
    title: str = Field(..., description="Título do caso")
    case_number: Optional[str] = Field(None, description="Número do processo")
    description: Optional[str] = Field(None, description="Descrição do caso")
    case_type: Optional[str] = Field(None, description="Tipo do processo")
    court: Optional[str] = Field(None, description="Tribunal ou vara")
    plaintiff: Optional[str] = Field(None, description="Autor/requerente")
    defendant: Optional[str] = Field(None, description="Réu/requerido")
    status: str = Field(..., description="Status atual do caso")
    owner_id: UUID = Field(..., description="ID do usuário proprietário")
    metadata: Optional[dict[str, Any]] = Field(None, description="Metadados adicionais")
    created_at: datetime = Field(..., description="Data de criação")
    updated_at: datetime = Field(..., description="Data da última atualização")

    model_config = {"from_attributes": True}


class PaginatedCaseResponse(BaseModel):
    """Schema de resposta paginada para listagem de casos."""

    items: list[CaseResponse] = Field(..., description="Lista de casos retornados")
    total: int = Field(..., ge=0, description="Total de registros encontrados")
    page: int = Field(..., ge=1, description="Página atual")
    page_size: int = Field(..., ge=1, description="Tamanho da página")
    pages: int = Field(..., ge=0, description="Total de páginas disponíveis")


class MessageResponse(BaseModel):
    """Schema genérico de resposta com mensagem."""

    message: str = Field(..., description="Mensagem descritiva da operação")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=PaginatedCaseResponse,
    summary="Listar casos/processos",
    description="Retorna lista paginada de casos do usuário autenticado, com filtros opcionais.",
)
async def list_cases(
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página"),
    search: Optional[str] = Query(
        None,
        max_length=255,
        description="Busca textual por título, número do processo ou descrição",
    ),
    case_type: Optional[str] = Query(
        None,
        max_length=100,
        description="Filtrar por tipo de processo",
    ),
    status: Optional[str] = Query(
        None,
        max_length=50,
        description="Filtrar por status (ex.: ativo, arquivado)",
    ),
    court: Optional[str] = Query(
        None,
        max_length=255,
        description="Filtrar por tribunal/vara",
    ),
    sort_by: str = Query(
        "created_at",
        description="Campo para ordenação (created_at, updated_at, title)",
    ),
    sort_order: str = Query(
        "desc",
        description="Direção da ordenação (asc, desc)",
    ),
    current_user: dict = Depends(get_current_user),
    use_case: ListCasesUseCase = Depends(get_list_cases_use_case),
) -> PaginatedCaseResponse:
    """Lista casos/processos com paginação e filtros.

    Retorna apenas os casos que o usuário autenticado tem permissão
    para visualizar, respeitando as regras de RBAC.
    """
    logger.info(
        "Listando casos",
        user_id=str(current_user.get("id")),
        page=page,
        page_size=page_size,
        search=search,
    )

    # Validação do campo de ordenação
    allowed_sort_fields = {"created_at", "updated_at", "title", "case_number", "status"}
    if sort_by not in allowed_sort_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Campo de ordenação inválido: '{sort_by}'. "
            f"Campos permitidos: {', '.join(sorted(allowed_sort_fields))}",
        )

    if sort_order.lower() not in {"asc", "desc"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Direção de ordenação inválida. Use 'asc' ou 'desc'.",
        )

    try:
        # TODO: Ajustar parâmetros conforme assinatura real de ListCasesUseCase.execute
        result = await use_case.execute(
            user_id=current_user["id"],
            page=page,
            page_size=page_size,
            search=search,
            case_type=case_type,
            status=status,
            court=court,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except Exception as exc:
        logger.error("Erro ao listar casos", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao listar casos. Tente novamente mais tarde.",
        ) from exc

    # Calcula total de páginas
    total = result.get("total", 0) if isinstance(result, dict) else getattr(result, "total", 0)
    items = result.get("items", []) if isinstance(result, dict) else getattr(result, "items", [])
    pages = (total + page_size - 1) // page_size if total > 0 else 0

    return PaginatedCaseResponse(
        items=[CaseResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/{case_id}",
    response_model=CaseResponse,
    summary="Obter detalhes de um caso",
    description="Retorna os detalhes completos de um caso/processo específico.",
)
async def get_case(
    case_id: UUID,
    current_user: dict = Depends(get_current_user),
    use_case: GetCaseUseCase = Depends(get_get_case_use_case),
) -> CaseResponse:
    """Obtém detalhes de um caso específico pelo ID.

    Verifica se o usuário autenticado tem permissão para acessar o caso.
    """
    logger.info(
        "Buscando caso",
        case_id=str(case_id),
        user_id=str(current_user.get("id")),
    )

    try:
        # TODO: Ajustar parâmetros conforme assinatura real de GetCaseUseCase.execute
        result = await use_case.execute(
            case_id=case_id,
            user_id=current_user["id"],
        )
    except Exception as exc:
        logger.error("Erro ao buscar caso", case_id=str(case_id), error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao buscar caso. Tente novamente mais tarde.",
        ) from exc

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Caso com ID '{case_id}' não encontrado ou sem permissão de acesso.",
        )

    return CaseResponse.model_validate(result)


@router.post(
    "",
    response_model=CaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar novo caso/processo",
    description="Cria um novo caso/processo jurídico vinculado ao usuário autenticado.",
)
async def create_case(
    payload: CaseCreateRequest,
    current_user: dict = Depends(get_current_user),
    use_case: CreateCaseUseCase = Depends(get_create_case_use_case),
) -> CaseResponse:
    """Cria um novo caso/processo jurídico.

    O caso é automaticamente vinculado ao usuário autenticado como
    proprietário (owner).
    """
    logger.info(
        "Criando novo caso",
        user_id=str(current_user.get("id")),
        title=payload.title,
    )

    try:
        # TODO: Ajustar parâmetros conforme assinatura real de CreateCaseUseCase.execute
        result = await use_case.execute(
            owner_id=current_user["id"],
            title=payload.title,
            case_number=payload.case_number,
            description=payload.description,
            case_type=payload.case_type,
            court=payload.court,
            plaintiff=payload.plaintiff,
            defendant=payload.defendant,
            metadata=payload.metadata,
        )
    except ValueError as exc:
        logger.warning(
            "Dados inválidos na criação de caso",
            error=str(exc),
            user_id=str(current_user.get("id")),
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("Erro ao criar caso", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao criar caso. Tente novamente mais tarde.",
        ) from exc

    logger.info(
        "Caso criado com sucesso",
        case_id=str(getattr(result, "id", None)),
        user_id=str(current_user.get("id")),
    )

    return CaseResponse.model_validate(result)


@router.put(
    "/{case_id}",
    response_model=CaseResponse,
    summary="Atualizar caso/processo",
    description="Atualiza os dados de um caso/processo existente.",
)
async def update_case(
    case_id: UUID,
    payload: CaseUpdateRequest,
    current_user: dict = Depends(get_current_user),
    use_case: UpdateCaseUseCase = Depends(get_update_case_use_case),
) -> CaseResponse:
    """Atualiza um caso/processo existente.

    Apenas campos enviados no payload serão atualizados (atualização parcial).
    Verifica permissão do usuário antes de aplicar as alterações.
    """
    logger.info(
        "Atualizando caso",
        case_id=str(case_id),
        user_id=str(current_user.get("id")),
    )

    # Extrai apenas campos que foram explicitamente enviados
    update_data = payload.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum campo enviado para atualização.",
        )

    try:
        # TODO: Ajustar parâmetros conforme assinatura real de UpdateCaseUseCase.execute
        result = await use_case.execute(
            case_id=case_id,
            user_id=current_user["id"],
            **update_data,
        )
    except ValueError as exc:
        logger.warning(
            "Dados inválidos na atualização de caso",
            case_id=str(case_id),
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(
            "Erro ao atualizar caso",
            case_id=str(case_id),
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao atualizar caso. Tente novamente mais tarde.",
        ) from exc

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Caso com ID '{case_id}' não encontrado ou sem permissão de acesso.",
        )

    logger.info(
        "Caso atualizado com sucesso",
        case_id=str(case_id),
        user_id=str(current_user.get("id")),
    )

    return CaseResponse.model_validate(result)


@router.delete(
    "/{case_id}",
    response_model=MessageResponse,
    summary="Remover caso/processo",
    description="Realiza a remoção lógica (soft delete) de um caso/processo.",
)
async def delete_case(
    case_id: UUID,
    current_user: dict = Depends(get_current_user),
    use_case: DeleteCaseUseCase = Depends(get_delete_case_use_case),
) -> MessageResponse:
    """Remove logicamente um caso/processo.

    A remoção é lógica (soft delete): o registro é marcado como
    removido mas permanece no banco para fins de auditoria e
    conformidade com requisitos de compliance jurídico.
    """
    logger.info(
        "Removendo caso",
        case_id=str(case_id),
        user_id=str(current_user.get("id")),
    )

    try:
        # TODO: Ajustar parâmetros conforme assinatura real de DeleteCaseUseCase.execute
        success = await use_case.execute(
            case_id=case_id,
            user_id=current_user["id"],
        )
    except Exception as exc:
        logger.error(
            "Erro ao remover caso",
            case_id=str(case_id),
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao remover caso. Tente novamente mais tarde.",
        ) from exc

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Caso com ID '{case_id}' não encontrado ou sem permissão de acesso.",
        )

    logger.info(
        "Caso removido com sucesso",
        case_id=str(case_id),
        user_id=str(current_user.get("id")),
    )

    return MessageResponse(
        message=f"Caso '{case_id}' removido com sucesso.",
    )
