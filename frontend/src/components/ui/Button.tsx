import React from 'react';

/** Variantes visuais disponíveis para o botão */
type ButtonVariant = 'primary' | 'secondary' | 'danger';

/** Tamanhos disponíveis para o botão */
type ButtonSize = 'sm' | 'md' | 'lg';

/**
 * Props do componente Button reutilizável.
 * Estende as props nativas de <button> do HTML.
 */
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Variante visual do botão */
  variant?: ButtonVariant;
  /** Tamanho do botão */
  size?: ButtonSize;
  /** Indica estado de carregamento — desabilita o botão e exibe spinner */
  loading?: boolean;
  /** Ícone opcional renderizado antes do texto */
  leftIcon?: React.ReactNode;
  /** Ícone opcional renderizado após o texto */
  rightIcon?: React.ReactNode;
  /** Se true, o botão ocupa 100% da largura do container pai */
  fullWidth?: boolean;
}

/**
 * Classes base compartilhadas por todas as variantes.
 * Utiliza Tailwind CSS conforme stack definida.
 */
const baseClasses =
  'inline-flex items-center justify-center font-medium rounded-lg transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed';

/**
 * Mapa de classes Tailwind por variante visual.
 */
const variantClasses: Record<ButtonVariant, string> = {
  primary:
    'bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800 focus:ring-blue-500',
  secondary:
    'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50 active:bg-gray-100 focus:ring-gray-400',
  danger:
    'bg-red-600 text-white hover:bg-red-700 active:bg-red-800 focus:ring-red-500',
};

/**
 * Mapa de classes Tailwind por tamanho.
 */
const sizeClasses: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-sm gap-1.5',
  md: 'px-4 py-2 text-base gap-2',
  lg: 'px-6 py-3 text-lg gap-2.5',
};

/**
 * Componente Spinner interno para estado de carregamento.
 * Renderiza um ícone SVG animado com rotação.
 */
const Spinner: React.FC<{ className?: string }> = ({ className = '' }) => (
  <svg
    className={`animate-spin h-4 w-4 ${className}`}
    xmlns="http://www.w3.org/2000/svg"
    fill="none"
    viewBox="0 0 24 24"
    aria-hidden="true"
  >
    <circle
      className="opacity-25"
      cx="12"
      cy="12"
      r="10"
      stroke="currentColor"
      strokeWidth="4"
    />
    <path
      className="opacity-75"
      fill="currentColor"
      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
    />
  </svg>
);

/**
 * Componente Button reutilizável para a aplicação de Automação Jurídica.
 *
 * Suporta três variantes visuais (primary, secondary, danger), três tamanhos
 * (sm, md, lg), estado de carregamento com spinner, ícones laterais e
 * largura total opcional.
 *
 * @example
 * ```tsx
 * <Button variant="primary" loading={isSubmitting}>
 *   Salvar documento
 * </Button>
 *
 * <Button variant="danger" onClick={handleDelete}>
 *   Excluir
 * </Button>
 * ```
 */
export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      loading = false,
      leftIcon,
      rightIcon,
      fullWidth = false,
      disabled,
      children,
      className = '',
      type = 'button',
      ...rest
    },
    ref
  ) => {
    const isDisabled = disabled || loading;

    const combinedClasses = [
      baseClasses,
      variantClasses[variant],
      sizeClasses[size],
      fullWidth ? 'w-full' : '',
      className,
    ]
      .filter(Boolean)
      .join(' ');

    return (
      <button
        ref={ref}
        type={type}
        disabled={isDisabled}
        className={combinedClasses}
        aria-busy={loading}
        aria-disabled={isDisabled}
        {...rest}
      >
        {loading ? (
          <Spinner
            className={variant === 'secondary' ? 'text-gray-500' : 'text-white'}
          />
        ) : (
          leftIcon && <span className="flex-shrink-0">{leftIcon}</span>
        )}

        {loading ? (
          <span>Carregando...</span>
        ) : (
          children
        )}

        {!loading && rightIcon && (
          <span className="flex-shrink-0">{rightIcon}</span>
        )}
      </button>
    );
  }
);

Button.displayName = 'Button';

export default Button;
