interface ConfirmRowProps {
  label: string;
  value: string;
  isNumeric?: boolean;
}

export default function ConfirmRow({ label, value, isNumeric = false }: ConfirmRowProps) {
  return (
    <div className="flex justify-between items-start sm:items-center gap-3 p-2.5 sm:p-3 px-3 sm:px-4 bg-parchment-warm rounded-[--radius-sm]">
      <span className="text-[0.82rem] sm:text-[0.85rem] text-soil-500 font-medium shrink-0">{label}</span>
      <span
        className="text-[0.88rem] sm:text-[0.95rem] font-semibold text-soil-800 text-left"
        dir={isNumeric ? "ltr" : undefined}
      >
        {value}
      </span>
    </div>
  );
}
