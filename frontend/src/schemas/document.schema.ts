import { z } from 'zod';

/**
 * Tipos MIME permitidos para upload de documentos jurídicos.
 * Inclui formatos comuns no contexto jurídico brasileiro.
 */
export const ALLOWED_MIME_TYPES = [
 'application/pdf',
 'application/msword',
 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
 'application/vnd.oasis.opendocument.text',
 'text/plain',
 'image/png',
 'image/jpeg',
 'image/tiff',
] as const;

/** Rótulos legíveis para cada tipo MIME aceito */
export const MIME_TYPE_LABELS: Record<string, string> = {
 'application/pdf': 'PDF',
 'application/msword': 'DOC (Word 97-2003)',
 'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'DOCX (Word)',
 'application/vnd.oasis.opendocument.text': 'ODT (LibreOffice)',
 'text/plain': 'Texto Simples (.txt)',
 'image/png': 'Imagem PNG',
 'image/jpeg': 'Imagem JPEG',
 'image/tiff': 'Imagem TIFF',
};

/** Extensões de arquivo permitidas (para validação complementar no front) */
export const ALLOWED_EXTENSIONS = [
 '.pdf',
 '.doc',
 '.docx',
 '.odt',
 '.txt',
 '.png',
 '.jpg',
 '.jpeg',
 '.tiff',
 '.tif',
] as const;

/** Tamanho máximo de arquivo em bytes (50 MB) */
export const MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024;

/** Tamanho máximo de arquivo formatado para exibição */
export const MAX_FILE_SIZE_LABEL = '50 MB';

/** Quantidade máxima de arquivos por upload simultâneo */
export const MAX_FILES_PER_UPLOAD = 10;

/**
 * Categorias de documento jurídico disponíveis no sistema.
 * Utilizado para classificação no momento do upload.
 */
export const DOCUMENT_CATEGORIES = [
 'peticao_inicial',
 'contestacao',
 'recurso',
 'sentenca',
 'acordao',
 'contrato',
 'procuracao',
 'parecer',
 'notificacao',
 'outros',
] as const;

/** Rótulos em PT-BR para as categorias de documento */
export const DOCUMENT_CATEGORY_LABELS: Record<DocumentCategory, string> = {
 peticao_inicial: 'Petição Inicial',
 contestacao: 'Contestação',
 recurso: 'Recurso',
 sentenca: 'Sentença',
 acordao: 'Acórdão',
 contrato: 'Contrato',
 procuracao: 'Procuração',
 parecer: 'Parecer',
 notificacao: 'Notificação',
 outros: 'Outros',
};

/** Tipo derivado das categorias de documento */
export type DocumentCategory = (typeof DOCUMENT_CATEGORIES)[number];

/** Tipo derivado dos MIME types permitidos */
export type AllowedMimeType = (typeof ALLOWED_MIME_TYPES)[number];

/**
 * Verifica se o nome do arquivo possui uma extensão permitida.
 * Validação complementar ao MIME type para maior segurança.
 */
function hasAllowedExtension(fileName: string): boolean {
 const lowerName = fileName.toLowerCase();
 return ALLOWED_EXTENSIONS.some((ext) => lowerName.endsWith(ext));
}

/**
 * Schema Zod para validação de um único arquivo de upload.
 * Valida tipo MIME, tamanho e extensão do arquivo.
 */
export const singleFileSchema = z
 .custom<File>(
 (val) => val instanceof File,
 { message: 'O valor fornecido não é um arquivo válido.' }
 )
 .refine(
 (file) => file.size > 0,
 { message: 'O arquivo está vazio. Por favor, selecione um arquivo com conteúdo.' }
 )
 .refine(
 (file) => file.size <= MAX_FILE_SIZE_BYTES,
 {
 message: `O arquivo excede o tamanho máximo permitido de ${MAX_FILE_SIZE_LABEL}. Por favor, reduza o tamanho do arquivo e tente novamente.`,
 }
 )
 .refine(
 (file) => (ALLOWED_MIME_TYPES as readonly string[]).includes(file.type),
 {
 message: `Tipo de arquivo não permitido. Formatos aceitos: ${Object.values(MIME_TYPE_LABELS).join(', ')}.`,
 }
 )
 .refine(
 (file) => hasAllowedExtension(file.name),
 {
 message: `Extensão de arquivo não permitida. Extensões aceitas: ${ALLOWED_EXTENSIONS.join(', ')}.`,
 }
 );

/**
 * Schema Zod para os metadados do formulário de upload de documento.
 * Inclui campos descritivos e classificação do documento.
 */
export const documentMetadataSchema = z.object({
 /** Título descritivo do documento */
 title: z
 .string({ required_error: 'O título do documento é obrigatório.' })
 .trim()
 .min(3, { message: 'O título deve ter no mínimo 3 caracteres.' })
 .max(255, { message: 'O título deve ter no máximo 255 caracteres.' }),

 /** Descrição opcional do documento */
 description: z
 .string()
 .trim()
 .max(2000, { message: 'A descrição deve ter no máximo 2.000 caracteres.' })
 .optional()
 .default(''),

 /** Categoria/tipo do documento jurídico */
 category: z.enum(DOCUMENT_CATEGORIES, {
 required_error: 'A categoria do documento é obrigatória.',
 invalid_type_error: 'Categoria de documento inválida.',
 }),

 /** Número do processo judicial associado (formato CNJ opcional) */
 processNumber: z
 .string()
 .trim()
 .max(25, { message: 'O número do processo deve ter no máximo 25 caracteres.' })
 .regex(
 /^(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})?$/,
 { message: 'Formato de número de processo inválido. Use o padrão CNJ: NNNNNNN-DD.AAAA.J.TR.OOOO' }
 )
 .optional()
 .default(''),

 /** Tags livres para organização */
 tags: z
 .array(
 z.string().trim().min(1).max(50, { message: 'Cada tag deve ter no máximo 50 caracteres.' })
 )
 .max(20, { message: 'É permitido no máximo 20 tags por documento.' })
 .optional()
 .default([]),
});

/**
 * Schema Zod completo para o formulário de upload de documento.
 * Combina validação de arquivo(s) com metadados descritivos.
 */
export const documentUploadSchema = z.object({
 /** Arquivo(s) selecionado(s) para upload */
 files: z
 .array(singleFileSchema)
 .min(1, { message: 'Selecione pelo menos um arquivo para upload.' })
 .max(MAX_FILES_PER_UPLOAD, {
 message: `É permitido enviar no máximo ${MAX_FILES_PER_UPLOAD} arquivos por vez.`,
 }),

 /** Metadados do documento */
 metadata: documentMetadataSchema,
});

/**
 * Schema para upload simplificado (apenas arquivo, sem metadados obrigatórios).
 * Útil para fluxos de arrastar-e-soltar rápidos onde metadados são preenchidos depois.
 */
export const quickUploadSchema = z.object({
 files: z
 .array(singleFileSchema)
 .min(1, { message: 'Selecione pelo menos um arquivo para upload.' })
 .max(MAX_FILES_PER_UPLOAD, {
 message: `É permitido enviar no máximo ${MAX_FILES_PER_UPLOAD} arquivos por vez.`,
 }),
});

/** Tipo inferido do schema de metadados do documento */
export type DocumentMetadataInput = z.infer<typeof documentMetadataSchema>;

/** Tipo inferido do schema completo de upload */
export type DocumentUploadInput = z.infer<typeof documentUploadSchema>;

/** Tipo inferido do schema de upload rápido */
export type QuickUploadInput = z.infer<typeof quickUploadSchema>;

/**
 * Utilitário para formatar o tamanho de arquivo em unidades legíveis (PT-BR).
 * @param bytes - Tamanho em bytes
 * @returns String formatada (ex: "2,5 MB")
 */
export function formatFileSize(bytes: number): string {
 if (bytes === 0) return '0 Bytes';

 const units = ['Bytes', 'KB', 'MB', 'GB'];
 const k = 1024;
 const i = Math.floor(Math.log(bytes) / Math.log(k));
 const size = bytes / Math.pow(k, i);

 return `${size.toLocaleString('pt-BR', { maximumFractionDigits: 2 })} ${units[i]}`;
}

/**
 * Utilitário para obter o rótulo legível de um tipo MIME.
 * @param mimeType - Tipo MIME do arquivo
 * @returns Rótulo em PT-BR ou o próprio MIME type se não mapeado
 */
export function getMimeTypeLabel(mimeType: string): string {
 return MIME_TYPE_LABELS[mimeType] ?? mimeType;
}

/**
 * Utilitário para obter o rótulo legível de uma categoria de documento.
 * @param category - Chave da categoria
 * @returns Rótulo em PT-BR
 */
export function getCategoryLabel(category: DocumentCategory): string {
 return DOCUMENT_CATEGORY_LABELS[category];
}
