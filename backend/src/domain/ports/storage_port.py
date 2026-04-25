"""Porta abstrata (Protocol) para serviço de armazenamento de arquivos.

Define a interface que qualquer adaptador de armazenamento deve implementar,
seguindo os princípios de Clean Architecture (Ports & Adapters).
Permite trocar a implementação concreta (sistema de arquivos local, S3, MinIO, etc.)
sem alterar a camada de domínio ou aplicação.
"""

from __future__ import annotations

import uuid
from typing import Protocol, runtime_checkable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class StorageBackendType(str, Enum):
    """Tipos de backend de armazenamento suportados."""

    LOCAL = "local"
    S3 = "s3"
    MINIO = "minio"


@dataclass(frozen=True)
class FileMetadata:
    """Metadados de um arquivo armazenado.

    Objeto de valor (Value Object) imutável que representa
    as informações descritivas de um arquivo no sistema de armazenamento.

    Attributes:
        file_id: Identificador único do arquivo.
        original_filename: Nome original do arquivo enviado pelo usuário.
        content_type: Tipo MIME do arquivo (ex: application/pdf).
        size_bytes: Tamanho do arquivo em bytes.
        storage_path: Caminho interno no backend de armazenamento.
        checksum_sha256: Hash SHA-256 do conteúdo para verificação de integridade.
        uploaded_at: Data e hora do upload.
        uploaded_by_user_id: ID do usuário que realizou o upload.
        tags: Tags opcionais para categorização do arquivo.
    """

    file_id: uuid.UUID
    original_filename: str
    content_type: str
    size_bytes: int
    storage_path: str
    checksum_sha256: str
    uploaded_at: datetime
    uploaded_by_user_id: uuid.UUID | None = None
    tags: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class PresignedUrlInfo:
    """Informações de uma URL pré-assinada para acesso temporário a um arquivo.

    Attributes:
        url: URL pré-assinada para download ou upload direto.
        expires_at: Data e hora de expiração da URL.
        http_method: Método HTTP permitido (GET para download, PUT para upload).
    """

    url: str
    expires_at: datetime
    http_method: str = "GET"


@runtime_checkable
class StoragePort(Protocol):
    """Interface abstrata para serviço de armazenamento de arquivos.

    Define o contrato que qualquer adaptador de armazenamento deve seguir.
    Todas as operações são assíncronas para compatibilidade com FastAPI
    e o ecossistema asyncio.

    Implementações concretas possíveis:
        - LocalFileStorageAdapter: armazenamento em disco local (desenvolvimento).
        - S3StorageAdapter: Amazon S3 ou compatível (produção).
        - MinIOStorageAdapter: MinIO para ambientes on-premise.
    """

    async def upload(
        self,
        file_content: bytes,
        filename: str,
        content_type: str,
        *,
        user_id: uuid.UUID | None = None,
        tags: dict[str, str] | None = None,
        directory: str | None = None,
    ) -> FileMetadata:
        """Realiza o upload de um arquivo para o armazenamento.

        Args:
            file_content: Conteúdo binário do arquivo.
            filename: Nome original do arquivo.
            content_type: Tipo MIME do arquivo (ex: 'application/pdf').
            user_id: ID do usuário que está realizando o upload.
            tags: Tags opcionais para categorização.
            directory: Diretório/prefixo opcional para organização.

        Returns:
            FileMetadata com os metadados do arquivo armazenado.

        Raises:
            StorageUploadError: Quando ocorre falha no envio do arquivo.
            StorageQuotaExceededError: Quando a cota de armazenamento é excedida.
            InvalidFileTypeError: Quando o tipo de arquivo não é permitido.
        """
        ...

    async def download(self, file_id: uuid.UUID) -> tuple[bytes, FileMetadata]:
        """Realiza o download de um arquivo do armazenamento.

        Args:
            file_id: Identificador único do arquivo.

        Returns:
            Tupla contendo o conteúdo binário e os metadados do arquivo.

        Raises:
            FileNotFoundError: Quando o arquivo não é encontrado.
            StorageDownloadError: Quando ocorre falha na leitura do arquivo.
        """
        ...

    async def download_stream(
        self,
        file_id: uuid.UUID,
        chunk_size: int = 8192,
    ):
        """Realiza o download de um arquivo em modo streaming.

        Útil para arquivos grandes, evitando carregar todo o conteúdo em memória.

        Args:
            file_id: Identificador único do arquivo.
            chunk_size: Tamanho de cada chunk em bytes (padrão: 8KB).

        Yields:
            Chunks de bytes do conteúdo do arquivo.

        Raises:
            FileNotFoundError: Quando o arquivo não é encontrado.
            StorageDownloadError: Quando ocorre falha na leitura do arquivo.
        """
        ...

    async def delete(self, file_id: uuid.UUID) -> bool:
        """Remove um arquivo do armazenamento.

        Args:
            file_id: Identificador único do arquivo a ser removido.

        Returns:
            True se o arquivo foi removido com sucesso, False se não existia.

        Raises:
            StorageDeleteError: Quando ocorre falha na remoção do arquivo.
        """
        ...

    async def get_metadata(self, file_id: uuid.UUID) -> FileMetadata | None:
        """Obtém os metadados de um arquivo sem baixar o conteúdo.

        Args:
            file_id: Identificador único do arquivo.

        Returns:
            FileMetadata se o arquivo existir, None caso contrário.
        """
        ...

    async def exists(self, file_id: uuid.UUID) -> bool:
        """Verifica se um arquivo existe no armazenamento.

        Args:
            file_id: Identificador único do arquivo.

        Returns:
            True se o arquivo existe, False caso contrário.
        """
        ...

    async def generate_presigned_url(
        self,
        file_id: uuid.UUID,
        *,
        expires_in_seconds: int = 3600,
        http_method: str = "GET",
    ) -> PresignedUrlInfo:
        """Gera uma URL pré-assinada para acesso temporário ao arquivo.

        Permite acesso direto ao arquivo sem passar pela API,
        útil para downloads de arquivos grandes.

        Args:
            file_id: Identificador único do arquivo.
            expires_in_seconds: Tempo de validade da URL em segundos (padrão: 1 hora).
            http_method: Método HTTP permitido ('GET' para download, 'PUT' para upload).

        Returns:
            PresignedUrlInfo com a URL e informações de expiração.

        Raises:
            FileNotFoundError: Quando o arquivo não é encontrado.
            PresignedUrlGenerationError: Quando a geração da URL falha.
        """
        ...

    async def list_files(
        self,
        *,
        directory: str | None = None,
        user_id: uuid.UUID | None = None,
        content_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[FileMetadata]:
        """Lista arquivos no armazenamento com filtros opcionais.

        Args:
            directory: Filtrar por diretório/prefixo.
            user_id: Filtrar por usuário que realizou o upload.
            content_type: Filtrar por tipo MIME.
            limit: Número máximo de resultados (padrão: 100).
            offset: Deslocamento para paginação.

        Returns:
            Lista de FileMetadata dos arquivos encontrados.
        """
        ...

    async def copy(
        self,
        source_file_id: uuid.UUID,
        *,
        destination_directory: str | None = None,
        new_tags: dict[str, str] | None = None,
    ) -> FileMetadata:
        """Copia um arquivo para um novo local no armazenamento.

        Args:
            source_file_id: ID do arquivo de origem.
            destination_directory: Diretório de destino (opcional).
            new_tags: Novas tags para o arquivo copiado (opcional).

        Returns:
            FileMetadata do novo arquivo criado pela cópia.

        Raises:
            FileNotFoundError: Quando o arquivo de origem não é encontrado.
            StorageCopyError: Quando ocorre falha na cópia.
        """
        ...

    async def get_total_usage_bytes(
        self,
        *,
        user_id: uuid.UUID | None = None,
        directory: str | None = None,
    ) -> int:
        """Calcula o uso total de armazenamento em bytes.

        Args:
            user_id: Filtrar por usuário específico.
            directory: Filtrar por diretório/prefixo.

        Returns:
            Total de bytes utilizados.
        """
        ...

    async def validate_file_type(
        self,
        filename: str,
        content_type: str,
        file_content: bytes | None = None,
    ) -> bool:
        """Valida se o tipo de arquivo é permitido no sistema.

        Realiza validação tanto pela extensão/MIME type quanto pelo
        conteúdo real do arquivo (magic bytes) quando disponível.

        Tipos permitidos no contexto jurídico:
            - application/pdf (documentos jurídicos)
            - application/msword, application/vnd.openxmlformats-officedocument.wordprocessingml.document (DOC/DOCX)
            - text/plain (textos simples)
            - image/jpeg, image/png (imagens de documentos digitalizados)

        Args:
            filename: Nome do arquivo para verificação de extensão.
            content_type: Tipo MIME declarado.
            file_content: Conteúdo do arquivo para verificação de magic bytes (opcional).

        Returns:
            True se o tipo é permitido, False caso contrário.
        """
        ...
