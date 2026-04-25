/// <reference types="vite/client" />

import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';

/**
 * Configuração do Vite para o projeto Automação Jurídica Assistida.
 *
 * Inclui:
 * - Plugin React com Fast Refresh
 * - Proxy reverso para API backend (FastAPI) em desenvolvimento
 * - Aliases de importação para organização do código
 * - Configurações de build otimizadas para produção
 * - Exposição controlada de variáveis de ambiente
 */
export default defineConfig(({ mode }) => {
  /**
   * Carrega variáveis de ambiente com prefixo VITE_
   * Ex: VITE_API_BASE_URL, VITE_APP_TITLE
   */
  const env = loadEnv(mode, process.cwd(), 'VITE_');

  /** URL base da API backend — padrão para desenvolvimento local */
  const apiTarget = env.VITE_API_BASE_URL || 'http://localhost:8000';

  return {
    plugins: [
      /**
       * Plugin oficial React com suporte a Fast Refresh (HMR instantâneo).
       * Utiliza Babel para transformações JSX em desenvolvimento.
       */
      react(),
    ],

    /**
     * Aliases de importação para evitar caminhos relativos profundos.
     * Uso: import { Button } from '@/components/Button'
     *
     * Nota: manter sincronizado com tsconfig.json (paths).
     */
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src'),
        '@components': path.resolve(__dirname, 'src/components'),
        '@pages': path.resolve(__dirname, 'src/pages'),
        '@hooks': path.resolve(__dirname, 'src/hooks'),
        '@services': path.resolve(__dirname, 'src/services'),
        '@utils': path.resolve(__dirname, 'src/utils'),
        '@types': path.resolve(__dirname, 'src/types'),
        '@assets': path.resolve(__dirname, 'src/assets'),
      },
    },

    /**
     * Configuração do servidor de desenvolvimento.
     */
    server: {
      port: 3000,
      strictPort: false,
      open: false,

      /**
       * Proxy reverso para redirecionar chamadas à API backend (FastAPI)
       * durante o desenvolvimento, evitando problemas de CORS.
       *
       * Todas as requisições para /api/* são encaminhadas ao backend.
       */
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
          secure: false,
          /**
           * Rewrite opcional: remove o prefixo /api se o backend
           * não espera esse prefixo nas rotas.
           * Descomentrar a linha abaixo caso necessário:
           */
          // rewrite: (reqPath) => reqPath.replace(/^\/api/, ''),
        },
        /**
         * Proxy para documentação OpenAPI do FastAPI (Swagger/ReDoc)
         * disponível em desenvolvimento para facilitar testes.
         */
        '/docs': {
          target: apiTarget,
          changeOrigin: true,
          secure: false,
        },
        '/redoc': {
          target: apiTarget,
          changeOrigin: true,
          secure: false,
        },
        '/openapi.json': {
          target: apiTarget,
          changeOrigin: true,
          secure: false,
        },
      },

      /**
       * Headers de segurança para o servidor de desenvolvimento.
       * Em produção, esses headers devem ser configurados no Nginx.
       */
      headers: {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
      },
    },

    /**
     * Configuração do servidor de preview (vite preview).
     */
    preview: {
      port: 4173,
      strictPort: false,
    },

    /**
     * Configurações de build para produção.
     */
    build: {
      /** Diretório de saída do build */
      outDir: 'dist',

      /** Gera source maps para depuração em produção (Sentry, etc.) */
      sourcemap: mode === 'production' ? 'hidden' : true,

      /** Target de compatibilidade dos navegadores */
      target: 'es2020',

      /** Limiar de aviso para tamanho de chunks (em kB) */
      chunkSizeWarningLimit: 1000,

      /**
       * Configuração do Rollup para otimização de chunks.
       * Separa dependências pesadas em chunks independentes
       * para melhor cache e carregamento paralelo.
       */
      rollupOptions: {
        output: {
          manualChunks: {
            /** Chunk do React core — raramente muda entre deploys */
            'vendor-react': ['react', 'react-dom'],

            /**
             * Chunk do roteador — separado para lazy loading de rotas.
             * TODO: Adicionar 'react-router-dom' quando instalado.
             */
            // 'vendor-router': ['react-router-dom'],

            /**
             * Chunk de bibliotecas de formulário e validação.
             * TODO: Adicionar quando react-hook-form e zod forem instalados.
             */
            // 'vendor-forms': ['react-hook-form', '@hookform/resolvers', 'zod'],

            /**
             * Chunk do TanStack Query para gerenciamento de estado servidor.
             * TODO: Adicionar quando @tanstack/react-query for instalado.
             */
            // 'vendor-query': ['@tanstack/react-query'],
          },
        },
      },

      /** Minificação com esbuild (padrão do Vite, mais rápido que terser) */
      minify: 'esbuild',

      /** Limpa o diretório de saída antes de cada build */
      emptyOutDir: true,
    },

    /**
     * Configuração de variáveis de ambiente.
     * Apenas variáveis com prefixo VITE_ são expostas ao código cliente.
     * Isso previne vazamento acidental de secrets do servidor.
     */
    envPrefix: 'VITE_',

    /**
     * Configuração de otimização de dependências (pre-bundling).
     * O Vite pré-empacota dependências com esbuild para acelerar o HMR.
     */
    optimizeDeps: {
      include: [
        'react',
        'react-dom',
      ],
      /**
       * Exclui dependências que não devem ser pré-empacotadas.
       * Útil para pacotes que usam import dinâmico ou têm efeitos colaterais.
       */
      exclude: [],
    },

    /**
     * Configuração de CSS.
     */
    css: {
      /**
       * Habilita source maps de CSS em desenvolvimento
       * para facilitar depuração de estilos.
       */
      devSourcemap: true,

      /**
       * Configuração de módulos CSS (caso utilizado além do Tailwind).
       */
      modules: {
        localsConvention: 'camelCaseOnly',
      },
    },

    /**
     * Define constantes globais substituídas em tempo de build.
     * Útil para injetar metadados da aplicação.
     */
    define: {
      __APP_VERSION__: JSON.stringify(process.env.npm_package_version || '0.1.0'),
    },
  };
});
