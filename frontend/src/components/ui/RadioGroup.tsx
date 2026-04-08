interface RadioOption {
  value: string;
  label: string;
  description?: string;
}

interface RadioGroupProps {
  name: string;
  options: RadioOption[];
  value: string | undefined;
  onChange: (value: string) => void;
  label?: string;
  required?: boolean;
  error?: string;
}

export default function RadioGroup({
  name,
  options,
  value,
  onChange,
  label,
  required,
  error,
}: RadioGroupProps) {
  return (
    <fieldset className="space-y-2">
      {label && (
        <legend className="block text-lg font-semibold text-soil-800 mb-2">
          {label}
          {required && <span className="text-terra-500 ms-0.5">*</span>}
        </legend>
      )}

      <div className="flex flex-col gap-2.5">
        {options.map((opt) => {
          const isSelected = value === opt.value;
          return (
            <label
              key={opt.value}
              className={[
                "flex gap-3 p-3.5 px-4 rounded-[--radius-md] cursor-pointer transition-all border-[1.5px] has-[:focus-visible]:outline has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-olive-600 has-[:focus-visible]:outline-offset-2",
                isSelected
                  ? "border-olive-600 bg-olive-50 shadow-[0_0_0_3px_rgba(61,90,62,0.1)]"
                  : "border-[#D8D0C4] bg-white hover:border-olive-300 hover:bg-olive-50",
              ].join(" ")}
            >
              <input
                type="radio"
                name={name}
                value={opt.value}
                checked={isSelected}
                onChange={() => onChange(opt.value)}
                className="sr-only"
              />

              {/* Custom radio dot */}
              <span
                className={[
                  "mt-0.5 shrink-0 w-[22px] h-[22px] rounded-full border-2 flex items-center justify-center transition-colors",
                  isSelected ? "border-olive-600 bg-olive-600" : "border-[#D8D0C4] bg-white",
                ].join(" ")}
                aria-hidden="true"
              >
                {isSelected && <span className="w-2 h-2 rounded-full bg-white" />}
              </span>

              <span>
                <span className="block text-[0.95rem] font-semibold text-soil-800">
                  {opt.label}
                </span>
                {opt.description && (
                  <span className="block text-[0.8rem] text-soil-500 mt-0.5">
                    {opt.description}
                  </span>
                )}
              </span>
            </label>
          );
        })}
      </div>

      {error && (
        <p role="alert" className="text-[0.8rem] text-error mt-1 leading-normal">{error}</p>
      )}
    </fieldset>
  );
}
