"""Módulo de hashing e verificação de senhas.

Implementa hashing seguro de senhas utilizando bcrypt como algoritmo principal
e Argon2 como alternativa recomendada para novos deployments. Segue as
diretrizes OWASP para armazenamento seguro de credenciais.

Utiliza passlib para abstração dos algoritmos, permitindo migração transparente
entre esquemas de hashing (upgrade automático de hashes legados).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Protocol

from passlib.context import CryptContext

logger = logging.getLogger(__name__)


class HashingScheme(str, Enum):
    """Esquemas de hashing suportados pela aplicação."""

    BCRYPT = "bcrypt"
    ARGON2 = "argon2"


class PasswordHasherPort(Protocol):
    """Port (interface) para o serviço de hashing de senhas.

    Define o contrato que qualquer implementação de hasher deve seguir,
    conforme os princípios de Clean Architecture (Ports & Adapters).
    """

    def hash(self, plain_password: str) -> str:
        """Gera o hash de uma senha em texto plano.

        Args:
            plain_password: Senha em texto plano a ser hasheada.

        Returns:
            String contendo o hash da senha.
        """
        ...

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Verifica se uma senha em texto plano corresponde ao hash armazenado.

        Args:
            plain_password: Senha em texto plano para verificação.
            hashed_password: Hash armazenado para comparação.

        Returns:
            True se a senha corresponder ao hash, False caso contrário.
        """
        ...

    def needs_rehash(self, hashed_password: str) -> bool:
        """Verifica se o hash precisa ser recalculado.

        Útil para migração transparente entre algoritmos ou atualização
        de parâmetros de custo (rounds/iterations).

        Args:
            hashed_password: Hash armazenado a ser verificado.

        Returns:
            True se o hash deve ser recalculado, False caso contrário.
        """
        ...


class BcryptPasswordHasher:
    """Implementação de hashing de senhas utilizando bcrypt.

    Configuração padrão segue recomendações OWASP:
    - bcrypt com custo (rounds) de 12
    - Suporte a upgrade automático de hashes legados
    - Truncamento de senha em 72 bytes (limitação do bcrypt)

    Attributes:
        _context: Instância do CryptContext do passlib configurada.
    """

    # Comprimento máximo de senha aceito pelo bcrypt (72 bytes)
    BCRYPT_MAX_PASSWORD_LENGTH = 72

    # Número de rounds padrão (OWASP recomenda mínimo de 10, ideal 12+)
    DEFAULT_BCRYPT_ROUNDS = 12

    def __init__(self, rounds: int | None = None) -> None:
        """Inicializa o hasher bcrypt.

        Args:
            rounds: Número de rounds para o bcrypt. Se não informado,
                    utiliza o valor padrão (12). Valores maiores aumentam
                    a segurança mas também o tempo de processamento.
        """
        effective_rounds = rounds or self.DEFAULT_BCRYPT_ROUNDS

        self._context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=effective_rounds,
        )

        logger.info(
            "Hasher bcrypt inicializado com %d rounds.",
            effective_rounds,
        )

    def hash(self, plain_password: str) -> str:
        """Gera o hash bcrypt de uma senha em texto plano.

        Args:
            plain_password: Senha em texto plano a ser hasheada.

        Returns:
            String contendo o hash bcrypt da senha.

        Raises:
            ValueError: Se a senha estiver vazia ou for None.
        """
        self._validate_password(plain_password)
        self._warn_if_truncated(plain_password)

        hashed = self._context.hash(plain_password)
        logger.debug("Hash de senha gerado com sucesso.")
        return hashed

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Verifica se uma senha em texto plano corresponde ao hash bcrypt.

        Utiliza comparação em tempo constante para prevenir ataques de
        timing side-channel.

        Args:
            plain_password: Senha em texto plano para verificação.
            hashed_password: Hash bcrypt armazenado para comparação.

        Returns:
            True se a senha corresponder ao hash, False caso contrário.
        """
        if not plain_password or not hashed_password:
            logger.warning("Tentativa de verificação com senha ou hash vazio.")
            return False

        try:
            is_valid = self._context.verify(plain_password, hashed_password)
        except Exception as exc:
            # passlib pode lançar exceções para hashes malformados
            logger.warning(
                "Erro ao verificar hash de senha: %s",
                str(exc),
            )
            return False

        if is_valid:
            logger.debug("Verificação de senha bem-sucedida.")
        else:
            logger.debug("Verificação de senha falhou — senha incorreta.")

        return is_valid

    def needs_rehash(self, hashed_password: str) -> bool:
        """Verifica se o hash bcrypt precisa ser recalculado.

        Cenários em que rehash é necessário:
        - O número de rounds foi alterado na configuração
        - O hash utiliza um esquema deprecated
        - Migração de algoritmo legado

        Args:
            hashed_password: Hash armazenado a ser verificado.

        Returns:
            True se o hash deve ser recalculado, False caso contrário.
        """
        if not hashed_password:
            return True

        try:
            needs_update = self._context.needs_update(hashed_password)
        except Exception as exc:
            logger.warning(
                "Erro ao verificar necessidade de rehash: %s",
                str(exc),
            )
            return True

        if needs_update:
            logger.info(
                "Hash de senha identificado como desatualizado — rehash recomendado."
            )

        return needs_update

    def verify_and_update(
        self, plain_password: str, hashed_password: str
    ) -> tuple[bool, str | None]:
        """Verifica a senha e retorna novo hash se necessário.

        Combina verificação e rehash em uma única operação atômica,
        útil para migração transparente de algoritmos durante o login.

        Args:
            plain_password: Senha em texto plano para verificação.
            hashed_password: Hash armazenado para comparação.

        Returns:
            Tupla (is_valid, new_hash) onde:
            - is_valid: True se a senha está correta
            - new_hash: Novo hash se rehash for necessário, None caso contrário
        """
        is_valid = self.verify(plain_password, hashed_password)

        if not is_valid:
            return False, None

        if self.needs_rehash(hashed_password):
            new_hash = self.hash(plain_password)
            logger.info(
                "Hash de senha atualizado automaticamente durante verificação."
            )
            return True, new_hash

        return True, None

    def _validate_password(self, password: str) -> None:
        """Valida a senha antes do hashing.

        Args:
            password: Senha a ser validada.

        Raises:
            ValueError: Se a senha estiver vazia ou for None.
        """
        if not password:
            raise ValueError("A senha não pode estar vazia.")

    def _warn_if_truncated(self, password: str) -> None:
        """Emite aviso se a senha será truncada pelo bcrypt.

        O bcrypt possui limitação de 72 bytes. Senhas maiores são
        silenciosamente truncadas, o que pode ser um risco de segurança.

        Args:
            password: Senha a ser verificada.
        """
        password_bytes = password.encode("utf-8")
        if len(password_bytes) > self.BCRYPT_MAX_PASSWORD_LENGTH:
            logger.warning(
                "Senha excede %d bytes e será truncada pelo bcrypt. "
                "Considere utilizar Argon2 para senhas longas.",
                self.BCRYPT_MAX_PASSWORD_LENGTH,
            )


class Argon2PasswordHasher:
    """Implementação de hashing de senhas utilizando Argon2id.

    Argon2id é o algoritmo vencedor da Password Hashing Competition (PHC)
    e é recomendado pela OWASP como primeira escolha para novos sistemas.

    Vantagens sobre bcrypt:
    - Resistente a ataques com GPU e ASIC (memory-hard)
    - Sem limitação de comprimento de senha
    - Parâmetros configuráveis de memória, tempo e paralelismo

    Requer instalação adicional: pip install passlib[argon2]

    Attributes:
        _context: Instância do CryptContext do passlib configurada.
    """

    # Parâmetros padrão seguindo recomendações OWASP (Argon2id)
    DEFAULT_TIME_COST = 3  # iterações
    DEFAULT_MEMORY_COST = 65536  # 64 MB em KiB
    DEFAULT_PARALLELISM = 4  # threads

    def __init__(
        self,
        time_cost: int | None = None,
        memory_cost: int | None = None,
        parallelism: int | None = None,
    ) -> None:
        """Inicializa o hasher Argon2id.

        Args:
            time_cost: Número de iterações. Padrão: 3.
            memory_cost: Memória utilizada em KiB. Padrão: 65536 (64 MB).
            parallelism: Grau de paralelismo. Padrão: 4.
        """
        effective_time_cost = time_cost or self.DEFAULT_TIME_COST
        effective_memory_cost = memory_cost or self.DEFAULT_MEMORY_COST
        effective_parallelism = parallelism or self.DEFAULT_PARALLELISM

        self._context = CryptContext(
            schemes=["argon2"],
            deprecated="auto",
            argon2__type="ID",
            argon2__time_cost=effective_time_cost,
            argon2__memory_cost=effective_memory_cost,
            argon2__parallelism=effective_parallelism,
        )

        logger.info(
            "Hasher Argon2id inicializado — time_cost=%d, memory_cost=%d KiB, parallelism=%d.",
            effective_time_cost,
            effective_memory_cost,
            effective_parallelism,
        )

    def hash(self, plain_password: str) -> str:
        """Gera o hash Argon2id de uma senha em texto plano.

        Args:
            plain_password: Senha em texto plano a ser hasheada.

        Returns:
            String contendo o hash Argon2id da senha.

        Raises:
            ValueError: Se a senha estiver vazia ou for None.
        """
        if not plain_password:
            raise ValueError("A senha não pode estar vazia.")

        hashed = self._context.hash(plain_password)
        logger.debug("Hash Argon2id de senha gerado com sucesso.")
        return hashed

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Verifica se uma senha em texto plano corresponde ao hash Argon2id.

        Args:
            plain_password: Senha em texto plano para verificação.
            hashed_password: Hash Argon2id armazenado para comparação.

        Returns:
            True se a senha corresponder ao hash, False caso contrário.
        """
        if not plain_password or not hashed_password:
            logger.warning("Tentativa de verificação com senha ou hash vazio.")
            return False

        try:
            is_valid = self._context.verify(plain_password, hashed_password)
        except Exception as exc:
            logger.warning(
                "Erro ao verificar hash Argon2id: %s",
                str(exc),
            )
            return False

        if is_valid:
            logger.debug("Verificação de senha Argon2id bem-sucedida.")
        else:
            logger.debug("Verificação de senha Argon2id falhou — senha incorreta.")

        return is_valid

    def needs_rehash(self, hashed_password: str) -> bool:
        """Verifica se o hash Argon2id precisa ser recalculado.

        Args:
            hashed_password: Hash armazenado a ser verificado.

        Returns:
            True se o hash deve ser recalculado, False caso contrário.
        """
        if not hashed_password:
            return True

        try:
            return self._context.needs_update(hashed_password)
        except Exception as exc:
            logger.warning(
                "Erro ao verificar necessidade de rehash Argon2id: %s",
                str(exc),
            )
            return True

    def verify_and_update(
        self, plain_password: str, hashed_password: str
    ) -> tuple[bool, str | None]:
        """Verifica a senha e retorna novo hash se necessário.

        Args:
            plain_password: Senha em texto plano para verificação.
            hashed_password: Hash armazenado para comparação.

        Returns:
            Tupla (is_valid, new_hash) onde:
            - is_valid: True se a senha está correta
            - new_hash: Novo hash se rehash for necessário, None caso contrário
        """
        is_valid = self.verify(plain_password, hashed_password)

        if not is_valid:
            return False, None

        if self.needs_rehash(hashed_password):
            new_hash = self.hash(plain_password)
            logger.info(
                "Hash Argon2id atualizado automaticamente durante verificação."
            )
            return True, new_hash

        return True, None


def create_password_hasher(
    scheme: HashingScheme = HashingScheme.BCRYPT,
    **kwargs: int,
) -> BcryptPasswordHasher | Argon2PasswordHasher:
    """Factory para criação de instâncias de password hasher.

    Centraliza a criação do hasher adequado com base na configuração
    do projeto. Facilita a troca de algoritmo sem alterar código consumidor.

    Args:
        scheme: Esquema de hashing desejado. Padrão: BCRYPT.
        **kwargs: Parâmetros adicionais específicos do algoritmo
                  (ex: rounds para bcrypt, time_cost para argon2).

    Returns:
        Instância configurada do hasher correspondente ao esquema.

    Raises:
        ValueError: Se o esquema informado não for suportado.

    Exemplo:
        >>> hasher = create_password_hasher(HashingScheme.BCRYPT, rounds=14)
        >>> hashed = hasher.hash("minha_senha_segura")
        >>> hasher.verify("minha_senha_segura", hashed)
        True
    """
    if scheme == HashingScheme.BCRYPT:
        return BcryptPasswordHasher(rounds=kwargs.get("rounds"))

    if scheme == HashingScheme.ARGON2:
        return Argon2PasswordHasher(
            time_cost=kwargs.get("time_cost"),
            memory_cost=kwargs.get("memory_cost"),
            parallelism=kwargs.get("parallelism"),
        )

    raise ValueError(
        f"Esquema de hashing não suportado: '{scheme}'. "
        f"Esquemas válidos: {[s.value for s in HashingScheme]}"
    )


# Instância padrão para uso direto via injeção de dependência
# Em produção, a configuração deve vir de variáveis de ambiente
default_password_hasher = create_password_hasher(HashingScheme.BCRYPT)
