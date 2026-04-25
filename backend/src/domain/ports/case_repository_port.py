"""Interface abstrata (Protocol) para repositório de processos jurídicos.

Define o contrato que qualquer implementação concreta de repositório
de processos (Case) deve seguir, seguindo o padrão Ports & Adapters
da Clean Architecture. Isso permite desacoplar a camada de domínio
da infraestrutura de persistência.
"""

from __future__ import annotations

from abc import abstractmethod
from datetime import datetime
from typing import Optional, Protocol, Sequence
from uuid import UUID

from backend.src.domain.entities.case import Case, CaseStatus


class CaseRepositoryPort(Protocol):
    """Porta (interface) do repositório de processos jurídicos.

    Define as operações de persistência disponíveis para a entidade Case.
    Implementações concretas (adapters) devem respeitar este contrato,
    seja usando SQLAlchemy, repositório em memória para testes, etc.

    Todas as operações são assíncronas para compatibilidade com
    o runtime async do FastAPI e SQLAlchemy 2.0 async.
    """

    @abstractmethod
    async def create(self, case: Case) -> Case:
        """Persiste um novo processo no repositório.

        Args:
            case: Entidade Case já validada pelas regras de domínio.

        Returns:
            A entidade Case persistida, com campos gerados (id, timestamps).

        Raises:
            RepositoryError: Se ocorrer erro de persistência.
            DuplicateError: Se já existir processo com mesmo número CNJ.
        """
        ...

    @abstractmethod
    async def get_by_id(self, case_id: UUID) -> Optional[Case]:
        """Busca um processo pelo seu identificador único.

        Args:
            case_id: UUID do processo.

        Returns:
            A entidade Case encontrada ou None se não existir.
        """
        ...

    @abstractmethod
    async def get_by_cnj_number(self, cnj_number: str) -> Optional[Case]:
        """Busca um processo pelo número CNJ.

        Args:
            cnj_number: Número do processo no formato CNJ
                (ex: 0000000-00.0000.0.00.0000).

        Returns:
            A entidade Case encontrada ou None se não existir.
        """
        ...

    @abstractmethod
    async def list_by_owner(
        self,
        owner_id: UUID,
        *,
        status: Optional[CaseStatus] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[Case]:
        """Lista processos pertencentes a um usuário específico.

        Args:
            owner_id: UUID do usuário proprietário dos processos.
            status: Filtro opcional por status do processo.
            offset: Deslocamento para paginação (padrão: 0).
            limit: Quantidade máxima de registros retornados (padrão: 50).

        Returns:
            Sequência de entidades Case ordenadas por data de criação
            (mais recentes primeiro).
        """
        ...

    @abstractmethod
    async def count_by_owner(
        self,
        owner_id: UUID,
        *,
        status: Optional[CaseStatus] = None,
    ) -> int:
        """Conta o total de processos de um usuário.

        Útil para paginação e exibição de totais na interface.

        Args:
            owner_id: UUID do usuário proprietário dos processos.
            status: Filtro opcional por status do processo.

        Returns:
            Número total de processos que atendem aos critérios.
        """
        ...

    @abstractmethod
    async def update(self, case: Case) -> Case:
        """Atualiza um processo existente no repositório.

        A entidade Case deve conter o id do registro a ser atualizado.
        Campos de auditoria (updated_at) devem ser atualizados
        automaticamente pela implementação.

        Args:
            case: Entidade Case com os dados atualizados.

        Returns:
            A entidade Case atualizada.

        Raises:
            RepositoryError: Se ocorrer erro de persistência.
            NotFoundError: Se o processo não existir no repositório.
        """
        ...

    @abstractmethod
    async def delete(self, case_id: UUID) -> bool:
        """Remove um processo do repositório (soft delete recomendado).

        Implementações devem preferencialmente realizar soft delete,
        marcando o registro como inativo em vez de removê-lo
        fisicamente, para manter a trilha de auditoria.

        Args:
            case_id: UUID do processo a ser removido.

        Returns:
            True se o processo foi removido com sucesso,
            False se não foi encontrado.
        """
        ...

    @abstractmethod
    async def search(
        self,
        *,
        query: Optional[str] = None,
        status: Optional[CaseStatus] = None,
        owner_id: Optional[UUID] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[Case]:
        """Busca processos com filtros combinados.

        Permite busca textual por título, descrição ou número CNJ,
        combinada com filtros por status, proprietário e período.

        Args:
            query: Texto livre para busca em título, descrição e número CNJ.
            status: Filtro por status do processo.
            owner_id: Filtro por proprietário.
            created_after: Filtro por data de criação mínima.
            created_before: Filtro por data de criação máxima.
            offset: Deslocamento para paginação (padrão: 0).
            limit: Quantidade máxima de registros retornados (padrão: 50).

        Returns:
            Sequência de entidades Case que atendem aos critérios,
            ordenadas por relevância ou data de criação.
        """
        ...

    @abstractmethod
    async def exists_by_cnj_number(self, cnj_number: str) -> bool:
        """Verifica se já existe um processo com o número CNJ informado.

        Útil para validação antes da criação de novos processos,
        evitando duplicatas.

        Args:
            cnj_number: Número do processo no formato CNJ.

        Returns:
            True se já existe processo com este número CNJ.
        """
        ...
