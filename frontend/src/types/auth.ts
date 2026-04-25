/**
 * Tipos de autenticação para o módulo de auth do sistema Automação Jurídica Assistida.
 *
 * Define as interfaces e tipos relacionados a autenticação, autorização,
 * credenciais de login, tokens JWT e papéis de usuário (RBAC).
 */

/* ========================================================================== */
/*  Papéis de Usuário (RBAC)                                                  */
/* ========================================================================== */

/**
 * Papéis disponíveis no sistema de controle de acesso baseado em papéis.
 *
 * - `admin` — Administrador do sistema com acesso total.
 * - `lawyer` — Advogado com acesso a funcionalidades jurídicas completas.
 * - `analyst` — Analista jurídico com acesso a consultas e análises.
 * - `intern` — Estagiário com acesso restrito e supervisionado.
 * - `viewer` — Visualizador somente leitura.
 */
export type UserRole = 'admin' | 'lawyer' | 'analyst' | 'intern' | 'viewer';

/** Mapeamento de rótulos legíveis para cada papel de usuário (PT-BR). */
export const USER_ROLE_LABELS: Record<UserRole, string> = {
  admin: 'Administrador',
  lawyer: 'Advogado(a)',
  analyst: 'Analista Jurídico',
  intern: 'Estagiário(a)',
  viewer: 'Visualizador',
} as const;

/* ========================================================================== */
/*  Usuário Autenticado                                                       */
/* ========================================================================== */

/** Representação do usuário autenticado retornado pelo backend. */
export interface AuthUser {
  /** Identificador único do usuário (UUID). */
  readonly id: string;

  /** Nome completo do usuário. */
  readonly fullName: string;

  /** Endereço de e-mail do usuário. */
  readonly email: string;

  /** Papel principal do usuário no sistema. */
  readonly role: UserRole;

  /** Indica se o MFA (autenticação multifator) está habilitado. */
  readonly mfaEnabled: boolean;

  /** URL do avatar do usuário (opcional). */
  readonly avatarUrl?: string;

  /** Data/hora do último login (ISO 8601). */
  readonly lastLoginAt?: string;
}

/* ========================================================================== */
/*  Credenciais e Payloads de Login                                           */
/* ========================================================================== */

/** Credenciais enviadas no formulário de login. */
export interface LoginCredentials {
  /** E-mail do usuário. */
  readonly email: string;

  /** Senha do usuário. */
  readonly password: string;

  /** Indica se o dispositivo deve ser lembrado (sessão estendida). */
  readonly rememberMe?: boolean;
}

/** Payload para verificação do código MFA (TOTP). */
export interface MfaVerificationPayload {
  /** Token temporário recebido após login com credenciais válidas. */
  readonly mfaToken: string;

  /** Código TOTP de 6 dígitos gerado pelo aplicativo autenticador. */
  readonly totpCode: string;
}

/** Payload para solicitação de redefinição de senha. */
export interface PasswordResetRequest {
  /** E-mail do usuário que deseja redefinir a senha. */
  readonly email: string;
}

/** Payload para confirmação de redefinição de senha. */
export interface PasswordResetConfirm {
  /** Token de redefinição recebido por e-mail. */
  readonly resetToken: string;

  /** Nova senha escolhida pelo usuário. */
  readonly newPassword: string;

  /** Confirmação da nova senha. */
  readonly newPasswordConfirm: string;
}

/* ========================================================================== */
/*  Tokens JWT                                                                */
/* ========================================================================== */

/** Par de tokens JWT retornado pelo endpoint de autenticação. */
export interface TokenPair {
  /** Token de acesso (curta duração). */
  readonly accessToken: string;

  /** Token de atualização (longa duração). */
  readonly refreshToken: string;

  /** Tipo do token (geralmente "Bearer"). */
  readonly tokenType: 'Bearer';

  /** Tempo de expiração do access token em segundos. */
  readonly expiresIn: number;
}

/** Payload decodificado do JWT (claims relevantes para o frontend). */
export interface JwtPayload {
  /** Subject — ID do usuário. */
  readonly sub: string;

  /** Papel do usuário. */
  readonly role: UserRole;

  /** Timestamp de emissão (issued at). */
  readonly iat: number;

  /** Timestamp de expiração. */
  readonly exp: number;

  /** Identificador único do token (jti) para revogação. */
  readonly jti: string;
}

/* ========================================================================== */
/*  Estado de Autenticação (Store / Context)                                  */
/* ========================================================================== */

/** Status possíveis do fluxo de autenticação. */
export type AuthStatus =
  | 'idle'
  | 'loading'
  | 'authenticated'
  | 'mfa_required'
  | 'unauthenticated'
  | 'error';

/** Estado global de autenticação gerenciado pelo contexto React. */
export interface AuthState {
  /** Status atual do fluxo de autenticação. */
  readonly status: AuthStatus;

  /** Dados do usuário autenticado (null se não autenticado). */
  readonly user: AuthUser | null;

  /** Par de tokens JWT (null se não autenticado). */
  readonly tokens: TokenPair | null;

  /** Mensagem de erro da última operação de auth (null se sem erro). */
  readonly error: string | null;

  /**
   * Token temporário para fluxo MFA.
   * Preenchido quando `status === 'mfa_required'`.
   */
  readonly mfaToken: string | null;
}

/** Estado inicial padrão para o contexto de autenticação. */
export const INITIAL_AUTH_STATE: AuthState = {
  status: 'idle',
  user: null,
  tokens: null,
  error: null,
  mfaToken: null,
} as const;

/* ========================================================================== */
/*  Respostas da API de Autenticação                                          */
/* ========================================================================== */

/** Resposta do endpoint de login quando MFA não é necessário. */
export interface LoginSuccessResponse {
  readonly user: AuthUser;
  readonly tokens: TokenPair;
}

/** Resposta do endpoint de login quando MFA é obrigatório. */
export interface LoginMfaRequiredResponse {
  /** Indica que o segundo fator é necessário. */
  readonly mfaRequired: true;

  /** Token temporário para completar o fluxo MFA. */
  readonly mfaToken: string;
}

/** União discriminada das possíveis respostas de login. */
export type LoginResponse = LoginSuccessResponse | LoginMfaRequiredResponse;

/** Resposta do endpoint de refresh token. */
export interface RefreshTokenResponse {
  readonly tokens: TokenPair;
}

/* ========================================================================== */
/*  Type Guards                                                               */
/* ========================================================================== */

/**
 * Verifica se a resposta de login requer MFA.
 *
 * @param response - Resposta do endpoint de login.
 * @returns `true` se MFA é necessário.
 */
export function isMfaRequiredResponse(
  response: LoginResponse,
): response is LoginMfaRequiredResponse {
  return 'mfaRequired' in response && response.mfaRequired === true;
}

/**
 * Verifica se uma string é um papel de usuário válido.
 *
 * @param value - Valor a ser verificado.
 * @returns `true` se o valor é um `UserRole` válido.
 */
export function isValidUserRole(value: unknown): value is UserRole {
  return (
    typeof value === 'string' &&
    ['admin', 'lawyer', 'analyst', 'intern', 'viewer'].includes(value)
  );
}
