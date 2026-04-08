import { useEffect, useRef, useCallback } from "react";

interface DeleteConfirmModalProps {
  count: number;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function DeleteConfirmModal({ count, onConfirm, onCancel }: DeleteConfirmModalProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);
  const confirmRef = useRef<HTMLButtonElement>(null);

  // Auto-focus the cancel button on open
  useEffect(() => {
    cancelRef.current?.focus();
  }, []);

  // Close on Escape + focus trap (Tab/Shift+Tab stays within modal)
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === "Escape") {
      onCancel();
      return;
    }
    if (e.key === "Tab") {
      const focusable = [cancelRef.current, confirmRef.current].filter(Boolean) as HTMLElement[];
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  }, [onCancel]);

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  return (
    <div
      className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-modal-title"
        className="bg-white rounded-[--radius-lg] p-6 max-w-sm w-full shadow-lg"
        style={{ animation: "cardIn 0.2s ease-out both" }}
      >
        <div className="text-center mb-4">
          <div className="text-3xl mb-2" aria-hidden="true">&#9888;</div>
          <h3
            id="delete-modal-title"
            className="font-heading text-[1.1rem] font-bold text-soil-800"
          >
            מחיקת בדיקות
          </h3>
        </div>

        <p className="text-center text-soil-600 text-[0.9rem] mb-6 leading-relaxed">
          האם למחוק {count} בדיקות? פעולה זו אינה ניתנת לביטול.
        </p>

        <div className="flex gap-3 justify-center">
          <button
            ref={cancelRef}
            type="button"
            onClick={onCancel}
            className="px-5 py-2.5 border border-[#D8D0C4] text-soil-600 text-[0.85rem] font-medium rounded-[--radius-sm] hover:bg-parchment-warm active:scale-[0.98] transition-all cursor-pointer"
          >
            ביטול
          </button>
          <button
            ref={confirmRef}
            type="button"
            onClick={onConfirm}
            className="px-5 py-2.5 bg-terra-500 text-white text-[0.85rem] font-semibold rounded-[--radius-sm] hover:bg-terra-600 active:scale-[0.98] transition-all cursor-pointer"
          >
            מחק
          </button>
        </div>
      </div>
    </div>
  );
}
