interface DeleteBarProps {
  count: number;
  onDelete: () => void;
  onCancel: () => void;
}

export default function DeleteBar({ count, onDelete, onCancel }: DeleteBarProps) {
  if (count === 0) return null;

  return (
    <div
      className="fixed bottom-0 left-0 right-0 bg-white border-t border-[#D8D0C4] shadow-lg p-3 px-6 z-40"
      style={{
        animation: "slideUp 0.25s ease-out both",
      }}
    >
      <div className="max-w-3xl mx-auto flex items-center justify-between gap-4">
        <span className="text-soil-800 font-semibold text-[0.9rem]">
          {count} נבחרו
        </span>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 text-soil-600 text-[0.85rem] font-medium rounded-[--radius-sm] hover:bg-parchment-warm active:scale-[0.98] transition-all cursor-pointer"
          >
            ביטול
          </button>
          <button
            type="button"
            onClick={onDelete}
            className="px-4 py-2 bg-terra-500 text-white text-[0.85rem] font-semibold rounded-[--radius-sm] hover:bg-terra-600 active:scale-[0.98] transition-all cursor-pointer"
          >
            מחק נבחרים
          </button>
        </div>
      </div>
    </div>
  );
}
