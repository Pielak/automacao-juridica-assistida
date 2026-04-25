"""Rotas da API para o módulo de análise jurídica assistida por IA.

Endpoints disponíveis:
- POST /analyses — Solicitar nova análise de documento via LLM
- GET /analyses/{analysis_id} — Consultar resultado de uma análise existente
- GET /cases/{case_id}/analyses — Listar análises associadas a um caso

Todos os endpoints requerem autenticação JWT e seguem os princípios
de Clean Architecture, dependendo apenas de use cases injetados via
o sistema de dependências do FastAPI.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.src.api.dependencies import (
    get_current_user,
    get_analysis_use_cases,
)
from backend.src.application.use_cases.analysis_use_cases import AnalysisUseCases

import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Análises"])


# ---------------------------------------------------------------------------
# Schemas de request / response (Pydantic v2)
# ---------------------------------------------------------------------------


class CreateAnalysisRequest(BaseModel):
    """Schema de entrada para solicitar uma nova análise jurídica."""

    document_id: uuid.UUID = Field(
        ...,
        description="Identificador único do documento a ser analisado.",
    )
    case_id: uuid.UUID = Field(
        ...,
        description="Identificador único do caso ao qual o documento pertence.",
    )
    analysis_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description=(
            "Tipo de análise a ser realizada (ex.: 'resumo', 'riscos', "
            "'conformidade', 'parecer')."
        ),
    )
    parameters: dict[str, Any] | None = Field(
        default=None,
        description="Parâmetros adicionais opcionais para personalizar a análise.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "document_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "case_id": "f0e1d2c3-b4a5-6789-0fed-cba987654321",
                    "analysis_type": "resumo",
                    "parameters": {"idioma": "pt-br", "max_tokens": 2000},
                }
            ]
        }
    }


class AnalysisResponse(BaseModel):
    """Schema de resposta representando uma análise jurídica."""

    id: uuid.UUID = Field(description="Identificador único da análise.")
    document_id: uuid.UUID = Field(
        description="Identificador do documento analisado."
    )
    case_id: uuid.UUID = Field(
        description="Identificador do caso associado."
    )
    analysis_type: str = Field(description="Tipo de análise realizada.")
    status: str = Field(
        description=(
            "Estado atual da análise (ex.: 'pendente', 'processando', "
            "'concluida', 'erro')."
        )
    )
    result: dict[str, Any] | None = Field(
        default=None,
        description="Resultado da análise quando concluída.",
    )
    created_at: str = Field(description="Data/hora de criação (ISO 8601).")
    updated_at: str | None = Field(
        default=None,
        description="Data/hora da última atualização (ISO 8601).",
    )
    requested_by: uuid.UUID = Field(
        description="Identificador do usuário que solicitou a análise."
    )

    model_config = {"from_attributes": True}


class AnalysisListResponse(BaseModel):
    """Schema de resposta para listagem paginada de análises."""

    items: list[AnalysisResponse] = Field(
        description="Lista de análises retornadas."
    )
    total: int = Field(description="Total de análises encontradas.")
    page: int = Field(description="Página atual.")
    page_size: int = Field(description="Quantidade de itens por página.")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/analyses",
    response_model=AnalysisResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Solicitar nova análise jurídica",
    description=(
        "Cria uma solicitação de análise de documento jurídico via LLM. "
        "A análise é processada de forma assíncrona e o status pode ser "
        "consultado pelo endpoint GET /analyses/{id}."
    ),
)
async def create_analysis(
    payload: CreateAnalysisRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
    use_cases: AnalysisUseCases = Depends(get_analysis_use_cases),
) -> AnalysisResponse:
    """Solicita uma nova análise jurídica assistida por IA.

    Valida os dados de entrada, verifica permissões do usuário e
    delega a criação ao use case correspondente. O processamento
    real via LLM ocorre de forma assíncrona (Celery).

    Args:
        payload: Dados da solicitação de análise.
        current_user: Usuário autenticado extraído do token JWT.
        use_cases: Instância dos use cases de análise (injetada).

    Returns:
        AnalysisResponse com status inicial 'pendente'.

    Raises:
        HTTPException 404: Documento ou caso não encontrado.
        HTTPException 422: Dados de entrada inválidos.
        HTTPException 500: Erro interno ao processar a solicitação.
    """
    user_id: uuid.UUID = current_user["id"]

    logger.info(
        "Solicitação de nova análise recebida",
        user_id=str(user_id),
        document_id=str(payload.document_id),
        case_id=str(payload.case_id),
        analysis_type=payload.analysis_type,
    )

    try:
        # TODO: O método exato do use case depende da implementação completa
        # de analysis_use_cases.py. Ajustar nome do método e parâmetros
        # conforme a interface final definida no use case.
        result = await use_cases.request_analysis(
            document_id=payload.document_id,
            case_id=payload.case_id,
            analysis_type=payload.analysis_type,
            parameters=payload.parameters,
            requested_by=user_id,
        )
    except ValueError as exc:
        logger.warning(
            "Dados inválidos na solicitação de análise",
            error=str(exc),
            user_id=str(user_id),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recurso não encontrado: {exc}",
        ) from exc
    except Exception as exc:
        logger.error(
            "Erro interno ao solicitar análise",
            error=str(exc),
            user_id=str(user_id),
            document_id=str(payload.document_id),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao processar a solicitação de análise. Tente novamente mais tarde.",
        ) from exc

    logger.info(
        "Análise criada com sucesso",
        analysis_id=str(result.id),
        user_id=str(user_id),
    )

    return AnalysisResponse(
        id=result.id,
        document_id=result.document_id,
        case_id=result.case_id,
        analysis_type=result.analysis_type,
        status=result.status,
        result=result.result,
        created_at=result.created_at.isoformat() if hasattr(result.created_at, "isoformat") else str(result.created_at),
        updated_at=result.updated_at.isoformat() if result.updated_at and hasattr(result.updated_at, "isoformat") else None,
        requested_by=result.requested_by,
    )


@router.get(
    "/analyses/{analysis_id}",
    response_model=AnalysisResponse,
    summary="Consultar resultado de uma análise",
    description=(
        "Retorna os detalhes e o resultado (quando disponível) de uma "
        "análise jurídica previamente solicitada."
    ),
)
async def get_analysis(
    analysis_id: uuid.UUID,
    current_user: dict[str, Any] = Depends(get_current_user),
    use_cases: AnalysisUseCases = Depends(get_analysis_use_cases),
) -> AnalysisResponse:
    """Consulta o resultado de uma análise existente.

    Args:
        analysis_id: Identificador único da análise.
        current_user: Usuário autenticado extraído do token JWT.
        use_cases: Instância dos use cases de análise (injetada).

    Returns:
        AnalysisResponse com dados completos da análise.

    Raises:
        HTTPException 404: Análise não encontrada.
        HTTPException 403: Usuário sem permissão para acessar esta análise.
    """
    user_id: uuid.UUID = current_user["id"]

    logger.info(
        "Consulta de análise solicitada",
        analysis_id=str(analysis_id),
        user_id=str(user_id),
    )

    try:
        # TODO: Ajustar nome do método conforme interface final do use case.
        result = await use_cases.get_analysis(
            analysis_id=analysis_id,
            requested_by=user_id,
        )
    except ValueError as exc:
        logger.warning(
            "Análise não encontrada",
            analysis_id=str(analysis_id),
            user_id=str(user_id),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Análise não encontrada: {analysis_id}",
        ) from exc
    except PermissionError as exc:
        logger.warning(
            "Acesso negado à análise",
            analysis_id=str(analysis_id),
            user_id=str(user_id),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acessar esta análise.",
        ) from exc
    except Exception as exc:
        logger.error(
            "Erro interno ao consultar análise",
            error=str(exc),
            analysis_id=str(analysis_id),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao consultar a análise. Tente novamente mais tarde.",
        ) from exc

    return AnalysisResponse(
        id=result.id,
        document_id=result.document_id,
        case_id=result.case_id,
        analysis_type=result.analysis_type,
        status=result.status,
        result=result.result,
        created_at=result.created_at.isoformat() if hasattr(result.created_at, "isoformat") else str(result.created_at),
        updated_at=result.updated_at.isoformat() if result.updated_at and hasattr(result.updated_at, "isoformat") else None,
        requested_by=result.requested_by,
    )


@router.get(
    "/cases/{case_id}/analyses",
    response_model=AnalysisListResponse,
    summary="Listar análises de um caso",
    description=(
        "Retorna uma lista paginada de todas as análises jurídicas "
        "associadas a um caso específico."
    ),
)
async def list_analyses_by_case(
    case_id: uuid.UUID,
    page: int = Query(
        default=1,
        ge=1,
        description="Número da página (inicia em 1).",
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Quantidade de itens por página (máximo 100).",
    ),
    analysis_type: str | None = Query(
        default=None,
        description="Filtrar por tipo de análise (opcional).",
    ),
    analysis_status: str | None = Query(
        default=None,
        alias="status",
        description="Filtrar por status da análise (opcional).",
    ),
    current_user: dict[str, Any] = Depends(get_current_user),
    use_cases: AnalysisUseCases = Depends(get_analysis_use_cases),
) -> AnalysisListResponse:
    """Lista todas as análises associadas a um caso jurídico.

    Suporta paginação e filtros opcionais por tipo e status.

    Args:
        case_id: Identificador único do caso.
        page: Número da página para paginação.
        page_size: Quantidade de itens por página.
        analysis_type: Filtro opcional por tipo de análise.
        analysis_status: Filtro opcional por status da análise.
        current_user: Usuário autenticado extraído do token JWT.
        use_cases: Instância dos use cases de análise (injetada).

    Returns:
        AnalysisListResponse com lista paginada de análises.

    Raises:
        HTTPException 404: Caso não encontrado.
        HTTPException 403: Usuário sem permissão para acessar este caso.
    """
    user_id: uuid.UUID = current_user["id"]

    logger.info(
        "Listagem de análises por caso solicitada",
        case_id=str(case_id),
        user_id=str(user_id),
        page=page,
        page_size=page_size,
        analysis_type=analysis_type,
        analysis_status=analysis_status,
    )

    try:
        # TODO: Ajustar nome do método e parâmetros conforme interface
        # final do use case. O use case deve retornar um objeto com
        # atributos 'items' (lista) e 'total' (int).
        result = await use_cases.list_analyses_by_case(
            case_id=case_id,
            requested_by=user_id,
            page=page,
            page_size=page_size,
            analysis_type=analysis_type,
            status=analysis_status,
        )
    except ValueError as exc:
        logger.warning(
            "Caso não encontrado para listagem de análises",
            case_id=str(case_id),
            user_id=str(user_id),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Caso não encontrado: {case_id}",
        ) from exc
    except PermissionError as exc:
        logger.warning(
            "Acesso negado ao caso para listagem de análises",
            case_id=str(case_id),
            user_id=str(user_id),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acessar as análises deste caso.",
        ) from exc
    except Exception as exc:
        logger.error(
            "Erro interno ao listar análises do caso",
            error=str(exc),
            case_id=str(case_id),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao listar análises. Tente novamente mais tarde.",
        ) from exc

    items = [
        AnalysisResponse(
            id=item.id,
            document_id=item.document_id,
            case_id=item.case_id,
            analysis_type=item.analysis_type,
            status=item.status,
            result=item.result,
            created_at=item.created_at.isoformat() if hasattr(item.created_at, "isoformat") else str(item.created_at),
            updated_at=item.updated_at.isoformat() if item.updated_at and hasattr(item.updated_at, "isoformat") else None,
            requested_by=item.requested_by,
        )
        for item in result.items
    ]

    logger.info(
        "Listagem de análises concluída",
        case_id=str(case_id),
        total=result.total,
        page=page,
    )

    return AnalysisListResponse(
        items=items,
        total=result.total,
        page=page,
        page_size=page_size,
    )
