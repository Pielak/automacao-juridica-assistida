import { z } from 'zod';

// ============================================================================
// Schema Zod para validação de formulários de processo jurídico
// Inclui validação de número CNJ, partes processuais, dados do caso, etc.
// ============================================================================

/**
 * Regex para validação do número CNJ no formato NNNNNNN-DD.AAAA.J.TR.OOOO
 * Conforme Resolução CNJ nº 65/2008:
 * - NNNNNNN: número sequencial (7 dígitos)
 * - DD: dígito verificador (2 dígitos)
 * - AAAA: ano de ajuizamento (4 dígitos)
 * - J: segmento de justiça (1 dígito)
 * - TR: tribunal (2 dígitos)
 * - OOOO: origem (4 dígitos)
 */
const CNJ_REGEX = /^\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}$/;

/**
 * Regex para validação de CPF (formato com pontuação)
 */
const CPF_REGEX = /^\d{3}\.\d{3}\.\d{3}-\d{2}$/;

/**
 * Regex para validação de CNPJ (formato com pontuação)
 */
const CNPJ_REGEX = /^\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}$/;

// ============================================================================
// Enums e constantes do domínio jurídico
// ============================================================================

/** Tipos de parte processual */
export const PartyRole = z.enum([
  'autor',
  'reu',
  'terceiro_interessado',
  'assistente',
  'litisconsorte',
  'amicus_curiae',
  'ministerio_publico',
  'perito',
], {
  errorMap: () => ({ message: 'Selecione um papel processual válido.' }),
});

/** Tipo de pessoa (física ou jurídica) */
export const PersonType = z.enum(['fisica', 'juridica'], {
  errorMap: () => ({ message: 'Selecione o tipo de pessoa (física ou jurídica).' }),
});

/** Status do processo */
export const CaseStatus = z.enum([
  'em_andamento',
  'suspenso',
  'arquivado',
  'baixado',
  'transitado_em_julgado',
  'em_cumprimento',
  'encerrado',
], {
  errorMap: () => ({ message: 'Selecione um status válido para o processo.' }),
});

/** Segmentos de justiça conforme CNJ */
export const JusticeSegment = z.enum([
  'estadual',
  'federal',
  'trabalhista',
  'eleitoral',
  'militar',
  'superior',
], {
  errorMap: () => ({ message: 'Selecione o segmento de justiça.' }),
});

/** Grau de jurisdição */
export const JurisdictionLevel = z.enum([
  'primeiro_grau',
  'segundo_grau',
  'tribunal_superior',
  'supremo',
], {
  errorMap: () => ({ message: 'Selecione o grau de jurisdição.' }),
});

/** Área do direito */
export const LegalArea = z.enum([
  'civel',
  'criminal',
  'trabalhista',
  'tributario',
  'administrativo',
  'constitucional',
  'ambiental',
  'consumidor',
  'familia',
  'empresarial',
  'previdenciario',
  'outro',
], {
  errorMap: () => ({ message: 'Selecione a área do direito.' }),
});

// ============================================================================
// Funções auxiliares de validação
// ============================================================================

/**
 * Valida dígitos verificadores de CPF.
 * @param cpf - CPF sem pontuação (apenas dígitos)
 * @returns true se o CPF é válido
 */
function isValidCpfDigits(cpf: string): boolean {
  const digits = cpf.replace(/\D/g, '');
  if (digits.length !== 11) return false;
  if (/^(\d)\1{10}$/.test(digits)) return false;

  let sum = 0;
  for (let i = 0; i < 9; i++) {
    sum += parseInt(digits.charAt(i), 10) * (10 - i);
  }
  let remainder = (sum * 10) % 11;
  if (remainder === 10) remainder = 0;
  if (remainder !== parseInt(digits.charAt(9), 10)) return false;

  sum = 0;
  for (let i = 0; i < 10; i++) {
    sum += parseInt(digits.charAt(i), 10) * (11 - i);
  }
  remainder = (sum * 10) % 11;
  if (remainder === 10) remainder = 0;
  if (remainder !== parseInt(digits.charAt(10), 10)) return false;

  return true;
}

/**
 * Valida dígitos verificadores de CNPJ.
 * @param cnpj - CNPJ sem pontuação (apenas dígitos)
 * @returns true se o CNPJ é válido
 */
function isValidCnpjDigits(cnpj: string): boolean {
  const digits = cnpj.replace(/\D/g, '');
  if (digits.length !== 14) return false;
  if (/^(\d)\1{13}$/.test(digits)) return false;

  const weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
  const weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];

  let sum = 0;
  for (let i = 0; i < 12; i++) {
    sum += parseInt(digits.charAt(i), 10) * weights1[i];
  }
  let remainder = sum % 11;
  const firstDigit = remainder < 2 ? 0 : 11 - remainder;
  if (firstDigit !== parseInt(digits.charAt(12), 10)) return false;

  sum = 0;
  for (let i = 0; i < 13; i++) {
    sum += parseInt(digits.charAt(i), 10) * weights2[i];
  }
  remainder = sum % 11;
  const secondDigit = remainder < 2 ? 0 : 11 - remainder;
  if (secondDigit !== parseInt(digits.charAt(13), 10)) return false;

  return true;
}

// ============================================================================
// Schemas compostos
// ============================================================================

/**
 * Schema para endereço (opcional em partes processuais).
 */
export const addressSchema = z.object({
  street: z
    .string()
    .min(3, 'Logradouro deve ter no mínimo 3 caracteres.')
    .max(200, 'Logradouro deve ter no máximo 200 caracteres.'),
  number: z
    .string()
    .max(10, 'Número deve ter no máximo 10 caracteres.')
    .optional(),
  complement: z
    .string()
    .max(100, 'Complemento deve ter no máximo 100 caracteres.')
    .optional(),
  neighborhood: z
    .string()
    .min(2, 'Bairro deve ter no mínimo 2 caracteres.')
    .max(100, 'Bairro deve ter no máximo 100 caracteres.'),
  city: z
    .string()
    .min(2, 'Cidade deve ter no mínimo 2 caracteres.')
    .max(100, 'Cidade deve ter no máximo 100 caracteres.'),
  state: z
    .string()
    .length(2, 'UF deve conter exatamente 2 caracteres.')
    .toUpperCase(),
  zipCode: z
    .string()
    .regex(/^\d{5}-?\d{3}$/, 'CEP deve estar no formato 00000-000.'),
});

/**
 * Schema para representante legal (advogado).
 */
export const legalRepresentativeSchema = z.object({
  /** Nome completo do advogado */
  name: z
    .string({ required_error: 'Nome do advogado é obrigatório.' })
    .min(3, 'Nome do advogado deve ter no mínimo 3 caracteres.')
    .max(200, 'Nome do advogado deve ter no máximo 200 caracteres.')
    .trim(),

  /** Número de inscrição na OAB */
  oabNumber: z
    .string({ required_error: 'Número da OAB é obrigatório.' })
    .regex(
      /^[A-Z]{2}\d{3,6}$/,
      'Número da OAB deve estar no formato UF seguido de 3 a 6 dígitos (ex: SP123456).'
    ),

  /** E-mail de contato */
  email: z
    .string()
    .email('Informe um e-mail válido para o advogado.')
    .optional(),

  /** Telefone de contato */
  phone: z
    .string()
    .regex(
      /^\(?\d{2}\)?\s?\d{4,5}-?\d{4}$/,
      'Informe um telefone válido (ex: (11) 99999-9999).'
    )
    .optional(),
});

/**
 * Schema para parte processual (autor, réu, terceiros, etc.).
 * Valida CPF ou CNPJ conforme o tipo de pessoa.
 */
export const partySchema = z
  .object({
    /** Nome completo ou razão social */
    name: z
      .string({ required_error: 'Nome da parte é obrigatório.' })
      .min(3, 'Nome da parte deve ter no mínimo 3 caracteres.')
      .max(300, 'Nome da parte deve ter no máximo 300 caracteres.')
      .trim(),

    /** Tipo de pessoa */
    personType: PersonType,

    /** CPF (obrigatório para pessoa física) */
    cpf: z
      .string()
      .regex(CPF_REGEX, 'CPF deve estar no formato 000.000.000-00.')
      .refine((val) => isValidCpfDigits(val), {
        message: 'CPF inválido. Verifique os dígitos informados.',
      })
      .optional(),

    /** CNPJ (obrigatório para pessoa jurídica) */
    cnpj: z
      .string()
      .regex(CNPJ_REGEX, 'CNPJ deve estar no formato 00.000.000/0000-00.')
      .refine((val) => isValidCnpjDigits(val), {
        message: 'CNPJ inválido. Verifique os dígitos informados.',
      })
      .optional(),

    /** Papel processual */
    role: PartyRole,

    /** E-mail de contato */
    email: z
      .string()
      .email('Informe um e-mail válido.')
      .optional(),

    /** Telefone de contato */
    phone: z
      .string()
      .regex(
        /^\(?\d{2}\)?\s?\d{4,5}-?\d{4}$/,
        'Informe um telefone válido (ex: (11) 99999-9999).'
      )
      .optional(),

    /** Endereço */
    address: addressSchema.optional(),

    /** Representante legal (advogado) */
    legalRepresentative: legalRepresentativeSchema.optional(),
  })
  .superRefine((data, ctx) => {
    // Pessoa física deve ter CPF
    if (data.personType === 'fisica' && !data.cpf) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'CPF é obrigatório para pessoa física.',
        path: ['cpf'],
      });
    }
    // Pessoa jurídica deve ter CNPJ
    if (data.personType === 'juridica' && !data.cnpj) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'CNPJ é obrigatório para pessoa jurídica.',
        path: ['cnpj'],
      });
    }
  });

// ============================================================================
// Schema principal do processo (case)
// ============================================================================

/**
 * Schema principal para validação de formulário de processo jurídico.
 * Valida número CNJ, partes processuais, dados do caso e metadados.
 */
export const caseSchema = z.object({
  /** Número CNJ do processo no formato NNNNNNN-DD.AAAA.J.TR.OOOO */
  cnjNumber: z
    .string({ required_error: 'Número CNJ é obrigatório.' })
    .regex(
      CNJ_REGEX,
      'Número CNJ deve estar no formato NNNNNNN-DD.AAAA.J.TR.OOOO (ex: 0001234-56.2024.8.26.0100).'
    ),

  /** Título descritivo do processo */
  title: z
    .string({ required_error: 'Título do processo é obrigatório.' })
    .min(5, 'Título deve ter no mínimo 5 caracteres.')
    .max(500, 'Título deve ter no máximo 500 caracteres.')
    .trim(),

  /** Descrição ou resumo do caso */
  description: z
    .string()
    .max(5000, 'Descrição deve ter no máximo 5.000 caracteres.')
    .optional(),

  /** Área do direito */
  legalArea: LegalArea,

  /** Segmento de justiça */
  justiceSegment: JusticeSegment,

  /** Grau de jurisdição */
  jurisdictionLevel: JurisdictionLevel,

  /** Status atual do processo */
  status: CaseStatus.default('em_andamento'),

  /** Comarca / Foro */
  court: z
    .string({ required_error: 'Comarca/Foro é obrigatório.' })
    .min(3, 'Comarca/Foro deve ter no mínimo 3 caracteres.')
    .max(200, 'Comarca/Foro deve ter no máximo 200 caracteres.')
    .trim(),

  /** Vara */
  branch: z
    .string()
    .max(200, 'Vara deve ter no máximo 200 caracteres.')
    .optional(),

  /** Nome do juiz responsável */
  judgeName: z
    .string()
    .max(200, 'Nome do juiz deve ter no máximo 200 caracteres.')
    .optional(),

  /** Data de distribuição */
  distributionDate: z
    .string({ required_error: 'Data de distribuição é obrigatória.' })
    .refine(
      (val) => !isNaN(Date.parse(val)),
      'Data de distribuição inválida. Use o formato AAAA-MM-DD.'
    )
    .refine(
      (val) => new Date(val) <= new Date(),
      'Data de distribuição não pode ser no futuro.'
    ),

  /** Valor da causa em centavos (inteiro) para evitar problemas de ponto flutuante */
  amountInCents: z
    .number({ required_error: 'Valor da causa é obrigatório.' })
    .int('Valor da causa deve ser um número inteiro (em centavos).')
    .nonnegative('Valor da causa não pode ser negativo.'),

  /** Partes processuais — mínimo de 2 (autor e réu) */
  parties: z
    .array(partySchema, {
      required_error: 'É necessário informar as partes processuais.',
    })
    .min(2, 'O processo deve ter no mínimo 2 partes (autor e réu).')
    .max(50, 'O processo pode ter no máximo 50 partes.')
    .superRefine((parties, ctx) => {
      // Deve haver pelo menos um autor
      const hasAuthor = parties.some((p) => p.role === 'autor');
      if (!hasAuthor) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: 'O processo deve ter pelo menos um autor.',
          path: [],
        });
      }

      // Deve haver pelo menos um réu
      const hasDefendant = parties.some((p) => p.role === 'reu');
      if (!hasDefendant) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: 'O processo deve ter pelo menos um réu.',
          path: [],
        });
      }
    }),

  /** Classe processual (tabela unificada CNJ) */
  processClass: z
    .string()
    .max(200, 'Classe processual deve ter no máximo 200 caracteres.')
    .optional(),

  /** Assuntos processuais (tabela unificada CNJ) */
  subjects: z
    .array(
      z
        .string()
        .min(2, 'Assunto deve ter no mínimo 2 caracteres.')
        .max(200, 'Assunto deve ter no máximo 200 caracteres.')
    )
    .max(20, 'Máximo de 20 assuntos por processo.')
    .optional(),

  /** Tags para organização interna */
  tags: z
    .array(
      z
        .string()
        .min(1, 'Tag não pode ser vazia.')
        .max(50, 'Tag deve ter no máximo 50 caracteres.')
        .trim()
    )
    .max(10, 'Máximo de 10 tags por processo.')
    .optional(),

  /** Observações internas (não públicas) */
  internalNotes: z
    .string()
    .max(10000, 'Observações internas devem ter no máximo 10.000 caracteres.')
    .optional(),

  /** Prioridade do caso */
  priority: z
    .enum(['baixa', 'media', 'alta', 'urgente'], {
      errorMap: () => ({ message: 'Selecione uma prioridade válida.' }),
    })
    .default('media'),

  /** Prazo fatal (deadline) — se houver */
  deadline: z
    .string()
    .refine(
      (val) => !val || !isNaN(Date.parse(val)),
      'Data de prazo inválida. Use o formato AAAA-MM-DD.'
    )
    .optional(),
});

// ============================================================================
// Schema para edição parcial (PATCH)
// ============================================================================

/**
 * Schema parcial para atualização de processo.
 * Todos os campos são opcionais, permitindo atualização parcial (PATCH).
 */
export const caseUpdateSchema = caseSchema.partial();

// ============================================================================
// Schema para filtros de busca de processos
// ============================================================================

/**
 * Schema para filtros de listagem/busca de processos.
 */
export const caseFilterSchema = z.object({
  /** Busca textual (título, número CNJ, partes) */
  search: z.string().max(200, 'Termo de busca muito longo.').optional(),

  /** Filtro por status */
  status: CaseStatus.optional(),

  /** Filtro por área do direito */
  legalArea: LegalArea.optional(),

  /** Filtro por segmento de justiça */
  justiceSegment: JusticeSegment.optional(),

  /** Filtro por prioridade */
  priority: z.enum(['baixa', 'media', 'alta', 'urgente']).optional(),

  /** Data de distribuição — início do intervalo */
  distributionDateFrom: z
    .string()
    .refine((val) => !val || !isNaN(Date.parse(val)), 'Data inválida.')
    .optional(),

  /** Data de distribuição — fim do intervalo */
  distributionDateTo: z
    .string()
    .refine((val) => !val || !isNaN(Date.parse(val)), 'Data inválida.')
    .optional(),

  /** Paginação — página atual */
  page: z.coerce
    .number()
    .int()
    .positive('Página deve ser um número positivo.')
    .default(1),

  /** Paginação — itens por página */
  pageSize: z.coerce
    .number()
    .int()
    .min(1, 'Mínimo de 1 item por página.')
    .max(100, 'Máximo de 100 itens por página.')
    .default(20),

  /** Ordenação */
  sortBy: z
    .enum(['distributionDate', 'title', 'status', 'priority', 'createdAt'])
    .default('createdAt'),

  /** Direção da ordenação */
  sortOrder: z.enum(['asc', 'desc']).default('desc'),
});

// ============================================================================
// Tipos inferidos (exportados para uso em componentes e hooks)
// ============================================================================

/** Tipo inferido do schema de endereço */
export type Address = z.infer<typeof addressSchema>;

/** Tipo inferido do schema de representante legal */
export type LegalRepresentative = z.infer<typeof legalRepresentativeSchema>;

/** Tipo inferido do schema de parte processual */
export type Party = z.infer<typeof partySchema>;

/** Tipo inferido do schema principal de processo */
export type Case = z.infer<typeof caseSchema>;

/** Tipo inferido do schema de atualização parcial */
export type CaseUpdate = z.infer<typeof caseUpdateSchema>;

/** Tipo inferido do schema de filtros de busca */
export type CaseFilter = z.infer<typeof caseFilterSchema>;

/** Tipo inferido dos enums */
export type PartyRoleType = z.infer<typeof PartyRole>;
export type PersonTypeType = z.infer<typeof PersonType>;
export type CaseStatusType = z.infer<typeof CaseStatus>;
export type JusticeSegmentType = z.infer<typeof JusticeSegment>;
export type JurisdictionLevelType = z.infer<typeof JurisdictionLevel>;
export type LegalAreaType = z.infer<typeof LegalArea>;
