import React, { Component, type ErrorInfo, type ReactNode } from 'react';
import { RouterProvider } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { router } from '@/routes/index';

/* ---------------------------------------------------------------------------
 * Query Client — configuração global do TanStack Query
 * --------------------------------------------------------------------------- */

/**
 * Instância global do QueryClient.
 *
 * - `staleTime`: dados são considerados frescos por 2 minutos.
 * - `retry`: até 1 tentativa automática em caso de falha.
 * - `refetchOnWindowFocus`: desabilitado para evitar chamadas excessivas
 *   em contextos jurídicos onde o usuário alterna entre abas frequentemente.
 */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 2,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

/* ---------------------------------------------------------------------------
 * Error Boundary Global
 * --------------------------------------------------------------------------- */

interface ErrorBoundaryProps {
  /** Elementos filhos a serem renderizados. */
  children: ReactNode;
}

interface ErrorBoundaryState {
  /** Indica se um erro foi capturado. */
  hasError: boolean;
  /** Mensagem do erro capturado, se houver. */
  errorMessage: string | null;
}

/**
 * Componente de Error Boundary global.
 *
 * Captura erros não tratados na árvore de componentes React e exibe
 * uma tela de fallback amigável, evitando que a aplicação inteira quebre
 * sem feedback ao usuário.
 */
class GlobalErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, errorMessage: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, errorMessage: error.message };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // TODO: Integrar com serviço de monitoramento de erros (ex.: Sentry)
    console.error('[GlobalErrorBoundary] Erro não tratado capturado:', error, errorInfo);
  }

  /**
   * Reinicia o estado do error boundary, permitindo que o usuário
   * tente novamente sem recarregar a página inteira.
   */
  private handleReset = (): void => {
    this.setState({ hasError: false, errorMessage: null });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div
          role="alert"
          className="flex min-h-screen flex-col items-center justify-center bg-gray-50 px-4 text-center"
        >
          <div className="max-w-md rounded-lg bg-white p-8 shadow-lg">
            <h1 className="mb-4 text-2xl font-bold text-red-600">
              Algo deu errado
            </h1>
            <p className="mb-2 text-gray-700">
              Ocorreu um erro inesperado na aplicação. Por favor, tente novamente.
            </p>
            {this.state.errorMessage && (
              <p className="mb-6 rounded bg-red-50 p-3 text-sm text-red-500">
                {this.state.errorMessage}
              </p>
            )}
            <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
              <button
                type="button"
                onClick={this.handleReset}
                className="rounded-md bg-blue-600 px-6 py-2 text-white transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              >
                Tentar novamente
              </button>
              <button
                type="button"
                onClick={() => window.location.assign('/')}
                className="rounded-md border border-gray-300 bg-white px-6 py-2 text-gray-700 transition-colors hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              >
                Voltar ao início
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

/* ---------------------------------------------------------------------------
 * Componente App — raiz da aplicação
 * --------------------------------------------------------------------------- */

/**
 * Componente raiz da aplicação **Automação Jurídica Assistida**.
 *
 * Responsabilidades:
 * - Prover o **Error Boundary global** para captura de erros não tratados.
 * - Prover o **QueryClientProvider** (TanStack Query) para gerenciamento
 *   de estado servidor e cache.
 * - Montar o **RouterProvider** com as rotas definidas em `@/routes/index`.
 *
 * A árvore de providers segue a ordem:
 * `ErrorBoundary → QueryClientProvider → RouterProvider`
 */
const App: React.FC = () => {
  return (
    <GlobalErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </GlobalErrorBoundary>
  );
};

export default App;
