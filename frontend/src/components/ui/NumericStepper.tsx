interface NumericStepperProps {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  label: string;
  helpText?: string;
  required?: boolean;
}

export default function NumericStepper({
  value,
  onChange,
  min = 0,
  max = 10,
  label,
  helpText,
  required,
}: NumericStepperProps) {
  const decrement = () => {
    if (value > min) onChange(value - 1);
  };

  const increment = () => {
    if (value < max) onChange(value + 1);
  };

  return (
    <div className="space-y-2">
      <label className="block text-lg font-semibold text-soil-800">
        {label}
        {required && <span className="text-terra-500 ms-0.5">*</span>}
      </label>

      <div className="flex w-fit" dir="ltr" role="group" aria-label={label}>
        <button
          type="button"
          onClick={decrement}
          disabled={value <= min}
          aria-label="הפחת"
          className="w-12 h-12 flex items-center justify-center border-[1.5px] border-[#D8D0C4] bg-white rounded-l-[--radius-md] text-olive-700 font-semibold text-[1.4rem] hover:bg-olive-50 hover:border-olive-300 active:scale-95 transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
        >
          &minus;
        </button>

        <div
          className="w-16 h-12 flex items-center justify-center border-y-[1.5px] border-[#D8D0C4] bg-white font-heading text-[1.25rem] font-bold text-soil-800"
          dir="ltr"
          role="status"
          aria-live="polite"
          aria-label={`ערך נוכחי: ${value}`}
        >
          {value}
        </div>

        <button
          type="button"
          onClick={increment}
          disabled={value >= max}
          aria-label="הוסף"
          className="w-12 h-12 flex items-center justify-center border-[1.5px] border-[#D8D0C4] bg-white rounded-r-[--radius-md] text-olive-700 font-semibold text-[1.4rem] hover:bg-olive-50 hover:border-olive-300 active:scale-95 transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
        >
          +
        </button>
      </div>

      {helpText && (
        <p className="text-[0.8rem] text-soil-500 mt-1.5 leading-normal">
          {helpText}
        </p>
      )}
    </div>
  );
}
