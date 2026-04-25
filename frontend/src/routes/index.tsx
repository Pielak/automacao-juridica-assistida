import React, { lazy, Suspense } from 'react';
import {
  createBrowserRouter,
  RouterProvider,
  Navigate,
  type RouteObject,
} from 'react-router-dom';

import { AuthGuard } from '@/routes/AuthGuard';

/* ---------------------------------------------------------------------------
 * Lazy-loaded pages
 * Cada página é carregada sob demanda para reduzir o bundle inicial.
 * --------------------------------------------------------------------------- */

/** Página de login (pública). */
const LoginPage = lazy(() => import('@/pages/LoginPage'));

/** Dashboard principal (autenticado). */
const DashboardPage = lazy(() => import('@/pages/DashboardPage'));

/** Página de análises IA (autenticado). */
const AnalysisPage = lazy(() => import('@/pages/AnalysisPage'));

/** Página de chat com assistente jurídico (autenticado). */
const ChatPage = lazy(() => import('@/pages/ChatPage'));

/** Página de auditoria — restrita a administradores. */
const AuditPage = lazy(() => import('@/pages/AuditPage'));

/* ---------------------------------------------------------------------------
 * Componente de fallback para Suspense
 * --------------------------------------------------------------------------- */

/**
 * Spinner / indicador de carregamento exibido enquanto as páginas
 * lazy-loaded estão sendo baixadas.
 */
function LoadingFallback(): React.ReactElement {
  return (
    <div
      role="status"
      aria-label="Carregando página"
      className="flex min-h-screen items-center justify-center"
    >
      <div className="flex flex-col items-center gap-3">
        {/* Spinner simples via Tailwind */}
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-gray-300 border-t-blue-600" />
        <span className="text-sm text-gray-500">Carregando…</span>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------------------
 * Wrapper utilitário — envolve página lazy em Suspense
 * --------------------------------------------------------------------------- */

/**
 * Envolve um componente lazy-loaded em `React.Suspense` com o fallback
 * padrão de carregamento.
 *
 * @param Component - Componente React lazy-loaded.
 * @returns Elemento JSX com Suspense.
 */
function withSuspense(Component: React.LazyExoticComponent<React.ComponentType<unknown>>): React.ReactNode {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <Component />
    </Suspense>
  );
}

/* ---------------------------------------------------------------------------
 * Definição de rotas
 * --------------------------------------------------------------------------- */

/**
 * Árvore de rotas da aplicação.
 *
 * Estrutura:
 * - `/login`        → Página pública de autenticação.
 * - `/`             → Rotas protegidas por AuthGuard (qualquer usuário autenticado).
 *   - `/`           → Redireciona para `/dashboard`.
 *   - `/dashboard`  → Painel principal.
 *   - `/analysis`   → Análises IA.
 *   - `/chat`       → Chat com assistente jurídico.
 * - `/admin`        → Rotas protegidas por AuthGuard com role "admin".
 *   - `/admin/audit`→ Trilha de auditoria.
 * - `*`             → Redireciona para `/dashboard` (fallback).
 */
const routes: RouteObject[] = [
  /* -------------------------------------------------------------------------
   * Rotas públicas
   * ----------------------------------------------------------------------- */
  {
    path: '/login',
    element: withSuspense(LoginPage),
  },

  /* -------------------------------------------------------------------------
   * Rotas protegidas — qualquer usuário autenticado
   * ----------------------------------------------------------------------- */
  {
    element: <AuthGuard />,
    children: [
      {
        path: '/',
        element: <Navigate to="/dashboard" replace />,
      },
      {
        path: '/dashboard',
        element: withSuspense(DashboardPage),
      },
      {
        path: '/analysis',
        element: withSuspense(AnalysisPage),
      },
      {
        path: '/analysis/:analysisId',
        element: withSuspense(AnalysisPage),
      },
      {
        path: '/chat',
        element: withSuspense(ChatPage),
      },
      {
        path: '/chat/:sessionId',
        element: withSuspense(ChatPage),
      },
    ],
  },

  /* -------------------------------------------------------------------------
   * Rotas protegidas — somente administradores (RBAC)
   * ----------------------------------------------------------------------- */
  {
    element: <AuthGuard allowedRoles={['admin']} />,
    children: [
      {
        path: '/admin/audit',
        element: withSuspense(AuditPage),
      },
      // TODO: Adicionar outras rotas administrativas conforme módulos forem criados
      // (ex.: /admin/users, /admin/settings)
    ],
  },

  /* -------------------------------------------------------------------------
   * Fallback — redireciona rotas desconhecidas para o dashboard
   * ----------------------------------------------------------------------- */
  {
    path: '*',
    element: <Navigate to="/dashboard" replace />,
  },
];

/* ---------------------------------------------------------------------------
 * Router instance
 * --------------------------------------------------------------------------- */

/**
 * Instância do router criada via `createBrowserRouter`.
 * Utiliza a API de dados do React Router v6.4+ para suporte futuro a loaders
 * e actions caso necessário.
 */
const router = createBrowserRouter(routes);

/* ---------------------------------------------------------------------------
 * Componente exportado
 * --------------------------------------------------------------------------- */

/**
 * Componente raiz de roteamento da aplicação.
 *
 * Deve ser renderizado dentro do `AuthProvider` (contexto de autenticação)
 * para que o `AuthGuard` funcione corretamente.
 *
 * @example
 * ```tsx
 * import { AppRouter } from '@/routes';
 * import { AuthProvider } from '@/lib/auth-context';
 *
 * function App() {
 *   return (
 *     <AuthProvider>
 *       <AppRouter />
 *     </AuthProvider>
 *   );
 * }
 * ```
 */
export function AppRouter(): React.ReactElement {
  return <RouterProvider router={router} />;
}

export default AppRouter;
export { routes };
