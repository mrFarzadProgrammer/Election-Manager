import React, { useEffect } from 'react';

export type ResultModalVariant = 'success' | 'error' | 'info' | 'warning';

export interface ResultModalProps {
    open: boolean;
    variant: ResultModalVariant;
    title: string;
    message?: string;
    children?: React.ReactNode;
    onClose: () => void;
    dismissable?: boolean;
    primaryLabel?: string;
    hideCloseIcon?: boolean;
}

const variantDotClass: Record<ResultModalVariant, string> = {
    success: 'bg-green-500',
    error: 'bg-red-500',
    info: 'bg-blue-500',
    warning: 'bg-amber-500',
};

const variantButtonClass: Record<ResultModalVariant, string> = {
    success: 'bg-green-600 text-white hover:bg-green-700',
    error: 'bg-red-600 text-white hover:bg-red-700',
    info: 'bg-blue-600 text-white hover:bg-blue-700',
    warning: 'bg-amber-600 text-white hover:bg-amber-700',
};

const ResultModal: React.FC<ResultModalProps> = ({
    open,
    variant,
    title,
    message,
    children,
    onClose,
    dismissable = true,
    primaryLabel = 'باشه',
    hideCloseIcon,
}) => {
    useEffect(() => {
        if (!open || !dismissable) return;
        const onKeyDown = (ev: KeyboardEvent) => {
            if (ev.key === 'Escape') onClose();
        };
        window.addEventListener('keydown', onKeyDown);
        return () => window.removeEventListener('keydown', onKeyDown);
    }, [open, dismissable, onClose]);

    if (!open) return null;

    const effectiveHideCloseIcon = hideCloseIcon ?? !dismissable;

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 animate-fade-in"
            role="dialog"
            aria-modal="true"
            onMouseDown={(e) => {
                if (!dismissable) return;
                if (e.target === e.currentTarget) onClose();
            }}
        >
            <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl overflow-hidden animate-fade-in-up">
                <div className="p-5 border-b border-gray-100 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <div className={`w-2.5 h-2.5 rounded-full ${variantDotClass[variant]}`} />
                        <h4 className="font-bold text-gray-800">{title}</h4>
                    </div>

                    {!effectiveHideCloseIcon && (
                        <button
                            onClick={onClose}
                            className="text-gray-400 hover:text-gray-600 transition"
                            aria-label="بستن"
                            type="button"
                        >
                            ×
                        </button>
                    )}
                </div>

                <div className="p-5">
                    {children ? (
                        children
                    ) : (
                        <p className="text-sm text-gray-600 leading-6 whitespace-pre-wrap break-words">{message}</p>
                    )}

                    <div className="flex justify-end mt-5">
                        <button
                            onClick={onClose}
                            type="button"
                            disabled={!dismissable && !onClose}
                            className={`px-6 py-2.5 rounded-xl font-medium transition ${variantButtonClass[variant]}`}
                        >
                            {primaryLabel}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ResultModal;
