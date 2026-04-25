"""Use cases de auditoria: registrar eventos e consultar trilha de auditoria.

Implementa os casos de uso relacionados ao módulo de auditoria,
orquestrando as regras de negócio e delegando persistência ao
repositório via porta abstrata (Clean Architecture).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional, Sequence

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Porta do repositório de auditoria (interface abstrata do domínio)
# ---------------------------------------------------------------------------
# NOTA: O arquivo peer está truncado, então inferimos os contratos mínimos
# que a porta deve expor. Os nomes abaixo devem corresponder exatamente
# aos definidos em audit_repository_port.py.
# ---------------------------------------------------------------------------
from backend.src.domain.ports.audit_repository_port import (
    AuditRepositoryPort,  # Protocol / ABC do repositório
    AuditEntry,           # DTO / dataclass que representa um registro de auditoria
    AuditFilter,          # DTO / dataclass para filtros de consulta
)

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# DTOs de entrada / saída dos use cases
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RegisterAuditEventInput:
    """Dados de entrada para registrar um evento de auditoria."""

    user_id: uuid.UUID
    action: str
    entity_type: str
    entity_id: uuid.UUID
    details: dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


@dataclass(frozen=True)
class RegisterAuditEventOutput:
    """Resultado do registro de um evento de auditoria."""

    audit_id: uuid.UUID
    recorded_at: datetime


@dataclass(frozen=True)
class QueryAuditTrailInput:
    """Dados de entrada para consultar a trilha de auditoria."""

    entity_type: Optional[str] = None
    entity_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    action: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = 1
    page_size: int = 50


@dataclass(frozen=True)
class QueryAuditTrailOutput:
    """Resultado paginado da consulta à trilha de auditoria."""

    entries: Sequence[AuditEntry]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Use Cases
# ---------------------------------------------------------------------------

class RegisterAuditEventUseCase:
    """Caso de uso: registrar um evento na trilha de auditoria.

    Responsável por validar os dados do evento, enriquecer com metadados
    (timestamp, ID único) e delegar a persistência ao repositório.
    """

    def __init__(self, audit_repository: AuditRepositoryPort) -> None:
        """Inicializa o use case com a porta do repositório de auditoria.

        Args:
            audit_repository: Implementação concreta da porta de auditoria.
        """
        self._repo = audit_repository

    async def execute(self, input_data: RegisterAuditEventInput) -> RegisterAuditEventOutput:
        """Executa o registro de um evento de auditoria.

        Args:
            input_data: Dados do evento a ser registrado.

        Returns:
            Resultado contendo o ID do registro e o timestamp.

        Raises:
            ValueError: Se os dados de entrada forem inválidos.
        """
        # Validações de negócio
        self._validate_input(input_data)

        audit_id = uuid.uuid4()
        recorded_at = datetime.utcnow()

        entry = AuditEntry(
            id=audit_id,
            user_id=input_data.user_id,
            action=input_data.action,
            entity_type=input_data.entity_type,
            entity_id=input_data.entity_id,
            details=input_data.details,
            ip_address=input_data.ip_address,
            user_agent=input_data.user_agent,
            created_at=recorded_at,
        )

        await self._repo.save(entry)

        logger.info(
            "Evento de auditoria registrado com sucesso",
            audit_id=str(audit_id),
            user_id=str(input_data.user_id),
            action=input_data.action,
            entity_type=input_data.entity_type,
            entity_id=str(input_data.entity_id),
        )

        return RegisterAuditEventOutput(
            audit_id=audit_id,
            recorded_at=recorded_at,
        )

    @staticmethod
    def _validate_input(input_data: RegisterAuditEventInput) -> None:
        """Valida os dados de entrada do evento de auditoria.

        Args:
            input_data: Dados a serem validados.

        Raises:
            ValueError: Se algum campo obrigatório estiver vazio ou inválido.
        """
        if not input_data.action or not input_data.action.strip():
            raise ValueError("A ação do evento de auditoria é obrigatória.")

        if not input_data.entity_type or not input_data.entity_type.strip():
            raise ValueError("O tipo da entidade é obrigatório para o registro de auditoria.")


class QueryAuditTrailByEntityUseCase:
    """Caso de uso: consultar trilha de auditoria filtrada por entidade.

    Permite buscar todos os eventos de auditoria relacionados a uma
    entidade específica (ex.: um documento, um processo), com suporte
    a paginação e filtros temporais.
    """

    def __init__(self, audit_repository: AuditRepositoryPort) -> None:
        """Inicializa o use case com a porta do repositório de auditoria.

        Args:
            audit_repository: Implementação concreta da porta de auditoria.
        """
        self._repo = audit_repository

    async def execute(self, input_data: QueryAuditTrailInput) -> QueryAuditTrailOutput:
        """Executa a consulta à trilha de auditoria por entidade.

        Args:
            input_data: Filtros e parâmetros de paginação.

        Returns:
            Resultado paginado com os registros de auditoria encontrados.

        Raises:
            ValueError: Se nenhum critério de filtro for informado.
        """
        if not input_data.entity_type and not input_data.entity_id:
            raise ValueError(
                "É necessário informar ao menos o tipo ou o ID da entidade "
                "para consultar a trilha de auditoria por entidade."
            )

        # Normaliza paginação
        page = max(1, input_data.page)
        page_size = max(1, min(input_data.page_size, 200))  # Limite máximo de 200

        audit_filter = AuditFilter(
            entity_type=input_data.entity_type,
            entity_id=input_data.entity_id,
            user_id=input_data.user_id,
            action=input_data.action,
            start_date=input_data.start_date,
            end_date=input_data.end_date,
        )

        entries, total = await self._repo.find_by_filter(
            audit_filter=audit_filter,
            page=page,
            page_size=page_size,
        )

        logger.info(
            "Consulta de auditoria por entidade realizada",
            entity_type=input_data.entity_type,
            entity_id=str(input_data.entity_id) if input_data.entity_id else None,
            total_encontrado=total,
            page=page,
        )

        return QueryAuditTrailOutput(
            entries=entries,
            total=total,
            page=page,
            page_size=page_size,
        )


class QueryAuditTrailByUserUseCase:
    """Caso de uso: consultar trilha de auditoria filtrada por usuário.

    Permite buscar todos os eventos de auditoria realizados por um
    usuário específico, com suporte a paginação e filtros temporais.
    Essencial para investigações de conformidade e análise de atividades.
    """

    def __init__(self, audit_repository: AuditRepositoryPort) -> None:
        """Inicializa o use case com a porta do repositório de auditoria.

        Args:
            audit_repository: Implementação concreta da porta de auditoria.
        """
        self._repo = audit_repository

    async def execute(self, input_data: QueryAuditTrailInput) -> QueryAuditTrailOutput:
        """Executa a consulta à trilha de auditoria por usuário.

        Args:
            input_data: Filtros e parâmetros de paginação.

        Returns:
            Resultado paginado com os registros de auditoria encontrados.

        Raises:
            ValueError: Se o ID do usuário não for informado.
        """
        if not input_data.user_id:
            raise ValueError(
                "O ID do usuário é obrigatório para consultar a trilha de auditoria por usuário."
            )

        # Normaliza paginação
        page = max(1, input_data.page)
        page_size = max(1, min(input_data.page_size, 200))

        audit_filter = AuditFilter(
            entity_type=input_data.entity_type,
            entity_id=input_data.entity_id,
            user_id=input_data.user_id,
            action=input_data.action,
            start_date=input_data.start_date,
            end_date=input_data.end_date,
        )

        entries, total = await self._repo.find_by_filter(
            audit_filter=audit_filter,
            page=page,
            page_size=page_size,
        )

        logger.info(
            "Consulta de auditoria por usuário realizada",
            user_id=str(input_data.user_id),
            total_encontrado=total,
            page=page,
        )

        return QueryAuditTrailOutput(
            entries=entries,
            total=total,
            page=page,
            page_size=page_size,
        )


# ---------------------------------------------------------------------------
# Exports públicos do módulo
# ---------------------------------------------------------------------------
__all__ = [
    "RegisterAuditEventInput",
    "RegisterAuditEventOutput",
    "RegisterAuditEventUseCase",
    "QueryAuditTrailInput",
    "QueryAuditTrailOutput",
    "QueryAuditTrailByEntityUseCase",
    "QueryAuditTrailByUserUseCase",
]
