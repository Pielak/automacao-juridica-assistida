"""Pacote de domínio da aplicação Automação Jurídica Assistida.

Este pacote contém as entidades, objetos de valor, exceções e interfaces
(ports) que compõem o núcleo do domínio jurídico da aplicação.

Seguindo os princípios de Clean Architecture, esta camada:
- NÃO depende de nenhuma camada externa (infraestrutura, aplicação, apresentação).
- Define as regras de negócio fundamentais e invariantes do domínio.
- Expõe interfaces (ports) que serão implementadas pela camada de infraestrutura.
- Contém entidades ricas com comportamento de domínio, não apenas dados.

Módulos do domínio:
- entities: Entidades de domínio (User, Document, Analysis, ChatSession, AuditLog).
- value_objects: Objetos de valor imutáveis (CPF, OABNumber, DocumentStatus, etc.).
- exceptions: Exceções de domínio tipadas para erros de regra de negócio.
- ports: Interfaces abstratas (repositories, serviços externos) — Ports do padrão
  Ports & Adapters.
- events: Eventos de domínio para comunicação desacoplada entre módulos.
"""

__all__ = [
    "entities",
    "value_objects",
    "exceptions",
    "ports",
    "events",
]
