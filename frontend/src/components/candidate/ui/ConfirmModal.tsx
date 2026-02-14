import React, { useEffect } from 'react';

export type ConfirmModalVariant = 'info' | 'warning' | 'error' | 'success';

interface ConfirmModalProps {
    open: boolean;
    variant?: ConfirmModalVariant;
    title: string;
    message?: string;
    confirmLabel?: string;
    cancelLabel?: string;
    onConfirm: () => void;
    onCancel: () => void;
    dismissable?: boolean;
}

const variantDotClass: Record<ConfirmModalVariant, string> = {
    success: 'bg-green-500',
    error: 'bg-red-500',
    info: 'bg-blue-500',
    warning: 'bg-amber-500',
};

const confirmButtonClass: Record<ConfirmModalVariant, string> = {
    success: 'bg-green-600 text-white hover:bg-green-700',
    error: 'bg-red-600 text-white hover:bg-red-700',
    info: 'bg-blue-600 text-white hover:bg-blue-700',
    warning: 'bg-amber-600 text-white hover:bg-amber-700',
};

const cancelButtonClass = 'bg-gray-100 text-gray-700 hover:bg-gray-200';

const ConfirmModal: React.FC<ConfirmModalProps> = ({
    open,
    variant = 'warning',
    title,
    message,
    confirmLabel = 'تأیید',
    cancelLabel = 'انصراف',
    onConfirm,
    onCancel,
    dismissable = true,
}) => {
    useEffect(() => {
        if (!open || !dismissable) return;
        const onKeyDown = (ev: KeyboardEvent) => {
            if (ev.key === 'Escape') onCancel();
        };
        window.addEventListener('keydown', onKeyDown);
        return () => window.removeEventListener('keydown', onKeyDown);
    }, [open, dismissable, onCancel]);

    if (!open) return null;

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 animate-fade-in"
            role="dialog"
            aria-modal="true"
            onMouseDown={(e) => {
                if (!dismissable) return;
                if (e.target === e.currentTarget) onCancel();
            }}
        >
            <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl overflow-hidden animate-fade-in-up">
                <div className="p-5 border-b border-gray-100 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <div className={`w-2.5 h-2.5 rounded-full ${variantDotClass[variant]}`} />
                        <h4 className="font-bold text-gray-800">{title}</h4>
                    </div>
                    {dismissable && (
                        <button
                            onClick={onCancel}
                            className="text-gray-400 hover:text-gray-600 transition"
                            aria-label="بستن"
                            type="button"
                        >
                            ×
                        </button>
                    )}
                </div>

                <div className="p-5">
                    {!!message && (
                        <p className="text-sm text-gray-600 leading-6 whitespace-pre-wrap break-words">{message}</p>
                    )}

                    <div className="flex justify-end gap-2 mt-5">
                        <button
                            onClick={onCancel}
                            type="button"
                            className={`px-5 py-2.5 rounded-xl font-medium transition ${cancelButtonClass}`}
                        >
                            {cancelLabel}
                        </button>
                        <button
                            onClick={onConfirm}
                            type="button"
                            className={`px-5 py-2.5 rounded-xl font-medium transition ${confirmButtonClass[variant]}`}
                        >
                            {confirmLabel}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ConfirmModal;
