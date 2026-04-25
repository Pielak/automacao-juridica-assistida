import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '@/lib/auth-context';
import type { AuthUser } from '@/lib/auth-context';

/* ---------------------------------------------------------------------------
 * Tipos
 * --------------------------------------------------------------------------- */

/** Propriedades aceitas pelo componente AuthGuard. */
export interface AuthGuardProps {
  /**
   * Lista opcional de roles (papéis RBAC) permitidos para acessar as rotas
   * filhas. Quando omitido, qualquer usuário autenticado tem acesso.
   *
   * Exemplo: `['admin', 'advogado']`
   */
  allowedRoles?: string[];

  /**
   * Rota para redirecionamento quando o usuário não está autenticado.
   * @default '/login'
   */
  loginPath?: string;

  /**
   * Rota para redirecionamento quando o usuário está autenticado mas não
   * possui a role necessária.
   * @default '/acesso-negado'
   */
  unauthorizedPath?: string;

  /**
   * Elemento filho opcional. Quando não fornecido, renderiza `<Outlet />`
   * para compor com o React Router v6.
   */
  children?: React.ReactNode;
}

/* ---------------------------------------------------------------------------
 * Helpers
 * --------------------------------------------------------------------------- */

/**
 * Verifica se o usuário possui ao menos uma das roles exigidas.
 *
 * @param user - Usuário autenticado.
 * @param allowedRoles - Roles permitidas para a rota.
 * @returns `true` se o usuário possui pelo menos uma role permitida.
 */
function hasRequiredRole(user: AuthUser, allowedRoles: string[]): boolean {
  if (!allowedRoles || allowedRoles.length === 0) {
    return true;
  }

  // `user.roles` é um array de strings conforme definido em AuthUser
  return user.roles?.some((role) => allowedRoles.includes(role)) ?? false;
}

/* ---------------------------------------------------------------------------
 * Componente
 * --------------------------------------------------------------------------- */

/**
 * Guard de rota para o React Router v6.
 *
 * Responsabilidades:
 * 1. Redireciona para a página de login caso o usuário não esteja autenticado.
 * 2. Redireciona para a página de acesso negado caso o usuário não possua
 *    as roles (papéis RBAC) necessárias.
 * 3. Preserva a localização original via `state.from` para que o login
 *    possa redirecionar de volta após autenticação bem-sucedida.
 *
 * @example
 * ```tsx
 * <Route element={<AuthGuard allowedRoles={['admin']} />}>
 *   <Route path="/painel" element={<Painel />} />
 * </Route>
 * ```
 */
export const AuthGuard: React.FC<AuthGuardProps> = ({
  allowedRoles,
  loginPath = '/login',
  unauthorizedPath = '/acesso-negado',
  children,
}) => {
  const { user, isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  /* -------------------------------------------------------------------------
   * Estado de carregamento
   *
   * Enquanto o contexto de autenticação ainda está verificando o token
   * (ex.: refresh silencioso), exibimos um indicador de carregamento para
   * evitar flashes de redirecionamento indevido.
   * ----------------------------------------------------------------------- */
  if (isLoading) {
    return (
      <div
        role="status"
        aria-label="Verificando autenticação"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
        }}
      >
        {/* TODO: Substituir por componente de loading do design system quando disponível */}
        <span>Verificando autenticação…</span>
      </div>
    );
  }

  /* -------------------------------------------------------------------------
   * Usuário não autenticado → redireciona para login
   *
   * Preservamos a localização atual em `state.from` para que a página de
   * login possa redirecionar o usuário de volta após autenticação.
   * ----------------------------------------------------------------------- */
  if (!isAuthenticated || !user) {
    return <Navigate to={loginPath} state={{ from: location }} replace />;
  }

  /* -------------------------------------------------------------------------
   * Usuário autenticado mas sem role necessária → acesso negado
   * ----------------------------------------------------------------------- */
  if (allowedRoles && allowedRoles.length > 0 && !hasRequiredRole(user, allowedRoles)) {
    return <Navigate to={unauthorizedPath} state={{ from: location }} replace />;
  }

  /* -------------------------------------------------------------------------
   * Usuário autenticado e autorizado → renderiza conteúdo protegido
   * ----------------------------------------------------------------------- */
  return <>{children ?? <Outlet />}</>;
};

export default AuthGuard;
