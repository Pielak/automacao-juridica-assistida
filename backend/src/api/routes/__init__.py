"""Pacote de rotas da API.

Este módulo centraliza o registro de todos os routers modulares da aplicação,
seguindo a arquitetura de monólito modular. Cada módulo funcional expõe seu
próprio router que é agregado aqui para inclusão na aplicação FastAPI principal.
"""

from fastapi import APIRouter

# Router principal que agrega todos os sub-routers da aplicação
main_router = APIRouter()

# TODO: Importar e incluir os routers de cada módulo funcional conforme forem criados.
# Cada módulo deve expor seu próprio APIRouter em seu respectivo arquivo de rotas.
#
# Módulos planejados (conforme arquitetura Clean Architecture):
#   - auth: autenticação JWT, MFA, gestão de sessões
#   - users: CRUD de usuários e perfis RBAC
#   - documents: upload, gestão e ciclo de vida de documentos jurídicos
#   - analysis: análise de documentos via IA (integração Anthropic Claude)
#   - chat: interface conversacional assistida por IA
#   - audit: trilha de auditoria e logs de conformidade
#
# Exemplo de inclusão (descomentar quando os módulos existirem):
#
# from backend.src.api.routes.auth import router as auth_router
# from backend.src.api.routes.users import router as users_router
# from backend.src.api.routes.documents import router as documents_router
# from backend.src.api.routes.analysis import router as analysis_router
# from backend.src.api.routes.chat import router as chat_router
# from backend.src.api.routes.audit import router as audit_router
#
# main_router.include_router(
#     auth_router,
#     prefix="/auth",
#     tags=["Autenticação"],
# )
# main_router.include_router(
#     users_router,
#     prefix="/users",
#     tags=["Usuários"],
# )
# main_router.include_router(
#     documents_router,
#     prefix="/documents",
#     tags=["Documentos"],
# )
# main_router.include_router(
#     analysis_router,
#     prefix="/analysis",
#     tags=["Análise"],
# )
# main_router.include_router(
#     chat_router,
#     prefix="/chat",
#     tags=["Chat Assistido"],
# )
# main_router.include_router(
#     audit_router,
#     prefix="/audit",
#     tags=["Auditoria"],
# )


# Router de verificação de saúde — disponível imediatamente
health_router = APIRouter(tags=["Saúde"])


@health_router.get(
    "/health",
    summary="Verificação de saúde da API",
    description="Endpoint para verificar se a API está operacional.",
)
async def health_check() -> dict:
    """Retorna o status de saúde da aplicação.

    Returns:
        Dicionário com status da API e informações básicas.
    """
    return {
        "status": "ok",
        "servico": "Automação Jurídica Assistida - API",
    }


main_router.include_router(health_router)

__all__ = ["main_router"]
