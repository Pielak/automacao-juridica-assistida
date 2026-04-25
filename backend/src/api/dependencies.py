"""Dependências injetáveis do FastAPI — Automação Jurídica Assistida.

Centraliza todas as dependências (Depends) utilizadas nos endpoints da API:
- Sessão de banco de dados assíncrona
- Autenticação e autorização do usuário corrente
- Fábricas de repositórios (ports & adapters)
- Fábricas de use cases da camada de aplicação

Segue os princípios de Clean Architecture: os endpoints dependem apenas
de interfaces (ports), e as implementações concretas são injetadas aqui.

Exemplo de uso nos routers:
    from backend.src.api.dependencies import (
        get_current_user,
        get_db_session,
        get_user_repository,
        get_document_repository,
    )

    @router.get("/me")
    async def me(
        current_user = Depends(get_current_user),
    ):
        return current_user
"""

from __future__ import annotations

from typing import Annotated, AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Infraestrutura — sessão de banco de dados
# ---------------------------------------------------------------------------
from backend.src.infrastructure.database.session import get_async_session

# ---------------------------------------------------------------------------
# Infraestrutura — segurança / JWT
# ---------------------------------------------------------------------------
from backend.src.infrastructure.security.jwt_handler import (
    decode_token,
    is_token_blacklisted,
)

# ---------------------------------------------------------------------------
# Repositórios concretos (adapters)
# ---------------------------------------------------------------------------
from backend.src.infrastructure.repositories.user_repository import UserRepository
from backend.src.infrastructure.repositories.case_repository import CaseRepository
from backend.src.infrastructure.repositories.document_repository import (
    SqlAlchemyDocumentRepository,
)
from backend.src.infrastructure.repositories.analysis_repository import (
    SQLAlchemyAnalysisRepository,
)
from backend.src.infrastructure.repositories.audit_repository import (
    # TODO: Confirmar nome exato da classe exportada pelo peer audit_repository.
    #       Assumindo padrão SQLAlchemyAuditRepository conforme convenção do projeto.
    SQLAlchemyAuditRepository,  # type: ignore[attr-defined]
)
from backend.src.infrastructure.repositories.chat_repository import (
    SqlAlchemyChatRepository,
)

# ---------------------------------------------------------------------------
# Esquema OAuth2 — extrai o token do header Authorization: Bearer <token>
# ---------------------------------------------------------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ===================================================================
# 1. SESSÃO DE BANCO DE DADOS
# ===================================================================

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Fornece uma sessão assíncrona do SQLAlchemy para injeção via Depends.

    Delega para :func:`get_async_session` da camada de infraestrutura,
    garantindo que a sessão seja fechada ao final da requisição.

    Yields:
        AsyncSession: sessão ativa do banco de dados.
    """
    async for session in get_async_session():
        yield session


# Alias tipado para uso conciso nos routers
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


# ===================================================================
# 2. AUTENTICAÇÃO — USUÁRIO CORRENTE
# ===================================================================

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: DbSession,
):
    """Valida o JWT e retorna o usuário autenticado.

    Fluxo:
        1. Decodifica o token JWT.
        2. Verifica se o token está na blacklist (logout/revogação).
        3. Busca o usuário no banco pelo subject (UUID).
        4. Verifica se o usuário está ativo.

    Args:
        token: JWT extraído do header ``Authorization: Bearer``.
        session: sessão assíncrona do banco de dados.

    Returns:
        Modelo do usuário autenticado.

    Raises:
        HTTPException 401: token inválido, expirado, revogado ou usuário inexistente.
        HTTPException 403: usuário desativado.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas. Faça login novamente.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 1. Decodificar token
    try:
        payload = decode_token(token)
    except Exception:
        raise credentials_exception

    if payload is None:
        raise credentials_exception

    # Extrair subject (user id) do payload
    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # 2. Verificar blacklist (suporte a logout / revogação)
    try:
        if await is_token_blacklisted(token):
            raise credentials_exception
    except TypeError:
        # is_token_blacklisted pode ser síncrono em algumas implementações
        if is_token_blacklisted(token):  # type: ignore[arg-type]
            raise credentials_exception

    # 3. Buscar usuário no repositório
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)

    if user is None:
        raise credentials_exception

    # 4. Verificar se o usuário está ativo
    if hasattr(user, "is_active") and not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta de usuário desativada. Entre em contato com o administrador.",
        )

    return user


# Alias tipado para injeção rápida nos routers
# TODO: Substituir `Any` pelo tipo concreto do modelo User quando disponível.
from typing import Any  # noqa: E402 — import tardio intencional para manter organização

CurrentUser = Annotated[Any, Depends(get_current_user)]


# ---------------------------------------------------------------------------
# Dependência de autorização por papel (RBAC)
# ---------------------------------------------------------------------------

class RoleChecker:
    """Verificador de papéis (roles) para autorização RBAC.

    Uso:
        @router.get("/admin", dependencies=[Depends(RoleChecker(["admin"]))])
        async def admin_only(): ...
    """

    def __init__(self, allowed_roles: list[str]) -> None:
        """Inicializa com a lista de papéis permitidos.

        Args:
            allowed_roles: lista de nomes de papéis aceitos (ex: ["admin", "advogado"]).
        """
        self.allowed_roles = allowed_roles

    async def __call__(
        self,
        current_user: CurrentUser,
    ) -> None:
        """Verifica se o usuário corrente possui um dos papéis permitidos.

        Raises:
            HTTPException 403: usuário não possui permissão suficiente.
        """
        user_role = getattr(current_user, "role", None)
        if user_role is None:
            user_role = getattr(current_user, "papel", None)

        if user_role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão insuficiente para acessar este recurso.",
            )


# ===================================================================
# 3. FÁBRICAS DE REPOSITÓRIOS
# ===================================================================

async def get_user_repository(session: DbSession) -> UserRepository:
    """Fornece instância do repositório de usuários.

    Args:
        session: sessão assíncrona injetada.

    Returns:
        UserRepository configurado com a sessão corrente.
    """
    return UserRepository(session)


async def get_case_repository(session: DbSession) -> CaseRepository:
    """Fornece instância do repositório de processos jurídicos.

    Args:
        session: sessão assíncrona injetada.

    Returns:
        CaseRepository configurado com a sessão corrente.
    """
    return CaseRepository(session)


async def get_document_repository(session: DbSession) -> SqlAlchemyDocumentRepository:
    """Fornece instância do repositório de documentos.

    Args:
        session: sessão assíncrona injetada.

    Returns:
        SqlAlchemyDocumentRepository configurado com a sessão corrente.
    """
    return SqlAlchemyDocumentRepository(session)


async def get_analysis_repository(session: DbSession) -> SQLAlchemyAnalysisRepository:
    """Fornece instância do repositório de análises de IA.

    Args:
        session: sessão assíncrona injetada.

    Returns:
        SQLAlchemyAnalysisRepository configurado com a sessão corrente.
    """
    return SQLAlchemyAnalysisRepository(session)


async def get_audit_repository(session: DbSession) -> SQLAlchemyAuditRepository:
    """Fornece instância do repositório de auditoria.

    Args:
        session: sessão assíncrona injetada.

    Returns:
        SQLAlchemyAuditRepository configurado com a sessão corrente.
    """
    return SQLAlchemyAuditRepository(session)


async def get_chat_repository(session: DbSession) -> SqlAlchemyChatRepository:
    """Fornece instância do repositório de chat.

    Args:
        session: sessão assíncrona injetada.

    Returns:
        SqlAlchemyChatRepository configurado com a sessão corrente.
    """
    return SqlAlchemyChatRepository(session)


# Aliases tipados para repositórios — uso conciso nos routers
UserRepo = Annotated[UserRepository, Depends(get_user_repository)]
CaseRepo = Annotated[CaseRepository, Depends(get_case_repository)]
DocumentRepo = Annotated[SqlAlchemyDocumentRepository, Depends(get_document_repository)]
AnalysisRepo = Annotated[SQLAlchemyAnalysisRepository, Depends(get_analysis_repository)]
AuditRepo = Annotated[SQLAlchemyAuditRepository, Depends(get_audit_repository)]
ChatRepo = Annotated[SqlAlchemyChatRepository, Depends(get_chat_repository)]


# ===================================================================
# 4. FÁBRICAS DE USE CASES
# ===================================================================
# TODO: Implementar fábricas de use cases quando os módulos da camada
#       de aplicação estiverem definidos. Cada use case receberá os
#       repositórios necessários via injeção de dependência.
#
# Padrão esperado:
#
#   async def get_create_document_use_case(
#       document_repo: DocumentRepo,
#       audit_repo: AuditRepo,
#   ) -> CreateDocumentUseCase:
#       return CreateDocumentUseCase(
#           document_repository=document_repo,
#           audit_repository=audit_repo,
#       )
#
# Use cases previstos:
#   - auth: LoginUseCase, RegisterUseCase, RefreshTokenUseCase, LogoutUseCase
#   - documents: CreateDocumentUseCase, GetDocumentUseCase, ListDocumentsUseCase
#   - analysis: RequestAnalysisUseCase, GetAnalysisResultUseCase
#   - chat: CreateChatSessionUseCase, SendMessageUseCase, GetChatHistoryUseCase
#   - cases: CreateCaseUseCase, UpdateCaseUseCase, ListCasesUseCase
#   - audit: ListAuditLogsUseCase


# ===================================================================
# 5. UTILITÁRIOS DE DEPENDÊNCIA
# ===================================================================

def require_roles(*roles: str) -> RoleChecker:
    """Atalho para criar um verificador de papéis RBAC.

    Uso:
        @router.delete(
            "/users/{user_id}",
            dependencies=[Depends(require_roles("admin"))],
        )
        async def delete_user(user_id: str): ...

    Args:
        *roles: nomes dos papéis permitidos.

    Returns:
        Instância de RoleChecker configurada.
    """
    return RoleChecker(allowed_roles=list(roles))
