"""
Ponto de entrada principal da aplicação Automação Jurídica Assistida.

Responsável por inicializar a aplicação FastAPI, registrar routers,
configurar middlewares (CORS, HTTPS redirect, logging) e expor
os endpoints da REST API para o frontend React.

Decisão arquitetural: Monólito modular com Clean Architecture.
O backend é uma REST API FastAPI servindo um frontend React SPA.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import auth_router, cases_router, documents_router, calculations_router, dashboard_router, ai_router
from app.database import engine, Base

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gerencia o ciclo de vida da aplicação.

    Cria as tabelas do banco de dados na inicialização e
    libera recursos no encerramento.

    Args:
        app: Instância da aplicação FastAPI.

    Yields:
        None: Controle retorna à aplicação durante a execução.
    """
    logger.info("Iniciando Automação Jurídica Assistida v0.1.0")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Tabelas do banco de dados criadas/verificadas.")
    yield
    logger.info("Encerrando aplicação.")
    await engine.dispose()


def create_app() -> FastAPI:
    """Cria e configura a instância FastAPI.

    Registra todos os routers de módulos, configura CORS e
    middlewares de segurança declarados no compliance.

    Returns:
        FastAPI: Instância configurada da aplicação.
    """
    app = FastAPI(
        title="Automação Jurídica Assistida",
        description="Sistema para auxiliar advogados de Processo Cível em suas atividades do dia a dia.",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router, prefix="/api/v1/auth", tags=["Autenticação"])
    app.include_router(cases_router, prefix="/api/v1/cases", tags=["Casos"])
    app.include_router(documents_router, prefix="/api/v1/documents", tags=["Documentos"])
    app.include_router(calculations_router, prefix="/api/v1/calculations", tags=["Cálculos"])
    app.include_router(dashboard_router, prefix="/api/v1/dashboard", tags=["Painel"])
    app.include_router(ai_router, prefix="/api/v1/ai", tags=["IA"])

    @app.get("/health", tags=["Infraestrutura"])
    async def health_check() -> dict:
        """Verifica se a aplicação está saudável.

        Returns:
            dict: Status da aplicação com versão.
        """
        return {"status": "healthy", "version": "0.1.0"}

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
