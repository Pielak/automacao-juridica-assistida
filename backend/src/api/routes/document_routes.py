"""Rotas da API para o módulo de documentos jurídicos.

Define os endpoints REST para upload, download, listagem e exclusão
de documentos, seguindo os princípios de Clean Architecture.
Os endpoints delegam toda lógica de negócio aos use cases da camada
de aplicação, recebidos via injeção de dependência do FastAPI.

Endpoints:
    POST   /documents/upload      — Upload de documento jurídico
    GET    /documents              — Listagem paginada de documentos
    GET    /documents/{document_id} — Detalhes de um documento específico
    DELETE /documents/{document_id} — Exclusão lógica de documento
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

import structlog
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field

from backend.src.api.dependencies import (
    get_current_user,
    get_document_use_cases,
)
from backend.src.application.use_cases.document_use_cases import (
    DocumentUseCases,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constantes de validação
# ---------------------------------------------------------------------------

ALLOWED_CONTENT_TYPES: set[str] = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "application/rtf",
}

MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB

# ---------------------------------------------------------------------------
# Schemas de resposta (Pydantic v2)
# ---------------------------------------------------------------------------


class DocumentResponse(BaseModel):
    """Schema de resposta para um documento individual."""

    id: uuid.UUID = Field(..., description="Identificador único do documento")
    filename: str = Field(..., description="Nome original do arquivo")
    content_type: str = Field(..., description="Tipo MIME do arquivo")
    size_bytes: int = Field(..., description="Tamanho do arquivo em bytes")
    status: str = Field(..., description="Status atual do documento")
    owner_id: uuid.UUID = Field(..., description="ID do usuário proprietário")
    created_at: str = Field(..., description="Data de criação (ISO 8601)")
    updated_at: Optional[str] = Field(None, description="Data da última atualização (ISO 8601)")

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """Schema de resposta para listagem paginada de documentos."""

    items: list[DocumentResponse] = Field(
        default_factory=list, description="Lista de documentos"
    )
    total: int = Field(..., description="Total de documentos encontrados")
    page: int = Field(..., description="Página atual")
    page_size: int = Field(..., description="Quantidade de itens por página")
    pages: int = Field(..., description="Total de páginas disponíveis")


class DocumentUploadResponse(BaseModel):
    """Schema de resposta para upload bem-sucedido."""

    id: uuid.UUID = Field(..., description="Identificador do documento criado")
    filename: str = Field(..., description="Nome original do arquivo")
    status: str = Field(..., description="Status inicial do documento")
    message: str = Field(..., description="Mensagem de confirmação")


class DocumentDeleteResponse(BaseModel):
    """Schema de resposta para exclusão de documento."""

    id: uuid.UUID = Field(..., description="Identificador do documento excluído")
    message: str = Field(..., description="Mensagem de confirmação")


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(
    prefix="/documents",
    tags=["Documentos"],
    responses={
        401: {"description": "Não autenticado"},
        403: {"description": "Sem permissão para acessar este recurso"},
    },
)


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


def _validate_upload_file(file: UploadFile) -> None:
    """Valida tipo MIME e tamanho do arquivo enviado.

    Args:
        file: Arquivo recebido via multipart/form-data.

    Raises:
        HTTPException: Se o tipo ou tamanho do arquivo for inválido.
    """
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Tipo de arquivo não suportado: '{file.content_type}'. "
                f"Tipos permitidos: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}"
            ),
        )

    # Verificação de tamanho — lê o tamanho reportado pelo header quando disponível
    if file.size is not None and file.size > MAX_FILE_SIZE_BYTES:
        max_mb = MAX_FILE_SIZE_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"Arquivo excede o tamanho máximo permitido de {max_mb} MB."
            ),
        )


def _entity_to_response(document: Any) -> DocumentResponse:
    """Converte uma entidade de domínio Document para o schema de resposta.

    Args:
        document: Entidade Document retornada pelo use case.

    Returns:
        DocumentResponse serializado.
    """
    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        status=document.status.value if hasattr(document.status, "value") else str(document.status),
        owner_id=document.owner_id,
        created_at=document.created_at.isoformat() if document.created_at else "",
        updated_at=document.updated_at.isoformat() if document.updated_at else None,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload de documento jurídico",
    description=(
        "Realiza o upload de um documento jurídico (PDF, DOCX, DOC, TXT, RTF). "
        "O arquivo é validado quanto ao tipo e tamanho antes de ser persistido."
    ),
)
async def upload_document(
    file: UploadFile = File(
        ...,
        description="Arquivo do documento jurídico (máx. 50 MB)",
    ),
    current_user: Any = Depends(get_current_user),
    use_cases: DocumentUseCases = Depends(get_document_use_cases),
) -> DocumentUploadResponse:
    """Endpoint de upload de documento jurídico.

    Valida o arquivo recebido e delega a persistência ao use case
    de criação de documentos.

    Args:
        file: Arquivo enviado via multipart/form-data.
        current_user: Usuário autenticado (injetado via JWT).
        use_cases: Instância dos use cases de documento.

    Returns:
        DocumentUploadResponse com ID e status do documento criado.

    Raises:
        HTTPException 413: Arquivo excede tamanho máximo.
        HTTPException 415: Tipo de arquivo não suportado.
        HTTPException 500: Erro interno ao processar upload.
    """
    _validate_upload_file(file)

    log = logger.bind(
        user_id=str(current_user.id),
        filename=file.filename,
        content_type=file.content_type,
    )
    log.info("Iniciando upload de documento")

    try:
        file_content = await file.read()

        # Validação de tamanho real do conteúdo lido
        if len(file_content) > MAX_FILE_SIZE_BYTES:
            max_mb = MAX_FILE_SIZE_BYTES // (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Arquivo excede o tamanho máximo permitido de {max_mb} MB.",
            )

        # TODO: Verificar assinatura exata do método create/upload no DocumentUseCases.
        # A chamada abaixo assume a interface mais provável baseada no peer.
        document = await use_cases.upload_document(
            filename=file.filename or "sem_nome",
            content=file_content,
            content_type=file.content_type or "application/octet-stream",
            owner_id=current_user.id,
        )

        log.info(
            "Documento enviado com sucesso",
            document_id=str(document.id),
        )

        return DocumentUploadResponse(
            id=document.id,
            filename=document.filename,
            status=document.status.value if hasattr(document.status, "value") else str(document.status),
            message="Documento enviado com sucesso.",
        )

    except HTTPException:
        raise
    except Exception as exc:
        log.error("Erro ao processar upload de documento", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao processar o upload do documento. Tente novamente.",
        ) from exc
    finally:
        await file.close()


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="Listagem paginada de documentos",
    description="Retorna a lista de documentos do usuário autenticado com paginação.",
)
async def list_documents(
    page: int = Query(
        default=1,
        ge=1,
        description="Número da página (inicia em 1)",
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Quantidade de itens por página (máx. 100)",
    ),
    status_filter: Optional[str] = Query(
        default=None,
        alias="status",
        description="Filtrar por status do documento",
    ),
    search: Optional[str] = Query(
        default=None,
        max_length=200,
        description="Termo de busca no nome do arquivo",
    ),
    current_user: Any = Depends(get_current_user),
    use_cases: DocumentUseCases = Depends(get_document_use_cases),
) -> DocumentListResponse:
    """Endpoint de listagem paginada de documentos.

    Retorna os documentos pertencentes ao usuário autenticado,
    com suporte a filtros e paginação.

    Args:
        page: Número da página.
        page_size: Itens por página.
        status_filter: Filtro opcional por status.
        search: Termo de busca opcional.
        current_user: Usuário autenticado.
        use_cases: Instância dos use cases de documento.

    Returns:
        DocumentListResponse com itens e metadados de paginação.
    """
    log = logger.bind(
        user_id=str(current_user.id),
        page=page,
        page_size=page_size,
    )
    log.info("Listando documentos do usuário")

    try:
        # TODO: Verificar assinatura exata do método list no DocumentUseCases.
        result = await use_cases.list_documents(
            owner_id=current_user.id,
            page=page,
            page_size=page_size,
            status_filter=status_filter,
            search=search,
        )

        # O resultado pode ser uma tupla (items, total) ou um objeto com atributos
        if isinstance(result, tuple):
            items, total = result
        else:
            items = result.items if hasattr(result, "items") else result
            total = result.total if hasattr(result, "total") else len(items)

        total_pages = max(1, (total + page_size - 1) // page_size)

        return DocumentListResponse(
            items=[_entity_to_response(doc) for doc in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=total_pages,
        )

    except Exception as exc:
        log.error("Erro ao listar documentos", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao listar documentos. Tente novamente.",
        ) from exc


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Detalhes de um documento",
    description="Retorna os detalhes de um documento específico pelo seu ID.",
)
async def get_document(
    document_id: uuid.UUID,
    current_user: Any = Depends(get_current_user),
    use_cases: DocumentUseCases = Depends(get_document_use_cases),
) -> DocumentResponse:
    """Endpoint para obter detalhes de um documento específico.

    Verifica se o documento pertence ao usuário autenticado antes
    de retornar os dados.

    Args:
        document_id: Identificador UUID do documento.
        current_user: Usuário autenticado.
        use_cases: Instância dos use cases de documento.

    Returns:
        DocumentResponse com os detalhes do documento.

    Raises:
        HTTPException 404: Documento não encontrado.
        HTTPException 403: Documento não pertence ao usuário.
    """
    log = logger.bind(
        user_id=str(current_user.id),
        document_id=str(document_id),
    )
    log.info("Buscando documento por ID")

    try:
        # TODO: Verificar assinatura exata do método get no DocumentUseCases.
        document = await use_cases.get_document(
            document_id=document_id,
            owner_id=current_user.id,
        )

        if document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Documento não encontrado.",
            )

        # Verificação de propriedade (defesa em profundidade)
        if hasattr(document, "owner_id") and document.owner_id != current_user.id:
            log.warning(
                "Tentativa de acesso a documento de outro usuário",
                document_owner_id=str(document.owner_id),
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para acessar este documento.",
            )

        return _entity_to_response(document)

    except HTTPException:
        raise
    except Exception as exc:
        log.error("Erro ao buscar documento", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao buscar documento. Tente novamente.",
        ) from exc


@router.delete(
    "/{document_id}",
    response_model=DocumentDeleteResponse,
    summary="Exclusão de documento",
    description=(
        "Realiza a exclusão lógica de um documento. "
        "O documento é marcado como excluído mas permanece no banco para auditoria."
    ),
)
async def delete_document(
    document_id: uuid.UUID,
    current_user: Any = Depends(get_current_user),
    use_cases: DocumentUseCases = Depends(get_document_use_cases),
) -> DocumentDeleteResponse:
    """Endpoint para exclusão lógica de um documento.

    Verifica propriedade e delega a exclusão ao use case.
    A exclusão é lógica (soft delete) para manter rastreabilidade
    conforme requisitos de auditoria.

    Args:
        document_id: Identificador UUID do documento.
        current_user: Usuário autenticado.
        use_cases: Instância dos use cases de documento.

    Returns:
        DocumentDeleteResponse com confirmação da exclusão.

    Raises:
        HTTPException 404: Documento não encontrado.
        HTTPException 403: Documento não pertence ao usuário.
    """
    log = logger.bind(
        user_id=str(current_user.id),
        document_id=str(document_id),
    )
    log.info("Solicitação de exclusão de documento")

    try:
        # TODO: Verificar assinatura exata do método delete no DocumentUseCases.
        result = await use_cases.delete_document(
            document_id=document_id,
            owner_id=current_user.id,
        )

        if result is None or (isinstance(result, bool) and not result):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Documento não encontrado ou já foi excluído.",
            )

        log.info("Documento excluído com sucesso")

        return DocumentDeleteResponse(
            id=document_id,
            message="Documento excluído com sucesso.",
        )

    except HTTPException:
        raise
    except Exception as exc:
        log.error("Erro ao excluir documento", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao excluir documento. Tente novamente.",
        ) from exc
