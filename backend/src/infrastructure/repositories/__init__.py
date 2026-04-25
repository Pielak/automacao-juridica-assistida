"""Pacote de repositórios da camada de infraestrutura.

Este pacote contém as implementações concretas dos repositórios
(adapters) que satisfazem as interfaces (ports) definidas na camada
de aplicação/domínio, seguindo os princípios de Clean Architecture
(Ports & Adapters).

Cada módulo funcional (auth, users, documents, analysis, chat, audit)
possui seu próprio repositório com acesso ao banco de dados via
SQLAlchemy 2.0 assíncrono.
"""

# TODO: Importar e re-exportar repositórios concretos conforme forem implementados.
# Exemplo esperado após implementação dos módulos:
#
# from backend.src.infrastructure.repositories.user_repository import UserRepository
# from backend.src.infrastructure.repositories.document_repository import DocumentRepository
# from backend.src.infrastructure.repositories.analysis_repository import AnalysisRepository
# from backend.src.infrastructure.repositories.chat_repository import ChatRepository
# from backend.src.infrastructure.repositories.audit_repository import AuditRepository
#
# __all__ = [
#     "UserRepository",
#     "DocumentRepository",
#     "AnalysisRepository",
#     "ChatRepository",
#     "AuditRepository",
# ]

__all__: list[str] = []
