"""Router raiz da API — Automação Jurídica Assistida.

Agrega todos os sub-routers dos módulos funcionais da aplicação,
aplicando prefixos e tags consistentes para a documentação OpenAPI.

Módulos registrados:
    - auth      — Autenticação e autorização (login, registro, refresh, logout)
    - cases     — CRUD de casos/processos jurídicos
    - documents — Upload, listagem e gestão de documentos jurídicos
    - analysis  — Análise jurídica assistida por IA (LLM)
    - chat      — Chat jurídico assistido com sessões e histórico
    - audit     — Trilha de auditoria (admin only)
    - health    — Health checks (liveness e readiness probes)

Exemplo de uso:
    from backend.src.api.router import api_router
    app.include_router(api_router)
"""

from __future__ import annotations

from fastapi import APIRouter

# ---------------------------------------------------------------------------
# Importação dos sub-routers de cada módulo funcional.
# Cada módulo expõe um objeto `router` (instância de APIRouter) com seus
# endpoints já definidos.
# ---------------------------------------------------------------------------
from backend.src.api.routes.auth_routes import router as auth_router
from backend.src.api.routes.case_routes import router as case_router
from backend.src.api.routes.document_routes import router as document_router
from backend.src.api.routes.analysis_routes import router as analysis_router
from backend.src.api.routes.chat_routes import router as chat_router
from backend.src.api.routes.audit_routes import router as audit_router
from backend.src.api.routes.health_routes import router as health_router

# ---------------------------------------------------------------------------
# Router raiz — ponto central de agregação de todas as rotas da API.
# O prefixo "/api/v1" é aplicado aqui para versionamento consistente.
# Os sub-routers de health ficam fora do prefixo versionado por convenção
# (probes de infraestrutura não são versionadas).
# ---------------------------------------------------------------------------

API_V1_PREFIX = "/api/v1"

api_router = APIRouter()
"""Router raiz que agrega todos os módulos da aplicação."""


def _build_api_router() -> APIRouter:
    """Constrói e retorna o router raiz com todos os sub-routers registrados.

    A função centraliza a inclusão dos sub-routers para facilitar testes
    e evitar efeitos colaterais na importação do módulo.

    Returns:
        APIRouter configurado com todos os endpoints da aplicação.
    """
    router = APIRouter()

    # ------------------------------------------------------------------
    # Rotas versionadas (v1) — módulos de negócio
    # ------------------------------------------------------------------
    router.include_router(
        auth_router,
        prefix=f"{API_V1_PREFIX}/auth",
        tags=["Autenticação"],
    )

    router.include_router(
        case_router,
        prefix=f"{API_V1_PREFIX}/cases",
        tags=["Casos / Processos"],
    )

    router.include_router(
        document_router,
        prefix=f"{API_V1_PREFIX}/documents",
        tags=["Documentos"],
    )

    router.include_router(
        analysis_router,
        prefix=f"{API_V1_PREFIX}/analyses",
        tags=["Análise Jurídica IA"],
    )

    router.include_router(
        chat_router,
        prefix=f"{API_V1_PREFIX}/chat",
        tags=["Chat Jurídico"],
    )

    router.include_router(
        audit_router,
        prefix=f"{API_V1_PREFIX}/audit",
        tags=["Auditoria"],
    )

    # ------------------------------------------------------------------
    # Rotas de infraestrutura — sem versionamento
    # Health checks são utilizados por orquestradores (k8s, ECS, etc.)
    # e não devem depender da versão da API de negócio.
    # ------------------------------------------------------------------
    router.include_router(
        health_router,
        prefix="/health",
        tags=["Health Check"],
    )

    return router


# Constrói o router raiz na inicialização do módulo.
api_router = _build_api_router()
