"""Pacote raiz do backend — Automação Jurídica Assistida.

Este pacote contém todos os módulos do sistema de automação jurídica,
organizado seguindo os princípios de Clean Architecture (Ports & Adapters)
em um monólito modular.

Módulos principais:
    - auth: Autenticação JWT, MFA e gestão de sessões.
    - users: CRUD de usuários e perfis RBAC.
    - documents: Gestão de documentos jurídicos e integração DataJud.
    - analysis: Análise de documentos com IA (Anthropic Claude).
    - chat: Interface conversacional assistida por IA.
    - audit: Trilha de auditoria e logs de conformidade.

Arquitetura:
    presentation (API FastAPI) → application (Use Cases) → domain (Entidades)
    ↕ infrastructure (Repositórios, Serviços Externos)
"""

__version__ = "0.1.0"
__app_name__ = "automacao-juridica-assistida"
