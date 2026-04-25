"""Pacote de entidades do domínio.

Este módulo exporta todas as entidades de domínio da aplicação
de Automação Jurídica Assistida. As entidades representam os
objetos centrais do negócio jurídico, independentes de frameworks
ou infraestrutura externa (princípio da Clean Architecture).

Entidades disponíveis:
- User: Usuário do sistema com perfil RBAC.
- Document: Documento jurídico com ciclo de vida gerenciado.
- Analysis: Análise de documento gerada por IA (Claude).
- ChatSession / ChatMessage: Sessão e mensagens do chat assistido.
- AuditLog: Registro de auditoria para conformidade e rastreabilidade.
"""

from domain.entities.user import User
from domain.entities.document import Document
from domain.entities.analysis import Analysis
from domain.entities.chat import ChatMessage, ChatSession
from domain.entities.audit_log import AuditLog

__all__ = [
    "User",
    "Document",
    "Analysis",
    "ChatSession",
    "ChatMessage",
    "AuditLog",
]
