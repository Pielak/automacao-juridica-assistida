"""Portas (interfaces) da camada de domínio.

Este pacote define as interfaces abstratas (ports) que estabelecem os contratos
entre a camada de domínio/aplicação e a camada de infraestrutura, seguindo os
princípios de Clean Architecture (Ports & Adapters).

As portas são divididas em duas categorias:
- **Driven Ports (Repositórios/Gateways):** Interfaces que a camada de aplicação
  utiliza para acessar recursos externos (banco de dados, APIs, serviços de IA, etc.).
- **Driving Ports (Use Cases):** Interfaces que definem os casos de uso disponíveis
  para a camada de apresentação.

Todas as implementações concretas residem na camada de infraestrutura e são
injetadas via inversão de dependência.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Generic, Optional, Protocol, TypeVar
from uuid import UUID

# ---------------------------------------------------------------------------
# Tipos genéricos reutilizáveis
# ---------------------------------------------------------------------------

T = TypeVar("T")
ID = TypeVar("ID")


# ---------------------------------------------------------------------------
# Port base para repositórios CRUD
# ---------------------------------------------------------------------------


class RepositoryPort(ABC, Generic[T, ID]):
    """Interface base para repositórios de persistência.

    Define operações CRUD genéricas que todo repositório de entidade
    deve implementar. Implementações concretas residem na camada de
    infraestrutura.
    """

    @abstractmethod
    async def get_by_id(self, entity_id: ID) -> Optional[T]:
        """Busca uma entidade pelo seu identificador único.

        Args:
            entity_id: Identificador único da entidade.

        Returns:
            A entidade encontrada ou None se não existir.
        """
        ...

    @abstractmethod
    async def list_all(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[T]:
        """Lista entidades com paginação.

        Args:
            offset: Número de registros a pular.
            limit: Número máximo de registros a retornar.

        Returns:
            Lista de entidades.
        """
        ...

    @abstractmethod
    async def save(self, entity: T) -> T:
        """Persiste uma entidade (criação ou atualização).

        Args:
            entity: Entidade a ser persistida.

        Returns:
            A entidade persistida com campos atualizados (ex.: id, timestamps).
        """
        ...

    @abstractmethod
    async def delete(self, entity_id: ID) -> bool:
        """Remove uma entidade pelo seu identificador.

        Args:
            entity_id: Identificador único da entidade.

        Returns:
            True se a entidade foi removida, False se não encontrada.
        """
        ...


# ---------------------------------------------------------------------------
# Port para repositório de usuários
# ---------------------------------------------------------------------------


class UserRepositoryPort(RepositoryPort[Any, UUID], ABC):
    """Interface do repositório de usuários.

    Estende o repositório base com operações específicas de busca
    por credenciais e perfil.
    """

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[Any]:
        """Busca um usuário pelo endereço de e-mail.

        Args:
            email: Endereço de e-mail do usuário.

        Returns:
            O usuário encontrado ou None.
        """
        ...

    @abstractmethod
    async def get_by_username(self, username: str) -> Optional[Any]:
        """Busca um usuário pelo nome de usuário.

        Args:
            username: Nome de usuário (login).

        Returns:
            O usuário encontrado ou None.
        """
        ...

    @abstractmethod
    async def exists_by_email(self, email: str) -> bool:
        """Verifica se já existe um usuário com o e-mail informado.

        Args:
            email: Endereço de e-mail a verificar.

        Returns:
            True se o e-mail já está cadastrado.
        """
        ...


# ---------------------------------------------------------------------------
# Port para repositório de documentos
# ---------------------------------------------------------------------------


class DocumentRepositoryPort(RepositoryPort[Any, UUID], ABC):
    """Interface do repositório de documentos jurídicos.

    Estende o repositório base com operações de busca por proprietário
    e filtros específicos do domínio jurídico.
    """

    @abstractmethod
    async def list_by_owner(
        self,
        owner_id: UUID,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Any]:
        """Lista documentos pertencentes a um usuário.

        Args:
            owner_id: Identificador do proprietário.
            offset: Número de registros a pular.
            limit: Número máximo de registros a retornar.

        Returns:
            Lista de documentos do usuário.
        """
        ...

    @abstractmethod
    async def get_by_protocol(self, protocol_number: str) -> Optional[Any]:
        """Busca um documento pelo número de protocolo.

        Args:
            protocol_number: Número de protocolo do documento.

        Returns:
            O documento encontrado ou None.
        """
        ...


# ---------------------------------------------------------------------------
# Port para serviço de autenticação / tokens
# ---------------------------------------------------------------------------


class AuthTokenPort(ABC):
    """Interface para geração e validação de tokens de autenticação (JWT)."""

    @abstractmethod
    def create_access_token(
        self,
        subject: str,
        *,
        extra_claims: Optional[dict[str, Any]] = None,
    ) -> str:
        """Gera um token de acesso JWT.

        Args:
            subject: Identificador do sujeito (geralmente user_id).
            extra_claims: Claims adicionais a incluir no payload.

        Returns:
            Token JWT codificado.
        """
        ...

    @abstractmethod
    def create_refresh_token(self, subject: str) -> str:
        """Gera um token de atualização (refresh token).

        Args:
            subject: Identificador do sujeito.

        Returns:
            Refresh token codificado.
        """
        ...

    @abstractmethod
    def decode_token(self, token: str) -> dict[str, Any]:
        """Decodifica e valida um token JWT.

        Args:
            token: Token JWT a decodificar.

        Returns:
            Payload decodificado do token.

        Raises:
            TokenInvalidError: Se o token for inválido ou expirado.
        """
        ...


# ---------------------------------------------------------------------------
# Port para serviço de hashing de senhas
# ---------------------------------------------------------------------------


class PasswordHasherPort(ABC):
    """Interface para hashing e verificação de senhas."""

    @abstractmethod
    def hash(self, plain_password: str) -> str:
        """Gera o hash de uma senha em texto plano.

        Args:
            plain_password: Senha em texto plano.

        Returns:
            Hash da senha.
        """
        ...

    @abstractmethod
    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Verifica se uma senha corresponde ao hash armazenado.

        Args:
            plain_password: Senha em texto plano fornecida pelo usuário.
            hashed_password: Hash armazenado no banco de dados.

        Returns:
            True se a senha corresponde ao hash.
        """
        ...


# ---------------------------------------------------------------------------
# Port para serviço de IA (Anthropic Claude)
# ---------------------------------------------------------------------------


class AIAnalysisPort(ABC):
    """Interface para o serviço de análise de IA (integração com Anthropic Claude).

    Define operações de análise de documentos jurídicos e interação
    conversacional assistida por IA.
    """

    @abstractmethod
    async def analyze_document(
        self,
        content: str,
        *,
        analysis_type: str,
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Analisa o conteúdo de um documento jurídico via IA.

        Args:
            content: Texto do documento a ser analisado.
            analysis_type: Tipo de análise solicitada (ex.: 'resumo', 'riscos', 'cláusulas').
            context: Contexto adicional para a análise.

        Returns:
            Resultado estruturado da análise.
        """
        ...

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        system_prompt: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> str:
        """Envia mensagens para o assistente de IA e obtém resposta.

        Args:
            messages: Histórico de mensagens da conversa.
            system_prompt: Prompt de sistema para contextualizar o assistente.
            context: Contexto adicional (documentos, metadados).

        Returns:
            Resposta textual do assistente.
        """
        ...


# ---------------------------------------------------------------------------
# Port para armazenamento de arquivos
# ---------------------------------------------------------------------------


class FileStoragePort(ABC):
    """Interface para armazenamento de arquivos (uploads de documentos)."""

    @abstractmethod
    async def upload(
        self,
        file_content: bytes,
        *,
        filename: str,
        content_type: str,
        metadata: Optional[dict[str, str]] = None,
    ) -> str:
        """Faz upload de um arquivo para o armazenamento.

        Args:
            file_content: Conteúdo binário do arquivo.
            filename: Nome do arquivo.
            content_type: Tipo MIME do arquivo.
            metadata: Metadados adicionais.

        Returns:
            Identificador/caminho do arquivo armazenado.
        """
        ...

    @abstractmethod
    async def download(self, file_path: str) -> bytes:
        """Baixa o conteúdo de um arquivo armazenado.

        Args:
            file_path: Identificador/caminho do arquivo.

        Returns:
            Conteúdo binário do arquivo.

        Raises:
            FileNotFoundError: Se o arquivo não existir.
        """
        ...

    @abstractmethod
    async def delete(self, file_path: str) -> bool:
        """Remove um arquivo do armazenamento.

        Args:
            file_path: Identificador/caminho do arquivo.

        Returns:
            True se o arquivo foi removido com sucesso.
        """
        ...

    @abstractmethod
    async def get_url(self, file_path: str, *, expires_in: int = 3600) -> str:
        """Gera uma URL temporária para acesso ao arquivo.

        Args:
            file_path: Identificador/caminho do arquivo.
            expires_in: Tempo de expiração da URL em segundos.

        Returns:
            URL temporária de acesso.
        """
        ...


# ---------------------------------------------------------------------------
# Port para auditoria
# ---------------------------------------------------------------------------


class AuditLogPort(ABC):
    """Interface para registro de eventos de auditoria.

    Garante rastreabilidade de ações no sistema conforme requisitos
    de compliance jurídico.
    """

    @abstractmethod
    async def log_event(
        self,
        *,
        actor_id: UUID,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Registra um evento de auditoria.

        Args:
            actor_id: Identificador do usuário que realizou a ação.
            action: Ação realizada (ex.: 'document.create', 'user.login').
            resource_type: Tipo do recurso afetado.
            resource_id: Identificador do recurso afetado.
            details: Detalhes adicionais do evento.
            ip_address: Endereço IP de origem.
            timestamp: Momento do evento (usa datetime.utcnow() se omitido).
        """
        ...

    @abstractmethod
    async def list_events(
        self,
        *,
        actor_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Lista eventos de auditoria com filtros.

        Args:
            actor_id: Filtrar por usuário.
            resource_type: Filtrar por tipo de recurso.
            resource_id: Filtrar por recurso específico.
            start_date: Data inicial do período.
            end_date: Data final do período.
            offset: Número de registros a pular.
            limit: Número máximo de registros a retornar.

        Returns:
            Lista de eventos de auditoria.
        """
        ...


# ---------------------------------------------------------------------------
# Port para fila de tarefas assíncronas
# ---------------------------------------------------------------------------


class TaskQueuePort(ABC):
    """Interface para enfileiramento de tarefas assíncronas (Celery)."""

    @abstractmethod
    async def enqueue(
        self,
        task_name: str,
        *,
        payload: dict[str, Any],
        queue: Optional[str] = None,
        priority: int = 0,
    ) -> str:
        """Enfileira uma tarefa para processamento assíncrono.

        Args:
            task_name: Nome/identificador da tarefa.
            payload: Dados de entrada da tarefa.
            queue: Fila específica (opcional).
            priority: Prioridade da tarefa (0 = normal).

        Returns:
            Identificador da tarefa enfileirada.
        """
        ...

    @abstractmethod
    async def get_status(self, task_id: str) -> dict[str, Any]:
        """Consulta o status de uma tarefa enfileirada.

        Args:
            task_id: Identificador da tarefa.

        Returns:
            Dicionário com status, resultado e metadados da tarefa.
        """
        ...


# ---------------------------------------------------------------------------
# Port para busca semântica (vetorial)
# ---------------------------------------------------------------------------


class SemanticSearchPort(ABC):
    """Interface para busca semântica em documentos jurídicos.

    Utiliza índice vetorial (FAISS ou Milvus — decisão pendente G002 ADR)
    para busca por similaridade semântica.
    """

    @abstractmethod
    async def index_document(
        self,
        document_id: str,
        content: str,
        *,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Indexa um documento para busca semântica.

        Args:
            document_id: Identificador único do documento.
            content: Conteúdo textual a ser indexado.
            metadata: Metadados associados ao documento.
        """
        ...

    @abstractmethod
    async def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """Realiza busca semântica por similaridade.

        Args:
            query: Texto de consulta.
            top_k: Número máximo de resultados.
            filters: Filtros adicionais de metadados.

        Returns:
            Lista de resultados ordenados por relevância, cada um contendo
            document_id, score e metadados.
        """
        ...

    @abstractmethod
    async def remove_document(self, document_id: str) -> None:
        """Remove um documento do índice semântico.

        Args:
            document_id: Identificador do documento a remover.
        """
        ...


# ---------------------------------------------------------------------------
# Exports públicos
# ---------------------------------------------------------------------------

__all__ = [
    "RepositoryPort",
    "UserRepositoryPort",
    "DocumentRepositoryPort",
    "AuthTokenPort",
    "PasswordHasherPort",
    "AIAnalysisPort",
    "FileStoragePort",
    "AuditLogPort",
    "TaskQueuePort",
    "SemanticSearchPort",
]
