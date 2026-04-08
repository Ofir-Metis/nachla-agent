import type { JobSummary } from "@/types";
import { PHASE_LABELS } from "@/lib/labels";

interface JobCardProps {
  job: JobSummary;
  selected: boolean;
  onSelect: (jobId: string) => void;
  onAction: (job: JobSummary) => void;
  type: "progress" | "completed";
}

const PHASE_BADGE_STYLES: Record<string, string> = {
  intake: "bg-olive-100 text-olive-700",
  taba_analysis: "bg-info/10 text-info",
  building_mapping: "bg-wheat-100 text-wheat-700",
  classification_checkpoint: "bg-warning/10 text-warning",
  calculations: "bg-olive-200 text-olive-800",
  report: "bg-olive-300 text-olive-900",
};

function formatDate(dateStr: string): string {
  try {
    return new Intl.DateTimeFormat("he-IL", {
      day: "numeric",
      month: "short",
      year: "numeric",
    }).format(new Date(dateStr));
  } catch {
    return dateStr;
  }
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("he-IL", {
    style: "currency",
    currency: "ILS",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

export default function JobCard({ job, selected, onSelect, onAction, type }: JobCardProps) {
  const isCompleted = type === "completed";
  const phaseLabel = PHASE_LABELS[job.phase] ?? job.phase;
  const badgeStyle = PHASE_BADGE_STYLES[job.phase] ?? "bg-olive-100 text-olive-700";

  return (
    <div
      className={`
        bg-white border rounded-[--radius-md] p-3 sm:p-4
        transition-all duration-200 ease-out
        hover:shadow-sm hover:-translate-y-px
        ${selected ? "bg-olive-50 border-olive-300" : "border-[#D8D0C4]"}
      `}
      style={{ animation: "cardIn 0.3s ease-out both" }}
    >
      <div className="flex items-center gap-3 sm:gap-4">
        {/* Checkbox */}
        <label className="flex items-center shrink-0 cursor-pointer">
          <input
            type="checkbox"
            checked={selected}
            onChange={() => onSelect(job.job_id)}
            className="sr-only peer"
            aria-label={`בחר בדיקה של ${job.owner_name} - ${job.moshav_name}`}
          />
          <span
            className={`
              w-6 h-6 rounded-[6px] border-2 flex items-center justify-center transition-all
              ${selected
                ? "bg-olive-600 border-olive-600"
                : "border-[#C4B8A8] bg-white peer-hover:border-olive-400"
              }
            `}
          >
            {selected && (
              <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            )}
          </span>
        </label>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-soil-800 truncate">{job.owner_name}</div>
          <div className="text-[0.85rem] text-soil-500 truncate">{job.moshav_name}</div>
        </div>

        {/* Phase badge or completion info — desktop */}
        <div className="hidden sm:flex flex-col items-end gap-1 shrink-0 text-left">
          {isCompleted ? (
            <>
              {job.completed_at && (
                <span className="text-[0.78rem] text-soil-500">
                  {formatDate(job.completed_at)}
                </span>
              )}
              {job.total_cost != null && (
                <span className="text-[0.85rem] font-semibold text-olive-700">
                  {formatCurrency(job.total_cost)}
                </span>
              )}
            </>
          ) : (
            <>
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[0.78rem] font-semibold ${badgeStyle}`}
              >
                {phaseLabel}
              </span>
              <span className="text-[0.78rem] text-soil-500">
                {formatDate(job.created_at)}
              </span>
            </>
          )}
        </div>

        {/* Action button */}
        <button
          type="button"
          onClick={() => onAction(job)}
          className={`
            shrink-0 px-3 sm:px-4 py-2 rounded-[--radius-sm] text-[0.82rem] sm:text-[0.85rem] font-semibold
            transition-all duration-150 cursor-pointer
            ${isCompleted
              ? "bg-olive-100 text-olive-700 hover:bg-olive-200"
              : "bg-olive-600 text-white hover:bg-olive-700"
            }
          `}
        >
          {isCompleted ? "תוצאות" : "המשך"}
        </button>
      </div>

      {/* Phase badge or completion info — mobile (below content) */}
      <div className="flex sm:hidden items-center gap-2 mt-2 ps-9">
        {isCompleted ? (
          <>
            {job.completed_at && (
              <span className="text-[0.78rem] text-soil-500">
                {formatDate(job.completed_at)}
              </span>
            )}
            {job.total_cost != null && (
              <span className="text-[0.85rem] font-semibold text-olive-700 ms-auto">
                {formatCurrency(job.total_cost)}
              </span>
            )}
          </>
        ) : (
          <>
            <span
              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[0.78rem] font-semibold ${badgeStyle}`}
            >
              {phaseLabel}
            </span>
            <span className="text-[0.78rem] text-soil-500 ms-auto">
              {formatDate(job.created_at)}
            </span>
          </>
        )}
      </div>
    </div>
  );
}
