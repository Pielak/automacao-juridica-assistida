"""Pacote de módulos da aplicação Automação Jurídica Assistida.

Este pacote contém os módulos funcionais do sistema, organizados seguindo
os princípios de Clean Architecture (Ports & Adapters). Cada submódulo
corresponde a um domínio de negócio específico e é mapeado 1:1 com os
itens do backlog do projeto.

Módulos planejados:
    - auth: Autenticação JWT, MFA (TOTP), gestão de sessões e tokens.
    - users: CRUD de usuários, perfis e controle de acesso RBAC.
    - documents: Upload, armazenamento, versionamento e ciclo de vida
      de documentos jurídicos (integração DataJud via state machine).
    - analysis: Análise de documentos assistida por IA (integração
      com API Anthropic/Claude), extração de informações e sumarização.
    - chat: Interface conversacional com o assistente jurídico,
      histórico de conversas e contexto por documento.
    - audit: Trilha de auditoria completa, logs de ações do usuário
      e conformidade com requisitos de compliance jurídico.

Arquitetura interna de cada módulo:
    modulo/
    ├── domain/          # Entidades e regras de negócio puras
    │   ├── entities.py
    │   └── exceptions.py
    ├── application/     # Use cases e ports (interfaces)
    │   ├── use_cases.py
    │   ├── ports.py
    │   └── dtos.py
    ├── infrastructure/  # Adapters (repositórios, clientes externos)
    │   ├── repositories.py
    │   └── adapters.py
    ├── presentation/    # Routers FastAPI e schemas Pydantic
    │   ├── router.py
    │   └── schemas.py
    └── __init__.py
"""

# Lista de módulos disponíveis para facilitar descoberta e registro dinâmico
AVAILABLE_MODULES: list[str] = [
    "auth",
    "users",
    "documents",
    "analysis",
    "chat",
    "audit",
]

__all__ = ["AVAILABLE_MODULES"]
