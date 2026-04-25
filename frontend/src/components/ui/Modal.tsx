import React, { useEffect, useRef, useCallback, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

/**
 * Propriedades do componente Modal.
 */
export interface ModalProps {
  /** Controla a visibilidade do modal */
  isOpen: boolean;
  /** Callback executado ao solicitar fechamento do modal */
  onClose: () => void;
  /** Conteúdo renderizado dentro do modal */
  children: ReactNode;
  /** Título exibido no cabeçalho do modal (acessibilidade via aria-labelledby) */
  title?: string;
  /** Descrição para acessibilidade via aria-describedby */
  description?: string;
  /** Permite fechar o modal ao clicar no overlay. Padrão: true */
  closeOnOverlayClick?: boolean;
  /** Permite fechar o modal ao pressionar Escape. Padrão: true */
  closeOnEscape?: boolean;
  /** Classes CSS adicionais para o container do modal */
  className?: string;
  /** Tamanho predefinido do modal */
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  /** Exibe botão de fechar no cabeçalho. Padrão: true */
  showCloseButton?: boolean;
}

/** Mapeamento de tamanhos para classes CSS de largura */
const SIZE_CLASSES: Record<NonNullable<ModalProps['size']>, string> = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
  full: 'max-w-full mx-4',
};

/**
 * Retorna todos os elementos focáveis dentro de um container.
 */
function getFocusableElements(container: HTMLElement): HTMLElement[] {
  const selectors = [
    'a[href]',
    'button:not([disabled])',
    'textarea:not([disabled])',
    'input:not([disabled])',
    'select:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
  ];
  return Array.from(container.querySelectorAll<HTMLElement>(selectors.join(', ')));
}

/**
 * Componente Modal acessível com suporte a:
 * - Renderização via React Portal
 * - Focus trap (armadilha de foco)
 * - Fechamento via tecla Escape
 * - Fechamento ao clicar no overlay
 * - Atributos ARIA para acessibilidade
 *
 * @example
 * ```tsx
 * <Modal isOpen={aberto} onClose={() => setAberto(false)} title="Confirmar ação">
 *   <p>Deseja realmente prosseguir?</p>
 * </Modal>
 * ```
 */
export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  children,
  title,
  description,
  closeOnOverlayClick = true,
  closeOnEscape = true,
  className = '',
  size = 'md',
  showCloseButton = true,
}) => {
  const modalRef = useRef<HTMLDivElement>(null);
  const previousActiveElement = useRef<HTMLElement | null>(null);

  const titleId = title ? 'modal-title' : undefined;
  const descriptionId = description ? 'modal-description' : undefined;

  /**
   * Gerencia o fechamento via tecla Escape.
   */
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (event.key === 'Escape' && closeOnEscape) {
        event.stopPropagation();
        onClose();
        return;
      }

      // Focus trap: captura Tab e Shift+Tab dentro do modal
      if (event.key === 'Tab' && modalRef.current) {
        const focusableElements = getFocusableElements(modalRef.current);
        if (focusableElements.length === 0) {
          event.preventDefault();
          return;
        }

        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (event.shiftKey) {
          // Shift+Tab: se o foco está no primeiro elemento, vai para o último
          if (document.activeElement === firstElement) {
            event.preventDefault();
            lastElement.focus();
          }
        } else {
          // Tab: se o foco está no último elemento, vai para o primeiro
          if (document.activeElement === lastElement) {
            event.preventDefault();
            firstElement.focus();
          }
        }
      }
    },
    [closeOnEscape, onClose],
  );

  /**
   * Gerencia o clique no overlay (fundo escuro).
   */
  const handleOverlayClick = useCallback(
    (event: React.MouseEvent<HTMLDivElement>) => {
      // Fecha apenas se o clique foi diretamente no overlay, não em filhos
      if (closeOnOverlayClick && event.target === event.currentTarget) {
        onClose();
      }
    },
    [closeOnOverlayClick, onClose],
  );

  // Efeito: gerenciar foco, scroll lock e event listeners
  useEffect(() => {
    if (!isOpen) return;

    // Salva o elemento ativo atual para restaurar depois
    previousActiveElement.current = document.activeElement as HTMLElement;

    // Bloqueia scroll do body enquanto o modal está aberto
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    // Adiciona listener de teclado
    document.addEventListener('keydown', handleKeyDown);

    // Move o foco para o modal após renderização
    const timeoutId = setTimeout(() => {
      if (modalRef.current) {
        const focusableElements = getFocusableElements(modalRef.current);
        if (focusableElements.length > 0) {
          focusableElements[0].focus();
        } else {
          // Se não há elementos focáveis, foca o próprio container
          modalRef.current.focus();
        }
      }
    }, 0);

    return () => {
      // Cleanup: restaura scroll, remove listener e devolve foco
      document.body.style.overflow = originalOverflow;
      document.removeEventListener('keydown', handleKeyDown);
      clearTimeout(timeoutId);

      // Restaura o foco ao elemento que estava ativo antes de abrir o modal
      if (previousActiveElement.current && previousActiveElement.current.focus) {
        previousActiveElement.current.focus();
      }
    };
  }, [isOpen, handleKeyDown]);

  // Não renderiza nada se o modal está fechado
  if (!isOpen) return null;

  const sizeClass = SIZE_CLASSES[size];

  const modalContent = (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      role="presentation"
    >
      {/* Overlay (fundo escuro) */}
      <div
        className="fixed inset-0 bg-black/60 transition-opacity"
        aria-hidden="true"
        onClick={handleOverlayClick}
        data-testid="modal-overlay"
      />

      {/* Container do modal */}
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        tabIndex={-1}
        className={[
          'relative z-50 w-full rounded-lg bg-white shadow-xl',
          'transform transition-all',
          'max-h-[90vh] overflow-y-auto',
          sizeClass,
          className,
        ]
          .filter(Boolean)
          .join(' ')}
        data-testid="modal-container"
      >
        {/* Cabeçalho do modal */}
        {(title || showCloseButton) && (
          <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
            {title && (
              <h2
                id={titleId}
                className="text-lg font-semibold text-gray-900"
              >
                {title}
              </h2>
            )}
            {showCloseButton && (
              <button
                type="button"
                onClick={onClose}
                className={[
                  'rounded-md p-1 text-gray-400 transition-colors',
                  'hover:bg-gray-100 hover:text-gray-600',
                  'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
                  !title ? 'ml-auto' : '',
                ].join(' ')}
                aria-label="Fechar modal"
                data-testid="modal-close-button"
              >
                {/* Ícone X (SVG inline para evitar dependência externa) */}
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-5 w-5"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  aria-hidden="true"
                >
                  <path
                    fillRule="evenodd"
                    d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                    clipRule="evenodd"
                  />
                </svg>
              </button>
            )}
          </div>
        )}

        {/* Descrição oculta para acessibilidade */}
        {description && (
          <p id={descriptionId} className="sr-only">
            {description}
          </p>
        )}

        {/* Corpo do modal */}
        <div className="px-6 py-4" data-testid="modal-body">
          {children}
        </div>
      </div>
    </div>
  );

  // Renderiza via portal no body para evitar problemas de z-index e overflow
  return createPortal(modalContent, document.body);
};

export default Modal;
