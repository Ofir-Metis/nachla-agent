import { forwardRef, type InputHTMLAttributes } from "react";

interface TextInputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  helpText?: string;
  error?: string;
  datalistOptions?: string[];
}

const TextInput = forwardRef<HTMLInputElement, TextInputProps>(
  ({ label, helpText, error, required, datalistOptions, id, name, className = "", ...rest }, ref) => {
    const inputId = id ?? name ?? label;
    const listId = datalistOptions ? `${inputId}-list` : undefined;
    const helpId = helpText ? `${inputId}-help` : undefined;
    const errorId = `${inputId}-error`;

    // Build aria-describedby: always include help id when helpText exists
    // (the element stays in DOM as sr-only so the reference is valid).
    const describedBy = [helpId, error ? errorId : undefined]
      .filter(Boolean)
      .join(" ") || undefined;

    return (
      <div className="space-y-2">
        <label htmlFor={inputId} className="block text-lg font-semibold text-soil-800">
          {label}
          {required && <span className="text-terra-500 ms-0.5">*</span>}
        </label>

        <input
          ref={ref}
          id={inputId}
          name={name}
          list={listId}
          aria-invalid={!!error}
          aria-describedby={describedBy}
          aria-errormessage={error ? errorId : undefined}
          className={[
            "w-full px-4 py-3.5 font-[inherit] text-base text-soil-800 bg-white",
            "border-[1.5px] rounded-[--radius-md] outline-none transition-all",
            "placeholder:text-[#B5ADA2] placeholder:font-light",
            error
              ? "border-error"
              : "border-[#D8D0C4] focus:border-olive-600 focus:shadow-[0_0_0_3px_rgba(61,90,62,0.1)]",
            className,
          ].join(" ")}
          {...rest}
        />

        {datalistOptions && (
          <datalist id={listId}>
            {datalistOptions.map((opt) => (
              <option key={opt} value={opt} />
            ))}
          </datalist>
        )}

        {error && (
          <p id={errorId} role="alert" className="text-[0.8rem] text-error mt-1 leading-normal">
            {error}
          </p>
        )}

        {/* Help text stays in DOM (sr-only when error is shown) so that
            aria-describedby always resolves to a valid element. */}
        {helpText && (
          <p
            id={helpId}
            className={
              error
                ? "sr-only"
                : "text-[0.8rem] text-soil-500 mt-1.5 leading-normal"
            }
          >
            {helpText}
          </p>
        )}
      </div>
    );
  }
);

TextInput.displayName = "TextInput";

export default TextInput;
