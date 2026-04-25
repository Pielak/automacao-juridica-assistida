import React, { useState, useCallback } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from '@/components/layout/Sidebar';
import Header from '@/components/layout/Header';

/**
 * Layout principal da aplicação.
 *
 * Compõe a estrutura visual padrão do portal autenticado:
 * - **Sidebar** fixa à esquerda com navegação principal.
 * - **Header** no topo com informações do usuário, breadcrumbs e notificações.
 * - **Área de conteúdo** responsiva que renderiza as rotas filhas via `<Outlet />`.
 *
 * Em telas menores (mobile), a sidebar é recolhida e pode ser alternada
 * por meio de um botão hambúrguer no header.
 */
const MainLayout: React.FC = () => {
  /* -------------------------------------------------------------------------
   * Estado: controle de visibilidade da sidebar em dispositivos móveis
   * ----------------------------------------------------------------------- */
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(false);

  /** Alterna a visibilidade da sidebar (mobile). */
  const handleToggleSidebar = useCallback(() => {
    setSidebarOpen((prev) => !prev);
  }, []);

  /** Fecha a sidebar — útil ao navegar em mobile. */
  const handleCloseSidebar = useCallback(() => {
    setSidebarOpen(false);
  }, []);

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      {/* ---------------------------------------------------------------
       * Overlay escuro visível apenas em mobile quando a sidebar está aberta
       * --------------------------------------------------------------- */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/50 lg:hidden"
          onClick={handleCloseSidebar}
          aria-hidden="true"
        />
      )}

      {/* ---------------------------------------------------------------
       * Sidebar de navegação
       *
       * - Em desktop (lg+): sempre visível, posição estática.
       * - Em mobile (<lg): posição fixa, controlada por `sidebarOpen`.
       * --------------------------------------------------------------- */}
      <aside
        className={[
          'fixed inset-y-0 left-0 z-30 w-64 transform bg-white shadow-lg transition-transform duration-200 ease-in-out',
          'lg:static lg:inset-auto lg:z-auto lg:translate-x-0 lg:shadow-none lg:border-r lg:border-gray-200',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full',
        ].join(' ')}
      >
        <Sidebar />
      </aside>

      {/* ---------------------------------------------------------------
       * Coluna principal: header + conteúdo
       * --------------------------------------------------------------- */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Header com botão de menu mobile */}
        <header className="relative z-10 flex-shrink-0">
          {/* Botão hambúrguer — visível apenas em mobile */}
          <div className="flex items-center lg:hidden">
            <button
              type="button"
              className="ml-3 mt-3 inline-flex items-center justify-center rounded-md p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500"
              onClick={handleToggleSidebar}
              aria-label="Abrir menu de navegação"
              aria-expanded={sidebarOpen}
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-6 w-6"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M4 6h16M4 12h16M4 18h16"
                />
              </svg>
            </button>
          </div>

          <Header />
        </header>

        {/* Área de conteúdo — renderiza rotas filhas */}
        <main
          className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8"
          role="main"
          aria-label="Conteúdo principal"
        >
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default MainLayout;
