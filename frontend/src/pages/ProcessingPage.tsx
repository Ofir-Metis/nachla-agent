import { useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useJobPolling } from "@/hooks/useJobPolling";
import ProgressStepper from "@/components/processing/ProgressStepper";
import ErrorState from "@/components/processing/ErrorState";
import FocusManager from "@/components/ui/FocusManager";

export default function ProcessingPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data, isLoading, phases, isCheckpoint, isComplete, isFailed } =
    useJobPolling(jobId);

  // Auto-navigate to results when complete
  useEffect(() => {
    if (isComplete && jobId) {
      navigate(`/jobs/${jobId}/results`, { replace: true });
    }
  }, [isComplete, jobId, navigate]);

  const handleRetry = () => {
    queryClient.invalidateQueries({ queryKey: ["job-status", jobId] });
  };

  return (
    <FocusManager focusKey="processing">
    <div>
      <button
        type="button"
        onClick={() => navigate("/")}
        className="mb-2 flex items-center gap-1.5 text-[0.85rem] text-soil-500 hover:text-olive-700 transition-colors cursor-pointer bg-transparent border-none"
      >
        <span>&rarr;</span>
        <span>חזרה לרשימת הבדיקות</span>
      </button>
    <div
      dir="rtl"
      className="bg-cream border border-[#D8D0C4] rounded-[--radius-lg] sm:rounded-[--radius-xl] p-5 sm:p-7 sm:px-8 shadow-[--shadow-md] relative overflow-hidden animate-[cardIn_0.4s_ease-out]"
    >
      {/* Gradient top bar */}
      <div
        className="absolute top-0 right-0 left-0 h-1 bg-gradient-to-l from-olive-700 via-olive-400 to-wheat-400"
        aria-hidden="true"
      />

      {/* Header */}
      <div className="mb-6">
        <h1 tabIndex={-1} className="outline-none font-heading text-[1.35rem] font-bold text-olive-800 mb-1">
          <span aria-hidden="true" className="ml-2">&#128300;</span>
          הבדיקה מתבצעת
        </h1>
        <p className="text-[0.9rem] text-soil-500">
          המערכת מנתחת את הנתונים. אין צורך לעשות דבר.
        </p>
      </div>

      {/* Loading skeleton */}
      {isLoading && !data && (
        <div className="flex flex-col gap-4 py-8 animate-pulse">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="flex gap-4 items-center">
              <div className="w-10 h-10 rounded-full bg-olive-100" />
              <div className="flex-1 space-y-2">
                <div className="h-4 bg-olive-100 rounded w-1/3" />
                <div className="h-3 bg-olive-50 rounded w-1/2" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Failed state */}
      {isFailed && (
        <ErrorState
          message={data?.message ?? "אירעה שגיאה בתהליך הבדיקה"}
          detail="אם הבעיה חוזרת, אנא צרו קשר עם צוות התמיכה."
          onRetry={handleRetry}
        />
      )}

      {/* Progress stepper — show when not failed and data exists */}
      {!isFailed && data && <ProgressStepper phases={phases} />}

      {/* Status message */}
      {data?.message && !isFailed && (
        <div className="mt-4 py-3 px-4 bg-olive-50 rounded-[--radius-md] border border-olive-200">
          <p className="text-[0.85rem] text-olive-700">{data.message}</p>
        </div>
      )}

      {/* Checkpoint button */}
      {isCheckpoint && (
        <div className="mt-6 flex">
          <button
            type="button"
            className="ms-auto px-6 py-2.5 rounded-[--radius-md] font-semibold text-[0.9rem] bg-olive-700 text-white hover:bg-olive-600 active:scale-[0.98] transition-all cursor-pointer flex items-center gap-1"
            onClick={() => navigate(`/jobs/${jobId}/checkpoint`)}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="none"
              className="inline-block ml-1"
              aria-hidden="true"
            >
              <path d="M9 3L4 8L9 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            לאישור סיווג המבנים
          </button>
        </div>
      )}
    </div>
    </div>
    </FocusManager>
  );
}
