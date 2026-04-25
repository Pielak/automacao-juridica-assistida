"""DTOs (Data Transfer Objects) para o módulo de autenticação.

Define os schemas Pydantic v2 utilizados para validação e serialização
de dados nas operações de autenticação: login, registro, refresh de token
e respostas de token JWT.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# Constantes de validação
# ---------------------------------------------------------------------------

_PASSWORD_MIN_LENGTH = 8
_PASSWORD_MAX_LENGTH = 128
_PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':"  # noqa: ISC003
    r'"\\|,.<>\/?]).+$'
)

_NAME_MIN_LENGTH = 2
_NAME_MAX_LENGTH = 120


def _validate_password_strength(password: str) -> str:
    """Valida a força da senha conforme requisitos de segurança.

    Requisitos:
        - Mínimo de 8 caracteres
        - Pelo menos uma letra maiúscula
        - Pelo menos uma letra minúscula
        - Pelo menos um dígito
        - Pelo menos um caractere especial

    Args:
        password: Senha a ser validada.

    Returns:
        A senha validada, sem alterações.

    Raises:
        ValueError: Se a senha não atender aos requisitos mínimos.
    """
    if len(password) < _PASSWORD_MIN_LENGTH:
        raise ValueError(
            f"A senha deve ter no mínimo {_PASSWORD_MIN_LENGTH} caracteres."
        )
    if len(password) > _PASSWORD_MAX_LENGTH:
        raise ValueError(
            f"A senha deve ter no máximo {_PASSWORD_MAX_LENGTH} caracteres."
        )
    if not re.search(r"[a-z]", password):
        raise ValueError("A senha deve conter pelo menos uma letra minúscula.")
    if not re.search(r"[A-Z]", password):
        raise ValueError("A senha deve conter pelo menos uma letra maiúscula.")
    if not re.search(r"\d", password):
        raise ValueError("A senha deve conter pelo menos um dígito.")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':" r'"\\|,.<>\/?]', password):
        raise ValueError(
            "A senha deve conter pelo menos um caractere especial."
        )
    return password


# ---------------------------------------------------------------------------
# Request DTOs
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    """DTO para requisição de login.

    Recebe as credenciais do usuário (e-mail e senha) e, opcionalmente,
    o código TOTP para autenticação multifator (MFA).
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "advogado@escritorio.com.br",
                "password": "SenhaForte@123",
                "mfa_code": "123456",
            }
        }
    )

    email: EmailStr = Field(
        ...,
        description="Endereço de e-mail cadastrado do usuário.",
    )
    password: str = Field(
        ...,
        min_length=_PASSWORD_MIN_LENGTH,
        max_length=_PASSWORD_MAX_LENGTH,
        description="Senha do usuário.",
    )
    mfa_code: Optional[str] = Field(
        default=None,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="Código TOTP de 6 dígitos para autenticação multifator (MFA).",
    )


class RegisterRequest(BaseModel):
    """DTO para requisição de registro de novo usuário.

    Contém os dados necessários para criação de uma nova conta no sistema
    de automação jurídica.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "full_name": "Maria da Silva",
                "email": "maria.silva@escritorio.com.br",
                "password": "SenhaForte@123",
                "password_confirmation": "SenhaForte@123",
                "oab_number": "SP123456",
            }
        }
    )

    full_name: str = Field(
        ...,
        min_length=_NAME_MIN_LENGTH,
        max_length=_NAME_MAX_LENGTH,
        description="Nome completo do usuário.",
    )
    email: EmailStr = Field(
        ...,
        description="Endereço de e-mail que será utilizado para login.",
    )
    password: str = Field(
        ...,
        min_length=_PASSWORD_MIN_LENGTH,
        max_length=_PASSWORD_MAX_LENGTH,
        description="Senha do usuário. Deve atender aos requisitos de complexidade.",
    )
    password_confirmation: str = Field(
        ...,
        min_length=_PASSWORD_MIN_LENGTH,
        max_length=_PASSWORD_MAX_LENGTH,
        description="Confirmação da senha. Deve ser idêntica ao campo 'password'.",
    )
    oab_number: Optional[str] = Field(
        default=None,
        max_length=20,
        pattern=r"^[A-Z]{2}\d{3,6}[A-Z]?$",
        description=(
            "Número de inscrição na OAB (opcional). "
            "Formato esperado: UF seguido de dígitos, ex.: SP123456."
        ),
    )

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        """Valida que o nome completo contém pelo menos nome e sobrenome."""
        stripped = value.strip()
        if len(stripped.split()) < 2:
            raise ValueError(
                "Informe o nome completo (nome e sobrenome)."
            )
        return stripped

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        """Valida a complexidade da senha."""
        return _validate_password_strength(value)

    @field_validator("password_confirmation")
    @classmethod
    def validate_password_confirmation(
        cls, value: str, info: object
    ) -> str:
        """Valida que a confirmação de senha corresponde à senha informada."""
        # info.data contém os campos já validados até este ponto
        data = getattr(info, "data", {})
        password = data.get("password")
        if password is not None and value != password:
            raise ValueError("A confirmação de senha não corresponde à senha informada.")
        return value


class RefreshRequest(BaseModel):
    """DTO para requisição de renovação de token JWT.

    Utilizado quando o access token expira e o cliente deseja obter
    um novo par de tokens sem exigir novo login.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }
    )

    refresh_token: str = Field(
        ...,
        min_length=1,
        description="Refresh token JWT válido emitido durante o login.",
    )


# ---------------------------------------------------------------------------
# Response DTOs
# ---------------------------------------------------------------------------


class TokenResponse(BaseModel):
    """DTO de resposta contendo os tokens JWT após autenticação bem-sucedida.

    Retornado nas operações de login e refresh de token.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "Bearer",
                "expires_in": 1800,
                "expires_at": "2024-12-01T12:30:00Z",
                "mfa_required": False,
            }
        }
    )

    access_token: str = Field(
        ...,
        description="Token JWT de acesso para autenticação nas requisições.",
    )
    refresh_token: str = Field(
        ...,
        description="Token JWT de renovação para obter novos access tokens.",
    )
    token_type: str = Field(
        default="Bearer",
        description="Tipo do token. Sempre 'Bearer' conforme RFC 6750.",
    )
    expires_in: int = Field(
        ...,
        gt=0,
        description="Tempo de expiração do access token em segundos.",
    )
    expires_at: datetime = Field(
        ...,
        description="Data/hora UTC de expiração do access token (ISO 8601).",
    )
    mfa_required: bool = Field(
        default=False,
        description=(
            "Indica se a autenticação multifator (MFA) é necessária. "
            "Quando True, o cliente deve reenviar o login com o campo 'mfa_code'."
        ),
    )


class MfaRequiredResponse(BaseModel):
    """DTO de resposta quando MFA é obrigatório e ainda não foi fornecido.

    Retornado no login quando o usuário possui MFA habilitado mas não
    enviou o código TOTP na requisição.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "mfa_required": True,
                "message": "Autenticação multifator necessária. Informe o código TOTP.",
                "mfa_type": "totp",
            }
        }
    )

    mfa_required: bool = Field(
        default=True,
        description="Sempre True nesta resposta.",
    )
    message: str = Field(
        default="Autenticação multifator necessária. Informe o código TOTP.",
        description="Mensagem descritiva para o cliente.",
    )
    mfa_type: str = Field(
        default="totp",
        description="Tipo de MFA configurado (atualmente apenas 'totp').",
    )


class AuthErrorResponse(BaseModel):
    """DTO padrão para respostas de erro de autenticação.

    Utilizado para padronizar mensagens de erro retornadas pelos
    endpoints de autenticação.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detail": "Credenciais inválidas.",
                "error_code": "INVALID_CREDENTIALS",
            }
        }
    )

    detail: str = Field(
        ...,
        description="Mensagem descritiva do erro em PT-BR.",
    )
    error_code: str = Field(
        ...,
        description=(
            "Código de erro padronizado para tratamento no frontend. "
            "Ex.: INVALID_CREDENTIALS, TOKEN_EXPIRED, MFA_REQUIRED."
        ),
    )
