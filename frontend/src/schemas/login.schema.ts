import { z } from 'zod';

/**
 * Schema Zod para validação do formulário de login.
 *
 * Garante que o e-mail seja válido e que a senha atenda aos requisitos
 * mínimos de comprimento antes de enviar a requisição ao backend.
 */
export const loginSchema = z.object({
  /**
   * E-mail do usuário — campo obrigatório, deve ser um endereço válido.
   */
  email: z
    .string({
      required_error: 'O e-mail é obrigatório.',
    })
    .trim()
    .min(1, { message: 'O e-mail é obrigatório.' })
    .email({ message: 'Informe um endereço de e-mail válido.' })
    .max(254, { message: 'O e-mail deve ter no máximo 254 caracteres.' }),

  /**
   * Senha do usuário — campo obrigatório com comprimento mínimo de 8 caracteres.
   */
  password: z
    .string({
      required_error: 'A senha é obrigatória.',
    })
    .min(1, { message: 'A senha é obrigatória.' })
    .min(8, { message: 'A senha deve ter no mínimo 8 caracteres.' })
    .max(128, { message: 'A senha deve ter no máximo 128 caracteres.' }),

  /**
   * Código TOTP para autenticação multifator (MFA).
   * Opcional — só é exigido quando o backend indica que MFA está habilitado
   * para a conta do usuário (fluxo em duas etapas).
   */
  mfaCode: z
    .string()
    .regex(/^\d{6}$/, {
      message: 'O código MFA deve conter exatamente 6 dígitos numéricos.',
    })
    .optional(),
});

/**
 * Tipo inferido a partir do schema de login.
 * Utilizado pelo React Hook Form para tipagem do formulário.
 */
export type LoginFormData = z.infer<typeof loginSchema>;

/**
 * Schema parcial para a primeira etapa do login (antes de solicitar MFA).
 * Valida apenas e-mail e senha.
 */
export const loginStepOneSchema = loginSchema.pick({
  email: true,
  password: true,
});

/** Tipo inferido para a primeira etapa do login. */
export type LoginStepOneData = z.infer<typeof loginStepOneSchema>;

/**
 * Schema para a segunda etapa do login (somente código MFA).
 * Utilizado quando o backend responde que MFA é necessário.
 */
export const loginMfaSchema = z.object({
  mfaCode: z
    .string({ required_error: 'O código MFA é obrigatório.' })
    .regex(/^\d{6}$/, {
      message: 'O código MFA deve conter exatamente 6 dígitos numéricos.',
    }),
});

/** Tipo inferido para a etapa de MFA. */
export type LoginMfaData = z.infer<typeof loginMfaSchema>;
