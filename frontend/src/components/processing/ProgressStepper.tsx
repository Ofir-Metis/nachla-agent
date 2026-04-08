import type { PhaseInfo } from "@/hooks/useJobPolling";
import { PHASE_LABELS } from "@/lib/labels";
import ProgressNode from "./ProgressNode";
import ProgressBar from "./ProgressBar";

const PHASE_DESCRIPTIONS: Record<string, string> = {
  intake: "קליטת פרטי הלקוח והמסמכים",
  taba_analysis: 'שליפה וניתוח של תכנית בניין עיר',
  building_mapping: "זיהוי מבנים ממפת המדידה",
  classification_checkpoint: "סיווג המבנים לאישורכם",
  calculations: 'חישוב דמי היתר, שימוש, היוון ופיצול',
  report: "יצירת דוח מקצועי בפורמט Word ו-Excel",
};

const STATUS_LABELS: Record<string, string> = {
  completed: "הושלם",
  running: "פעיל כעת",
  checkpoint: "ממתין לאישור",
  failed: "נכשל",
  pending: "ממתין",
};

interface ProgressStepperProps {
  phases: PhaseInfo[];
}

export default function ProgressStepper({ phases }: ProgressStepperProps) {
  const runningPhase = phases.find((p) => p.status === "running");

  return (
    <div
      className="flex flex-col"
      dir="rtl"
      role="list"
      aria-label="שלבי הבדיקה"
    >
      {/* Live region for screen reader announcements */}
      <div aria-live="polite" className="sr-only">
        {runningPhase
          ? `שלב פעיל: ${PHASE_LABELS[runningPhase.id] ?? runningPhase.id} - ${PHASE_DESCRIPTIONS[runningPhase.id] ?? ""}`
          : null}
      </div>

      {phases.map((phase, index) => {
        const isLast = index === phases.length - 1;
        const lineColor =
          phase.status === "completed" ? "bg-olive-400" : "bg-[#D8D0C4]";

        return (
          <div
            key={phase.id}
            className="flex flex-row gap-4 py-4 relative"
            role="listitem"
            aria-current={phase.status === "running" ? "step" : undefined}
            aria-label={`${PHASE_LABELS[phase.id] ?? phase.id}: ${STATUS_LABELS[phase.status] ?? phase.status}`}
          >
            {/* Connecting line */}
            {!isLast && (
              <div
                className={`absolute right-[19px] top-[48px] sm:top-[52px] bottom-0 w-[2px] ${lineColor}`}
                aria-hidden="true"
              />
            )}

            {/* Node */}
            <ProgressNode status={phase.status} stepNumber={index + 1} />

            {/* Phase info */}
            <div className="flex flex-col justify-center min-w-0 flex-1">
              <span className="font-semibold text-[0.95rem] text-soil-800">
                {PHASE_LABELS[phase.id] ?? phase.id}
              </span>
              <span
                className="text-[0.82rem] text-soil-500"
                {...(phase.status === "running" ? { role: "status" } : {})}
              >
                {PHASE_DESCRIPTIONS[phase.id] ?? ""}
              </span>

              {/* Progress bar for active phase */}
              {phase.status === "running" &&
                phase.progressPercent !== undefined && (
                  <ProgressBar
                    percent={phase.progressPercent}
                    timeEstimate={phase.timeEstimate}
                  />
                )}

              {/* Checkpoint hint */}
              {phase.status === "checkpoint" && (
                <span className="text-[0.82rem] text-wheat-700 font-medium mt-1">
                  ממתין לאישורכם
                </span>
              )}

              {/* Failed hint */}
              {phase.status === "failed" && (
                <span className="text-[0.82rem] text-error font-medium mt-1">
                  אירעה שגיאה בשלב זה
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
