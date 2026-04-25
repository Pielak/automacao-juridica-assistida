"""Seed de dados de referência: tipos de ação cível, tribunais e status de processo.

Revision ID: 002
Revises: 001
Create Date: 2024-01-15

Esta migração popula as tabelas de referência com dados essenciais para o
funcionamento do sistema de automação jurídica. Inclui:
- Tipos de ação cível mais comuns no judiciário brasileiro
- Tribunais estaduais e superiores
- Status possíveis para o ciclo de vida de um processo
"""

from typing import Union

from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone


# Identificadores de revisão do Alembic
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


# ---------------------------------------------------------------------------
# Dados de referência
# ---------------------------------------------------------------------------

ACTION_TYPES = [
    {"code": "AC_INDENIZATORIA", "name": "Ação de Indenização", "category": "civel", "description": "Ação para reparação de danos materiais e/ou morais"},
    {"code": "AC_COBRANCA", "name": "Ação de Cobrança", "category": "civel", "description": "Ação para cobrança de dívida líquida e certa"},
    {"code": "AC_OBRIGACAO_FAZER", "name": "Ação de Obrigação de Fazer", "category": "civel", "description": "Ação para compelir cumprimento de obrigação de fazer ou não fazer"},
    {"code": "AC_DESPEJO", "name": "Ação de Despejo", "category": "civel", "description": "Ação para retomada de imóvel locado"},
    {"code": "AC_REVISIONAL", "name": "Ação Revisional de Contrato", "category": "civel", "description": "Ação para revisão de cláusulas contratuais abusivas"},
    {"code": "AC_CONSIGNACAO", "name": "Ação de Consignação em Pagamento", "category": "civel", "description": "Ação para depósito judicial de valor devido"},
    {"code": "AC_REINTEGRACAO", "name": "Ação de Reintegração de Posse", "category": "civel", "description": "Ação para recuperação da posse de bem esbulhado"},
    {"code": "AC_MANUTENCAO_POSSE", "name": "Ação de Manutenção de Posse", "category": "civel", "description": "Ação para proteção da posse contra turbação"},
    {"code": "AC_USUCAPIAO", "name": "Ação de Usucapião", "category": "civel", "description": "Ação para aquisição de propriedade por posse prolongada"},
    {"code": "AC_DISSOLUCAO_SOCIEDADE", "name": "Ação de Dissolução de Sociedade", "category": "civel", "description": "Ação para dissolução parcial ou total de sociedade empresária"},
    {"code": "AC_DECLARATORIA", "name": "Ação Declaratória", "category": "civel", "description": "Ação para declaração de existência ou inexistência de relação jurídica"},
    {"code": "AC_ANULATORIA", "name": "Ação Anulatória", "category": "civel", "description": "Ação para anulação de ato jurídico ou negócio jurídico"},
    {"code": "AC_MONITORIA", "name": "Ação Monitória", "category": "civel", "description": "Ação para constituição de título executivo com base em prova escrita"},
    {"code": "EXEC_TITULO_EXTRAJUDICIAL", "name": "Execução de Título Extrajudicial", "category": "civel", "description": "Execução fundada em título executivo extrajudicial"},
    {"code": "EXEC_TITULO_JUDICIAL", "name": "Cumprimento de Sentença", "category": "civel", "description": "Execução fundada em título executivo judicial"},
    {"code": "MS_INDIVIDUAL", "name": "Mandado de Segurança Individual", "category": "civel", "description": "Remédio constitucional contra ato de autoridade pública"},
    {"code": "HABEAS_DATA", "name": "Habeas Data", "category": "civel", "description": "Ação para acesso ou retificação de dados pessoais em registros públicos"},
    {"code": "AC_CONSUMIDOR", "name": "Ação de Direito do Consumidor", "category": "civel", "description": "Ação fundada no Código de Defesa do Consumidor"},
    {"code": "TUTELA_ANTECIPADA", "name": "Tutela Antecipada Antecedente", "category": "civel", "description": "Pedido de tutela provisória de urgência antecedente"},
    {"code": "TUTELA_CAUTELAR", "name": "Tutela Cautelar Antecedente", "category": "civel", "description": "Pedido de tutela provisória cautelar antecedente"},
]

COURTS = [
    # Tribunais Superiores
    {"code": "STF", "name": "Supremo Tribunal Federal", "level": "superior", "state": None, "description": "Corte constitucional do Brasil"},
    {"code": "STJ", "name": "Superior Tribunal de Justiça", "level": "superior", "state": None, "description": "Tribunal responsável pela uniformização da interpretação da lei federal"},
    {"code": "TST", "name": "Tribunal Superior do Trabalho", "level": "superior", "state": None, "description": "Tribunal superior da Justiça do Trabalho"},
    {"code": "TSE", "name": "Tribunal Superior Eleitoral", "level": "superior", "state": None, "description": "Tribunal superior da Justiça Eleitoral"},
    {"code": "STM", "name": "Superior Tribunal Militar", "level": "superior", "state": None, "description": "Tribunal superior da Justiça Militar"},
    # Tribunais Estaduais
    {"code": "TJAC", "name": "Tribunal de Justiça do Acre", "level": "estadual", "state": "AC", "description": "Tribunal de Justiça do Estado do Acre"},
    {"code": "TJAL", "name": "Tribunal de Justiça de Alagoas", "level": "estadual", "state": "AL", "description": "Tribunal de Justiça do Estado de Alagoas"},
    {"code": "TJAP", "name": "Tribunal de Justiça do Amapá", "level": "estadual", "state": "AP", "description": "Tribunal de Justiça do Estado do Amapá"},
    {"code": "TJAM", "name": "Tribunal de Justiça do Amazonas", "level": "estadual", "state": "AM", "description": "Tribunal de Justiça do Estado do Amazonas"},
    {"code": "TJBA", "name": "Tribunal de Justiça da Bahia", "level": "estadual", "state": "BA", "description": "Tribunal de Justiça do Estado da Bahia"},
    {"code": "TJCE", "name": "Tribunal de Justiça do Ceará", "level": "estadual", "state": "CE", "description": "Tribunal de Justiça do Estado do Ceará"},
    {"code": "TJDFT", "name": "Tribunal de Justiça do Distrito Federal e Territórios", "level": "estadual", "state": "DF", "description": "Tribunal de Justiça do Distrito Federal e dos Territórios"},
    {"code": "TJES", "name": "Tribunal de Justiça do Espírito Santo", "level": "estadual", "state": "ES", "description": "Tribunal de Justiça do Estado do Espírito Santo"},
    {"code": "TJGO", "name": "Tribunal de Justiça de Goiás", "level": "estadual", "state": "GO", "description": "Tribunal de Justiça do Estado de Goiás"},
    {"code": "TJMA", "name": "Tribunal de Justiça do Maranhão", "level": "estadual", "state": "MA", "description": "Tribunal de Justiça do Estado do Maranhão"},
    {"code": "TJMT", "name": "Tribunal de Justiça de Mato Grosso", "level": "estadual", "state": "MT", "description": "Tribunal de Justiça do Estado de Mato Grosso"},
    {"code": "TJMS", "name": "Tribunal de Justiça de Mato Grosso do Sul", "level": "estadual", "state": "MS", "description": "Tribunal de Justiça do Estado de Mato Grosso do Sul"},
    {"code": "TJMG", "name": "Tribunal de Justiça de Minas Gerais", "level": "estadual", "state": "MG", "description": "Tribunal de Justiça do Estado de Minas Gerais"},
    {"code": "TJPA", "name": "Tribunal de Justiça do Pará", "level": "estadual", "state": "PA", "description": "Tribunal de Justiça do Estado do Pará"},
    {"code": "TJPB", "name": "Tribunal de Justiça da Paraíba", "level": "estadual", "state": "PB", "description": "Tribunal de Justiça do Estado da Paraíba"},
    {"code": "TJPR", "name": "Tribunal de Justiça do Paraná", "level": "estadual", "state": "PR", "description": "Tribunal de Justiça do Estado do Paraná"},
    {"code": "TJPE", "name": "Tribunal de Justiça de Pernambuco", "level": "estadual", "state": "PE", "description": "Tribunal de Justiça do Estado de Pernambuco"},
    {"code": "TJPI", "name": "Tribunal de Justiça do Piauí", "level": "estadual", "state": "PI", "description": "Tribunal de Justiça do Estado do Piauí"},
    {"code": "TJRJ", "name": "Tribunal de Justiça do Rio de Janeiro", "level": "estadual", "state": "RJ", "description": "Tribunal de Justiça do Estado do Rio de Janeiro"},
    {"code": "TJRN", "name": "Tribunal de Justiça do Rio Grande do Norte", "level": "estadual", "state": "RN", "description": "Tribunal de Justiça do Estado do Rio Grande do Norte"},
    {"code": "TJRS", "name": "Tribunal de Justiça do Rio Grande do Sul", "level": "estadual", "state": "RS", "description": "Tribunal de Justiça do Estado do Rio Grande do Sul"},
    {"code": "TJRO", "name": "Tribunal de Justiça de Rondônia", "level": "estadual", "state": "RO", "description": "Tribunal de Justiça do Estado de Rondônia"},
    {"code": "TJRR", "name": "Tribunal de Justiça de Roraima", "level": "estadual", "state": "RR", "description": "Tribunal de Justiça do Estado de Roraima"},
    {"code": "TJSC", "name": "Tribunal de Justiça de Santa Catarina", "level": "estadual", "state": "SC", "description": "Tribunal de Justiça do Estado de Santa Catarina"},
    {"code": "TJSP", "name": "Tribunal de Justiça de São Paulo", "level": "estadual", "state": "SP", "description": "Tribunal de Justiça do Estado de São Paulo"},
    {"code": "TJSE", "name": "Tribunal de Justiça de Sergipe", "level": "estadual", "state": "SE", "description": "Tribunal de Justiça do Estado de Sergipe"},
    {"code": "TJTO", "name": "Tribunal de Justiça do Tocantins", "level": "estadual", "state": "TO", "description": "Tribunal de Justiça do Estado do Tocantins"},
    # Tribunais Regionais Federais
    {"code": "TRF1", "name": "Tribunal Regional Federal da 1ª Região", "level": "federal", "state": None, "description": "TRF da 1ª Região — sede em Brasília/DF"},
    {"code": "TRF2", "name": "Tribunal Regional Federal da 2ª Região", "level": "federal", "state": None, "description": "TRF da 2ª Região — sede no Rio de Janeiro/RJ"},
    {"code": "TRF3", "name": "Tribunal Regional Federal da 3ª Região", "level": "federal", "state": None, "description": "TRF da 3ª Região — sede em São Paulo/SP"},
    {"code": "TRF4", "name": "Tribunal Regional Federal da 4ª Região", "level": "federal", "state": None, "description": "TRF da 4ª Região — sede em Porto Alegre/RS"},
    {"code": "TRF5", "name": "Tribunal Regional Federal da 5ª Região", "level": "federal", "state": None, "description": "TRF da 5ª Região — sede em Recife/PE"},
    {"code": "TRF6", "name": "Tribunal Regional Federal da 6ª Região", "level": "federal", "state": None, "description": "TRF da 6ª Região — sede em Belo Horizonte/MG"},
]

PROCESS_STATUSES = [
    {"code": "DISTRIBUIDO", "name": "Distribuído", "description": "Processo distribuído ao juízo competente", "sort_order": 1, "is_active": True, "is_terminal": False},
    {"code": "EM_ANDAMENTO", "name": "Em Andamento", "description": "Processo em tramitação regular", "sort_order": 2, "is_active": True, "is_terminal": False},
    {"code": "AGUARDANDO_CITACAO", "name": "Aguardando Citação", "description": "Aguardando citação do réu", "sort_order": 3, "is_active": True, "is_terminal": False},
    {"code": "CITADO", "name": "Citado", "description": "Réu citado, aguardando contestação", "sort_order": 4, "is_active": True, "is_terminal": False},
    {"code": "CONTESTADO", "name": "Contestado", "description": "Contestação apresentada pelo réu", "sort_order": 5, "is_active": True, "is_terminal": False},
    {"code": "EM_INSTRUCAO", "name": "Em Instrução", "description": "Fase de instrução processual (produção de provas)", "sort_order": 6, "is_active": True, "is_terminal": False},
    {"code": "AGUARDANDO_PERICIA", "name": "Aguardando Perícia", "description": "Aguardando realização ou laudo de perícia", "sort_order": 7, "is_active": True, "is_terminal": False},
    {"code": "AGUARDANDO_AUDIENCIA", "name": "Aguardando Audiência", "description": "Audiência designada, aguardando realização", "sort_order": 8, "is_active": True, "is_terminal": False},
    {"code": "CONCLUSO_PARA_SENTENCA", "name": "Concluso para Sentença", "description": "Autos conclusos ao juiz para prolação de sentença", "sort_order": 9, "is_active": True, "is_terminal": False},
    {"code": "SENTENCIADO", "name": "Sentenciado", "description": "Sentença prolatada", "sort_order": 10, "is_active": True, "is_terminal": False},
    {"code": "EM_RECURSO", "name": "Em Recurso", "description": "Recurso interposto, aguardando julgamento", "sort_order": 11, "is_active": True, "is_terminal": False},
    {"code": "ACORDAO_PROFERIDO", "name": "Acórdão Proferido", "description": "Acórdão proferido pelo tribunal", "sort_order": 12, "is_active": True, "is_terminal": False},
    {"code": "TRANSITADO_EM_JULGADO", "name": "Transitado em Julgado", "description": "Decisão transitada em julgado, sem possibilidade de recurso", "sort_order": 13, "is_active": True, "is_terminal": False},
    {"code": "EM_CUMPRIMENTO", "name": "Em Cumprimento de Sentença", "description": "Fase de cumprimento de sentença", "sort_order": 14, "is_active": True, "is_terminal": False},
    {"code": "EM_EXECUCAO", "name": "Em Execução", "description": "Processo em fase de execução", "sort_order": 15, "is_active": True, "is_terminal": False},
    {"code": "SUSPENSO", "name": "Suspenso", "description": "Processo suspenso por determinação judicial", "sort_order": 16, "is_active": False, "is_terminal": False},
    {"code": "ACORDO_HOMOLOGADO", "name": "Acordo Homologado", "description": "Acordo entre as partes homologado judicialmente", "sort_order": 17, "is_active": True, "is_terminal": True},
    {"code": "EXTINTO_SEM_MERITO", "name": "Extinto sem Resolução de Mérito", "description": "Processo extinto sem resolução do mérito (art. 485 CPC)", "sort_order": 18, "is_active": True, "is_terminal": True},
    {"code": "EXTINTO_COM_MERITO", "name": "Extinto com Resolução de Mérito", "description": "Processo extinto com resolução do mérito (art. 487 CPC)", "sort_order": 19, "is_active": True, "is_terminal": True},
    {"code": "ARQUIVADO", "name": "Arquivado", "description": "Processo arquivado definitivamente", "sort_order": 20, "is_active": False, "is_terminal": True},
]


def upgrade() -> None:
    """Insere dados de referência nas tabelas de tipos de ação, tribunais e status de processo."""
    now = datetime.now(timezone.utc).isoformat()

    # -----------------------------------------------------------------------
    # Tabela: action_types — Tipos de ação cível
    # -----------------------------------------------------------------------
    action_types_table = sa.table(
        "action_types",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("category", sa.String),
        sa.column("description", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("created_at", sa.String),
        sa.column("updated_at", sa.String),
    )

    op.bulk_insert(
        action_types_table,
        [
            {
                "code": at["code"],
                "name": at["name"],
                "category": at["category"],
                "description": at["description"],
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            }
            for at in ACTION_TYPES
        ],
    )

    # -----------------------------------------------------------------------
    # Tabela: courts — Tribunais
    # -----------------------------------------------------------------------
    courts_table = sa.table(
        "courts",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("level", sa.String),
        sa.column("state", sa.String),
        sa.column("description", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("created_at", sa.String),
        sa.column("updated_at", sa.String),
    )

    op.bulk_insert(
        courts_table,
        [
            {
                "code": court["code"],
                "name": court["name"],
                "level": court["level"],
                "state": court["state"],
                "description": court["description"],
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            }
            for court in COURTS
        ],
    )

    # -----------------------------------------------------------------------
    # Tabela: process_statuses — Status de processo
    # -----------------------------------------------------------------------
    process_statuses_table = sa.table(
        "process_statuses",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.String),
        sa.column("sort_order", sa.Integer),
        sa.column("is_active", sa.Boolean),
        sa.column("is_terminal", sa.Boolean),
        sa.column("created_at", sa.String),
        sa.column("updated_at", sa.String),
    )

    op.bulk_insert(
        process_statuses_table,
        [
            {
                "code": ps["code"],
                "name": ps["name"],
                "description": ps["description"],
                "sort_order": ps["sort_order"],
                "is_active": ps["is_active"],
                "is_terminal": ps["is_terminal"],
                "created_at": now,
                "updated_at": now,
            }
            for ps in PROCESS_STATUSES
        ],
    )


def downgrade() -> None:
    """Remove todos os dados de referência inseridos por esta migração."""
    # Remoção na ordem inversa para respeitar possíveis foreign keys

    # Status de processo
    status_codes = [ps["code"] for ps in PROCESS_STATUSES]
    op.execute(
        sa.text(
            "DELETE FROM process_statuses WHERE code = ANY(:codes)"
        ).bindparams(codes=status_codes)
    )

    # Tribunais
    court_codes = [court["code"] for court in COURTS]
    op.execute(
        sa.text(
            "DELETE FROM courts WHERE code = ANY(:codes)"
        ).bindparams(codes=court_codes)
    )

    # Tipos de ação
    action_codes = [at["code"] for at in ACTION_TYPES]
    op.execute(
        sa.text(
            "DELETE FROM action_types WHERE code = ANY(:codes)"
        ).bindparams(codes=action_codes)
    )
