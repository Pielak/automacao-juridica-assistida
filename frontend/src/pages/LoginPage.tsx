import React from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate } from 'react-router-dom';

import { useAuth } from '@/lib/auth-context';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';

/* ---------------------------------------------------------------------------
 * Schema de validação — Zod
 * --------------------------------------------------------------------------- */

/**
 * Schema de validação do formulário de login.
 *
 * - `email`: obrigatório, formato de e-mail válido.
 * - `password`: obrigatória, mínimo 8 caracteres.
 * - `oab`: opcional — número de inscrição na OAB (formato UF + número, ex.: SP123456).
 */
const loginSchema = z.object({
  email: z
    .string()
    .min(1, 'O e-mail é obrigatório.')
    .email('Informe um e-mail válido.'),
  password: z
    .string()
    .min(8, 'A senha deve ter no mínimo 8 caracteres.'),
  oab: z
    .string()
    .regex(/^[A-Z]{2}\d{4,6}$/, 'Formato OAB inválido. Ex.: SP123456')
    .optional()
    .or(z.literal('')),
});

/** Tipo inferido a partir do schema de login. */
type LoginFormData = z.infer<typeof loginSchema>;

/* ---------------------------------------------------------------------------
 * Componente LoginPage
 * --------------------------------------------------------------------------- */

/**
 * Página de login da aplicação.
 *
 * Renderiza um formulário com campos de e-mail, senha e número OAB (opcional),
 * utilizando React Hook Form para gerenciamento de estado do formulário e Zod
 * para validação tipada. Ao submeter com sucesso, delega a autenticação ao
 * contexto `AuthContext` e redireciona o usuário para o dashboard.
 */
export default function LoginPage(): React.JSX.Element {
  const { login } = useAuth();
  const navigate = useNavigate();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setError,
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: '',
      password: '',
      oab: '',
    },
  });

  /**
   * Handler de submissão do formulário.
   *
   * Chama `login` do contexto de autenticação e, em caso de sucesso,
   * redireciona para `/dashboard`. Erros de autenticação são exibidos
   * como erro no campo raiz do formulário.
   */
  const onSubmit = async (data: LoginFormData): Promise<void> => {
    try {
      await login(data.email, data.password);
      navigate('/dashboard', { replace: true });
    } catch (error: unknown) {
      const message =
        error instanceof Error
          ? error.message
          : 'Não foi possível realizar o login. Tente novamente.';

      setError('root', { message });
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md rounded-lg bg-white p-8 shadow-md">
        {/* Cabeçalho */}
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-gray-900">
            Automação Jurídica Assistida
          </h1>
          <p className="mt-2 text-sm text-gray-600">
            Acesse sua conta para continuar
          </p>
        </div>

        {/* Formulário */}
        <form
          onSubmit={handleSubmit(onSubmit)}
          noValidate
          className="space-y-5"
        >
          {/* Erro geral de autenticação */}
          {errors.root && (
            <div
              role="alert"
              className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
            >
              {errors.root.message}
            </div>
          )}

          {/* Campo E-mail */}
          <Input
            label="E-mail"
            type="email"
            placeholder="seu@email.com.br"
            autoComplete="email"
            error={errors.email}
            {...register('email')}
          />

          {/* Campo Senha */}
          <Input
            label="Senha"
            type="password"
            placeholder="Sua senha"
            autoComplete="current-password"
            error={errors.password}
            {...register('password')}
          />

          {/* Campo OAB (opcional) */}
          <Input
            label="Número OAB (opcional)"
            type="text"
            placeholder="Ex.: SP123456"
            helperText="Informe sua inscrição na OAB, se aplicável."
            error={errors.oab}
            {...register('oab')}
          />

          {/* Botão de submissão */}
          <Button
            type="submit"
            variant="primary"
            size="lg"
            loading={isSubmitting}
            className="w-full"
          >
            Entrar
          </Button>
        </form>

        {/* Links auxiliares */}
        <div className="mt-6 text-center text-sm text-gray-500">
          <a
            href="/forgot-password"
            className="font-medium text-blue-600 hover:text-blue-500"
          >
            Esqueceu sua senha?
          </a>
        </div>
      </div>
    </main>
  );
}
