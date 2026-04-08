interface ErrorStateProps {
  message: string;
  detail?: string;
  onRetry: () => void;
}

export default function ErrorState({ message, detail, onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center gap-4 py-8" dir="rtl">
      {/* Error icon */}
      <div className="w-12 h-12 rounded-full bg-error flex items-center justify-center">
        <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">
          <path
            d="M6 6L16 16M16 6L6 16"
            stroke="white"
            strokeWidth="2.5"
            strokeLinecap="round"
          />
        </svg>
      </div>

      {/* Message */}
      <p className="text-[1rem] font-semibold text-soil-800 text-center">{message}</p>

      {/* Detail */}
      {detail && (
        <p className="text-[0.85rem] text-soil-500 text-center max-w-md">{detail}</p>
      )}

      {/* Actions */}
      <div className="flex gap-3 mt-2">
        <button
          type="button"
          onClick={onRetry}
          className="px-6 py-2.5 rounded-[--radius-md] font-semibold text-[0.9rem] bg-olive-700 text-white hover:bg-olive-600 active:scale-[0.98] transition-all cursor-pointer"
        >
          נסה שוב
        </button>
        <a
          href="tel:*9696"
          className="px-6 py-2.5 rounded-[--radius-md] font-semibold text-[0.9rem] border-[1.5px] border-[#D8D0C4] text-soil-600 hover:border-olive-300 hover:bg-olive-50 active:scale-[0.98] transition-all no-underline"
        >
          צרו קשר
        </a>
      </div>
    </div>
  );
}
