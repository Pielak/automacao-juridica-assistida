"""Porta (interface abstrata) para o repositório de auditoria.

Define o contrato que qualquer implementação concreta de repositório
de auditoria deve seguir, conforme os princípios de Clean Architecture
(Ports & Adapters). A camada de domínio depende apenas desta interface,
nunca de implementações concretas de infraestrutura.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# DTOs de domínio para auditoria
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AuditEntry:
    """Representa um registro imutável de auditoria no domínio.

    Cada entrada captura uma ação realizada por um ator (usuário ou sistema)
    sobre um recurso específico, incluindo metadados contextuais.
    """

    id: uuid.UUID
    """Identificador único do registro de auditoria."""

    actor_id: uuid.UUID
    """Identificador do usuário ou serviço que executou a ação."""

    action: str
    """Tipo da ação realizada (ex.: 'document.created', 'analysis.requested')."""

    resource_type: str
    """Tipo do recurso afetado (ex.: 'document', 'user', 'analysis')."""

    resource_id: str
    """Identificador do recurso afetado pela ação."""

    timestamp: datetime
    """Momento em que a ação foi registrada (UTC)."""

    ip_address: str | None = None
    """Endereço IP de origem da requisição, quando disponível."""

    user_agent: str | None = None
    """User-Agent do cliente que originou a requisição."""

    details: dict[str, Any] = field(default_factory=dict)
    """Metadados adicionais da ação (payload anterior/posterior, parâmetros, etc.)."""

    status: str = "success"
    """Resultado da ação: 'success', 'failure' ou 'denied'."""

    correlation_id: str | None = None
    """Identificador de correlação para rastreamento entre serviços/camadas."""


@dataclass(frozen=True)
class AuditQueryFilters:
    """Filtros para consulta de registros de auditoria.

    Todos os campos são opcionais; quando omitidos, não restringem a busca.
    """

    actor_id: uuid.UUID | None = None
    """Filtrar por ator específico."""

    action: str | None = None
    """Filtrar por tipo de ação (suporta prefixo, ex.: 'document.*')."""

    resource_type: str | None = None
    """Filtrar por tipo de recurso."""

    resource_id: str | None = None
    """Filtrar por recurso específico."""

    start_date: datetime | None = None
    """Data/hora inicial do intervalo de busca (inclusive)."""

    end_date: datetime | None = None
    """Data/hora final do intervalo de busca (inclusive)."""

    status: str | None = None
    """Filtrar por resultado da ação."""

    correlation_id: str | None = None
    """Filtrar por identificador de correlação."""

    offset: int = 0
    """Deslocamento para paginação."""

    limit: int = 50
    """Quantidade máxima de registros retornados (padrão: 50)."""


@dataclass(frozen=True)
class AuditQueryResult:
    """Resultado paginado de uma consulta de auditoria."""

    items: list[AuditEntry]
    """Lista de registros de auditoria encontrados."""

    total: int
    """Total de registros que atendem aos filtros (sem paginação)."""

    offset: int
    """Deslocamento aplicado."""

    limit: int
    """Limite aplicado."""


# ---------------------------------------------------------------------------
# Porta (Protocol) — contrato do repositório de auditoria
# ---------------------------------------------------------------------------


@runtime_checkable
class AuditRepositoryPort(Protocol):
    """Contrato abstrato para persistência de registros de auditoria.

    Implementações concretas (ex.: PostgreSQL via SQLAlchemy, Elasticsearch,
    armazenamento em arquivo) devem satisfazer este Protocol.

    Todas as operações são assíncronas para compatibilidade com o runtime
    async do FastAPI e SQLAlchemy 2.0 + asyncpg.
    """

    async def save(self, entry: AuditEntry) -> AuditEntry:
        """Persiste um novo registro de auditoria.

        Args:
            entry: Registro de auditoria a ser salvo.

        Returns:
            O registro persistido (potencialmente enriquecido com campos
            gerados pela infraestrutura).

        Raises:
            RepositoryError: Em caso de falha na persistência.
        """
        ...

    async def save_batch(self, entries: list[AuditEntry]) -> list[AuditEntry]:
        """Persiste múltiplos registros de auditoria em lote.

        Útil para operações em massa ou flush de buffer de auditoria.

        Args:
            entries: Lista de registros de auditoria a serem salvos.

        Returns:
            Lista dos registros persistidos.

        Raises:
            RepositoryError: Em caso de falha na persistência.
        """
        ...

    async def find_by_id(self, entry_id: uuid.UUID) -> AuditEntry | None:
        """Busca um registro de auditoria pelo seu identificador único.

        Args:
            entry_id: UUID do registro de auditoria.

        Returns:
            O registro encontrado ou None se não existir.

        Raises:
            RepositoryError: Em caso de falha na consulta.
        """
        ...

    async def find_by_resource(
        self,
        resource_type: str,
        resource_id: str,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> AuditQueryResult:
        """Busca registros de auditoria associados a um recurso específico.

        Retorna o histórico de ações sobre um determinado recurso,
        ordenado do mais recente para o mais antigo.

        Args:
            resource_type: Tipo do recurso (ex.: 'document').
            resource_id: Identificador do recurso.
            offset: Deslocamento para paginação.
            limit: Quantidade máxima de registros.

        Returns:
            Resultado paginado com os registros encontrados.

        Raises:
            RepositoryError: Em caso de falha na consulta.
        """
        ...

    async def find_by_actor(
        self,
        actor_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> AuditQueryResult:
        """Busca registros de auditoria de um ator (usuário) específico.

        Retorna o histórico de ações realizadas por um determinado ator,
        ordenado do mais recente para o mais antigo.

        Args:
            actor_id: UUID do ator.
            offset: Deslocamento para paginação.
            limit: Quantidade máxima de registros.

        Returns:
            Resultado paginado com os registros encontrados.

        Raises:
            RepositoryError: Em caso de falha na consulta.
        """
        ...

    async def query(self, filters: AuditQueryFilters) -> AuditQueryResult:
        """Consulta registros de auditoria com filtros compostos.

        Método genérico de busca que aceita múltiplos critérios de filtragem
        combinados. Ideal para telas de pesquisa avançada e relatórios.

        Args:
            filters: Objeto com os critérios de filtragem e paginação.

        Returns:
            Resultado paginado com os registros encontrados.

        Raises:
            RepositoryError: Em caso de falha na consulta.
        """
        ...

    async def count_by_action(
        self,
        action: str,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> int:
        """Conta registros de auditoria por tipo de ação em um período.

        Útil para métricas, dashboards e detecção de anomalias.

        Args:
            action: Tipo da ação a ser contada.
            start_date: Início do período (opcional).
            end_date: Fim do período (opcional).

        Returns:
            Quantidade de registros encontrados.

        Raises:
            RepositoryError: Em caso de falha na consulta.
        """
        ...

    async def delete_before(self, cutoff_date: datetime) -> int:
        """Remove registros de auditoria anteriores a uma data de corte.

        Utilizado para políticas de retenção de dados conforme requisitos
        de compliance (LGPD, regulamentações do setor jurídico).

        **Atenção:** Esta operação é irreversível. Implementações devem
        garantir que registros sejam arquivados antes da exclusão, se
        exigido pela política de retenção.

        Args:
            cutoff_date: Data de corte — registros anteriores serão removidos.

        Returns:
            Quantidade de registros removidos.

        Raises:
            RepositoryError: Em caso de falha na operação.
        """
        ...
