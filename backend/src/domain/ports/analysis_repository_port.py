"""Port (interface abstrata) para o repositório de análises jurídicas.

Define o contrato que qualquer implementação concreta de repositório de análises
deve seguir, conforme os princípios de Clean Architecture (Ports & Adapters).
A camada de domínio depende apenas desta interface, nunca de implementações concretas.
"""

from __future__ import annotations

import uuid
from abc import abstractmethod
from datetime import datetime
from typing import Protocol, runtime_checkable

from backend.src.domain.entities.analysis import Analysis, AnalysisStatus, AnalysisType


@runtime_checkable
class AnalysisRepositoryPort(Protocol):
    """Interface abstrata para persistência e consulta de análises jurídicas.

    Todas as implementações concretas (ex.: SQLAlchemy, in-memory para testes)
    devem satisfazer este protocolo. Os métodos são assíncronos para compatibilidade
    com o stack FastAPI + asyncpg.
    """

    @abstractmethod
    async def create(self, analysis: Analysis) -> Analysis:
        """Persiste uma nova análise no repositório.

        Args:
            analysis: Entidade de domínio Analysis já validada.

        Returns:
            A entidade Analysis persistida, incluindo campos gerados
            pelo repositório (ex.: timestamps de criação).

        Raises:
            RepositoryError: Em caso de falha na persistência.
        """
        ...

    @abstractmethod
    async def get_by_id(self, analysis_id: uuid.UUID) -> Analysis | None:
        """Busca uma análise pelo seu identificador único.

        Args:
            analysis_id: UUID da análise.

        Returns:
            A entidade Analysis correspondente ou None se não encontrada.
        """
        ...

    @abstractmethod
    async def list_by_document_id(
        self,
        document_id: uuid.UUID,
        *,
        analysis_type: AnalysisType | None = None,
        status: AnalysisStatus | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Analysis]:
        """Lista análises associadas a um documento específico.

        Args:
            document_id: UUID do documento ao qual as análises pertencem.
            analysis_type: Filtro opcional por tipo de análise.
            status: Filtro opcional por status da análise.
            offset: Deslocamento para paginação (padrão: 0).
            limit: Quantidade máxima de resultados (padrão: 50).

        Returns:
            Lista de entidades Analysis que atendem aos critérios.
        """
        ...

    @abstractmethod
    async def list_by_user_id(
        self,
        user_id: uuid.UUID,
        *,
        analysis_type: AnalysisType | None = None,
        status: AnalysisStatus | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Analysis]:
        """Lista análises criadas por um usuário específico.

        Args:
            user_id: UUID do usuário proprietário das análises.
            analysis_type: Filtro opcional por tipo de análise.
            status: Filtro opcional por status da análise.
            offset: Deslocamento para paginação (padrão: 0).
            limit: Quantidade máxima de resultados (padrão: 50).

        Returns:
            Lista de entidades Analysis que atendem aos critérios.
        """
        ...

    @abstractmethod
    async def update(self, analysis: Analysis) -> Analysis:
        """Atualiza uma análise existente no repositório.

        Args:
            analysis: Entidade de domínio Analysis com os dados atualizados.
                      O campo `id` deve corresponder a um registro existente.

        Returns:
            A entidade Analysis atualizada.

        Raises:
            RepositoryError: Se a análise não for encontrada ou houver falha
                na atualização.
        """
        ...

    @abstractmethod
    async def update_status(
        self,
        analysis_id: uuid.UUID,
        status: AnalysisStatus,
        *,
        error_message: str | None = None,
    ) -> Analysis:
        """Atualiza apenas o status de uma análise.

        Método otimizado para transições de estado no ciclo de vida da análise,
        evitando a necessidade de carregar e salvar a entidade completa.

        Args:
            analysis_id: UUID da análise a ser atualizada.
            status: Novo status da análise.
            error_message: Mensagem de erro opcional (relevante quando
                status é FAILED).

        Returns:
            A entidade Analysis com o status atualizado.

        Raises:
            RepositoryError: Se a análise não for encontrada ou a transição
                de status for inválida.
        """
        ...

    @abstractmethod
    async def delete(self, analysis_id: uuid.UUID) -> bool:
        """Remove uma análise do repositório.

        Args:
            analysis_id: UUID da análise a ser removida.

        Returns:
            True se a análise foi removida com sucesso, False se não encontrada.
        """
        ...

    @abstractmethod
    async def count_by_document_id(
        self,
        document_id: uuid.UUID,
        *,
        status: AnalysisStatus | None = None,
    ) -> int:
        """Conta o número de análises associadas a um documento.

        Args:
            document_id: UUID do documento.
            status: Filtro opcional por status para a contagem.

        Returns:
            Número total de análises que atendem aos critérios.
        """
        ...

    @abstractmethod
    async def exists(
        self,
        document_id: uuid.UUID,
        analysis_type: AnalysisType,
    ) -> bool:
        """Verifica se já existe uma análise de determinado tipo para um documento.

        Útil para evitar análises duplicadas do mesmo tipo sobre o mesmo documento.

        Args:
            document_id: UUID do documento.
            analysis_type: Tipo de análise a verificar.

        Returns:
            True se já existe uma análise desse tipo para o documento.
        """
        ...

    @abstractmethod
    async def list_pending(
        self,
        *,
        older_than: datetime | None = None,
        limit: int = 100,
    ) -> list[Analysis]:
        """Lista análises pendentes de processamento.

        Utilizado pelo worker Celery para buscar análises que precisam
        ser processadas ou reprocessadas.

        Args:
            older_than: Se informado, retorna apenas análises pendentes
                criadas antes desta data (útil para detectar análises travadas).
            limit: Quantidade máxima de resultados (padrão: 100).

        Returns:
            Lista de entidades Analysis com status pendente.
        """
        ...
