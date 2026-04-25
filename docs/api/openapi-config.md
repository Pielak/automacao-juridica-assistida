# Configuração da API OpenAPI — Automação Jurídica Assistida

## Sumário

1. [Visão Geral](#visão-geral)
2. [Configuração Base do FastAPI](#configuração-base-do-fastapi)
3. [Versionamento da API](#versionamento-da-api)
4. [Autenticação e Segurança](#autenticação-e-segurança)
5. [Estrutura de Routers Modulares](#estrutura-de-routers-modulares)
6. [Schemas e Exemplos](#schemas-e-exemplos)
7. [Respostas Padrão de Erro](#respostas-padrão-de-erro)
8. [Rate Limiting](#rate-limiting)
9. [CORS e Headers de Segurança](#cors-e-headers-de-segurança)
10. [Ambientes e Variáveis](#ambientes-e-variáveis)
11. [Referência Rápida de Endpoints](#referência-rápida-de-endpoints)

---

## Visão Geral

A API REST do projeto **Automação Jurídica Assistida** é construída com **FastAPI 0.100+** e gera documentação OpenAPI 3.1 automaticamente. Este documento descreve as convenções de configuração, autenticação, versionamento e exemplos de uso.

### Princípios

- **Documentação como código**: a especificação OpenAPI é gerada automaticamente a partir dos schemas Pydantic v2 e dos decorators do FastAPI.
- **Segurança por padrão**: todos os endpoints (exceto login e health check) exigem autenticação JWT.
- **Consistência**: respostas de erro seguem um schema padronizado em toda a API.
- **Versionamento explícito**: prefixo `/api/v1` em todas as rotas.

---

## Configuração Base do FastAPI

### Instância principal da aplicação

```python
# src/main.py
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def create_app() -> FastAPI:
    """Cria e configura a instância principal da aplicação FastAPI."""
    app = FastAPI(
        title="Automação Jurídica Assistida — API",
        description=(
            "API REST para automação de processos jurídicos com assistência de IA. "
            "Permite gestão de documentos, análise automatizada via Claude (Anthropic), "
            "consulta ao DataJud e geração de peças jurídicas."
        ),
        version="1.0.0",
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
        openapi_url="/api/v1/openapi.json",
        contact={
            "name": "Equipe de Desenvolvimento",
            "email": "dev@automacao-juridica.com.br",
        },
        license_info={
            "name": "Proprietária",
            "url": "https://automacao-juridica.com.br/licenca",
        },
        openapi_tags=get_openapi_tags(),
    )
    return app
```

### Tags OpenAPI

As tags organizam os endpoints por módulo funcional na documentação Swagger/ReDoc:

```python
def get_openapi_tags() -> list[dict]:
    """Retorna as tags OpenAPI organizadas por módulo funcional."""
    return [
        {
            "name": "auth",
            "description": "Autenticação, autorização, MFA e gestão de sessões JWT.",
        },
        {
            "name": "users",
            "description": "CRUD de usuários, perfis e controle de acesso RBAC.",
        },
        {
            "name": "documents",
            "description": (
                "Upload, versionamento e gestão do ciclo de vida de documentos jurídicos."
            ),
        },
        {
            "name": "analysis",
            "description": (
                "Análise automatizada de documentos via IA (Claude/Anthropic). "
                "Inclui extração de dados, sumarização e classificação."
            ),
        },
        {
            "name": "chat",
            "description": "Chat assistido por IA para consultas jurídicas contextualizadas.",
        },
        {
            "name": "datajud",
            "description": "Integração com a API DataJud para consulta de processos judiciais.",
        },
        {
            "name": "audit",
            "description": "Logs de auditoria e rastreabilidade de ações do sistema.",
        },
        {
            "name": "health",
            "description": "Verificação de saúde da aplicação e dependências.",
        },
    ]
```

### Schema OpenAPI customizado (opcional)

Para customizações avançadas do schema OpenAPI gerado:

```python
def custom_openapi(app: FastAPI) -> dict:
    """Gera schema OpenAPI customizado com informações adicionais de segurança."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )

    # Adiciona informações de servidor por ambiente
    openapi_schema["servers"] = [
        {
            "url": "https://api.automacao-juridica.com.br",
            "description": "Produção",
        },
        {
            "url": "https://staging-api.automacao-juridica.com.br",
            "description": "Homologação",
        },
        {
            "url": "http://localhost:8000",
            "description": "Desenvolvimento local",
        },
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema
```

---

## Versionamento da API

### Estratégia: Prefixo de URL

A API utiliza versionamento via prefixo de URL (`/api/v1/...`). Esta abordagem foi escolhida por:

- **Simplicidade**: fácil de implementar e entender.
- **Compatibilidade**: permite coexistência de versões durante migrações.
- **Visibilidade**: a versão é explícita em cada request.

### Estrutura de prefixos

| Versão | Prefixo      | Status       |
|--------|--------------|--------------|
| v1     | `/api/v1`    | Ativa        |
| v2     | `/api/v2`    | Planejada    |

### Implementação com APIRouter

```python
# src/api/v1/router.py
from fastapi import APIRouter

api_v1_router = APIRouter(prefix="/api/v1")

# Inclusão dos routers de cada módulo
api_v1_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(users_router, prefix="/users", tags=["users"])
api_v1_router.include_router(documents_router, prefix="/documents", tags=["documents"])
api_v1_router.include_router(analysis_router, prefix="/analysis", tags=["analysis"])
api_v1_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_v1_router.include_router(datajud_router, prefix="/datajud", tags=["datajud"])
api_v1_router.include_router(audit_router, prefix="/audit", tags=["audit"])
api_v1_router.include_router(health_router, prefix="/health", tags=["health"])
```

### Política de depreciação

- Versões antigas serão mantidas por **no mínimo 6 meses** após lançamento da nova versão.
- Endpoints depreciados incluirão o header `Deprecation: true` e `Sunset: <data>`.
- A documentação OpenAPI marcará endpoints depreciados com `deprecated: true`.

```python
@router.get(
    "/legacy-endpoint",
    deprecated=True,
    summary="[DEPRECIADO] Use /api/v2/new-endpoint",
)
async def legacy_endpoint():
    """Endpoint depreciado. Será removido em 2025-06-01."""
    ...
```

---

## Autenticação e Segurança

### Esquema de autenticação: JWT Bearer com RS256

A API utiliza tokens JWT assinados com algoritmo **RS256** (chave assimétrica). Isso permite que serviços externos validem tokens sem acesso à chave privada.

### Configuração OpenAPI Security Scheme

```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Security, Depends

# Esquema de segurança para documentação OpenAPI
bearer_scheme = HTTPBearer(
    scheme_name="JWT Bearer",
    description=(
        "Token JWT obtido via endpoint `/api/v1/auth/login`. "
        "Formato: `Bearer <token>`. "
        "Tokens expiram em 30 minutos. Use `/api/v1/auth/refresh` para renovar."
    ),
    auto_error=True,
)
```

### Fluxo de autenticação

```
┌─────────┐     POST /api/v1/auth/login      ┌──────────┐
│ Cliente  │ ──────────────────────────────► │  API     │
│ (React)  │     { email, senha }            │ FastAPI  │
│          │ ◄────────────────────────────── │          │
│          │     { access_token,             │          │
│          │       refresh_token,            │          │
│          │       token_type: "bearer" }    │          │
└─────────┘                                  └──────────┘
       │
       │  (se MFA habilitado)
       │
       ▼
┌─────────┐     POST /api/v1/auth/mfa/verify  ┌──────────┐
│ Cliente  │ ──────────────────────────────► │  API     │
│          │     { mfa_token, totp_code }    │          │
│          │ ◄────────────────────────────── │          │
│          │     { access_token,             │          │
│          │       refresh_token }           │          │
└─────────┘                                  └──────────┘
```

### Estrutura do token JWT

**Header:**
```json
{
  "alg": "RS256",
  "typ": "JWT"
}
```

**Payload (claims):**
```json
{
  "sub": "uuid-do-usuario",
  "email": "usuario@escritorio.com.br",
  "role": "advogado",
  "permissions": ["documents:read", "documents:write", "analysis:read"],
  "iat": 1700000000,
  "exp": 1700001800,
  "jti": "uuid-unico-do-token",
  "iss": "automacao-juridica-assistida"
}
```

### Tempos de expiração

| Token           | Expiração   | Renovável |
|-----------------|-------------|-----------|
| Access Token    | 30 minutos  | Não       |
| Refresh Token   | 7 dias      | Sim       |
| MFA Token       | 5 minutos   | Não       |

### Dependency de autenticação

```python
# src/api/dependencies/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """
    Valida o token JWT e retorna os dados do usuário autenticado.

    Raises:
        HTTPException 401: Token inválido, expirado ou ausente.
        HTTPException 403: Usuário sem permissão para o recurso.
    """
    token = credentials.credentials
    # TODO: Implementar validação completa do JWT com python-jose/PyJWT
    # - Verificar assinatura RS256
    # - Validar claims (exp, iss, sub)
    # - Buscar usuário no banco
    # - Verificar se token não foi revogado
    ...


def require_permissions(*permissions: str):
    """
    Dependency factory que verifica se o usuário possui as permissões necessárias.

    Uso:
        @router.get("/documents", dependencies=[Depends(require_permissions("documents:read"))])
    """
    async def _check_permissions(
        current_user: dict = Depends(get_current_user),
    ) -> dict:
        user_permissions = current_user.get("permissions", [])
        missing = [p for p in permissions if p not in user_permissions]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permissões insuficientes. Necessário: {', '.join(missing)}",
            )
        return current_user

    return _check_permissions
```

### Endpoints públicos (sem autenticação)

Os seguintes endpoints **não** exigem token JWT:

| Método | Endpoint                    | Descrição                        |
|--------|-----------------------------|----------------------------------|
| POST   | `/api/v1/auth/login`        | Login com email e senha          |
| POST   | `/api/v1/auth/refresh`      | Renovação de token               |
| POST   | `/api/v1/auth/mfa/verify`   | Verificação de código MFA        |
| GET    | `/api/v1/health`            | Health check da aplicação        |
| GET    | `/api/v1/docs`              | Documentação Swagger UI          |
| GET    | `/api/v1/redoc`             | Documentação ReDoc               |
| GET    | `/api/v1/openapi.json`      | Schema OpenAPI em JSON           |

> **Nota de segurança**: Em produção, os endpoints de documentação (`/docs`, `/redoc`, `/openapi.json`) devem ser desabilitados ou protegidos por autenticação. Veja a seção [Ambientes e Variáveis](#ambientes-e-variáveis).

---

## Estrutura de Routers Modulares

Cada módulo funcional possui seu próprio router, seguindo a Clean Architecture:

```
src/
├── api/
│   ├── v1/
│   │   ├── router.py              # Router agregador v1
│   │   ├── endpoints/
│   │   │   ├── auth.py            # Endpoints de autenticação
│   │   │   ├── users.py           # Endpoints de usuários
│   │   │   ├── documents.py       # Endpoints de documentos
│   │   │   ├── analysis.py        # Endpoints de análise IA
│   │   │   ├── chat.py            # Endpoints de chat assistido
│   │   │   ├── datajud.py         # Endpoints DataJud
│   │   │   ├── audit.py           # Endpoints de auditoria
│   │   │   └── health.py          # Endpoints de health check
│   │   └── schemas/
│   │       ├── auth.py            # Schemas Pydantic de auth
│   │       ├── users.py           # Schemas Pydantic de users
│   │       ├── documents.py       # Schemas Pydantic de documents
│   │       ├── analysis.py        # Schemas Pydantic de analysis
│   │       ├── chat.py            # Schemas Pydantic de chat
│   │       ├── common.py          # Schemas compartilhados
│   │       └── errors.py          # Schemas de erro padronizados
│   └── dependencies/
│       ├── auth.py                # Dependencies de autenticação
│       ├── database.py            # Sessão de banco de dados
│       └── rate_limit.py          # Rate limiting
```

### Convenção de definição de endpoints

```python
# src/api/v1/endpoints/documents.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from src.api.v1.schemas.documents import (
    DocumentResponse,
    DocumentListResponse,
    DocumentCreateRequest,
)
from src.api.v1.schemas.common import PaginatedResponse
from src.api.v1.schemas.errors import ErrorResponse
from src.api.dependencies.auth import get_current_user, require_permissions

router = APIRouter()


@router.get(
    "/",
    response_model=PaginatedResponse[DocumentListResponse],
    summary="Listar documentos",
    description="Retorna lista paginada de documentos do usuário autenticado.",
    responses={
        200: {
            "description": "Lista de documentos retornada com sucesso.",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": "550e8400-e29b-41d4-a716-446655440000",
                                "titulo": "Petição Inicial — Processo 0001234-56.2024.8.26.0100",
                                "tipo": "peticao_inicial",
                                "status": "analisado",
                                "criado_em": "2024-01-15T10:30:00Z",
                                "atualizado_em": "2024-01-15T14:22:00Z",
                            }
                        ],
                        "total": 42,
                        "pagina": 1,
                        "por_pagina": 20,
                        "total_paginas": 3,
                    }
                }
            },
        },
        401: {"model": ErrorResponse, "description": "Token inválido ou ausente."},
        403: {"model": ErrorResponse, "description": "Permissão insuficiente."},
    },
)
async def list_documents(
    pagina: int = 1,
    por_pagina: int = 20,
    tipo: str | None = None,
    status: str | None = None,
    current_user: dict = Depends(require_permissions("documents:read")),
):
    """Lista documentos jurídicos com filtros e paginação."""
    # TODO: Implementar lógica de listagem via use case
    ...
```

---

## Schemas e Exemplos

### Schemas Pydantic v2 — Convenções

Todos os schemas seguem estas convenções:

- Herdam de `pydantic.BaseModel` com `model_config` configurado.
- Campos possuem `description` em português para documentação OpenAPI.
- Exemplos são fornecidos via `model_config["json_schema_extra"]` ou `Field(examples=[...])`.
- Validações customizadas usam `@field_validator` com mensagens em português.

### Schema de erro padronizado

```python
# src/api/v1/schemas/errors.py
from pydantic import BaseModel, Field
from datetime import datetime


class ErrorDetail(BaseModel):
    """Detalhe individual de um erro de validação."""

    campo: str = Field(description="Nome do campo com erro.")
    mensagem: str = Field(description="Descrição do erro de validação.")
    tipo: str = Field(description="Tipo do erro (ex: 'value_error', 'type_error').")


class ErrorResponse(BaseModel):
    """Schema padrão de resposta de erro da API."""

    sucesso: bool = Field(default=False, description="Indica se a operação foi bem-sucedida.")
    codigo: int = Field(description="Código HTTP do erro.")
    mensagem: str = Field(description="Mensagem descritiva do erro em português.")
    detalhes: list[ErrorDetail] | None = Field(
        default=None,
        description="Lista de erros de validação (quando aplicável).",
    )
    request_id: str = Field(description="ID único da requisição para rastreabilidade.")
    timestamp: datetime = Field(description="Data/hora do erro em UTC.")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "sucesso": False,
                    "codigo": 422,
                    "mensagem": "Erro de validação nos dados enviados.",
                    "detalhes": [
                        {
                            "campo": "email",
                            "mensagem": "Endereço de e-mail inválido.",
                            "tipo": "value_error",
                        }
                    ],
                    "request_id": "req_abc123def456",
                    "timestamp": "2024-01-15T10:30:00Z",
                }
            ]
        }
    }
```

### Schema de autenticação — Exemplos

```python
# src/api/v1/schemas/auth.py
from pydantic import BaseModel, Field, EmailStr


class LoginRequest(BaseModel):
    """Schema de requisição de login."""

    email: EmailStr = Field(
        description="Endereço de e-mail cadastrado.",
        examples=["advogado@escritorio.com.br"],
    )
    senha: str = Field(
        description="Senha do usuário. Mínimo 8 caracteres.",
        min_length=8,
        max_length=128,
        examples=["SenhaSegura@123"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "advogado@escritorio.com.br",
                    "senha": "SenhaSegura@123",
                }
            ]
        }
    }


class LoginResponse(BaseModel):
    """Schema de resposta de login bem-sucedido."""

    access_token: str = Field(
        description="Token JWT de acesso. Expira em 30 minutos.",
        examples=["eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    refresh_token: str = Field(
        description="Token de renovação. Expira em 7 dias.",
        examples=["eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    token_type: str = Field(
        default="bearer",
        description="Tipo do token. Sempre 'bearer'.",
    )
    expira_em: int = Field(
        description="Tempo de expiração do access_token em segundos.",
        examples=[1800],
    )
    requer_mfa: bool = Field(
        default=False,
        description="Indica se o usuário precisa completar verificação MFA.",
    )


class MFAVerifyRequest(BaseModel):
    """Schema de requisição de verificação MFA."""

    mfa_token: str = Field(
        description="Token temporário recebido no login quando MFA é requerido.",
    )
    codigo_totp: str = Field(
        description="Código TOTP de 6 dígitos do aplicativo autenticador.",
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        examples=["123456"],
    )
```

### Schema de resposta paginada (genérico)

```python
# src/api/v1/schemas/common.py
from typing import Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Schema genérico para respostas paginadas."""

    items: list[T] = Field(description="Lista de itens da página atual.")
    total: int = Field(description="Total de itens encontrados.", examples=[42])
    pagina: int = Field(description="Número da página atual.", examples=[1])
    por_pagina: int = Field(description="Quantidade de itens por página.", examples=[20])
    total_paginas: int = Field(description="Total de páginas disponíveis.", examples=[3])


class SuccessResponse(BaseModel):
    """Schema genérico para respostas de sucesso sem dados."""

    sucesso: bool = Field(default=True, description="Indica operação bem-sucedida.")
    mensagem: str = Field(description="Mensagem descritiva do resultado.")
```

---

## Respostas Padrão de Erro

### Códigos HTTP utilizados

| Código | Significado                | Quando usar                                                    |
|--------|----------------------------|----------------------------------------------------------------|
| 200    | OK                         | Requisição processada com sucesso.                             |
| 201    | Created                    | Recurso criado com sucesso (POST).                             |
| 204    | No Content                 | Operação bem-sucedida sem corpo de resposta (DELETE).          |
| 400    | Bad Request                | Requisição malformada ou parâmetros inválidos.                 |
| 401    | Unauthorized               | Token JWT ausente, inválido ou expirado.                       |
| 403    | Forbidden                  | Usuário autenticado mas sem permissão para o recurso.          |
| 404    | Not Found                  | Recurso não encontrado.                                        |
| 409    | Conflict                   | Conflito de estado (ex: e-mail já cadastrado).                 |
| 413    | Payload Too Large          | Arquivo enviado excede o tamanho máximo permitido.             |
| 422    | Unprocessable Entity       | Erro de validação nos dados enviados (Pydantic).               |
| 429    | Too Many Requests          | Rate limit excedido.                                           |
| 500    | Internal Server Error      | Erro interno não tratado.                                      |
| 502    | Bad Gateway                | Erro na comunicação com serviço externo (Anthropic, DataJud).  |
| 503    | Service Unavailable        | Serviço temporariamente indisponível.                          |

### Handler global de exceções

```python
# src/api/exception_handlers.py
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from datetime import datetime, timezone
import uuid


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handler para erros de validação Pydantic — retorna mensagens em PT-BR."""
    detalhes = []
    for error in exc.errors():
        campo = " → ".join(str(loc) for loc in error["loc"])
        detalhes.append(
            {
                "campo": campo,
                "mensagem": error["msg"],
                "tipo": error["type"],
            }
        )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "sucesso": False,
            "codigo": 422,
            "mensagem": "Erro de validação nos dados enviados.",
            "detalhes": detalhes,
            "request_id": getattr(request.state, "request_id", str(uuid.uuid4())),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
```

---

## Rate Limiting

A API implementa rate limiting via **slowapi** para proteger contra abuso:

| Endpoint                  | Limite                  | Janela    |
|---------------------------|-------------------------|-----------|
| `POST /auth/login`        | 5 requisições           | 1 minuto  |
| `POST /auth/mfa/verify`   | 3 requisições           | 1 minuto  |
| `POST /analysis/*`        | 10 requisições          | 1 minuto  |
| `POST /chat/*`            | 20 requisições          | 1 minuto  |
| Demais endpoints          | 100 requisições         | 1 minuto  |

Quando o limite é excedido, a API retorna:

```json
{
  "sucesso": false,
  "codigo": 429,
  "mensagem": "Limite de requisições excedido. Tente novamente em 45 segundos.",
  "detalhes": null,
  "request_id": "req_abc123",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

Headers de rate limit incluídos em todas as respostas:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1700001860
Retry-After: 45  (apenas em respostas 429)
```

---

## CORS e Headers de Segurança

### Configuração CORS

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # Configurável por ambiente
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
    max_age=600,  # Cache de preflight por 10 minutos
)
```

### Origens permitidas por ambiente

| Ambiente       | Origens permitidas                                  |
|----------------|-----------------------------------------------------|
| Desenvolvimento| `http://localhost:5173`, `http://localhost:3000`     |
| Homologação    | `https://staging.automacao-juridica.com.br`          |
| Produção       | `https://app.automacao-juridica.com.br`              |

### Headers de segurança (via Nginx ou middleware)

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
Referrer-Policy: strict-origin-when-cross-origin
```

---

## Ambientes e Variáveis

### Variáveis de ambiente relevantes para OpenAPI

```bash
# Ambiente da aplicação (development | staging | production)
APP_ENV=development

# Habilitar/desabilitar documentação OpenAPI
# Em produção, recomenda-se desabilitar ou proteger com autenticação
OPENAPI_DOCS_ENABLED=true

# URL base da API (usada nos servers do OpenAPI)
API_BASE_URL=http://localhost:8000

# CORS
CORS_ORIGINS=["http://localhost:5173"]

# JWT
JWT_PRIVATE_KEY_PATH=/secrets/jwt-private.pem
JWT_PUBLIC_KEY_PATH=/secrets/jwt-public.pem
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
JWT_ALGORITHM=RS256
JWT_ISSUER=automacao-juridica-assistida

# Rate Limiting
RATE_LIMIT_DEFAULT=100/minute
RATE_LIMIT_AUTH=5/minute
```

### Desabilitação da documentação em produção

```python
import os

def create_app() -> FastAPI:
    """Cria a aplicação com documentação condicional por ambiente."""
    is_production = os.getenv("APP_ENV") == "production"
    docs_enabled = os.getenv("OPENAPI_DOCS_ENABLED", "true").lower() == "true"

    app = FastAPI(
        title="Automação Jurídica Assistida — API",
        version="1.0.0",
        docs_url="/api/v1/docs" if docs_enabled and not is_production else None,
        redoc_url="/api/v1/redoc" if docs_enabled and not is_production else None,
        openapi_url="/api/v1/openapi.json" if docs_enabled else None,
    )
    return app
```

---

## Referência Rápida de Endpoints

### Módulo: Auth

| Método | Endpoint                       | Descrição                              | Auth |
|--------|--------------------------------|----------------------------------------|------|
| POST   | `/api/v1/auth/login`           | Login com email e senha                | Não  |
| POST   | `/api/v1/auth/refresh`         | Renovar access token                   | Não  |
| POST   | `/api/v1/auth/logout`          | Revogar tokens da sessão               | Sim  |
| POST   | `/api/v1/auth/mfa/setup`       | Configurar MFA (TOTP)                  | Sim  |
| POST   | `/api/v1/auth/mfa/verify`      | Verificar código MFA                   | Não  |
| DELETE | `/api/v1/auth/mfa`             | Desabilitar MFA                        | Sim  |

### Módulo: Users

| Método | Endpoint                       | Descrição                              | Auth |
|--------|--------------------------------|----------------------------------------|------|
| GET    | `/api/v1/users/me`             | Dados do usuário autenticado           | Sim  |
| PUT    | `/api/v1/users/me`             | Atualizar perfil                       | Sim  |
| PATCH  | `/api/v1/users/me/password`    | Alterar senha                          | Sim  |
| GET    | `/api/v1/users`                | Listar usuários (admin)                | Sim  |
| POST   | `/api/v1/users`                | Criar usuário (admin)                  | Sim  |
| GET    | `/api/v1/users/{id}`           | Detalhes de um usuário (admin)         | Sim  |
| PUT    | `/api/v1/users/{id}`           | Atualizar usuário (admin)              | Sim  |
| DELETE | `/api/v1/users/{id}`           | Desativar usuário (admin)              | Sim  |

### Módulo: Documents

| Método | Endpoint                            | Descrição                              | Auth |
|--------|-------------------------------------|----------------------------------------|------|
| GET    | `/api/v1/documents`                 | Listar documentos                      | Sim  |
| POST   | `/api/v1/documents`                 | Upload de novo documento               | Sim  |
| GET    | `/api/v1/documents/{id}`            | Detalhes de um documento               | Sim  |
| PUT    | `/api/v1/documents/{id}`            | Atualizar metadados                    | Sim  |
| DELETE | `/api/v1/documents/{id}`            | Remover documento                      | Sim  |
| GET    | `/api/v1/documents/{id}/download`   | Download do arquivo                    | Sim  |
| GET    | `/api/v1/documents/{id}/versions`   | Histórico de versões                   | Sim  |

### Módulo: Analysis

| Método | Endpoint                            | Descrição                              | Auth |
|--------|-------------------------------------|----------------------------------------|------|
| POST   | `/api/v1/analysis`                  | Solicitar análise de documento via IA  | Sim  |
| GET    | `/api/v1/analysis/{id}`             | Status/resultado de uma análise        | Sim  |
| GET    | `/api/v1/analysis`                  | Listar análises do usuário             | Sim  |
| POST   | `/api/v1/analysis/{id}/retry`       | Reprocessar análise com erro           | Sim  |

### Módulo: Chat

| Método | Endpoint                            | Descrição                              | Auth |
|--------|-------------------------------------|----------------------------------------|------|
| POST   | `/api/v1/chat/sessions`             | Criar nova sessão de chat              | Sim  |
| GET    | `/api/v1/chat/sessions`             | Listar sessões de chat                 | Sim  |
| GET    | `/api/v1/chat/sessions/{id}`        | Histórico de uma sessão                | Sim  |
| POST   | `/api/v1/chat/sessions/{id}/messages` | Enviar mensagem ao chat IA           | Sim  |
| DELETE | `/api/v1/chat/sessions/{id}`        | Encerrar sessão de chat                | Sim  |

### Módulo: DataJud

| Método | Endpoint                            | Descrição                              | Auth |
|--------|-------------------------------------|----------------------------------------|------|
| GET    | `/api/v1/datajud/processos`         | Buscar processos no DataJud            | Sim  |
| GET    | `/api/v1/datajud/processos/{numero}`| Detalhes de um processo                | Sim  |
| GET    | `/api/v1/datajud/processos/{numero}/movimentacoes` | Movimentações do processo | Sim  |

### Módulo: Audit

| Método | Endpoint                            | Descrição                              | Auth |
|--------|-------------------------------------|----------------------------------------|------|
| GET    | `/api/v1/audit/logs`                | Listar logs de auditoria (admin)       | Sim  |
| GET    | `/api/v1/audit/logs/{id}`           | Detalhes de um log                     | Sim  |
| GET    | `/api/v1/audit/logs/export`         | Exportar logs em CSV                   | Sim  |

### Módulo: Health

| Método | Endpoint                            | Descrição                              | Auth |
|--------|-------------------------------------|----------------------------------------|------|
| GET    | `/api/v1/health`                    | Health check básico                    | Não  |
| GET    | `/api/v1/health/ready`              | Readiness (banco, Redis, etc.)         | Não  |
| GET    | `/api/v1/health/live`               | Liveness probe                         | Não  |

---

## Exemplos de Uso com cURL

### Login

```bash
curl -X POST https://api.automacao-juridica.com.br/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "advogado@escritorio.com.br",
    "senha": "SenhaSegura@123"
  }'
```

**Resposta (200):**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "bearer",
  "expira_em": 1800,
  "requer_mfa": false
}
```

### Listar documentos (autenticado)

```bash
curl -X GET "https://api.automacao-juridica.com.br/api/v1/documents?pagina=1&por_pagina=10&tipo=peticao_inicial" \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIs..."
```

### Upload de documento

```bash
curl -X POST https://api.automacao-juridica.com.br/api/v1/documents \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIs..." \
  -F "arquivo=@peticao-inicial.pdf" \
  -F "titulo=Petição Inicial — Caso Silva vs. Santos" \
  -F "tipo=peticao_inicial"
```

### Solicitar análise via IA

```bash
curl -X POST https://api.automacao-juridica.com.br/api/v1/analysis \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIs..." \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "550e8400-e29b-41d4-a716-446655440000",
    "tipo_analise": "sumarizacao",
    "instrucoes_adicionais": "Focar nos pedidos e fundamentos jurídicos."
  }'
```

---

## Middleware de Request ID

Todas as requisições recebem um ID único para rastreabilidade:

```python
# src/api/middleware/request_id.py
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware que adiciona um ID único a cada requisição para rastreabilidade."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

---

## Decisões Pendentes

- **G005 ADR**: Design tokens (cores, tipografia, breakpoints) — impacta documentação de schemas de UI.
- **G002 ADR**: FAISS vs. Milvus para busca semântica — pode adicionar endpoints de busca vetorial.

---

> **Última atualização**: Janeiro 2025
> **Responsável**: Equipe de Arquitetura — Automação Jurídica Assistida
