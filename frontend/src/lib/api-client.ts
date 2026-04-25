import axios from 'axios';
import type { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';

/**
 * URL base da API backend.
 * Utiliza variável de ambiente do Vite; fallback para localhost em desenvolvimento.
 */
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1';

/** Chaves utilizadas para armazenar tokens no localStorage. */
const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

/* ---------------------------------------------------------------------------
 * Helpers de token
 * -------------------------------------------------------------------------*/

/**
 * Recupera o access token armazenado.
 * @returns Token JWT ou `null` caso não exista.
 */
export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

/**
 * Recupera o refresh token armazenado.
 * @returns Refresh token ou `null` caso não exista.
 */
export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

/**
 * Persiste os tokens de autenticação no localStorage.
 * @param accessToken - JWT de acesso.
 * @param refreshToken - Token de renovação.
 */
export function setTokens(accessToken: string, refreshToken: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

/**
 * Remove todos os tokens de autenticação do localStorage.
 * Utilizado no logout ou quando o refresh falha.
 */
export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

/* ---------------------------------------------------------------------------
 * Instância Axios
 * -------------------------------------------------------------------------*/

/**
 * Instância Axios pré-configurada para comunicação com a API backend.
 *
 * Funcionalidades:
 * - `baseURL` apontando para a API (configurável via env).
 * - Interceptor de request que anexa o header `Authorization: Bearer <token>`.
 * - Interceptor de response que tenta refresh automático em caso de 401.
 * - Timeout padrão de 30 segundos.
 */
const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30_000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

/* ---------------------------------------------------------------------------
 * Interceptor de Request — anexa JWT
 * -------------------------------------------------------------------------*/

apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getAccessToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => Promise.reject(error),
);

/* ---------------------------------------------------------------------------
 * Interceptor de Response — refresh automático em 401
 * -------------------------------------------------------------------------*/

/**
 * Flag que evita múltiplas tentativas simultâneas de refresh.
 * Quando `true`, uma renovação já está em andamento.
 */
let isRefreshing = false;

/**
 * Fila de callbacks de requests que falharam com 401 enquanto o refresh
 * estava em andamento. São resolvidos/rejeitados após a conclusão do refresh.
 */
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}> = [];

/**
 * Processa a fila de requests pendentes após o resultado do refresh.
 * @param error - Erro caso o refresh tenha falhado; `null` em caso de sucesso.
 * @param token - Novo access token em caso de sucesso.
 */
function processQueue(error: unknown, token: string | null = null): void {
  failedQueue.forEach((promise) => {
    if (error) {
      promise.reject(error);
    } else if (token) {
      promise.resolve(token);
    }
  });
  failedQueue = [];
}

/** Interface esperada da resposta do endpoint de refresh. */
interface RefreshResponse {
  access_token: string;
  refresh_token: string;
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    // Só tenta refresh para 401 e quando não é uma retentativa
    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error);
    }

    // Se a própria request de refresh falhou, limpa tokens e redireciona
    if (originalRequest.url?.includes('/auth/refresh')) {
      clearTokens();
      window.location.href = '/login';
      return Promise.reject(error);
    }

    // Se já existe um refresh em andamento, enfileira a request
    if (isRefreshing) {
      return new Promise<string>((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      }).then((newToken) => {
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
        }
        return apiClient(originalRequest);
      });
    }

    originalRequest._retry = true;
    isRefreshing = true;

    const refreshToken = getRefreshToken();

    if (!refreshToken) {
      clearTokens();
      isRefreshing = false;
      processQueue(new Error('Refresh token não encontrado.'));
      window.location.href = '/login';
      return Promise.reject(error);
    }

    try {
      // Usa axios puro (sem interceptors) para evitar loop infinito
      const { data } = await axios.post<RefreshResponse>(
        `${BASE_URL}/auth/refresh`,
        { refresh_token: refreshToken },
        {
          headers: { 'Content-Type': 'application/json' },
        },
      );

      const { access_token: newAccessToken, refresh_token: newRefreshToken } = data;

      setTokens(newAccessToken, newRefreshToken);
      processQueue(null, newAccessToken);

      if (originalRequest.headers) {
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
      }

      return apiClient(originalRequest);
    } catch (refreshError) {
      processQueue(refreshError);
      clearTokens();
      window.location.href = '/login';
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  },
);

export default apiClient;
