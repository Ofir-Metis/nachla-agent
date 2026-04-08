import type { PhaseStatus } from "@/hooks/useJobPolling";

interface ProgressNodeProps {
  status: PhaseStatus;
  stepNumber: number;
}

export default function ProgressNode({ status, stepNumber }: ProgressNodeProps) {
  const base =
    "w-[38px] h-[38px] sm:w-[40px] sm:h-[40px] rounded-full flex items-center justify-center shrink-0 z-10 text-sm font-semibold transition-all duration-300";

  switch (status) {
    case "completed":
      return (
        <div className={`${base} bg-olive-400 text-white`}>
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
            <path
              d="M4 9.5L7.5 13L14 5.5"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
      );

    case "running":
      return (
        <div
          className={`${base} bg-olive-700 text-white`}
          style={{ animation: "pulse-ring 2s ease-in-out infinite" }}
        >
          <span aria-hidden="true" className="text-base">&#9203;</span>
        </div>
      );

    case "checkpoint":
      return (
        <div className={`${base} bg-wheat-500 text-white`}>
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
            <path d="M9 4V10" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
            <circle cx="9" cy="13.5" r="1.2" fill="currentColor" />
          </svg>
        </div>
      );

    case "failed":
      return (
        <div className={`${base} bg-error text-white`}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M4 4L12 12M12 4L4 12" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
          </svg>
        </div>
      );

    case "pending":
    default:
      return (
        <div className={`${base} bg-parchment-warm border-2 border-[#D8D0C4] text-soil-500`}>
          {stepNumber}
        </div>
      );
  }
}
