"""Pacote de infraestrutura de segurança.

Este pacote contém os módulos responsáveis pela segurança da aplicação,
incluindo autenticação JWT, hashing de senhas, MFA (TOTP), rate limiting
e utilitários de autorização RBAC.

Módulos planejados:
- jwt_handler: Geração e validação de tokens JWT (RS256)
- password_hasher: Hashing seguro de senhas com bcrypt
- mfa: Autenticação multifator via TOTP (Google Authenticator/Authy)
- rate_limiter: Controle de taxa de requisições
- rbac: Controle de acesso baseado em papéis (Role-Based Access Control)
"""

# TODO: Importar e re-exportar componentes públicos conforme módulos forem implementados.
# Exemplo esperado após implementação:
#
# from backend.src.infrastructure.security.jwt_handler import JWTHandler
# from backend.src.infrastructure.security.password_hasher import PasswordHasher
# from backend.src.infrastructure.security.mfa import TOTPManager
# from backend.src.infrastructure.security.rate_limiter import RateLimiterMiddleware
# from backend.src.infrastructure.security.rbac import RBACGuard
#
# __all__ = [
#     "JWTHandler",
#     "PasswordHasher",
#     "TOTPManager",
#     "RateLimiterMiddleware",
#     "RBACGuard",
# ]

__all__: list[str] = []
