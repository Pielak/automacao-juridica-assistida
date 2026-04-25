/**
 * Configuração PostCSS para o projeto Automação Jurídica Assistida.
 * Integra Tailwind CSS e autoprefixer para processamento de estilos.
 */
export default {
  plugins: {
    /**
     * Tailwind CSS — sistema de design utilitário responsivo.
     * Processa as diretivas @tailwind e classes utilitárias.
     */
    tailwindcss: {},

    /**
     * Autoprefixer — adiciona prefixos de vendor automaticamente
     * para garantir compatibilidade cross-browser.
     */
    autoprefixer: {},
  },
};
