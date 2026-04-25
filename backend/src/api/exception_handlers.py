"""Exception handlers globais para a API FastAPI.

Define handlers padronizados para exceções de domínio, validação,
recursos não encontrados e erros internos do servidor.
Todas as respostas de erro seguem um formato JSON consistente.
"""

import uuid
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Exceções de domínio base
# ---------------------------------------------------------------------------


class DomainError(Exception):
    """Exceção base para erros de domínio da aplicação.

    Todas as exceções de regra de negócio devem herdar desta classe
    para que o handler global as capture e retorne resposta padronizada.
    """

    def __init__(
        self,
        message: str = "Erro de regra de negócio.",
        code: str = "DOMAIN_ERROR",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(DomainError):
    """Exceção para recursos não encontrados no domínio."""

    def __init__(
        self,
        message: str = "Recurso não encontrado.",
        code: str = "NOT_FOUND",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class ConflictError(DomainError):
    """Exceção para conflitos de estado (ex.: recurso já existente)."""

    def __init__(
        self,
        message: str = "Conflito: o recurso já existe ou está em estado inconsistente.",
        code: str = "CONFLICT",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class ForbiddenError(DomainError):
    """Exceção para operações não permitidas ao usuário autenticado."""

    def __init__(
        self,
        message: str = "Você não tem permissão para realizar esta operação.",
        code: str = "FORBIDDEN",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class UnauthorizedError(DomainError):
    """Exceção para falhas de autenticação."""

    def __init__(
        self,
        message: str = "Credenciais inválidas ou sessão expirada.",
        code: str = "UNAUTHORIZED",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class ExternalServiceError(DomainError):
    """Exceção para falhas em serviços externos (ex.: API Anthropic, DataJud)."""

    def __init__(
        self,
        message: str = "Erro ao comunicar com serviço externo. Tente novamente mais tarde.",
        code: str = "EXTERNAL_SERVICE_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details,
        )


# ---------------------------------------------------------------------------
# Schema de resposta de erro padronizado
# ---------------------------------------------------------------------------


class ErrorDetail(BaseModel):
    """Schema de campo individual de erro de validação."""

    field: str
    message: str
    type: str


class ErrorResponse(BaseModel):
    """Schema padronizado para todas as respostas de erro da API.

    Garante consistência no formato de erros retornados ao frontend,
    facilitando tratamento uniforme no cliente.
    """

    success: bool = False
    error_code: str
    message: str
    details: dict[str, Any] | list[ErrorDetail] = {}
    request_id: str | None = None


# ---------------------------------------------------------------------------
# Funções utilitárias
# ---------------------------------------------------------------------------


def _extract_request_id(request: Request) -> str:
    """Extrai o request ID do state ou headers da requisição.

    O middleware de logging (correlation ID) deve popular `request.state.request_id`.
    Caso não exista, gera um UUID como fallback.
    """
    request_id = getattr(request.state, "request_id", None)
    if request_id is None:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    return str(request_id)


def _build_error_response(
    request: Request,
    status_code: int,
    error_code: str,
    message: str,
    details: dict[str, Any] | list[ErrorDetail] | None = None,
) -> JSONResponse:
    """Constrói uma JSONResponse padronizada de erro."""
    request_id = _extract_request_id(request)

    body = ErrorResponse(
        success=False,
        error_code=error_code,
        message=message,
        details=details if details is not None else {},
        request_id=request_id,
    )

    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(mode="json"),
    )


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    """Handler para exceções de domínio (DomainError e subclasses).

    Loga o erro com nível WARNING (erros de negócio esperados) e retorna
    resposta padronizada com o código e mensagem da exceção.
    """
    request_id = _extract_request_id(request)

    logger.warning(
        "Erro de domínio capturado",
        error_code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
        request_id=request_id,
        path=str(request.url),
        method=request.method,
    )

    return _build_error_response(
        request=request,
        status_code=exc.status_code,
        error_code=exc.code,
        message=exc.message,
        details=exc.details,
    )


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handler para erros de validação do Pydantic / FastAPI.

    Transforma os erros de validação em formato padronizado amigável,
    traduzindo as mensagens para PT-BR quando possível.
    """
    request_id = _extract_request_id(request)

    error_details: list[ErrorDetail] = []
    for error in exc.errors():
        # Monta o caminho do campo (ex.: "body.nome", "query.page")
        loc_parts = [str(part) for part in error.get("loc", [])]
        field_path = ".".join(loc_parts) if loc_parts else "desconhecido"

        # Tradução básica de mensagens comuns de validação
        original_msg = error.get("msg", "Valor inválido")
        translated_msg = _translate_validation_message(original_msg)

        error_details.append(
            ErrorDetail(
                field=field_path,
                message=translated_msg,
                type=error.get("type", "value_error"),
            )
        )

    logger.info(
        "Erro de validação na requisição",
        error_count=len(error_details),
        request_id=request_id,
        path=str(request.url),
        method=request.method,
    )

    return _build_error_response(
        request=request,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code="VALIDATION_ERROR",
        message="Os dados enviados contêm erros de validação. Verifique os campos e tente novamente.",
        details=error_details,
    )


async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler para rotas não encontradas (HTTP 404).

    Captura requisições a endpoints inexistentes.
    """
    request_id = _extract_request_id(request)

    logger.info(
        "Rota não encontrada",
        request_id=request_id,
        path=str(request.url),
        method=request.method,
    )

    return _build_error_response(
        request=request,
        status_code=status.HTTP_404_NOT_FOUND,
        error_code="NOT_FOUND",
        message=f"O recurso solicitado não foi encontrado: {request.method} {request.url.path}",
    )


async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler para erros internos não tratados (HTTP 500).

    Loga o erro completo com stack trace para investigação,
    mas retorna mensagem genérica ao cliente para não expor
    detalhes internos da aplicação (segurança).
    """
    request_id = _extract_request_id(request)

    logger.error(
        "Erro interno não tratado",
        request_id=request_id,
        path=str(request.url),
        method=request.method,
        exc_type=type(exc).__name__,
        exc_message=str(exc),
        exc_info=True,
    )

    return _build_error_response(
        request=request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code="INTERNAL_ERROR",
        message="Ocorreu um erro interno no servidor. Nossa equipe foi notificada. Tente novamente mais tarde.",
        details={"request_id": request_id},
    )


# ---------------------------------------------------------------------------
# Tradução de mensagens de validação
# ---------------------------------------------------------------------------

_VALIDATION_TRANSLATIONS: dict[str, str] = {
    "Field required": "Este campo é obrigatório.",
    "field required": "Este campo é obrigatório.",
    "value is not a valid email address": "Endereço de e-mail inválido.",
    "value is not a valid integer": "O valor deve ser um número inteiro.",
    "value is not a valid float": "O valor deve ser um número decimal.",
    "string does not match regex": "O formato do texto é inválido.",
    "ensure this value has at least": "O valor é menor que o mínimo permitido.",
    "ensure this value has at most": "O valor excede o máximo permitido.",
    "value is not a valid list": "O valor deve ser uma lista.",
    "value is not a valid dict": "O valor deve ser um objeto.",
    "value is not none": "O valor não pode ser nulo.",
    "Input should be a valid string": "O valor deve ser um texto válido.",
    "Input should be a valid integer": "O valor deve ser um número inteiro válido.",
    "String should have at least": "O texto deve ter o comprimento mínimo exigido.",
    "String should have at most": "O texto excede o comprimento máximo permitido.",
}


def _translate_validation_message(message: str) -> str:
    """Traduz mensagens de validação do Pydantic para PT-BR.

    Realiza busca exata e, se não encontrar, busca por prefixo
    nas traduções conhecidas. Retorna a mensagem original caso
    não haja tradução disponível.
    """
    # Busca exata
    if message in _VALIDATION_TRANSLATIONS:
        return _VALIDATION_TRANSLATIONS[message]

    # Busca por prefixo (mensagens parametrizadas do Pydantic)
    lower_msg = message.lower()
    for key, translation in _VALIDATION_TRANSLATIONS.items():
        if lower_msg.startswith(key.lower()):
            return translation

    return message


# ---------------------------------------------------------------------------
# Registro dos handlers na aplicação FastAPI
# ---------------------------------------------------------------------------


def register_exception_handlers(app: FastAPI) -> None:
    """Registra todos os exception handlers globais na instância FastAPI.

    Deve ser chamado durante a inicialização da aplicação (lifespan ou startup).

    Args:
        app: Instância da aplicação FastAPI.
    """
    # Handler para exceções de domínio (captura DomainError e todas as subclasses)
    app.add_exception_handler(DomainError, domain_error_handler)  # type: ignore[arg-type]

    # Handler para erros de validação do Pydantic/FastAPI
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]

    # Handler para 404 (rotas não encontradas)
    app.add_exception_handler(404, not_found_handler)  # type: ignore[arg-type]

    # Handler para erros internos não tratados (500)
    app.add_exception_handler(500, internal_error_handler)  # type: ignore[arg-type]

    logger.info("Exception handlers globais registrados com sucesso.")
