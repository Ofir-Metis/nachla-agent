interface CardCheckboxProps {
  value: string;
  label: string;
  description?: string;
  icon?: string;
  selected: boolean;
  onClick: (value: string) => void;
}

export default function CardCheckbox({
  value,
  label,
  description,
  icon,
  selected,
  onClick,
}: CardCheckboxProps) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={selected}
      onClick={() => onClick(value)}
      className={[
        "p-4 border-[1.5px] rounded-[--radius-md] bg-white cursor-pointer text-center relative transition-all",
        selected
          ? "border-olive-600 bg-olive-50 ring-2 ring-olive-600/20 shadow-[--shadow-sm]"
          : "border-[#D8D0C4] hover:border-olive-300 hover:bg-olive-50",
      ].join(" ")}
    >
      {/* Checkmark indicator */}
      <div
        className={[
          "absolute top-2.5 start-2.5 w-[22px] h-[22px] rounded-md border-[1.5px] flex items-center justify-center transition-all",
          selected
            ? "border-olive-600 bg-olive-600"
            : "border-[#D8D0C4] bg-white",
        ].join(" ")}
      >
        {selected && (
          <svg
            width="12"
            height="10"
            viewBox="0 0 12 10"
            fill="none"
            className="text-white"
          >
            <path
              d="M1 5L4.5 8.5L11 1.5"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        )}
      </div>

      {icon && <div className="text-2xl mb-1.5">{icon}</div>}

      <div className="font-semibold text-[0.88rem] text-soil-800">{label}</div>

      {description && (
        <div className="text-[0.78rem] text-soil-500 mt-0.5">{description}</div>
      )}
    </button>
  );
}
