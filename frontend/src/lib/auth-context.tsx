import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useMemo,
} from 'react';
import type { ReactNode } from 'react';
import { apiClient } from '@/lib/api-client';
import type { AxiosError } from 'axios';

/* ---------------------------------------------------------------------------
 * Tipos
 * --------------------------------------------------------------------------- */

/** Representação do usuário autenticado retornado pela API. */
export interface AuthUser {
  id: string;
  email: string;
  name: string;
  /** Papéis RBAC atribuídos ao usuário (ex.: "admin", "advogado", "estagiario"). */
  roles: string[];
  /** URL do avatar, quando disponível. */
  avatarUrl?: string;
}

/** Payload enviado ao endpoint de login. */
export interface LoginCredentials {
  email: string;
  password: string;
  /** Código TOTP para autenticação multifator, quando habilitado. */
  mfaCode?: string;
}

/** Resposta esperada do endpoint POST /auth/login. */
interface LoginResponse {
  access_token: string;
  refresh_token: string;
  user: AuthUser;
}

/** Resposta esperada do endpoint GET /auth/me. */
interface MeResponse {
  user: AuthUser;
}

/** Forma pública do contexto de autenticação. */
export interface AuthContextValue {
  /** Usuário autenticado ou `null` quando não logado. */
  user: AuthUser | null;
  /** Indica se existe um usuário autenticado. */
  isAuthenticated: boolean;
  /** Indica carregamento inicial (verificação de sessão existente). */
  isLoading: boolean;
  /** Mensagem de erro da última operação de autenticação. */
  error: string | null;
  /** Realiza login com credenciais. */
  login: (credentials: LoginCredentials) => Promise<void>;
  /** Encerra a sessão do usuário. */
  logout: () => Promise<void>;
  /** Limpa o estado de erro. */
  clearError: () => void;
}

/* ---------------------------------------------------------------------------
 * Chaves de armazenamento — espelhadas de api-client.ts
 * --------------------------------------------------------------------------- */
const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

/* ---------------------------------------------------------------------------
 * Contexto
 * --------------------------------------------------------------------------- */

const AuthContext = createContext<AuthContextValue | undefined>(undefined);
AuthContext.displayName = 'AuthContext';

/* ---------------------------------------------------------------------------
 * Provider
 * --------------------------------------------------------------------------- */

interface AuthProviderProps {
  children: ReactNode;
}

/**
 * Provider de autenticação da aplicação.
 *
 * Envolve a árvore React e disponibiliza estado do usuário, funções de
 * login/logout e flags auxiliares (`isAuthenticated`, `isLoading`, `error`).
 *
 * Na montagem inicial verifica se já existe um token válido no localStorage
 * e, em caso positivo, recupera os dados do usuário via GET /auth/me.
 *
 * @example
 * ```tsx
 * <AuthProvider>
 *   <App />
 * </AuthProvider>
 * ```
 */
export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  /* -------------------------------------------------------------------------
   * Helpers internos
   * ----------------------------------------------------------------------- */

  /**
   * Persiste os tokens JWT no localStorage.
   * Os interceptors do api-client.ts leem dessas mesmas chaves.
   */
  const storeTokens = useCallback(
    (accessToken: string, refreshToken: string) => {
      localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
      localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    },
    [],
  );

  /** Remove tokens do localStorage. */
  const clearTokens = useCallback(() => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  }, []);

  /**
   * Extrai uma mensagem amigável (PT-BR) a partir de um erro Axios ou genérico.
   */
  const extractErrorMessage = useCallback((err: unknown): string => {
    const axiosErr = err as AxiosError<{ detail?: string }>;
    if (axiosErr?.response?.data?.detail) {
      return axiosErr.response.data.detail;
    }
    if (axiosErr?.response?.status === 401) {
      return 'Credenciais inválidas. Verifique seu e-mail e senha.';
    }
    if (axiosErr?.response?.status === 403) {
      return 'Acesso negado. Você não possui permissão para esta ação.';
    }
    if (axiosErr?.response?.status === 429) {
      return 'Muitas tentativas. Aguarde alguns instantes e tente novamente.';
    }
    if (axiosErr?.message) {
      return axiosErr.message;
    }
    return 'Ocorreu um erro inesperado. Tente novamente mais tarde.';
  }, []);

  /* -------------------------------------------------------------------------
   * Verificação de sessão existente na montagem
   * ----------------------------------------------------------------------- */

  useEffect(() => {
    let cancelled = false;

    async function loadUser() {
      const token = localStorage.getItem(ACCESS_TOKEN_KEY);
      if (!token) {
        setIsLoading(false);
        return;
      }

      try {
        const response = await apiClient.get<MeResponse>('/auth/me');
        if (!cancelled) {
          setUser(response.data.user);
        }
      } catch {
        // Token expirado ou inválido — limpa estado silenciosamente.
        clearTokens();
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    loadUser();

    return () => {
      cancelled = true;
    };
  }, [clearTokens]);

  /* -------------------------------------------------------------------------
   * Login
   * ----------------------------------------------------------------------- */

  /**
   * Autentica o usuário enviando credenciais ao backend.
   *
   * @param credentials — e-mail, senha e código MFA opcional.
   * @throws Propaga o erro após atualizar o estado `error`.
   */
  const login = useCallback(
    async (credentials: LoginCredentials): Promise<void> => {
      setError(null);
      setIsLoading(true);

      try {
        const response = await apiClient.post<LoginResponse>(
          '/auth/login',
          {
            email: credentials.email,
            password: credentials.password,
            ...(credentials.mfaCode ? { mfa_code: credentials.mfaCode } : {}),
          },
        );

        const { access_token, refresh_token, user: loggedUser } = response.data;

        storeTokens(access_token, refresh_token);
        setUser(loggedUser);
      } catch (err) {
        const message = extractErrorMessage(err);
        setError(message);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [storeTokens, extractErrorMessage],
  );

  /* -------------------------------------------------------------------------
   * Logout
   * ----------------------------------------------------------------------- */

  /**
   * Encerra a sessão do usuário.
   *
   * Tenta notificar o backend (POST /auth/logout) para invalidar o refresh
   * token no servidor. Independentemente do resultado, limpa o estado local.
   */
  const logout = useCallback(async (): Promise<void> => {
    try {
      await apiClient.post('/auth/logout');
    } catch {
      // Falha silenciosa — o importante é limpar o estado local.
    } finally {
      clearTokens();
      setUser(null);
      setError(null);
    }
  }, [clearTokens]);

  /* -------------------------------------------------------------------------
   * Limpar erro
   * ----------------------------------------------------------------------- */

  /** Remove a mensagem de erro do estado. */
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  /* -------------------------------------------------------------------------
   * Valor memoizado do contexto
   * ----------------------------------------------------------------------- */

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: user !== null,
      isLoading,
      error,
      login,
      logout,
      clearError,
    }),
    [user, isLoading, error, login, logout, clearError],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/* ---------------------------------------------------------------------------
 * Hook de consumo
 * --------------------------------------------------------------------------- */

/**
 * Hook para acessar o contexto de autenticação.
 *
 * Deve ser utilizado dentro de um `<AuthProvider>`.
 *
 * @returns O valor atual do contexto de autenticação.
 *
 * @example
 * ```tsx
 * function ProfilePage() {
 *   const { user, logout } = useAuth();
 *   return (
 *     <div>
 *       <p>Olá, {user?.name}</p>
 *       <button onClick={logout}>Sair</button>
 *     </div>
 *   );
 * }
 * ```
 */
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);

  if (context === undefined) {
    throw new Error(
      'useAuth deve ser utilizado dentro de um <AuthProvider>. ' +
        'Verifique se o provider envolve a árvore de componentes.',
    );
  }

  return context;
}

export default AuthContext;
