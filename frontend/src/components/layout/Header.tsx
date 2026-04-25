import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '@/lib/auth-context';
import type { AuthUser } from '@/lib/auth-context';

/* ---------------------------------------------------------------------------
 * Tipos auxiliares
 * --------------------------------------------------------------------------- */

/** Item de breadcrumb derivado da rota atual. */
interface BreadcrumbItem {
  label: string;
  path: string;
}

/** Notificação exibida no dropdown de notificações. */
export interface HeaderNotification {
  id: string;
  title: string;
  message: string;
  read: boolean;
  createdAt: string;
}

/* ---------------------------------------------------------------------------
 * Constantes
 * --------------------------------------------------------------------------- */

/** Mapeamento de segmentos de rota para rótulos legíveis em PT-BR. */
const ROUTE_LABELS: Record<string, string> = {
  '': 'Início',
  dashboard: 'Painel',
  documents: 'Documentos',
  analysis: 'Análises',
  chat: 'Assistente',
  users: 'Usuários',
  settings: 'Configurações',
  profile: 'Perfil',
  audit: 'Auditoria',
};

/* ---------------------------------------------------------------------------
 * Helpers
 * --------------------------------------------------------------------------- */

/**
 * Gera a lista de breadcrumbs a partir do pathname atual.
 * @param pathname - pathname do react-router (ex.: "/documents/123")
 * @returns Lista de BreadcrumbItem ordenada da raiz ao segmento atual.
 */
function buildBreadcrumbs(pathname: string): BreadcrumbItem[] {
  const segments = pathname.split('/').filter(Boolean);
  const crumbs: BreadcrumbItem[] = [
    { label: 'Início', path: '/' },
  ];

  let accumulated = '';
  for (const segment of segments) {
    accumulated += `/${segment}`;
    const label =
      ROUTE_LABELS[segment] ?? segment.charAt(0).toUpperCase() + segment.slice(1);
    crumbs.push({ label, path: accumulated });
  }

  return crumbs;
}

/**
 * Retorna as iniciais do nome do usuário (até 2 caracteres).
 * @param name - Nome completo do usuário.
 */
function getInitials(name: string): string {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join('');
}

/* ---------------------------------------------------------------------------
 * Sub-componentes internos
 * --------------------------------------------------------------------------- */

/** Ícone de sino para notificações (SVG inline para evitar dependência externa). */
function BellIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </svg>
  );
}

/** Ícone de chevron para baixo. */
function ChevronDownIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

/** Ícone de chevron para direita (separador de breadcrumb). */
function ChevronRightIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <polyline points="9 18 15 12 9 6" />
    </svg>
  );
}

/* ---------------------------------------------------------------------------
 * Hook: clique fora do elemento
 * --------------------------------------------------------------------------- */

function useClickOutside(
  ref: React.RefObject<HTMLElement | null>,
  handler: () => void,
) {
  useEffect(() => {
    function listener(event: MouseEvent | TouchEvent) {
      if (!ref.current || ref.current.contains(event.target as Node)) {
        return;
      }
      handler();
    }
    document.addEventListener('mousedown', listener);
    document.addEventListener('touchstart', listener);
    return () => {
      document.removeEventListener('mousedown', listener);
      document.removeEventListener('touchstart', listener);
    };
  }, [ref, handler]);
}

/* ---------------------------------------------------------------------------
 * Componente principal: Header
 * --------------------------------------------------------------------------- */

export interface HeaderProps {
  /** Notificações a exibir no dropdown. Caso não fornecidas, o sino fica oculto. */
  notifications?: HeaderNotification[];
  /** Callback ao marcar notificação como lida. */
  onNotificationRead?: (id: string) => void;
  /** Callback ao clicar em "Ver todas" notificações. */
  onViewAllNotifications?: () => void;
}

/**
 * Header principal da aplicação.
 *
 * Exibe logotipo, breadcrumb baseado na rota atual, dropdown de notificações
 * e dropdown do usuário autenticado (perfil e logout).
 */
export function Header({
  notifications = [],
  onNotificationRead,
  onViewAllNotifications,
}: HeaderProps) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  /* --- Estado dos dropdowns --- */
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [notifMenuOpen, setNotifMenuOpen] = useState(false);

  const userMenuRef = useRef<HTMLDivElement>(null);
  const notifMenuRef = useRef<HTMLDivElement>(null);

  useClickOutside(userMenuRef, () => setUserMenuOpen(false));
  useClickOutside(notifMenuRef, () => setNotifMenuOpen(false));

  /* --- Breadcrumbs --- */
  const breadcrumbs = buildBreadcrumbs(location.pathname);

  /* --- Contagem de não-lidas --- */
  const unreadCount = notifications.filter((n) => !n.read).length;

  /* --- Handlers --- */
  const handleLogout = useCallback(async () => {
    setUserMenuOpen(false);
    await logout();
    navigate('/login');
  }, [logout, navigate]);

  const handleProfileClick = useCallback(() => {
    setUserMenuOpen(false);
    navigate('/profile');
  }, [navigate]);

  const handleNotificationClick = useCallback(
    (id: string) => {
      onNotificationRead?.(id);
    },
    [onNotificationRead],
  );

  /* --- Render --- */
  return (
    <header
      className="sticky top-0 z-30 flex h-16 w-full items-center justify-between border-b border-gray-200 bg-white px-4 shadow-sm dark:border-gray-700 dark:bg-gray-900 md:px-6"
      role="banner"
    >
      {/* ---- Lado esquerdo: Logo + Breadcrumb ---- */}
      <div className="flex items-center gap-4">
        {/* Logo */}
        <Link
          to="/"
          className="flex items-center gap-2 text-lg font-bold text-blue-700 dark:text-blue-400"
          aria-label="Ir para a página inicial"
        >
          {/* TODO: Substituir pelo componente de logo real quando design tokens forem definidos (G005 ADR) */}
          <span aria-hidden="true" className="text-2xl">⚖️</span>
          <span className="hidden sm:inline">Automação Jurídica</span>
        </Link>

        {/* Separador vertical */}
        <div className="hidden h-6 w-px bg-gray-300 dark:bg-gray-600 md:block" />

        {/* Breadcrumb */}
        <nav aria-label="Breadcrumb" className="hidden md:block">
          <ol className="flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400">
            {breadcrumbs.map((crumb, index) => {
              const isLast = index === breadcrumbs.length - 1;
              return (
                <li key={crumb.path} className="flex items-center gap-1">
                  {index > 0 && (
                    <ChevronRightIcon className="text-gray-400 dark:text-gray-500" />
                  )}
                  {isLast ? (
                    <span
                      className="font-medium text-gray-800 dark:text-gray-200"
                      aria-current="page"
                    >
                      {crumb.label}
                    </span>
                  ) : (
                    <Link
                      to={crumb.path}
                      className="transition-colors hover:text-blue-600 dark:hover:text-blue-400"
                    >
                      {crumb.label}
                    </Link>
                  )}
                </li>
              );
            })}
          </ol>
        </nav>
      </div>

      {/* ---- Lado direito: Notificações + User dropdown ---- */}
      <div className="flex items-center gap-2">
        {/* --- Notificações --- */}
        {notifications.length > 0 && (
          <div ref={notifMenuRef} className="relative">
            <button
              type="button"
              className="relative rounded-full p-2 text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200"
              aria-label={`Notificações${unreadCount > 0 ? ` (${unreadCount} não lidas)` : ''}`}
              aria-expanded={notifMenuOpen}
              aria-haspopup="true"
              onClick={() => setNotifMenuOpen((prev) => !prev)}
            >
              <BellIcon />
              {unreadCount > 0 && (
                <span className="absolute right-1 top-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </button>

            {notifMenuOpen && (
              <div
                className="absolute right-0 mt-2 w-80 rounded-lg border border-gray-200 bg-white shadow-lg dark:border-gray-700 dark:bg-gray-800"
                role="menu"
                aria-label="Notificações"
              >
                <div className="border-b border-gray-200 px-4 py-3 dark:border-gray-700">
                  <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200">
                    Notificações
                  </h3>
                </div>
                <ul className="max-h-72 overflow-y-auto">
                  {notifications.slice(0, 10).map((notif) => (
                    <li key={notif.id}>
                      <button
                        type="button"
                        className={`w-full px-4 py-3 text-left transition-colors hover:bg-gray-50 dark:hover:bg-gray-700 ${
                          !notif.read
                            ? 'bg-blue-50 dark:bg-blue-900/20'
                            : ''
                        }`}
                        role="menuitem"
                        onClick={() => handleNotificationClick(notif.id)}
                      >
                        <p className="text-sm font-medium text-gray-800 dark:text-gray-200">
                          {notif.title}
                        </p>
                        <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
                          {notif.message}
                        </p>
                      </button>
                    </li>
                  ))}
                </ul>
                {onViewAllNotifications && (
                  <div className="border-t border-gray-200 px-4 py-2 dark:border-gray-700">
                    <button
                      type="button"
                      className="w-full text-center text-sm font-medium text-blue-600 transition-colors hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                      onClick={() => {
                        setNotifMenuOpen(false);
                        onViewAllNotifications();
                      }}
                    >
                      Ver todas as notificações
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* --- User dropdown --- */}
        {user && (
          <div ref={userMenuRef} className="relative">
            <button
              type="button"
              className="flex items-center gap-2 rounded-lg p-1.5 text-sm transition-colors hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:hover:bg-gray-800"
              aria-label="Menu do usuário"
              aria-expanded={userMenuOpen}
              aria-haspopup="true"
              onClick={() => setUserMenuOpen((prev) => !prev)}
            >
              {/* Avatar com iniciais */}
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">
                {getInitials(user.name)}
              </span>
              <span className="hidden max-w-[120px] truncate text-gray-700 dark:text-gray-300 md:block">
                {user.name}
              </span>
              <ChevronDownIcon className="hidden text-gray-400 md:block" />
            </button>

            {userMenuOpen && (
              <div
                className="absolute right-0 mt-2 w-56 rounded-lg border border-gray-200 bg-white py-1 shadow-lg dark:border-gray-700 dark:bg-gray-800"
                role="menu"
                aria-label="Opções do usuário"
              >
                {/* Informações do usuário */}
                <div className="border-b border-gray-200 px-4 py-3 dark:border-gray-700">
                  <p className="text-sm font-medium text-gray-800 dark:text-gray-200">
                    {user.name}
                  </p>
                  <p className="truncate text-xs text-gray-500 dark:text-gray-400">
                    {user.email}
                  </p>
                </div>

                {/* Opções */}
                <button
                  type="button"
                  className="flex w-full items-center gap-2 px-4 py-2 text-left text-sm text-gray-700 transition-colors hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
                  role="menuitem"
                  onClick={handleProfileClick}
                >
                  Meu Perfil
                </button>

                {/* TODO: Adicionar link para configurações quando a rota estiver disponível */}

                <div className="border-t border-gray-200 dark:border-gray-700" />

                <button
                  type="button"
                  className="flex w-full items-center gap-2 px-4 py-2 text-left text-sm text-red-600 transition-colors hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
                  role="menuitem"
                  onClick={handleLogout}
                >
                  Sair
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </header>
  );
}

export default Header;
