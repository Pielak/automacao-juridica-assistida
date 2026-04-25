"""Pacote de configuração da infraestrutura.

Este pacote centraliza todas as configurações da aplicação,
incluindo variáveis de ambiente, conexões com banco de dados,
parâmetros de segurança e integrações externas.

Módulos esperados:
    - settings: Configurações gerais da aplicação via Pydantic Settings
    - database: Configuração de conexão com PostgreSQL (SQLAlchemy + asyncpg)
    - security: Parâmetros de segurança (JWT, hashing, CORS)
    - celery_config: Configuração do Celery para tarefas assíncronas
    - logging_config: Configuração de logs estruturados (structlog)
"""
