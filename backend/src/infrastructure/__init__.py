"""Pacote de infraestrutura — Camada de infraestrutura da Clean Architecture.

Este pacote contém as implementações concretas dos adaptadores (adapters)
definidos pelas interfaces (ports) na camada de aplicação. Inclui:

- **database**: Configuração do SQLAlchemy, sessões assíncronas e modelos ORM.
- **repositories**: Implementações concretas dos repositórios de persistência.
- **external**: Integrações com serviços externos (API Anthropic, DataJud, etc.).
- **security**: Implementações de autenticação JWT, hashing de senhas e MFA.
- **messaging**: Configuração do Celery e tarefas assíncronas.
- **storage**: Gerenciamento de upload e armazenamento de arquivos.
- **cache**: Configuração de cache (Redis) para sessões e dados temporários.
- **logging**: Configuração de logs estruturados com structlog.

Princípios seguidos:
    - Dependency Inversion: infraestrutura depende de abstrações da aplicação.
    - Cada submódulo implementa ports definidos na camada de aplicação.
    - Nenhuma regra de negócio reside nesta camada.
"""
