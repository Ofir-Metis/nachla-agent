interface ToggleButtonsProps {
  name: string;
  value: boolean | null;
  onChange: (value: boolean) => void;
  label?: string;
  helpText?: string;
  required?: boolean;
  error?: string;
  yesLabel?: string;
  noLabel?: string;
}

export default function ToggleButtons({
  name,
  value,
  onChange,
  label,
  helpText,
  required,
  error,
  yesLabel = "כן",
  noLabel = "לא",
}: ToggleButtonsProps) {
  return (
    <div className="space-y-2">
      {label && (
        <label className="block text-lg font-semibold text-soil-800">
          {label}
          {required && <span className="text-terra-500 ms-0.5">*</span>}
        </label>
      )}

      <div className="flex gap-2.5">
        <button
          type="button"
          name={`${name}-yes`}
          aria-pressed={value === true}
          onClick={() => onChange(true)}
          className={[
            "flex-1 py-3.5 px-5 rounded-[--radius-md] font-semibold text-base transition-all border-[1.5px] cursor-pointer",
            value === true
              ? "bg-olive-700 text-white border-olive-600"
              : "bg-white text-soil-600 border-[#D8D0C4] hover:border-olive-300 hover:bg-olive-50",
          ].join(" ")}
        >
          {yesLabel}
        </button>

        <button
          type="button"
          name={`${name}-no`}
          aria-pressed={value === false}
          onClick={() => onChange(false)}
          className={[
            "flex-1 py-3.5 px-5 rounded-[--radius-md] font-semibold text-base transition-all border-[1.5px] cursor-pointer",
            value === false
              ? "bg-soil-600 text-white border-soil-500"
              : "bg-white text-soil-600 border-[#D8D0C4] hover:border-olive-300 hover:bg-olive-50",
          ].join(" ")}
        >
          {noLabel}
        </button>
      </div>

      {error && (
        <p role="alert" className="text-[0.8rem] text-error mt-1 leading-normal">{error}</p>
      )}

      {helpText && !error && (
        <p className="text-[0.8rem] text-soil-500 mt-1.5 leading-normal">{helpText}</p>
      )}
    </div>
  );
}
