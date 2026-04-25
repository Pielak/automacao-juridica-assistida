# ADR-003: Estratégia de Anonimização Antes de Envio a LLMs (Presidio + NER)

## Status

**Aceito** — Data: 2024-01-15

## Contexto

O sistema **Automação Jurídica Assistida** processa documentos jurídicos que contêm dados pessoais sensíveis protegidos pela LGPD (Lei Geral de Proteção de Dados — Lei nº 13.709/2018). Esses documentos são enviados para análise por LLMs externas (Claude/Anthropic) para geração de resumos, análises e sugestões jurídicas.

O envio de dados pessoais identificáveis (PII — Personally Identifiable Information) para APIs externas de LLM apresenta riscos significativos:

1. **Risco regulatório**: Violação dos princípios de necessidade e adequação da LGPD (Art. 6º, III e IV).
2. **Risco de vazamento**: Dados pessoais podem ser retidos, logados ou utilizados para treinamento por provedores de LLM.
3. **Risco reputacional**: Exposição de dados de clientes de escritórios jurídicos compromete a relação de confiança.
4. **Risco ético-profissional**: O sigilo profissional do advogado (Art. 7º, II do Estatuto da OAB) exige proteção rigorosa das informações dos clientes.

### Tipos de Dados Sensíveis em Documentos Jurídicos

| Categoria | Exemplos | Criticidade |
|-----------|----------|-------------|
| Identificação pessoal | CPF, RG, CNH, passaporte | Crítica |
| Nome completo | Partes, advogados, juízes, testemunhas | Alta |
| Endereço | Residencial, comercial | Alta |
| Contato | Telefone, e-mail | Alta |
| Financeiro | Contas bancárias, valores de causa | Alta |
| Judicial | Número de processo, vara, comarca | Média |
| Saúde | CID, laudos médicos (em ações trabalhistas/previdenciárias) | Crítica |
| Biométrico | Dados biométricos mencionados em peças | Crítica |

## Decisão

Adotaremos uma **estratégia de anonimização em camadas** utilizando **Microsoft Presidio** como motor principal de detecção e anonimização de PII, complementado por **reconhecedores NER (Named Entity Recognition) customizados** para o domínio jurídico brasileiro.

### Arquitetura da Solução

```
┌─────────────────────────────────────────────────────────────────┐
│                    FLUXO DE ANONIMIZAÇÃO                        │
│                                                                 │
│  Documento   ┌──────────────┐  Texto      ┌──────────────────┐  │
│  Original ──►│  Extração de │─────────────►│  Pipeline de     │  │
│              │  Texto       │              │  Anonimização    │  │
│              └──────────────┘              │                  │  │
│                                            │  1. Presidio     │  │
│                                            │     Analyzer     │  │
│                                            │  2. NER Jurídico │  │
│                                            │     Customizado  │  │
│                                            │  3. Regex BR     │  │
│                                            │     Patterns     │  │
│                                            │  4. Presidio     │  │
│                                            │     Anonymizer   │  │
│                                            └────────┬─────────┘  │
│                                                     │            │
│                                            ┌────────▼─────────┐  │
│                                            │  Texto           │  │
│                                            │  Anonimizado     │  │
│                                            └────────┬─────────┘  │
│                                                     │            │
│                              ┌───────────┐ ┌────────▼─────────┐  │
│                              │ Mapeamento│ │  Envio para LLM  │  │
│                              │ Reversível│ │  (Anthropic API) │  │
│                              │ (Vault)   │ └────────┬─────────┘  │
│                              └─────┬─────┘          │            │
│                                    │       ┌────────▼─────────┐  │
│                                    │       │  Resposta LLM    │  │
│                                    │       │  (Anonimizada)   │  │
│                                    │       └────────┬─────────┘  │
│                                    │                │            │
│                              ┌─────▼────────────────▼─────────┐  │
│                              │  Desanonimização               │  │
│                              │  (Substituição reversa)        │  │
│                              └────────────────┬───────────────┘  │
│                                               │                  │
│                                      ┌────────▼─────────┐       │
│                                      │  Resposta Final   │       │
│                                      │  (Dados Reais)    │       │
│                                      └──────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

### Componentes Principais

#### 1. Presidio Analyzer (Detecção de PII)

O **Presidio Analyzer** será configurado com reconhecedores para o contexto brasileiro:

- **Reconhecedores nativos** (adaptados para pt-BR):
  - `PERSON` — nomes de pessoas
  - `EMAIL_ADDRESS` — endereços de e-mail
  - `PHONE_NUMBER` — números de telefone
  - `LOCATION` — endereços e localidades
  - `DATE_TIME` — datas

- **Reconhecedores customizados** (implementação própria):
  - `BR_CPF` — CPF com validação de dígitos verificadores
  - `BR_CNPJ` — CNPJ com validação
  - `BR_RG` — Registro Geral
  - `BR_OAB` — Número de inscrição na OAB
  - `BR_PROCESSO` — Número unificado de processo judicial (padrão CNJ: NNNNNNN-DD.AAAA.J.TR.OOOO)
  - `BR_CEP` — Código de Endereçamento Postal
  - `BR_CONTA_BANCARIA` — Dados bancários (agência/conta)
  - `BR_TELEFONE` — Telefones no formato brasileiro
  - `BR_PLACA_VEICULO` — Placas de veículos (Mercosul e formato antigo)

#### 2. NER Jurídico Customizado

Modelo de NER treinado/ajustado para reconhecer entidades específicas do domínio jurídico:

- **Partes processuais**: autor, réu, reclamante, reclamado, impetrante, impetrado
- **Operadores do direito**: juiz, desembargador, promotor, defensor
- **Entidades jurídicas**: varas, tribunais, comarcas, seções judiciárias
- **Referências normativas**: artigos de lei, súmulas, jurisprudência

Implementação sugerida: **spaCy** com modelo `pt_core_news_lg` + componente NER customizado treinado com corpus jurídico anotado.

#### 3. Presidio Anonymizer (Transformação)

Estratégias de anonimização por tipo de entidade:

| Entidade | Estratégia | Exemplo Original | Exemplo Anonimizado |
|----------|-----------|------------------|---------------------|
| `PERSON` | Substituição por placeholder | "João da Silva" | `<PESSOA_001>` |
| `BR_CPF` | Substituição por placeholder | "123.456.789-09" | `<CPF_001>` |
| `BR_CNPJ` | Substituição por placeholder | "12.345.678/0001-95" | `<CNPJ_001>` |
| `BR_PROCESSO` | Substituição por placeholder | "0001234-56.2023.8.26.0100" | `<PROCESSO_001>` |
| `BR_OAB` | Substituição por placeholder | "OAB/SP 123.456" | `<OAB_001>` |
| `EMAIL_ADDRESS` | Substituição por placeholder | "joao@email.com" | `<EMAIL_001>` |
| `PHONE_NUMBER` | Substituição por placeholder | "(11) 99999-1234" | `<TELEFONE_001>` |
| `LOCATION` | Substituição por placeholder | "Rua das Flores, 123" | `<ENDERECO_001>` |
| `BR_CONTA_BANCARIA` | Substituição por placeholder | "Ag 1234 CC 56789-0" | `<CONTA_001>` |
| `DATE_TIME` | Manter (geralmente relevante para análise) | "15/03/2023" | "15/03/2023" |

> **Nota**: Utilizamos **placeholders indexados** (e.g., `<PESSOA_001>`, `<PESSOA_002>`) em vez de mascaramento destrutivo para:
> - Preservar a coerência referencial no texto (a LLM entende que `<PESSOA_001>` é sempre a mesma pessoa)
> - Permitir desanonimização precisa na resposta
> - Manter a estrutura lógica do documento para análise pela LLM

#### 4. Mapeamento Reversível (Anonymization Vault)

Um mapeamento bidirecional será mantido **exclusivamente em memória e/ou banco de dados local** (nunca enviado à LLM):

```python
# Estrutura conceitual do mapeamento
anonymization_map = {
    "session_id": "uuid-da-sessao",
    "document_id": "uuid-do-documento",
    "created_at": "2024-01-15T10:30:00Z",
    "expires_at": "2024-01-15T11:30:00Z",  # TTL de 1 hora
    "mappings": {
        "<PESSOA_001>": "João da Silva",
        "<PESSOA_002>": "Maria Oliveira",
        "<CPF_001>": "123.456.789-09",
        "<PROCESSO_001>": "0001234-56.2023.8.26.0100",
    }
}
```

**Políticas de segurança do vault**:
- TTL (Time-To-Live) de **1 hora** — mapeamentos expiram automaticamente
- Armazenamento **criptografado** em banco de dados (AES-256)
- Acesso restrito ao módulo de desanonimização via interface (port)
- Log de auditoria para cada operação de desanonimização
- Sem persistência em disco em formato legível

### Pipeline de Processamento

```
1. ENTRADA
   └─► Texto extraído do documento jurídico

2. PRÉ-PROCESSAMENTO
   ├─► Normalização de encoding (UTF-8)
   ├─► Normalização de espaços e quebras de linha
   └─► Detecção de idioma (validar pt-BR)

3. DETECÇÃO (Presidio Analyzer)
   ├─► Reconhecedores nativos (PERSON, EMAIL, PHONE, LOCATION)
   ├─► Reconhecedores customizados BR (CPF, CNPJ, OAB, PROCESSO)
   ├─► NER jurídico customizado (spaCy)
   └─► Consolidação e resolução de conflitos (maior score vence)

4. VALIDAÇÃO
   ├─► Verificação de cobertura mínima (threshold de confiança ≥ 0.7)
   ├─► Revisão de falsos positivos conhecidos (e.g., nomes de leis)
   └─► Log de entidades detectadas (sem valores) para auditoria

5. ANONIMIZAÇÃO (Presidio Anonymizer)
   ├─► Aplicação de operadores por tipo de entidade
   ├─► Geração de mapeamento reversível
   └─► Armazenamento seguro do mapeamento no vault

6. SAÍDA
   └─► Texto anonimizado pronto para envio à LLM

7. PÓS-LLM
   ├─► Recepção da resposta da LLM
   ├─► Desanonimização via mapeamento do vault
   ├─► Invalidação do mapeamento (TTL ou explícita)
   └─► Entrega da resposta com dados reais ao usuário
```

### Integração com a Arquitetura Clean Architecture

A anonimização será implementada como um **módulo isolado** seguindo os princípios de Clean Architecture:

```
src/
└── modules/
    └── anonymization/
        ├── domain/
        │   ├── entities/
        │   │   ├── anonymization_result.py    # Entidade de resultado
        │   │   ├── entity_recognition.py       # Entidade reconhecida
        │   │   └── anonymization_mapping.py    # Mapeamento reversível
        │   ├── ports/
        │   │   ├── anonymizer_port.py          # Interface do anonimizador
        │   │   ├── recognizer_port.py          # Interface do reconhecedor
        │   │   └── vault_port.py               # Interface do vault
        │   └── value_objects/
        │       ├── entity_type.py              # Tipos de entidade (enum)
        │       └── confidence_score.py         # Score de confiança
        ├── application/
        │   ├── use_cases/
        │   │   ├── anonymize_text.py           # UC: anonimizar texto
        │   │   ├── deanonymize_text.py         # UC: desanonimizar texto
        │   │   └── analyze_pii_coverage.py     # UC: relatório de PII
        │   └── dtos/
        │       ├── anonymize_request.py
        │       └── anonymize_response.py
        └── infrastructure/
            ├── presidio_analyzer_adapter.py    # Adapter Presidio Analyzer
            ├── presidio_anonymizer_adapter.py  # Adapter Presidio Anonymizer
            ├── spacy_ner_adapter.py            # Adapter spaCy NER
            ├── recognizers/
            │   ├── br_cpf_recognizer.py        # Reconhecedor de CPF
            │   ├── br_cnpj_recognizer.py       # Reconhecedor de CNPJ
            │   ├── br_oab_recognizer.py        # Reconhecedor de OAB
            │   ├── br_processo_recognizer.py   # Reconhecedor de nº processo
            │   └── br_telefone_recognizer.py   # Reconhecedor de telefone BR
            └── vault/
                └── encrypted_vault_adapter.py  # Vault criptografado
```

### Dependências Adicionais

Bibliotecas a serem adicionadas ao `requirements.txt`:

```
presidio-analyzer>=2.2.0
presidio-anonymizer>=2.2.0
spacy>=3.7.0
# Modelo spaCy para português:
# python -m spacy download pt_core_news_lg
cryptography>=41.0.0  # Para criptografia do vault (AES-256)
```

### Configuração

Parâmetros configuráveis via variáveis de ambiente:

| Variável | Descrição | Valor Padrão |
|----------|-----------|-------------|
| `ANONYMIZATION_ENABLED` | Habilitar/desabilitar anonimização | `true` |
| `ANONYMIZATION_CONFIDENCE_THRESHOLD` | Score mínimo de confiança para detecção | `0.7` |
| `ANONYMIZATION_VAULT_TTL_SECONDS` | TTL do mapeamento no vault | `3600` |
| `ANONYMIZATION_VAULT_ENCRYPTION_KEY` | Chave de criptografia do vault (AES-256) | — (obrigatório) |
| `ANONYMIZATION_PRESERVE_DATES` | Manter datas sem anonimizar | `true` |
| `ANONYMIZATION_SPACY_MODEL` | Modelo spaCy para NER | `pt_core_news_lg` |
| `ANONYMIZATION_LOG_ENTITIES` | Logar tipos de entidades detectadas (sem valores) | `true` |
| `ANONYMIZATION_MAX_TEXT_LENGTH` | Tamanho máximo de texto para processamento (chars) | `500000` |

## Consequências

### Positivas

1. **Conformidade LGPD**: Dados pessoais não são transmitidos para APIs externas, atendendo aos princípios de necessidade e minimização.
2. **Proteção do sigilo profissional**: Informações de clientes permanecem dentro do perímetro controlado da aplicação.
3. **Qualidade da análise preservada**: O uso de placeholders indexados mantém a coerência referencial, permitindo que a LLM produza análises estruturalmente corretas.
4. **Reversibilidade**: A desanonimização permite apresentar resultados com dados reais ao usuário final.
5. **Auditabilidade**: Todas as operações de anonimização/desanonimização são logadas para trilha de auditoria.
6. **Extensibilidade**: Novos reconhecedores podem ser adicionados sem alterar o pipeline existente (Open/Closed Principle).
7. **Testabilidade**: Interfaces (ports) permitem mock completo em testes unitários.

### Negativas

1. **Latência adicional**: O pipeline de anonimização adiciona ~200-500ms por documento (aceitável para o caso de uso).
2. **Falsos positivos/negativos**: Nenhum sistema de NER é 100% preciso. Nomes próprios em contextos ambíguos podem ser perdidos ou detectados incorretamente.
3. **Complexidade operacional**: Necessidade de manter modelo spaCy atualizado e reconhecedores customizados calibrados.
4. **Custo de memória**: O vault de mapeamento consome memória proporcional ao volume de sessões ativas.
5. **Dependência de bibliotecas**: Presidio e spaCy são dependências significativas que aumentam o tamanho do deployment.

### Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|----------|
| Falso negativo (PII não detectada) | Média | Alto | Camadas múltiplas de detecção + revisão periódica de amostras + threshold conservador |
| Falso positivo (texto legítimo removido) | Média | Baixo | Whitelist de termos jurídicos comuns + ajuste fino de scores |
| Vazamento do vault de mapeamento | Baixa | Crítico | Criptografia AES-256 + TTL curto + sem persistência em texto claro |
| Degradação de performance com documentos grandes | Baixa | Médio | Chunking de textos longos + processamento assíncrono via Celery |
| Modelo spaCy desatualizado | Baixa | Médio | Pipeline de CI/CD com atualização periódica + testes de regressão |

## Alternativas Consideradas

### 1. Não anonimizar (enviar dados reais à LLM)

**Rejeitada** — Viola LGPD, sigilo profissional e expõe dados sensíveis a terceiros. Inaceitável para o domínio jurídico.

### 2. Anonimização destrutiva (mascaramento irreversível)

**Rejeitada** — Impede a apresentação de resultados úteis ao usuário. A LLM responderia com placeholders que o usuário não conseguiria interpretar sem contexto.

### 3. Usar apenas regex para detecção de PII

**Rejeitada** — Regex é eficaz para padrões estruturados (CPF, CNPJ, telefone) mas falha completamente para nomes de pessoas, endereços e entidades contextuais. A combinação Presidio + NER oferece cobertura muito superior.

### 4. LLM local (self-hosted) sem necessidade de anonimização

**Adiada** — Modelos locais de qualidade comparável ao Claude exigem infraestrutura GPU significativa (custo elevado). Pode ser reavaliada no futuro conforme evolução de modelos open-source. Não elimina completamente a necessidade de anonimização (princípio de defesa em profundidade).

### 5. Usar apenas o Presidio sem NER customizado

**Rejeitada** — O Presidio com reconhecedores padrão não cobre adequadamente entidades do domínio jurídico brasileiro (números de processo CNJ, inscrições OAB, terminologia processual). A camada NER customizada é essencial para cobertura adequada.

## Métricas de Sucesso

- **Taxa de detecção de PII** ≥ 95% (medida em corpus de teste anotado manualmente)
- **Taxa de falsos positivos** ≤ 10% (termos legítimos incorretamente anonimizados)
- **Latência do pipeline** ≤ 500ms para documentos de até 50.000 caracteres
- **Zero vazamentos de PII** em logs, métricas ou chamadas à API externa
- **100% de cobertura** para padrões estruturados (CPF, CNPJ, número de processo)

## Referências

- [Microsoft Presidio — Documentação](https://microsoft.github.io/presidio/)
- [spaCy — Modelos para Português](https://spacy.io/models/pt)
- [LGPD — Lei nº 13.709/2018](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm)
- [Resolução CNJ nº 65/2008 — Numeração Unificada de Processos](https://atos.cnj.jus.br/atos/detalhar/119)
- [OWASP — Data Protection Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Data_Protection_Cheat_Sheet.html)
- ADR-001: Escolha de LLM (Claude/Anthropic) — `docs/architecture/adr-001-llm-choice.md`
- ADR-002: Estratégia de busca vetorial — `docs/architecture/adr-002-vector-search.md`

## Notas de Implementação

<!-- TODO: Definir corpus de teste anotado para validação das taxas de detecção -->
<!-- TODO: Avaliar necessidade de treinamento customizado do modelo spaCy com dados jurídicos anotados -->
<!-- TODO: Definir política de rotação da chave de criptografia do vault (ANONYMIZATION_VAULT_ENCRYPTION_KEY) -->
<!-- TODO: Integrar com módulo de auditoria (audit module) para registro de operações de anonimização -->
<!-- TODO: Avaliar FAISS/Milvus (pendente ADR-002) para impacto na anonimização de embeddings -->

## Participantes

- **Decisor**: Arquiteto de Software (P5)
- **Consultados**: Especialista em Segurança (P7), Especialista em Compliance (P2)
- **Informados**: Equipe de Desenvolvimento, Product Owner

## Histórico de Revisões

| Data | Versão | Descrição |
|------|--------|-----------|
| 2024-01-15 | 1.0 | Versão inicial do ADR |
