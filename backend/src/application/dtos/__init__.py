"""Package de DTOs (Data Transfer Objects) da camada de aplicação.

Este pacote contém os objetos de transferência de dados utilizados para
comunicação entre as camadas da aplicação, seguindo os princípios de
Clean Architecture. Os DTOs garantem desacoplamento entre a camada de
apresentação (API) e a camada de domínio, além de fornecer validação
e serialização tipada via Pydantic v2.

Módulos planejados:
    - auth_dtos: DTOs para autenticação, login, registro e MFA.
    - user_dtos: DTOs para gestão de usuários e perfis RBAC.
    - document_dtos: DTOs para upload, listagem e ciclo de vida de documentos.
    - analysis_dtos: DTOs para análise jurídica assistida por IA.
    - chat_dtos: DTOs para interações de chat com o assistente jurídico.
    - audit_dtos: DTOs para trilha de auditoria e logs de conformidade.
    - common_dtos: DTOs compartilhados (paginação, ordenação, respostas padrão).
"""

# TODO: Importar e re-exportar DTOs dos submódulos conforme forem implementados.
# Exemplo esperado:
#   from backend.src.application.dtos.auth_dtos import (
#       LoginRequestDTO,
#       LoginResponseDTO,
#       RegisterRequestDTO,
#       TokenRefreshRequestDTO,
#       MfaSetupResponseDTO,
#       MfaVerifyRequestDTO,
#   )
#   from backend.src.application.dtos.common_dtos import (
#       PaginatedResponseDTO,
#       SortParamsDTO,
#       ErrorResponseDTO,
#   )

__all__: list[str] = []
