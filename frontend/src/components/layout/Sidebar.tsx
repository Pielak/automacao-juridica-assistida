import React from 'react';
import { NavLink } from 'react-router-dom';

/**
 * Definição de um item de navegação da sidebar.
 */
interface NavItem {
  /** Rótulo exibido no link */
  label: string;
  /** Caminho da rota (React Router) */
  path: string;
  /** Ícone SVG inline representando o item */
  icon: React.ReactNode;
}

/**
 * Lista de itens de navegação principal da aplicação.
 * Cada item corresponde a um módulo funcional do sistema.
 */
const NAV_ITEMS: NavItem[] = [
  {
    label: 'Dashboard',
    path: '/dashboard',
    icon: (
      <svg
        xmlns="http://www.w3.org/2000/svg"
        className="h-5 w-5"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <rect x="3" y="3" width="7" height="7" />
        <rect x="14" y="3" width="7" height="7" />
        <rect x="3" y="14" width="7" height="7" />
        <rect x="14" y="14" width="7" height="7" />
      </svg>
    ),
  },
  {
    label: 'Processos',
    path: '/processos',
    icon: (
      <svg
        xmlns="http://www.w3.org/2000/svg"
        className="h-5 w-5"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
      </svg>
    ),
  },
  {
    label: 'Documentos',
    path: '/documentos',
    icon: (
      <svg
        xmlns="http://www.w3.org/2000/svg"
        className="h-5 w-5"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
        <polyline points="10 9 9 9 8 9" />
      </svg>
    ),
  },
  {
    label: 'Análises',
    path: '/analises',
    icon: (
      <svg
        xmlns="http://www.w3.org/2000/svg"
        className="h-5 w-5"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <line x1="18" y1="20" x2="18" y2="10" />
        <line x1="12" y1="20" x2="12" y2="4" />
        <line x1="6" y1="20" x2="6" y2="14" />
      </svg>
    ),
  },
  {
    label: 'Chat',
    path: '/chat',
    icon: (
      <svg
        xmlns="http://www.w3.org/2000/svg"
        className="h-5 w-5"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    ),
  },
  {
    label: 'Auditoria',
    path: '/auditoria',
    icon: (
      <svg
        xmlns="http://www.w3.org/2000/svg"
        className="h-5 w-5"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      </svg>
    ),
  },
];

/** Props do componente Sidebar */
interface SidebarProps {
  /** Indica se a sidebar está colapsada (modo compacto) */
  collapsed?: boolean;
  /** Callback disparado ao solicitar toggle de colapso */
  onToggleCollapse?: () => void;
}

/**
 * Sidebar — Componente de navegação lateral principal da aplicação.
 *
 * Exibe links para os módulos: Dashboard, Processos, Documentos, Análises, Chat e Auditoria.
 * Suporta modo colapsado (apenas ícones) e expandido (ícones + rótulos).
 * Utiliza `NavLink` do React Router v6 para destacar a rota ativa.
 *
 * @example
 * ```tsx
 * <Sidebar collapsed={false} onToggleCollapse={() => setCollapsed(prev => !prev)} />
 * ```
 */
export const Sidebar: React.FC<SidebarProps> = ({
  collapsed = false,
  onToggleCollapse,
}) => {
  /**
   * Retorna as classes CSS para o NavLink com base no estado ativo.
   * Utiliza Tailwind CSS para estilização.
   */
  const getLinkClassName = ({ isActive }: { isActive: boolean }): string => {
    const baseClasses =
      'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500';

    if (isActive) {
      return `${baseClasses} bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300`;
    }

    return `${baseClasses} text-gray-600 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200`;
  };

  return (
    <aside
      className={`flex h-full flex-col border-r border-gray-200 bg-white transition-all duration-300 dark:border-gray-700 dark:bg-gray-900 ${
        collapsed ? 'w-16' : 'w-64'
      }`}
      role="navigation"
      aria-label="Navegação principal"
    >
      {/* Cabeçalho da sidebar */}
      <div className="flex h-16 items-center justify-between border-b border-gray-200 px-4 dark:border-gray-700">
        {!collapsed && (
          <span className="text-lg font-bold text-gray-800 dark:text-gray-100">
            Jurídico
          </span>
        )}
        {onToggleCollapse && (
          <button
            type="button"
            onClick={onToggleCollapse}
            className={`rounded-md p-1.5 text-gray-500 hover:bg-gray-100 hover:text-gray-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200 ${
              collapsed ? 'mx-auto' : ''
            }`}
            aria-label={collapsed ? 'Expandir menu lateral' : 'Recolher menu lateral'}
            title={collapsed ? 'Expandir menu lateral' : 'Recolher menu lateral'}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className={`h-5 w-5 transition-transform duration-200 ${
                collapsed ? 'rotate-180' : ''
              }`}
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="15 18 9 12 15 6" />
            </svg>
          </button>
        )}
      </div>

      {/* Links de navegação */}
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <ul className="flex flex-col gap-1" role="list">
          {NAV_ITEMS.map((item) => (
            <li key={item.path}>
              <NavLink
                to={item.path}
                className={getLinkClassName}
                title={collapsed ? item.label : undefined}
                end={item.path === '/dashboard'}
              >
                <span className="flex-shrink-0" aria-hidden="true">
                  {item.icon}
                </span>
                {!collapsed && <span>{item.label}</span>}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* Rodapé da sidebar */}
      <div className="border-t border-gray-200 px-3 py-3 dark:border-gray-700">
        {!collapsed && (
          <p className="text-xs text-gray-400 dark:text-gray-500">
            Automação Jurídica Assistida
          </p>
        )}
      </div>
    </aside>
  );
};

export default Sidebar;
