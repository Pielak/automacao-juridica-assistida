import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { UseMutationOptions } from '@tanstack/react-query';
import { apiClient } from '../lib/api-client';

/* ---------------------------------------------------------------------------
 * Tipos
 * --------------------------------------------------------------------------- */

/** Representa uma sessão de chat (conversa) com a IA. */
export interface ChatSession {
  /** Identificador único da sessão. */
  id: string;
  /** Título resumido da sessão (gerado automaticamente ou pelo usuário). */
  title: string;
  /** ID do documento jurídico associado, se houver. */
  document_id?: string | null;
  /** Data/hora de criação (ISO 8601). */
  created_at: string;
  /** Data/hora da última mensagem (ISO 8601). */
  updated_at: string;
}

/** Papel do autor da mensagem. */
export type MessageRole = 'user' | 'assistant' | 'system';

/** Representa uma mensagem individual dentro de uma sessão de chat. */
export interface ChatMessage {
  /** Identificador único da mensagem. */
  id: string;
  /** ID da sessão à qual a mensagem pertence. */
  session_id: string;
  /** Papel do autor. */
  role: MessageRole;
  /** Conteúdo textual da mensagem. */
  content: string;
  /** Data/hora de criação (ISO 8601). */
  created_at: string;
}

/** Payload para envio de uma nova mensagem ao backend. */
export interface SendMessagePayload {
  /** ID da sessão de chat. */
  session_id: string;
  /** Conteúdo da mensagem do usuário. */
  content: string;
  /** ID de documento para contextualizar a análise (opcional). */
  document_id?: string | null;
}

/** Resposta do backend ao enviar uma mensagem (inclui a resposta da IA). */
export interface SendMessageResponse {
  /** Mensagem do usuário persistida. */
  user_message: ChatMessage;
  /** Mensagem de resposta da IA. */
  assistant_message: ChatMessage;
}

/** Payload para criação de uma nova sessão de chat. */
export interface CreateSessionPayload {
  /** Título inicial da sessão (opcional — backend pode gerar). */
  title?: string;
  /** ID do documento jurídico associado (opcional). */
  document_id?: string | null;
}

/** Resposta paginada genérica retornada pelo backend. */
interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

/* ---------------------------------------------------------------------------
 * Chaves de cache do TanStack Query
 * --------------------------------------------------------------------------- */

export const chatKeys = {
  /** Raiz de todas as queries de chat. */
  all: ['chat'] as const,
  /** Lista de sessões do usuário. */
  sessions: () => [...chatKeys.all, 'sessions'] as const,
  /** Histórico de mensagens de uma sessão específica. */
  history: (sessionId: string) => [...chatKeys.all, 'history', sessionId] as const,
} as const;

/* ---------------------------------------------------------------------------
 * Funções de acesso à API
 * --------------------------------------------------------------------------- */

/**
 * Busca todas as sessões de chat do usuário autenticado.
 * @returns Lista paginada de sessões.
 */
async function fetchChatSessions(): Promise<PaginatedResponse<ChatSession>> {
  const response = await apiClient.get<PaginatedResponse<ChatSession>>('/chat/sessions');
  return response.data;
}

/**
 * Busca o histórico de mensagens de uma sessão de chat.
 * @param sessionId - Identificador da sessão.
 * @returns Lista paginada de mensagens ordenadas cronologicamente.
 */
async function fetchChatHistory(sessionId: string): Promise<PaginatedResponse<ChatMessage>> {
  const response = await apiClient.get<PaginatedResponse<ChatMessage>>(
    `/chat/sessions/${sessionId}/messages`,
  );
  return response.data;
}

/**
 * Envia uma mensagem do usuário e recebe a resposta da IA.
 * @param payload - Dados da mensagem.
 * @returns Mensagem do usuário e resposta da IA.
 */
async function sendMessage(payload: SendMessagePayload): Promise<SendMessageResponse> {
  const response = await apiClient.post<SendMessageResponse>(
    `/chat/sessions/${payload.session_id}/messages`,
    {
      content: payload.content,
      document_id: payload.document_id ?? null,
    },
  );
  return response.data;
}

/**
 * Cria uma nova sessão de chat.
 * @param payload - Dados iniciais da sessão.
 * @returns Sessão criada.
 */
async function createSession(payload: CreateSessionPayload): Promise<ChatSession> {
  const response = await apiClient.post<ChatSession>('/chat/sessions', payload);
  return response.data;
}

/* ---------------------------------------------------------------------------
 * Hooks — TanStack Query
 * --------------------------------------------------------------------------- */

/**
 * Hook para listar as sessões de chat do usuário autenticado.
 *
 * Utiliza cache com staleTime de 30 s para evitar requisições desnecessárias
 * enquanto o usuário navega entre telas.
 *
 * @example
 * ```tsx
 * const { data, isLoading } = useChatSessions();
 * ```
 */
export function useChatSessions() {
  return useQuery({
    queryKey: chatKeys.sessions(),
    queryFn: fetchChatSessions,
    staleTime: 30_000,
    refetchOnWindowFocus: true,
  });
}

/**
 * Hook para obter o histórico de mensagens de uma sessão de chat.
 *
 * A query só é habilitada quando `sessionId` é fornecido (não-vazio).
 * Realiza polling a cada 10 s para manter o histórico atualizado caso
 * haja processamento assíncrono no backend.
 *
 * @param sessionId - Identificador da sessão de chat.
 *
 * @example
 * ```tsx
 * const { data, isLoading } = useChatHistory(sessionId);
 * ```
 */
export function useChatHistory(sessionId: string | undefined) {
  return useQuery({
    queryKey: chatKeys.history(sessionId ?? ''),
    queryFn: () => fetchChatHistory(sessionId!),
    enabled: Boolean(sessionId),
    staleTime: 5_000,
    refetchInterval: 10_000,
  });
}

/**
 * Hook (mutation) para enviar uma mensagem ao chat e receber a resposta da IA.
 *
 * Após sucesso, invalida automaticamente o cache do histórico da sessão
 * correspondente para que a UI reflita as novas mensagens.
 *
 * @param options - Opções adicionais do TanStack Query mutation (onSuccess, onError, etc.).
 *
 * @example
 * ```tsx
 * const sendMsg = useSendMessage();
 * sendMsg.mutate({ session_id: '...', content: 'Analise este contrato.' });
 * ```
 */
export function useSendMessage(
  options?: Omit<
    UseMutationOptions<SendMessageResponse, Error, SendMessagePayload>,
    'mutationFn'
  >,
) {
  const queryClient = useQueryClient();

  return useMutation<SendMessageResponse, Error, SendMessagePayload>({
    mutationFn: sendMessage,
    onSuccess: (data, variables, context) => {
      // Invalida o cache do histórico para forçar refetch com as novas mensagens.
      queryClient.invalidateQueries({
        queryKey: chatKeys.history(variables.session_id),
      });

      // Atualiza a lista de sessões (updated_at pode ter mudado).
      queryClient.invalidateQueries({
        queryKey: chatKeys.sessions(),
      });

      // Repassa ao callback do consumidor, se fornecido.
      options?.onSuccess?.(data, variables, context);
    },
    onError: options?.onError,
    onSettled: options?.onSettled,
    ...options,
  });
}

/**
 * Hook (mutation) para criar uma nova sessão de chat.
 *
 * Após sucesso, invalida o cache da lista de sessões.
 *
 * @param options - Opções adicionais do TanStack Query mutation.
 *
 * @example
 * ```tsx
 * const create = useCreateChatSession();
 * create.mutate({ title: 'Análise de contrato' });
 * ```
 */
export function useCreateChatSession(
  options?: Omit<
    UseMutationOptions<ChatSession, Error, CreateSessionPayload>,
    'mutationFn'
  >,
) {
  const queryClient = useQueryClient();

  return useMutation<ChatSession, Error, CreateSessionPayload>({
    mutationFn: createSession,
    onSuccess: (data, variables, context) => {
      // Invalida a lista de sessões para incluir a recém-criada.
      queryClient.invalidateQueries({
        queryKey: chatKeys.sessions(),
      });

      options?.onSuccess?.(data, variables, context);
    },
    onError: options?.onError,
    onSettled: options?.onSettled,
    ...options,
  });
}
