"""Camada de aplicação — Use Cases e serviços de orquestração.

Esta camada implementa os casos de uso do sistema de Automação Jurídica Assistida,
orquestrando regras de negócio e coordenando interações entre as camadas de domínio
e infraestrutura seguindo os princípios de Clean Architecture (Ports & Adapters).

Responsabilidades:
    - Definição e execução de use cases por módulo funcional
    - Orquestração de regras de negócio entre entidades de domínio
    - Definição de interfaces (ports) para dependências externas
    - Transformação de dados via DTOs para comunicação entre camadas
    - Coordenação de fluxos transacionais e assíncronos

Módulos funcionais:
    - auth: Autenticação JWT, MFA, gestão de sessões
    - users: CRUD de usuários e perfis RBAC
    - documents: Upload, validação e ciclo de vida de documentos
    - analysis: Análise jurídica assistida por IA (integração Anthropic Claude)
    - chat: Interface conversacional para consultas jurídicas
    - audit: Trilha de auditoria e logs de conformidade

Princípios arquiteturais:
    - Inversão de dependência: use cases dependem de abstrações (ports), não de
      implementações concretas (adapters)
    - Isolamento de módulos: cada módulo expõe interfaces bem definidas
    - Testabilidade: dependências injetáveis facilitam testes unitários e de integração
    - Separação de responsabilidades: lógica de negócio isolada de detalhes de
      infraestrutura (banco de dados, APIs externas, filas)
"""

__all__: list[str] = []
