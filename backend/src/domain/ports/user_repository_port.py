"""Port (interface abstrata) para o repositório de usuários.

Define o contrato que qualquer implementação concreta de repositório
de usuários deve seguir, conforme os princípios de Clean Architecture
(Ports & Adapters). A camada de domínio e aplicação dependem apenas
desta interface, nunca de implementações concretas de infraestrutura.
"""

from __future__ import annotations

from abc import abstractmethod
from datetime import datetime
from typing import Optional, Protocol, Sequence, runtime_checkable
from uuid import UUID

from backend.src.domain.entities.user import User, UserRole


@runtime_checkable
class UserRepositoryPort(Protocol):
    """Interface abstrata para operações de persistência de usuários.

    Todas as implementações concretas (ex.: SQLAlchemy, in-memory para
    testes) devem satisfazer este protocolo. Os métodos são assíncronos
    para compatibilidade com o stack FastAPI + asyncpg.
    """

    # ------------------------------------------------------------------ #
    # Operações de leitura
    # ------------------------------------------------------------------ #

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Busca um usuário pelo seu identificador único.

        Args:
            user_id: UUID do usuário.

        Returns:
            Instância de ``User`` caso encontrado, ``None`` caso contrário.
        """
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """Busca um usuário pelo endereço de e-mail.

        O e-mail é tratado como identificador único de login.

        Args:
            email: Endereço de e-mail (case-insensitive na implementação).

        Returns:
            Instância de ``User`` caso encontrado, ``None`` caso contrário.
        """
        ...

    @abstractmethod
    async def get_by_oab_number(self, oab_number: str) -> Optional[User]:
        """Busca um usuário pelo número de registro na OAB.

        Args:
            oab_number: Número de inscrição na OAB (ex.: "123456/SP").

        Returns:
            Instância de ``User`` caso encontrado, ``None`` caso contrário.
        """
        ...

    @abstractmethod
    async def list_users(
        self,
        *,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[User]:
        """Lista usuários com filtros opcionais e paginação.

        Args:
            role: Filtrar por role RBAC específica.
            is_active: Filtrar por status ativo/inativo.
            offset: Número de registros a pular (paginação).
            limit: Quantidade máxima de registros retornados.

        Returns:
            Sequência (possivelmente vazia) de instâncias ``User``.
        """
        ...

    @abstractmethod
    async def count(
        self,
        *,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
    ) -> int:
        """Retorna a contagem total de usuários conforme os filtros.

        Útil para calcular paginação no frontend.

        Args:
            role: Filtrar por role RBAC específica.
            is_active: Filtrar por status ativo/inativo.

        Returns:
            Número inteiro de usuários que atendem aos critérios.
        """
        ...

    @abstractmethod
    async def exists_by_email(self, email: str) -> bool:
        """Verifica se já existe um usuário cadastrado com o e-mail informado.

        Método otimizado que evita carregar a entidade completa quando
        apenas a verificação de existência é necessária (ex.: registro).

        Args:
            email: Endereço de e-mail a verificar.

        Returns:
            ``True`` se o e-mail já estiver em uso, ``False`` caso contrário.
        """
        ...

    # ------------------------------------------------------------------ #
    # Operações de escrita
    # ------------------------------------------------------------------ #

    @abstractmethod
    async def create(self, user: User) -> User:
        """Persiste um novo usuário no repositório.

        Args:
            user: Entidade ``User`` já validada pelas regras de domínio.

        Returns:
            Entidade ``User`` persistida (com campos gerados, se houver).

        Raises:
            Exceção de infraestrutura caso o e-mail ou OAB já existam
            (violação de unicidade).
        """
        ...

    @abstractmethod
    async def update(self, user: User) -> User:
        """Atualiza os dados de um usuário existente.

        A implementação deve garantir que o ``user.id`` exista antes
        de aplicar a atualização.

        Args:
            user: Entidade ``User`` com os dados atualizados.

        Returns:
            Entidade ``User`` após a persistência da atualização.

        Raises:
            Exceção de infraestrutura caso o usuário não seja encontrado.
        """
        ...

    @abstractmethod
    async def soft_delete(self, user_id: UUID) -> bool:
        """Realiza exclusão lógica (soft delete) de um usuário.

        Em conformidade com requisitos de auditoria e compliance (LGPD),
        o registro não é removido fisicamente — apenas marcado como
        inativo/excluído.

        Args:
            user_id: UUID do usuário a ser desativado.

        Returns:
            ``True`` se o usuário foi encontrado e desativado,
            ``False`` caso não exista.
        """
        ...

    # ------------------------------------------------------------------ #
    # Operações de autenticação e segurança
    # ------------------------------------------------------------------ #

    @abstractmethod
    async def update_last_login(self, user_id: UUID, login_at: datetime) -> None:
        """Registra o timestamp do último login bem-sucedido.

        Args:
            user_id: UUID do usuário.
            login_at: Data/hora do login (timezone-aware, UTC).
        """
        ...

    @abstractmethod
    async def increment_failed_login_attempts(self, user_id: UUID) -> int:
        """Incrementa o contador de tentativas de login falhas.

        Utilizado para políticas de bloqueio temporário (account lockout)
        após múltiplas tentativas inválidas.

        Args:
            user_id: UUID do usuário.

        Returns:
            Número atualizado de tentativas falhas consecutivas.
        """
        ...

    @abstractmethod
    async def reset_failed_login_attempts(self, user_id: UUID) -> None:
        """Zera o contador de tentativas de login falhas.

        Deve ser chamado após um login bem-sucedido.

        Args:
            user_id: UUID do usuário.
        """
        ...
