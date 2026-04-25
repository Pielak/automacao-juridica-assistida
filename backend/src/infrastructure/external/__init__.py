"""Pacote de integrações externas.

Este pacote contém os adaptadores (adapters) para serviços externos
utilizados pela aplicação de Automação Jurídica Assistida, seguindo
o padrão Ports & Adapters da Clean Architecture.

Integrações incluídas:
- Anthropic (Claude) — análise de documentos jurídicos e chat assistido
- DataJud — consulta de processos e documentos judiciais
- Serviços de armazenamento de arquivos
- Serviços de busca vetorial (FAISS/Milvus)

Cada integração implementa uma interface (port) definida na camada
de aplicação, garantindo desacoplamento e testabilidade.
"""

__all__: list[str] = []
