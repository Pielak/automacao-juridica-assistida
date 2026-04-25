import { QueryClient, QueryCache, MutationCache } from '@tanstack/react-query';
import type { DefaultOptions } from '@tanstack/react-query';

/**
 * Verifica se o erro é um erro de autenticação (401) para tratamento global.
 * @param error - Erro capturado pelo TanStack Query.
 * @returns `true` se o erro indica sessão expirada ou não autenticada.
 */
function isUnauthorizedError(error: unknown): boolean {
  if (
    error !== null &&
    typeof error === 'object' &&
    'status' in error &&
    (error as { status: number }).status === 401
  ) {
    return true;
  }

  // Compatibilidade com erros Axios
  if (
    error !== null &&
    typeof error === 'object' &&
    'response' in error &&
    typeof (error as Record<string, unknown>).response === 'object' &&
    (error as { response: { status: number } }).response?.status === 401
  ) {
    return true;
  }

  return false;
}

/**
 * Tratamento global de erros para queries e mutations.
 * Redireciona para login em caso de sessão expirada (401).
 * @param error - Erro capturado.
 */
function handleGlobalError(error: unknown): void {
  if (isUnauthorizedError(error)) {
    // Limpa dados de autenticação e redireciona para login
    // Evita loops verificando se já está na página de login
    if (!window.location.pathname.includes('/login')) {
      // TODO: Integrar com o módulo de auth para limpar tokens do storage
      window.location.href = '/login?reason=session_expired';
    }
    return;
  }

  // Log estruturado de erros não tratados para observabilidade
  console.error('[QueryClient] Erro não tratado na requisição:', error);
}

/**
 * Determina se uma query com falha deve ser retentada.
 * Não retenta erros de autenticação (401), autorização (403) ou validação (400, 422).
 * @param failureCount - Número de tentativas já realizadas.
 * @param error - Erro da tentativa atual.
 * @returns `true` se a query deve ser retentada.
 */
function shouldRetryQuery(failureCount: number, error: unknown): boolean {
  const MAX_RETRIES = 3;

  // Não retenta erros de cliente (4xx)
  const nonRetryableStatuses = [400, 401, 403, 404, 409, 422];

  let status: number | undefined;

  if (error !== null && typeof error === 'object') {
    if ('status' in error) {
      status = (error as { status: number }).status;
    } else if (
      'response' in error &&
      typeof (error as Record<string, unknown>).response === 'object'
    ) {
      status = (error as { response: { status: number } }).response?.status;
    }
  }

  if (status !== undefined && nonRetryableStatuses.includes(status)) {
    return false;
  }

  return failureCount < MAX_RETRIES;
}

/**
 * Configurações padrão para todas as queries e mutations do TanStack Query.
 *
 * - `staleTime`: 2 minutos — dados são considerados frescos por este período,
 *   reduzindo requisições desnecessárias ao backend.
 * - `gcTime` (antigo cacheTime): 5 minutos — tempo que dados inativos
 *   permanecem em cache antes de serem coletados.
 * - `refetchOnWindowFocus`: desabilitado para evitar requisições excessivas
 *   em contexto jurídico onde o usuário alterna entre abas frequentemente.
 * - `retry`: lógica customizada que não retenta erros de cliente (4xx).
 */
const defaultOptions: DefaultOptions = {
  queries: {
    staleTime: 2 * 60 * 1000, // 2 minutos
    gcTime: 5 * 60 * 1000, // 5 minutos
    refetchOnWindowFocus: false,
    refetchOnReconnect: true,
    retry: shouldRetryQuery,
    retryDelay: (attemptIndex: number) =>
      Math.min(1000 * 2 ** attemptIndex, 15000), // Backoff exponencial, máx 15s
  },
  mutations: {
    retry: false, // Mutations não são retentadas por padrão (operações de escrita)
  },
};

/**
 * Cache de queries com tratamento global de erros.
 * Captura erros de todas as queries para logging e redirecionamento.
 */
const queryCache = new QueryCache({
  onError: (error, query) => {
    // Só loga erros de queries que já tinham dados em cache (refetch falhou)
    // para não poluir logs com erros de carregamento inicial
    if (query.state.data !== undefined) {
      console.warn(
        `[QueryClient] Falha ao atualizar dados da query [${String(query.queryKey)}]:`,
        error
      );
    }
    handleGlobalError(error);
  },
});

/**
 * Cache de mutations com tratamento global de erros.
 * Captura erros de todas as mutations para logging centralizado.
 */
const mutationCache = new MutationCache({
  onError: (error) => {
    handleGlobalError(error);
  },
});

/**
 * Instância singleton do QueryClient configurada para o projeto
 * Automação Jurídica Assistida.
 *
 * Configurações otimizadas para o domínio jurídico:
 * - Cache conservador para garantir dados atualizados em documentos legais
 * - Retry inteligente que não retenta erros de validação ou autenticação
 * - Tratamento global de sessão expirada com redirecionamento
 * - Backoff exponencial para resiliência contra falhas temporárias
 *
 * @example
 * ```tsx
 * import { QueryClientProvider } from '@tanstack/react-query';
 * import { queryClient } from '@/lib/query-client';
 *
 * function App() {
 *   return (
 *     <QueryClientProvider client={queryClient}>
 *       <RouterProvider router={router} />
 *     </QueryClientProvider>
 *   );
 * }
 * ```
 */
export const queryClient = new QueryClient({
  queryCache,
  mutationCache,
  defaultOptions,
});

export default queryClient;
