import type { Config } from 'tailwindcss';
import defaultTheme from 'tailwindcss/defaultTheme';

/**
 * Configuração Tailwind CSS para o projeto Automação Jurídica Assistida.
 *
 * Define design tokens jurídicos incluindo paleta de cores institucional,
 * tipografia formal, breakpoints responsivos e utilitários customizados
 * adequados ao domínio jurídico.
 *
 * @see ADR G005 — Design tokens (cores, tipografia, breakpoints) — PENDENTE envio final.
 * Os valores abaixo são defaults sensatos para o domínio jurídico e devem ser
 * ajustados quando o ADR G005 for finalizado.
 */
const config: Config = {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],

  theme: {
    /**
     * Breakpoints responsivos — abordagem mobile-first.
     * Alinhados com dispositivos comuns usados por profissionais jurídicos
     * (smartphones, tablets em audiências, notebooks e monitores de escritório).
     */
    screens: {
      xs: '375px',
      sm: '640px',
      md: '768px',
      lg: '1024px',
      xl: '1280px',
      '2xl': '1536px',
    },

    extend: {
      /**
       * Paleta de cores institucional — domínio jurídico.
       *
       * - primary: Azul marinho — transmite confiança, autoridade e formalidade.
       * - secondary: Dourado/âmbar — remete à tradição jurídica e distinção.
       * - neutral: Cinzas neutros — para textos, bordas e backgrounds.
       * - success/warning/error/info: Cores semânticas para feedback ao usuário.
       *
       * TODO: Ajustar valores conforme ADR G005 quando finalizado.
       */
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#1e3a5f',
          600: '#1a3353',
          700: '#152b47',
          800: '#11233b',
          900: '#0d1b2f',
          950: '#081222',
        },
        secondary: {
          50: '#fffbeb',
          100: '#fef3c7',
          200: '#fde68a',
          300: '#fcd34d',
          400: '#fbbf24',
          500: '#b8860b',
          600: '#a3770a',
          700: '#8e6809',
          800: '#795908',
          900: '#644a07',
          950: '#4a3705',
        },
        neutral: {
          50: '#fafafa',
          100: '#f5f5f5',
          200: '#e5e5e5',
          300: '#d4d4d4',
          400: '#a3a3a3',
          500: '#737373',
          600: '#525252',
          700: '#404040',
          800: '#262626',
          900: '#171717',
          950: '#0a0a0a',
        },
        success: {
          50: '#f0fdf4',
          100: '#dcfce7',
          500: '#22c55e',
          600: '#16a34a',
          700: '#15803d',
        },
        warning: {
          50: '#fffbeb',
          100: '#fef3c7',
          500: '#f59e0b',
          600: '#d97706',
          700: '#b45309',
        },
        error: {
          50: '#fef2f2',
          100: '#fee2e2',
          500: '#ef4444',
          600: '#dc2626',
          700: '#b91c1c',
        },
        info: {
          50: '#eff6ff',
          100: '#dbeafe',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
        },
        /** Cor de fundo principal da aplicação */
        background: {
          DEFAULT: '#fafafa',
          dark: '#111827',
        },
        /** Cor de superfície para cards e painéis */
        surface: {
          DEFAULT: '#ffffff',
          dark: '#1f2937',
        },
      },

      /**
       * Tipografia — fontes formais adequadas ao contexto jurídico.
       *
       * - sans: Inter — legibilidade em interfaces digitais.
       * - serif: Merriweather — formalidade para documentos e títulos.
       * - mono: JetBrains Mono — exibição de códigos de processo, IDs, etc.
       *
       * TODO: Confirmar fontes finais conforme ADR G005.
       */
      fontFamily: {
        sans: ['Inter', ...defaultTheme.fontFamily.sans],
        serif: ['Merriweather', 'Georgia', ...defaultTheme.fontFamily.serif],
        mono: ['JetBrains Mono', ...defaultTheme.fontFamily.mono],
      },

      /**
       * Escala tipográfica estendida para documentos jurídicos.
       * Inclui tamanhos específicos para cabeçalhos de petições e minutas.
       */
      fontSize: {
        /** Texto muito pequeno — notas de rodapé, disclaimers */
        'xxs': ['0.625rem', { lineHeight: '0.875rem' }],
        /** Texto para corpo de documentos jurídicos — otimizado para leitura prolongada */
        'body': ['0.9375rem', { lineHeight: '1.625rem', letterSpacing: '0.01em' }],
        /** Título de seção de documento */
        'doc-heading': ['1.375rem', { lineHeight: '1.875rem', fontWeight: '700' }],
        /** Título principal de petição/documento */
        'doc-title': ['1.75rem', { lineHeight: '2.25rem', fontWeight: '700' }],
      },

      /**
       * Espaçamentos customizados para layout de documentos jurídicos.
       */
      spacing: {
        '4.5': '1.125rem',
        '13': '3.25rem',
        '15': '3.75rem',
        '18': '4.5rem',
        '88': '22rem',
        '100': '25rem',
        '120': '30rem',
        /** Largura padrão de sidebar de navegação */
        'sidebar': '16rem',
        /** Largura expandida de sidebar */
        'sidebar-expanded': '20rem',
      },

      /**
       * Larguras máximas para containers de conteúdo.
       */
      maxWidth: {
        /** Largura máxima para leitura confortável de documentos jurídicos (~70 caracteres) */
        'prose-legal': '42rem',
        /** Largura máxima do layout principal da aplicação */
        'app': '90rem',
        /** Largura máxima para formulários */
        'form': '36rem',
        /** Largura máxima para modais */
        'modal': '32rem',
        'modal-lg': '48rem',
        'modal-xl': '64rem',
      },

      /**
       * Bordas arredondadas — estilo sóbrio para contexto jurídico.
       */
      borderRadius: {
        /** Borda sutil para cards e containers */
        'subtle': '0.375rem',
        /** Borda para botões e inputs */
        'control': '0.5rem',
        /** Borda para cards principais */
        'card': '0.75rem',
      },

      /**
       * Sombras customizadas — sutis e profissionais.
       */
      boxShadow: {
        'card': '0 1px 3px 0 rgba(0, 0, 0, 0.06), 0 1px 2px -1px rgba(0, 0, 0, 0.06)',
        'card-hover': '0 4px 6px -1px rgba(0, 0, 0, 0.08), 0 2px 4px -2px rgba(0, 0, 0, 0.06)',
        'sidebar': '2px 0 8px -2px rgba(0, 0, 0, 0.08)',
        'modal': '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)',
        'dropdown': '0 4px 12px 0 rgba(0, 0, 0, 0.12)',
        /** Sombra interna para áreas de texto/editor de documentos */
        'inner-subtle': 'inset 0 1px 2px 0 rgba(0, 0, 0, 0.04)',
      },

      /**
       * Animações e transições — sutis para manter profissionalismo.
       */
      transitionDuration: {
        '250': '250ms',
        '350': '350ms',
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-in-out',
        'slide-in-right': 'slideInRight 0.3s ease-out',
        'slide-in-left': 'slideInLeft 0.3s ease-out',
        'slide-up': 'slideUp 0.25s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideInRight: {
          '0%': { transform: 'translateX(100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        slideInLeft: {
          '0%': { transform: 'translateX(-100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },

      /**
       * Z-index padronizados para camadas da aplicação.
       */
      zIndex: {
        'dropdown': '50',
        'sticky': '100',
        'sidebar': '200',
        'modal-backdrop': '300',
        'modal': '400',
        'toast': '500',
        'tooltip': '600',
      },

      /**
       * Aspect ratios para documentos e previews.
       */
      aspectRatio: {
        /** Proporção A4 — para preview de documentos jurídicos */
        'a4': '210 / 297',
      },
    },
  },

  plugins: [
    /**
     * TODO: Avaliar inclusão de plugins oficiais conforme necessidade:
     * - @tailwindcss/forms — estilos base para formulários
     * - @tailwindcss/typography — prose para renderização de documentos
     * - @tailwindcss/container-queries — queries de container para layouts responsivos
     *
     * Instalar com:
     *   npm install -D @tailwindcss/forms @tailwindcss/typography
     *
     * E descomentar abaixo:
     * require('@tailwindcss/forms'),
     * require('@tailwindcss/typography'),
     */
  ],
};

export default config;
