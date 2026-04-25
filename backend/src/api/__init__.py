"""Pacote da camada de API (apresentação REST).

Este pacote contém os routers, middlewares e dependências
da camada de apresentação da aplicação Automação Jurídica Assistida.

A camada de API é responsável por:
- Definir os endpoints REST organizados por domínio (routers modulares)
- Aplicar middlewares de autenticação, logging e rate limiting
- Validar entrada de dados via schemas Pydantic v2
- Gerar documentação OpenAPI automática via FastAPI
"""
