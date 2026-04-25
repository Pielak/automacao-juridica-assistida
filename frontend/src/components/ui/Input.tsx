import React, { forwardRef, type InputHTMLAttributes, type ReactNode } from 'react';
import type { FieldError } from 'react-hook-form';

/**
 * Propriedades do componente Input reutilizável.
 *
 * Integra-se com React Hook Form via `forwardRef` e exibe
 * mensagens de erro de validação automaticamente.
 */
export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  /** Rótulo exibido acima do campo */
  label?: string;

  /** Objeto de erro do React Hook Form (FieldError) */
  error?: FieldError;

  /** Texto auxiliar exibido abaixo do campo (quando não há erro) */
  helperText?: string;

  /** Ícone ou elemento renderizado à esquerda do input */
  leftAddon?: ReactNode;

  /** Ícone ou elemento renderizado à direita do input */
  rightAddon?: ReactNode;

  /** Indica se o campo é obrigatório (exibe asterisco no label) */
  isRequired?: boolean;

  /** Classes CSS adicionais para o container raiz */
  containerClassName?: string;
}

/**
 * Componente Input reutilizável com integração React Hook Form.
 *
 * @description
 * Campo de entrada genérico que suporta:
 * - Exibição de label com indicador de obrigatoriedade
 * - Exibição automática de mensagens de erro do React Hook Form
 * - Texto auxiliar (helper text)
 * - Addons (ícones) à esquerda e/ou direita
 * - Estilização via Tailwind CSS
 * - Encaminhamento de ref para integração com `register()` do React Hook Form
 *
 * @example
 * ```tsx
 * const { register, formState: { errors } } = useForm();
 *
 * <Input
 *   label="Nome completo"
 *   placeholder="Digite seu nome"
 *   isRequired
 *   error={errors.name}
 *   {...register('name')}
 * />
 * ```
 */
const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      label,
      error,
      helperText,
      leftAddon,
      rightAddon,
      isRequired = false,
      containerClassName = '',
      className = '',
      id,
      disabled,
      type = 'text',
      ...rest
    },
    ref
  ) => {
    // Gera um ID estável caso não seja fornecido
    const inputId = id ?? `input-${label?.toLowerCase().replace(/\s+/g, '-') ?? 'field'}`;
    const errorId = `${inputId}-error`;
    const helperId = `${inputId}-helper`;

    const hasError = Boolean(error);

    // Classes base do input
    const baseInputClasses = [
      'block w-full rounded-md border px-3 py-2 text-sm',
      'transition-colors duration-150 ease-in-out',
      'placeholder:text-gray-400',
      'focus:outline-none focus:ring-2 focus:ring-offset-1',
      'disabled:cursor-not-allowed disabled:bg-gray-50 disabled:text-gray-500',
    ].join(' ');

    // Classes condicionais baseadas no estado de erro
    const stateClasses = hasError
      ? 'border-red-500 focus:border-red-500 focus:ring-red-500'
      : 'border-gray-300 focus:border-blue-500 focus:ring-blue-500';

    // Classes para addons
    const addonClasses = [
      leftAddon ? 'pl-10' : '',
      rightAddon ? 'pr-10' : '',
    ]
      .filter(Boolean)
      .join(' ');

    const finalInputClasses = [
      baseInputClasses,
      stateClasses,
      addonClasses,
      className,
    ]
      .filter(Boolean)
      .join(' ');

    return (
      <div className={`flex flex-col gap-1 ${containerClassName}`}>
        {/* Label */}
        {label && (
          <label
            htmlFor={inputId}
            className="text-sm font-medium text-gray-700"
          >
            {label}
            {isRequired && (
              <span className="ml-0.5 text-red-500" aria-hidden="true">
                *
              </span>
            )}
          </label>
        )}

        {/* Container do input com addons */}
        <div className="relative">
          {/* Addon esquerdo */}
          {leftAddon && (
            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-gray-400">
              {leftAddon}
            </div>
          )}

          {/* Input */}
          <input
            ref={ref}
            id={inputId}
            type={type}
            disabled={disabled}
            aria-invalid={hasError}
            aria-describedby={
              hasError ? errorId : helperText ? helperId : undefined
            }
            aria-required={isRequired}
            className={finalInputClasses}
            {...rest}
          />

          {/* Addon direito */}
          {rightAddon && (
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400">
              {rightAddon}
            </div>
          )}
        </div>

        {/* Mensagem de erro */}
        {hasError && error?.message && (
          <p
            id={errorId}
            className="text-xs text-red-600"
            role="alert"
          >
            {error.message}
          </p>
        )}

        {/* Texto auxiliar (exibido apenas quando não há erro) */}
        {!hasError && helperText && (
          <p
            id={helperId}
            className="text-xs text-gray-500"
          >
            {helperText}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

export default Input;
