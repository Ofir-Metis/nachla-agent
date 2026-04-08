interface AlertWarningProps {
  icon?: string;
  message: string;
  visible: boolean;
}

export default function AlertWarning({
  icon = "\u26A0\uFE0F",
  message,
  visible,
}: AlertWarningProps) {
  if (!visible) return null;

  return (
    <div
      className="flex gap-2.5 p-3.5 px-4 bg-[#FFF8E1] border border-[#FFD54F] rounded-[--radius-md] mt-3 animate-[alertIn_0.3s_ease-out]"
      role="alert"
    >
      <span className="text-[1.2rem] shrink-0">{icon}</span>
      <p className="text-[0.85rem] text-[#7B6B1A] leading-normal m-0">
        {message}
      </p>
    </div>
  );
}
