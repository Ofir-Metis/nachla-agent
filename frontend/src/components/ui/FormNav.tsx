interface FormNavProps {
  onNext?: () => void;
  onBack?: () => void;
  nextLabel?: string;
  backLabel?: string;
  showBack?: boolean;
  nextDisabled?: boolean;
}

export default function FormNav({
  onNext,
  onBack,
  nextLabel = "המשך",
  backLabel = "הקודם",
  showBack = false,
  nextDisabled = false,
}: FormNavProps) {
  return (
    <div className="flex flex-col-reverse sm:flex-row gap-3 mt-5 sm:mt-6 pt-4 sm:pt-5 border-t border-[#D8D0C4] max-sm:sticky max-sm:bottom-0 max-sm:bg-[rgba(255,253,248,0.95)] max-sm:backdrop-blur-sm max-sm:border-t max-sm:border-[#D8D0C4] max-sm:z-20 max-sm:pb-3 max-sm:-mx-5 max-sm:px-5">
      {/* Back button (right side in RTL) */}
      {showBack && (
        <button
          type="button"
          onClick={onBack}
          className="px-6 py-3 sm:py-3.5 rounded-[--radius-md] font-semibold text-[0.95rem] sm:text-base bg-transparent text-soil-600 border-[1.5px] border-[#D8D0C4] hover:border-olive-300 hover:bg-olive-50 active:translate-y-0 transition-all cursor-pointer flex items-center justify-center gap-2"
        >
          <span className="text-[1.1em]">&rarr;</span>
          <span>{backLabel}</span>
        </button>
      )}

      {/* Next button (left side in RTL, pushed via ms-auto) */}
      {onNext && (
        <button
          type="button"
          onClick={onNext}
          disabled={nextDisabled}
          className="sm:ms-auto px-8 py-3 sm:py-3.5 rounded-[--radius-md] font-semibold text-[0.95rem] sm:text-base bg-olive-700 text-white shadow-[--shadow-sm] hover:bg-olive-600 hover:shadow-[--shadow-md] hover:-translate-y-px active:translate-y-0 transition-all cursor-pointer flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0"
        >
          <span>{nextLabel}</span>
          <span className="text-[1.1em]">&larr;</span>
        </button>
      )}
    </div>
  );
}
