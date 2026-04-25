import React from 'react';
import ReactDOM from 'react-dom/client';

import App from '@/App';

/**
 * Entry-point da aplicação React.
 *
 * Responsabilidades:
 * - Localiza o elemento raiz no DOM (`#root`).
 * - Renderiza a árvore React em modo `StrictMode` para detecção
 *   antecipada de problemas em desenvolvimento.
 * - Delega ao componente `<App />` toda a configuração de providers
 *   (QueryClientProvider, RouterProvider, ErrorBoundary, etc.).
 */

const rootElement = document.getElementById('root');

if (!rootElement) {
  throw new Error(
    '[main] Elemento raiz (#root) não encontrado no DOM. ' +
      'Verifique se o arquivo index.html contém <div id="root"></div>.',
  );
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
