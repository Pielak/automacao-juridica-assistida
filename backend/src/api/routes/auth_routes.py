"""Rotas de autenticação — Automação Jurídica Assistida.

Endpoints REST para o módulo de autenticação:
- POST /auth/login — Login com credenciais (email + senha)
- POST /auth/register — Registro de novo usuário com validação OAB
- POST /auth/refresh — Renovação de token JWT
- POST /auth/logout — Logout com revogação de token

Todos os endpoints delegam a lógica de negócio para os use cases
da camada de aplicação, seguindo Clean Architecture.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from backend.src.api.dependencies import (
    get_current_user,
    get_login_use_case,
    get_logout_use_case,
    get_refresh_token_use_case,
    get_register_use_case,
)
from backend.src.application.use_cases.auth_use_cases import (
    LoginUseCase,
    LogoutUseCase,
    RefreshTokenUseCase,
    RegisterUseCase,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Autenticação"])


# ---------------------------------------------------------------------------
# Schemas de request / response (Pydantic v2)
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    """Schema de entrada para login."""

    email: EmailStr = Field(
        ...,
        description="Endereço de e-mail cadastrado do usuário.",
        examples=["advogado@escritorio.com.br"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Senha do usuário. Mínimo de 8 caracteres.",
    )
    mfa_code: str | None = Field(
        default=None,
        min_length=6,
        max_length=6,
        description="Código MFA (TOTP) de 6 dígitos, se habilitado.",
        examples=["123456"],
    )


class RegisterRequest(BaseModel):
    """Schema de entrada para registro de novo usuário."""

    full_name: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Nome completo do usuário.",
        examples=["Maria da Silva"],
    )
    email: EmailStr = Field(
        ...,
        description="Endereço de e-mail para cadastro.",
        examples=["maria.silva@escritorio.com.br"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Senha com mínimo de 8 caracteres. Recomenda-se letras, números e símbolos.",
    )
    password_confirmation: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Confirmação da senha — deve ser idêntica ao campo 'password'.",
    )
    oab_number: str | None = Field(
        default=None,
        max_length=20,
        description="Número de inscrição na OAB (ex.: 'SP123456'). Obrigatório para advogados.",
        examples=["SP123456"],
    )
    oab_state: str | None = Field(
        default=None,
        min_length=2,
        max_length=2,
        description="UF da seccional da OAB (ex.: 'SP', 'RJ').",
        examples=["SP"],
    )


class RefreshTokenRequest(BaseModel):
    """Schema de entrada para renovação de token."""

    refresh_token: str = Field(
        ...,
        description="Refresh token JWT obtido no login.",
    )


class TokenResponse(BaseModel):
    """Schema de resposta contendo tokens JWT."""

    access_token: str = Field(
        ...,
        description="Token de acesso JWT (curta duração).",
    )
    refresh_token: str = Field(
        ...,
        description="Token de renovação JWT (longa duração).",
    )
    token_type: str = Field(
        default="bearer",
        description="Tipo do token — sempre 'bearer'.",
    )
    expires_in: int = Field(
        ...,
        description="Tempo de expiração do access_token em segundos.",
    )


class RegisterResponse(BaseModel):
    """Schema de resposta para registro bem-sucedido."""

    id: str = Field(
        ...,
        description="Identificador único (UUID) do usuário criado.",
    )
    email: str = Field(
        ...,
        description="E-mail do usuário registrado.",
    )
    full_name: str = Field(
        ...,
        description="Nome completo do usuário registrado.",
    )
    message: str = Field(
        default="Usuário registrado com sucesso.",
        description="Mensagem de confirmação.",
    )


class LogoutResponse(BaseModel):
    """Schema de resposta para logout."""

    message: str = Field(
        default="Logout realizado com sucesso.",
        description="Mensagem de confirmação do logout.",
    )


class MessageResponse(BaseModel):
    """Schema genérico de resposta com mensagem."""

    message: str = Field(..., description="Mensagem descritiva.")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Autenticar usuário",
    description="Realiza login com e-mail e senha. Retorna par de tokens JWT (access + refresh). "
    "Se MFA estiver habilitado, o campo 'mfa_code' é obrigatório.",
    responses={
        401: {"description": "Credenciais inválidas ou código MFA incorreto."},
        422: {"description": "Erro de validação nos dados de entrada."},
        429: {"description": "Limite de tentativas de login excedido."},
    },
)
async def login(
    body: LoginRequest,
    use_case: Annotated[LoginUseCase, Depends(get_login_use_case)],
) -> TokenResponse:
    """Endpoint de login — autentica o usuário e retorna tokens JWT."""
    logger.info("Tentativa de login para e-mail: %s", body.email)

    try:
        result = await use_case.execute(
            email=body.email,
            password=body.password,
            mfa_code=body.mfa_code,
        )
    except ValueError as exc:
        logger.warning("Falha no login para e-mail %s: %s", body.email, str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas. Verifique seu e-mail e senha.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except PermissionError as exc:
        logger.warning("Conta bloqueada ou inativa para e-mail %s: %s", body.email, str(exc))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta bloqueada ou inativa. Entre em contato com o administrador.",
        ) from exc
    except Exception as exc:
        logger.exception("Erro inesperado durante login para e-mail %s", body.email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao processar o login. Tente novamente mais tarde.",
        ) from exc

    logger.info("Login realizado com sucesso para e-mail: %s", body.email)

    return TokenResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type="bearer",
        expires_in=result.expires_in,
    )


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar novo usuário",
    description="Cria uma nova conta de usuário. Opcionalmente valida o número de inscrição na OAB.",
    responses={
        409: {"description": "E-mail já cadastrado no sistema."},
        422: {"description": "Erro de validação nos dados de entrada."},
    },
)
async def register(
    body: RegisterRequest,
    use_case: Annotated[RegisterUseCase, Depends(get_register_use_case)],
) -> RegisterResponse:
    """Endpoint de registro — cria novo usuário no sistema."""
    # Validação de confirmação de senha no nível da rota
    if body.password != body.password_confirmation:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="As senhas informadas não coincidem.",
        )

    logger.info("Tentativa de registro para e-mail: %s", body.email)

    try:
        result = await use_case.execute(
            full_name=body.full_name,
            email=body.email,
            password=body.password,
            oab_number=body.oab_number,
            oab_state=body.oab_state,
        )
    except ValueError as exc:
        error_msg = str(exc)
        logger.warning("Falha no registro para e-mail %s: %s", body.email, error_msg)

        # Diferencia conflito (e-mail duplicado) de validação genérica
        if "já cadastrado" in error_msg.lower() or "already" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="E-mail já cadastrado. Utilize outro endereço ou faça login.",
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_msg,
        ) from exc
    except Exception as exc:
        logger.exception("Erro inesperado durante registro para e-mail %s", body.email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao processar o registro. Tente novamente mais tarde.",
        ) from exc

    logger.info("Usuário registrado com sucesso: %s (ID: %s)", body.email, result.id)

    return RegisterResponse(
        id=str(result.id),
        email=result.email,
        full_name=result.full_name,
        message="Usuário registrado com sucesso.",
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Renovar token de acesso",
    description="Gera um novo par de tokens JWT a partir de um refresh token válido.",
    responses={
        401: {"description": "Refresh token inválido, expirado ou revogado."},
        422: {"description": "Erro de validação nos dados de entrada."},
    },
)
async def refresh_token(
    body: RefreshTokenRequest,
    use_case: Annotated[RefreshTokenUseCase, Depends(get_refresh_token_use_case)],
) -> TokenResponse:
    """Endpoint de refresh — renova tokens JWT sem necessidade de re-login."""
    logger.info("Tentativa de renovação de token.")

    try:
        result = await use_case.execute(
            refresh_token=body.refresh_token,
        )
    except ValueError as exc:
        logger.warning("Falha na renovação de token: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de renovação inválido ou expirado. Faça login novamente.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except Exception as exc:
        logger.exception("Erro inesperado durante renovação de token.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao renovar o token. Tente novamente mais tarde.",
        ) from exc

    logger.info("Token renovado com sucesso.")

    return TokenResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type="bearer",
        expires_in=result.expires_in,
    )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Encerrar sessão",
    description="Revoga o token de acesso atual, encerrando a sessão do usuário.",
    responses={
        401: {"description": "Usuário não autenticado."},
    },
)
async def logout(
    current_user: Annotated[dict, Depends(get_current_user)],
    use_case: Annotated[LogoutUseCase, Depends(get_logout_use_case)],
) -> LogoutResponse:
    """Endpoint de logout — revoga o token e encerra a sessão."""
    # TODO: Extrair o token do header Authorization para revogação.
    # A implementação exata depende de como get_current_user expõe o token.
    user_id = current_user.get("id") or current_user.get("sub")
    logger.info("Tentativa de logout para usuário ID: %s", user_id)

    try:
        await use_case.execute(
            user_id=user_id,
            # TODO: Passar o access_token para revogação quando a interface do use case for definida.
        )
    except Exception as exc:
        logger.exception("Erro inesperado durante logout para usuário ID: %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao processar o logout. Tente novamente mais tarde.",
        ) from exc

    logger.info("Logout realizado com sucesso para usuário ID: %s", user_id)

    return LogoutResponse(message="Logout realizado com sucesso.")
