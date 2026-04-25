"""Pacote de casos de uso (use cases) da camada de aplicação.

Este pacote contém os casos de uso organizados por módulo funcional,
seguindo os princípios de Clean Architecture. Cada submódulo agrupa
os use cases de um domínio específico do sistema de Automação Jurídica Assistida.

Módulos planejados:
    - auth: Casos de uso de autenticação, autorização e MFA.
    - users: Casos de uso de gestão de usuários e perfis RBAC.
    - documents: Casos de uso de upload, validação e ciclo de vida de documentos.
    - analysis: Casos de uso de análise jurídica assistida por IA (Anthropic Claude).
    - chat: Casos de uso de interação conversacional com o assistente jurídico.
    - audit: Casos de uso de auditoria e rastreabilidade de ações.

Convenções:
    - Cada use case é uma classe com um único método público ``execute``.
    - Dependências externas são injetadas via construtor (ports/interfaces).
    - Use cases não dependem de frameworks ou detalhes de infraestrutura.
    - DTOs (Data Transfer Objects) são usados para entrada e saída.
"""

__all__: list[str] = []
