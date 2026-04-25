import React, { useCallback, useState, useMemo } from 'react';
import { useDropzone, type Accept, type FileRejection } from 'react-dropzone';

/**
 * Tipos de arquivo permitidos por padrão para documentos jurídicos.
 * Inclui PDFs, documentos Word e imagens de digitalizações.
 */
const DEFAULT_ACCEPT: Accept = {
  'application/pdf': ['.pdf'],
  'application/msword': ['.doc'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'image/png': ['.png'],
  'image/jpeg': ['.jpg', '.jpeg'],
};

/** Tamanho máximo padrão: 25 MB */
const DEFAULT_MAX_SIZE = 25 * 1024 * 1024;

/** Quantidade máxima padrão de arquivos por upload */
const DEFAULT_MAX_FILES = 10;

/** Representa um arquivo em processo de upload com metadados de progresso */
export interface UploadFileItem {
  /** Identificador único local para rastreamento no componente */
  id: string;
  /** Referência ao objeto File nativo */
  file: File;
  /** Progresso do upload de 0 a 100 */
  progress: number;
  /** Status atual do arquivo */
  status: 'pending' | 'uploading' | 'success' | 'error';
  /** Mensagem de erro, se houver */
  errorMessage?: string;
  /** URL de preview para imagens */
  previewUrl?: string;
}

/** Props do componente FileUpload */
export interface FileUploadProps {
  /** Tipos MIME aceitos (padrão: PDF, DOC, DOCX, PNG, JPG) */
  accept?: Accept;
  /** Tamanho máximo por arquivo em bytes (padrão: 25 MB) */
  maxSize?: number;
  /** Quantidade máxima de arquivos (padrão: 10) */
  maxFiles?: number;
  /** Permite múltiplos arquivos (padrão: true) */
  multiple?: boolean;
  /** Desabilita o componente */
  disabled?: boolean;
  /** Callback chamado quando arquivos são aceitos e adicionados */
  onFilesAdded?: (files: File[]) => void;
  /**
   * Callback de upload customizado. Recebe o arquivo e uma função de progresso.
   * Deve retornar uma Promise que resolve quando o upload terminar.
   */
  onUpload?: (file: File, onProgress: (percent: number) => void) => Promise<void>;
  /** Callback chamado quando um arquivo é removido da lista */
  onFileRemoved?: (file: File) => void;
  /** Classes CSS adicionais para o container raiz */
  className?: string;
  /** Label acessível para o campo de upload */
  label?: string;
  /** Texto de ajuda exibido abaixo da zona de drop */
  helperText?: string;
}

/**
 * Gera um ID único simples para rastreamento local de arquivos.
 * Não é criptograficamente seguro — apenas para uso em chaves React.
 */
function generateLocalId(): string {
  return `file_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * Formata bytes em uma string legível (ex: "2.5 MB").
 */
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const k = 1024;
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  const size = parseFloat((bytes / Math.pow(k, i)).toFixed(1));
  return `${size} ${units[i]}`;
}

/**
 * Traduz códigos de erro do react-dropzone para mensagens em PT-BR.
 */
function translateDropzoneError(code: string, maxSize: number): string {
  switch (code) {
    case 'file-too-large':
      return `Arquivo excede o tamanho máximo de ${formatFileSize(maxSize)}.`;
    case 'file-too-small':
      return 'Arquivo é muito pequeno.';
    case 'too-many-files':
      return 'Quantidade máxima de arquivos excedida.';
    case 'file-invalid-type':
      return 'Tipo de arquivo não permitido. Envie PDF, DOC, DOCX, PNG ou JPG.';
    default:
      return 'Erro ao processar o arquivo.';
  }
}

/**
 * Verifica se o arquivo é uma imagem para gerar preview.
 */
function isImageFile(file: File): boolean {
  return file.type.startsWith('image/');
}

/**
 * Componente de upload de arquivos com suporte a drag-and-drop.
 *
 * Funcionalidades:
 * - Zona de arrastar e soltar (react-dropzone)
 * - Validação de tipo MIME e tamanho de arquivo
 * - Barra de progresso por arquivo
 * - Preview de imagens
 * - Remoção de arquivos da fila
 * - Mensagens de erro em PT-BR
 * - Acessibilidade com labels e roles ARIA
 *
 * @example
 * ```tsx
 * <FileUpload
 *   label="Documentos do processo"
 *   onUpload={async (file, onProgress) => {
 *     await api.uploadDocument(file, onProgress);
 *   }}
 *   maxSize={10 * 1024 * 1024}
 *   maxFiles={5}
 * />
 * ```
 */
export const FileUpload: React.FC<FileUploadProps> = ({
  accept = DEFAULT_ACCEPT,
  maxSize = DEFAULT_MAX_SIZE,
  maxFiles = DEFAULT_MAX_FILES,
  multiple = true,
  disabled = false,
  onFilesAdded,
  onUpload,
  onFileRemoved,
  className = '',
  label,
  helperText,
}) => {
  const [fileItems, setFileItems] = useState<UploadFileItem[]>([]);
  const [rejectionErrors, setRejectionErrors] = useState<string[]>([]);

  /**
   * Atualiza um campo específico de um UploadFileItem pelo ID.
   */
  const updateFileItem = useCallback(
    (id: string, updates: Partial<UploadFileItem>) => {
      setFileItems((prev) =>
        prev.map((item) => (item.id === id ? { ...item, ...updates } : item))
      );
    },
    []
  );

  /**
   * Processa o upload de um único arquivo, atualizando o progresso.
   */
  const processUpload = useCallback(
    async (item: UploadFileItem) => {
      if (!onUpload) return;

      updateFileItem(item.id, { status: 'uploading', progress: 0 });

      try {
        await onUpload(item.file, (percent: number) => {
          updateFileItem(item.id, { progress: Math.min(percent, 100) });
        });
        updateFileItem(item.id, { status: 'success', progress: 100 });
      } catch (error) {
        const message =
          error instanceof Error
            ? error.message
            : 'Erro desconhecido durante o upload.';
        updateFileItem(item.id, {
          status: 'error',
          errorMessage: message,
        });
      }
    },
    [onUpload, updateFileItem]
  );

  /**
   * Callback principal do react-dropzone quando arquivos são soltos/selecionados.
   */
  const onDrop = useCallback(
    (acceptedFiles: File[], fileRejections: FileRejection[]) => {
      // Limpa erros de rejeição anteriores
      setRejectionErrors([]);

      // Processa rejeições
      if (fileRejections.length > 0) {
        const errors = fileRejections.flatMap((rejection) =>
          rejection.errors.map(
            (err) =>
              `"${rejection.file.name}": ${translateDropzoneError(err.code, maxSize)}`
          )
        );
        setRejectionErrors(errors);
      }

      // Verifica se não excede o limite total
      const currentCount = fileItems.length;
      const availableSlots = maxFiles - currentCount;

      if (availableSlots <= 0 && acceptedFiles.length > 0) {
        setRejectionErrors((prev) => [
          ...prev,
          `Limite de ${maxFiles} arquivo(s) atingido. Remova arquivos antes de adicionar novos.`,
        ]);
        return;
      }

      const filesToAdd = acceptedFiles.slice(0, availableSlots);

      if (filesToAdd.length < acceptedFiles.length) {
        setRejectionErrors((prev) => [
          ...prev,
          `Apenas ${filesToAdd.length} de ${acceptedFiles.length} arquivo(s) foram adicionados devido ao limite de ${maxFiles}.`,
        ]);
      }

      // Cria itens de upload
      const newItems: UploadFileItem[] = filesToAdd.map((file) => {
        const item: UploadFileItem = {
          id: generateLocalId(),
          file,
          progress: 0,
          status: 'pending',
          previewUrl: isImageFile(file)
            ? URL.createObjectURL(file)
            : undefined,
        };
        return item;
      });

      setFileItems((prev) => [...prev, ...newItems]);

      // Notifica callback externo
      if (onFilesAdded && filesToAdd.length > 0) {
        onFilesAdded(filesToAdd);
      }

      // Inicia uploads se handler fornecido
      if (onUpload) {
        newItems.forEach((item) => {
          processUpload(item);
        });
      }
    },
    [fileItems.length, maxFiles, maxSize, onFilesAdded, onUpload, processUpload]
  );

  /**
   * Remove um arquivo da lista e libera URL de preview se existir.
   */
  const handleRemoveFile = useCallback(
    (id: string) => {
      setFileItems((prev) => {
        const item = prev.find((f) => f.id === id);
        if (item) {
          // Libera URL de preview para evitar memory leak
          if (item.previewUrl) {
            URL.revokeObjectURL(item.previewUrl);
          }
          if (onFileRemoved) {
            onFileRemoved(item.file);
          }
        }
        return prev.filter((f) => f.id !== id);
      });
    },
    [onFileRemoved]
  );

  /**
   * Tenta reenviar um arquivo que falhou.
   */
  const handleRetry = useCallback(
    (id: string) => {
      const item = fileItems.find((f) => f.id === id);
      if (item && onUpload) {
        updateFileItem(id, { status: 'pending', progress: 0, errorMessage: undefined });
        processUpload({ ...item, status: 'pending', progress: 0 });
      }
    },
    [fileItems, onUpload, updateFileItem, processUpload]
  );

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept,
    maxSize,
    maxFiles,
    multiple,
    disabled,
  });

  /** Extensões aceitas formatadas para exibição */
  const acceptedExtensions = useMemo(() => {
    return Object.values(accept)
      .flat()
      .map((ext) => ext.toUpperCase().replace('.', ''))
      .join(', ');
  }, [accept]);

  /**
   * Retorna classes CSS para a zona de drop baseado no estado atual.
   */
  const dropzoneClasses = useMemo(() => {
    const base =
      'relative flex flex-col items-center justify-center w-full min-h-[180px] p-6 border-2 border-dashed rounded-lg cursor-pointer transition-colors duration-200 focus-within:outline-none focus-within:ring-2 focus-within:ring-blue-500 focus-within:ring-offset-2';

    if (disabled) {
      return `${base} border-gray-200 bg-gray-50 cursor-not-allowed opacity-60`;
    }
    if (isDragReject) {
      return `${base} border-red-400 bg-red-50`;
    }
    if (isDragActive) {
      return `${base} border-blue-400 bg-blue-50`;
    }
    return `${base} border-gray-300 bg-white hover:border-blue-400 hover:bg-gray-50`;
  }, [disabled, isDragActive, isDragReject]);

  /**
   * Ícone de status para cada arquivo na lista.
   */
  const renderStatusIcon = (status: UploadFileItem['status']) => {
    switch (status) {
      case 'pending':
        return (
          <span className="text-gray-400" aria-label="Pendente" title="Pendente">
            ⏳
          </span>
        );
      case 'uploading':
        return (
          <span
            className="text-blue-500 animate-spin inline-block"
            aria-label="Enviando"
            title="Enviando"
          >
            ⟳
          </span>
        );
      case 'success':
        return (
          <span className="text-green-500" aria-label="Enviado com sucesso" title="Enviado com sucesso">
            ✓
          </span>
        );
      case 'error':
        return (
          <span className="text-red-500" aria-label="Erro no envio" title="Erro no envio">
            ✗
          </span>
        );
    }
  };

  /**
   * Ícone representativo do tipo de arquivo.
   */
  const renderFileTypeIcon = (file: File) => {
    if (file.type === 'application/pdf') {
      return <span className="text-red-500 text-lg" title="PDF">📄</span>;
    }
    if (
      file.type === 'application/msword' ||
      file.type ===
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ) {
      return <span className="text-blue-600 text-lg" title="Documento Word">📝</span>;
    }
    if (file.type.startsWith('image/')) {
      return <span className="text-green-500 text-lg" title="Imagem">🖼️</span>;
    }
    return <span className="text-gray-500 text-lg" title="Arquivo">📎</span>;
  };

  return (
    <div className={`w-full ${className}`}>
      {/* Label acessível */}
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {label}
        </label>
      )}

      {/* Zona de drop */}
      <div
        {...getRootProps()}
        className={dropzoneClasses}
        role="button"
        aria-label={label || 'Área de upload de arquivos'}
      >
        <input {...getInputProps()} aria-label="Selecionar arquivos" />

        {/* Ícone central */}
        <div className="text-4xl mb-3">
          {isDragReject ? '🚫' : isDragActive ? '📥' : '📁'}
        </div>

        {/* Texto principal */}
        {isDragReject ? (
          <p className="text-sm text-red-600 font-medium text-center">
            Tipo de arquivo não permitido
          </p>
        ) : isDragActive ? (
          <p className="text-sm text-blue-600 font-medium text-center">
            Solte os arquivos aqui...
          </p>
        ) : (
          <>
            <p className="text-sm text-gray-600 text-center">
              <span className="font-medium text-blue-600 hover:text-blue-500">
                Clique para selecionar
              </span>{' '}
              ou arraste arquivos aqui
            </p>
            <p className="text-xs text-gray-400 mt-1 text-center">
              {acceptedExtensions} — Máx. {formatFileSize(maxSize)} por arquivo
              {maxFiles > 1 && ` — Até ${maxFiles} arquivos`}
            </p>
          </>
        )}
      </div>

      {/* Texto de ajuda */}
      {helperText && (
        <p className="mt-1 text-xs text-gray-500">{helperText}</p>
      )}

      {/* Erros de rejeição */}
      {rejectionErrors.length > 0 && (
        <div
          className="mt-3 p-3 bg-red-50 border border-red-200 rounded-md"
          role="alert"
          aria-live="polite"
        >
          <p className="text-xs font-medium text-red-800 mb-1">
            Alguns arquivos não puderam ser adicionados:
          </p>
          <ul className="list-disc list-inside space-y-0.5">
            {rejectionErrors.map((error, index) => (
              <li key={index} className="text-xs text-red-600">
                {error}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Lista de arquivos */}
      {fileItems.length > 0 && (
        <ul className="mt-4 space-y-2" aria-label="Arquivos selecionados">
          {fileItems.map((item) => (
            <li
              key={item.id}
              className="flex items-start gap-3 p-3 bg-white border border-gray-200 rounded-lg shadow-sm"
            >
              {/* Preview de imagem ou ícone de tipo */}
              <div className="flex-shrink-0 w-10 h-10 flex items-center justify-center rounded bg-gray-50 overflow-hidden">
                {item.previewUrl ? (
                  <img
                    src={item.previewUrl}
                    alt={`Preview de ${item.file.name}`}
                    className="w-full h-full object-cover rounded"
                  />
                ) : (
                  renderFileTypeIcon(item.file)
                )}
              </div>

              {/* Informações do arquivo */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  {renderStatusIcon(item.status)}
                  <p
                    className="text-sm font-medium text-gray-700 truncate"
                    title={item.file.name}
                  >
                    {item.file.name}
                  </p>
                </div>

                <p className="text-xs text-gray-400 mt-0.5">
                  {formatFileSize(item.file.size)}
                </p>

                {/* Barra de progresso */}
                {(item.status === 'uploading' || item.status === 'success') && (
                  <div className="mt-1.5 w-full">
                    <div
                      className="w-full bg-gray-100 rounded-full h-1.5 overflow-hidden"
                      role="progressbar"
                      aria-valuenow={item.progress}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-label={`Progresso do upload de ${item.file.name}`}
                    >
                      <div
                        className={`h-full rounded-full transition-all duration-300 ease-out ${
                          item.status === 'success'
                            ? 'bg-green-500'
                            : 'bg-blue-500'
                        }`}
                        style={{ width: `${item.progress}%` }}
                      />
                    </div>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {item.progress}%
                    </p>
                  </div>
                )}

                {/* Mensagem de erro */}
                {item.status === 'error' && item.errorMessage && (
                  <p className="text-xs text-red-500 mt-1">{item.errorMessage}</p>
                )}
              </div>

              {/* Ações */}
              <div className="flex-shrink-0 flex items-center gap-1">
                {item.status === 'error' && onUpload && (
                  <button
                    type="button"
                    onClick={() => handleRetry(item.id)}
                    className="p-1 text-blue-500 hover:text-blue-700 hover:bg-blue-50 rounded transition-colors"
                    title="Tentar novamente"
                    aria-label={`Tentar enviar ${item.file.name} novamente`}
                  >
                    ↻
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => handleRemoveFile(item.id)}
                  className="p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded transition-colors"
                  title="Remover arquivo"
                  aria-label={`Remover ${item.file.name}`}
                  disabled={item.status === 'uploading'}
                >
                  ✕
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {/* Contador de arquivos */}
      {fileItems.length > 0 && (
        <p className="mt-2 text-xs text-gray-400 text-right">
          {fileItems.length} de {maxFiles} arquivo(s)
        </p>
      )}
    </div>
  );
};

export default FileUpload;
