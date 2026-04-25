import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import {
  useChat,
  useChatSessions,
  useCreateSession,
  useSendMessage,
  useDeleteSession,
  type ChatSession,
  type ChatMessage,
} from '../hooks/useChat';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';

/* ---------------------------------------------------------------------------
 * Schema de validação para envio de mensagem
 * --------------------------------------------------------------------------- */

const messageSchema = z.object({
  content: z
    .string()
    .min(1, 'A mensagem não pode estar vazia.')
    .max(4000, 'A mensagem deve ter no máximo 4000 caracteres.'),
});

type MessageFormData = z.infer<typeof messageSchema>;

/* ---------------------------------------------------------------------------
 * Schema de validação para criação de sessão
 * --------------------------------------------------------------------------- */

const newSessionSchema = z.object({
  title: z
    .string()
    .min(1, 'Informe um título para a sessão.')
    .max(120, 'O título deve ter no máximo 120 caracteres.'),
});

type NewSessionFormData = z.infer<typeof newSessionSchema>;

/* ---------------------------------------------------------------------------
 * Componente auxiliar: Item de sessão na barra lateral
 * --------------------------------------------------------------------------- */

interface SessionItemProps {
  session: ChatSession;
  isActive: boolean;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  isDeleting: boolean;
}

/**
 * Renderiza um item de sessão de chat na barra lateral.
 * Destaca a sessão ativa e permite exclusão.
 */
const SessionItem: React.FC<SessionItemProps> = ({
  session,
  isActive,
  onSelect,
  onDelete,
  isDeleting,
}) => {
  return (
    <li
      role="button"
      tabIndex={0}
      aria-current={isActive ? 'true' : undefined}
      className={`flex items-center justify-between gap-2 rounded-md px-3 py-2 text-sm cursor-pointer transition-colors ${
        isActive
          ? 'bg-blue-100 text-blue-900 font-medium'
          : 'hover:bg-gray-100 text-gray-700'
      }`}
      onClick={() => onSelect(session.id)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect(session.id);
        }
      }}
    >
      <span className="truncate flex-1" title={session.title}>
        {session.title}
      </span>
      <button
        type="button"
        aria-label={`Excluir sessão ${session.title}`}
        disabled={isDeleting}
        className="shrink-0 text-gray-400 hover:text-red-600 transition-colors disabled:opacity-50"
        onClick={(e) => {
          e.stopPropagation();
          onDelete(session.id);
        }}
      >
        ✕
      </button>
    </li>
  );
};

/* ---------------------------------------------------------------------------
 * Componente auxiliar: Bolha de mensagem
 * --------------------------------------------------------------------------- */

interface MessageBubbleProps {
  message: ChatMessage;
}

/**
 * Renderiza uma bolha de mensagem no painel de conversa.
 * Diferencia visualmente mensagens do usuário e da IA.
 */
const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <div
      className={`flex w-full ${
        isUser ? 'justify-end' : 'justify-start'
      } mb-3`}
    >
      <div
        className={`max-w-[75%] rounded-lg px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
          isUser
            ? 'bg-blue-600 text-white rounded-br-none'
            : 'bg-gray-100 text-gray-900 rounded-bl-none'
        }`}
      >
        {message.content}
        {message.created_at && (
          <span
            className={`block mt-1 text-xs ${
              isUser ? 'text-blue-200' : 'text-gray-400'
            }`}
          >
            {new Date(message.created_at).toLocaleTimeString('pt-BR', {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </span>
        )}
      </div>
    </div>
  );
};

/* ---------------------------------------------------------------------------
 * Componente auxiliar: Indicador de digitação da IA
 * --------------------------------------------------------------------------- */

const TypingIndicator: React.FC = () => (
  <div className="flex justify-start mb-3">
    <div className="bg-gray-100 rounded-lg rounded-bl-none px-4 py-3 flex items-center gap-1">
      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
    </div>
  </div>
);

/* ---------------------------------------------------------------------------
 * Página principal: ChatPage
 * --------------------------------------------------------------------------- */

/**
 * Página de Chat com IA Jurídica.
 *
 * Funcionalidades:
 * - Listagem e gerenciamento de sessões de conversa na barra lateral
 * - Interface conversacional com histórico de mensagens
 * - Envio de mensagens com validação
 * - Indicador de carregamento enquanto a IA responde
 * - Contexto do caso vinculado à sessão (quando disponível)
 */
const ChatPage: React.FC = () => {
  /* ---- Estado local ---- */
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [showNewSessionForm, setShowNewSessionForm] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  /* ---- Ref para auto-scroll ---- */
  const messagesEndRef = useRef<HTMLDivElement>(null);

  /* ---- Hooks de dados (useChat) ---- */
  const {
    data: sessions,
    isLoading: isLoadingSessions,
    isError: isSessionsError,
  } = useChatSessions();

  const {
    data: activeChat,
    isLoading: isLoadingChat,
  } = useChat(activeSessionId ?? '');

  const createSessionMutation = useCreateSession();
  const sendMessageMutation = useSendMessage();
  const deleteSessionMutation = useDeleteSession();

  /* ---- Formulário de mensagem ---- */
  const {
    register: registerMessage,
    handleSubmit: handleSubmitMessage,
    reset: resetMessageForm,
    formState: { errors: messageErrors },
  } = useForm<MessageFormData>({
    resolver: zodResolver(messageSchema),
    defaultValues: { content: '' },
  });

  /* ---- Formulário de nova sessão ---- */
  const {
    register: registerSession,
    handleSubmit: handleSubmitSession,
    reset: resetSessionForm,
    formState: { errors: sessionErrors },
  } = useForm<NewSessionFormData>({
    resolver: zodResolver(newSessionSchema),
    defaultValues: { title: '' },
  });

  /* ---- Auto-scroll ao receber novas mensagens ---- */
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [activeChat, scrollToBottom]);

  /* ---- Selecionar primeira sessão automaticamente ---- */
  useEffect(() => {
    if (!activeSessionId && sessions && sessions.length > 0) {
      setActiveSessionId(sessions[0].id);
    }
  }, [sessions, activeSessionId]);

  /* ---- Handlers ---- */

  /** Envia uma mensagem na sessão ativa. */
  const onSendMessage = useCallback(
    (data: MessageFormData) => {
      if (!activeSessionId) return;

      sendMessageMutation.mutate(
        { sessionId: activeSessionId, content: data.content },
        {
          onSuccess: () => {
            resetMessageForm();
          },
        },
      );
    },
    [activeSessionId, sendMessageMutation, resetMessageForm],
  );

  /** Cria uma nova sessão de chat. */
  const onCreateSession = useCallback(
    (data: NewSessionFormData) => {
      createSessionMutation.mutate(
        { title: data.title },
        {
          onSuccess: (newSession) => {
            // TODO: O tipo de retorno depende da implementação do hook useCreateSession.
            // Assumimos que retorna um objeto com `id`.
            if (newSession && typeof newSession === 'object' && 'id' in newSession) {
              setActiveSessionId((newSession as ChatSession).id);
            }
            resetSessionForm();
            setShowNewSessionForm(false);
          },
        },
      );
    },
    [createSessionMutation, resetSessionForm],
  );

  /** Exclui uma sessão de chat. */
  const onDeleteSession = useCallback(
    (sessionId: string) => {
      if (!window.confirm('Tem certeza que deseja excluir esta sessão?')) return;

      deleteSessionMutation.mutate(
        { sessionId },
        {
          onSuccess: () => {
            if (activeSessionId === sessionId) {
              setActiveSessionId(null);
            }
          },
        },
      );
    },
    [activeSessionId, deleteSessionMutation],
  );

  /** Atalho de teclado: Ctrl+Enter para enviar. */
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        handleSubmitMessage(onSendMessage)();
      }
    },
    [handleSubmitMessage, onSendMessage],
  );

  /* ---- Dados derivados ---- */
  const messages: ChatMessage[] = activeChat?.messages ?? [];
  const isAiResponding = sendMessageMutation.isPending;

  /* ---- Renderização ---- */
  return (
    <div className="flex h-full min-h-0 bg-white">
      {/* ================================================================
       * Barra lateral — Sessões de chat
       * ================================================================ */}
      <aside
        className={`${
          sidebarOpen ? 'w-72' : 'w-0'
        } shrink-0 border-r border-gray-200 bg-gray-50 transition-all duration-200 overflow-hidden flex flex-col`}
      >
        {/* Cabeçalho da sidebar */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
          <h2 className="text-sm font-semibold text-gray-800">Sessões</h2>
          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowNewSessionForm((prev) => !prev)}
            aria-label="Nova sessão de chat"
          >
            + Nova
          </Button>
        </div>

        {/* Formulário de nova sessão */}
        {showNewSessionForm && (
          <form
            onSubmit={handleSubmitSession(onCreateSession)}
            className="px-4 py-3 border-b border-gray-200 space-y-2"
          >
            <Input
              {...registerSession('title')}
              label="Título da sessão"
              placeholder="Ex.: Análise contrato de locação"
              error={sessionErrors.title}
              autoFocus
            />
            <div className="flex gap-2">
              <Button
                type="submit"
                variant="primary"
                size="sm"
                loading={createSessionMutation.isPending}
              >
                Criar
              </Button>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => {
                  setShowNewSessionForm(false);
                  resetSessionForm();
                }}
              >
                Cancelar
              </Button>
            </div>
          </form>
        )}

        {/* Lista de sessões */}
        <nav className="flex-1 overflow-y-auto px-2 py-2" aria-label="Sessões de chat">
          {isLoadingSessions && (
            <p className="text-xs text-gray-500 text-center py-4">
              Carregando sessões…
            </p>
          )}

          {isSessionsError && (
            <p className="text-xs text-red-500 text-center py-4">
              Erro ao carregar sessões. Tente novamente.
            </p>
          )}

          {!isLoadingSessions && sessions && sessions.length === 0 && (
            <p className="text-xs text-gray-400 text-center py-4">
              Nenhuma sessão encontrada. Crie uma nova para começar.
            </p>
          )}

          {sessions && sessions.length > 0 && (
            <ul className="space-y-1">
              {sessions.map((session) => (
                <SessionItem
                  key={session.id}
                  session={session}
                  isActive={session.id === activeSessionId}
                  onSelect={setActiveSessionId}
                  onDelete={onDeleteSession}
                  isDeleting={
                    deleteSessionMutation.isPending &&
                    // TODO: Verificar variável de sessão sendo excluída se o hook suportar
                    false
                  }
                />
              ))}
            </ul>
          )}
        </nav>
      </aside>

      {/* ================================================================
       * Painel principal — Conversa
       * ================================================================ */}
      <main className="flex flex-1 flex-col min-w-0">
        {/* Barra superior do chat */}
        <header className="flex items-center gap-3 px-4 py-3 border-b border-gray-200 bg-white shrink-0">
          <button
            type="button"
            className="text-gray-500 hover:text-gray-800 transition-colors lg:hidden"
            onClick={() => setSidebarOpen((prev) => !prev)}
            aria-label={sidebarOpen ? 'Fechar barra lateral' : 'Abrir barra lateral'}
          >
            ☰
          </button>

          {activeSessionId && activeChat ? (
            <div className="flex-1 min-w-0">
              <h1 className="text-base font-semibold text-gray-900 truncate">
                {activeChat.title ?? 'Conversa'}
              </h1>
              {/* TODO: Exibir contexto do caso vinculado (case_id, número do processo, etc.) */}
              {activeChat.case_context && (
                <p className="text-xs text-gray-500 truncate">
                  Caso: {activeChat.case_context}
                </p>
              )}
            </div>
          ) : (
            <h1 className="text-base font-semibold text-gray-500">
              Chat IA Jurídica
            </h1>
          )}
        </header>

        {/* Área de mensagens */}
        <div className="flex-1 overflow-y-auto px-4 py-4">
          {!activeSessionId && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center space-y-2">
                <p className="text-gray-400 text-lg">💬</p>
                <p className="text-gray-500 text-sm">
                  Selecione ou crie uma sessão para iniciar a conversa.
                </p>
              </div>
            </div>
          )}

          {activeSessionId && isLoadingChat && (
            <div className="flex items-center justify-center h-full">
              <p className="text-gray-400 text-sm">Carregando conversa…</p>
            </div>
          )}

          {activeSessionId && !isLoadingChat && messages.length === 0 && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center space-y-2">
                <p className="text-gray-400 text-lg">🤖</p>
                <p className="text-gray-500 text-sm">
                  Nenhuma mensagem ainda. Envie sua primeira pergunta jurídica.
                </p>
              </div>
            </div>
          )}

          {messages.length > 0 && (
            <div className="max-w-3xl mx-auto">
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
              {isAiResponding && <TypingIndicator />}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Formulário de envio de mensagem */}
        {activeSessionId && (
          <footer className="shrink-0 border-t border-gray-200 bg-white px-4 py-3">
            <form
              onSubmit={handleSubmitMessage(onSendMessage)}
              className="max-w-3xl mx-auto flex gap-3 items-end"
            >
              <div className="flex-1">
                <textarea
                  {...registerMessage('content')}
                  rows={2}
                  placeholder="Digite sua mensagem… (Ctrl+Enter para enviar)"
                  className={`w-full resize-none rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 transition-colors ${
                    messageErrors.content
                      ? 'border-red-400 focus:ring-red-300'
                      : 'border-gray-300 focus:ring-blue-300 focus:border-blue-400'
                  }`}
                  disabled={isAiResponding}
                  onKeyDown={handleKeyDown}
                  aria-label="Mensagem para a IA"
                />
                {messageErrors.content && (
                  <p className="mt-1 text-xs text-red-500">
                    {messageErrors.content.message}
                  </p>
                )}
              </div>
              <Button
                type="submit"
                variant="primary"
                size="md"
                loading={isAiResponding}
                disabled={isAiResponding}
              >
                Enviar
              </Button>
            </form>
            <p className="max-w-3xl mx-auto mt-1 text-xs text-gray-400">
              A IA pode cometer erros. Verifique informações jurídicas importantes.
            </p>
          </footer>
        )}
      </main>
    </div>
  );
};

export default ChatPage;
