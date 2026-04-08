import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useWizardContext } from "@/context/WizardContext";
import { intakeSchema } from "@/schemas/intake";
import { submitIntake, uploadFilesWithProgress } from "@/lib/api";
import ConfirmGrid from "@/components/confirm/ConfirmGrid";
import FocusManager from "@/components/ui/FocusManager";
import { useOnlineStatus } from "@/hooks/useOnlineStatus";
import type { IntakeData } from "@/types";

export default function ConfirmPage() {
  const navigate = useNavigate();
  const { formData, files, setJobId, clearDraft } = useWizardContext();

  const isOnline = useOnlineStatus();
  const [submitting, setSubmitting] = useState(false);
  const [submitPhase, setSubmitPhase] = useState<"data" | "files" | null>(null);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Route guard: redirect if form data is empty
  useEffect(() => {
    if (!formData.owner_name && !formData.moshav_name) {
      navigate("/intake", { replace: true });
    }
  }, [formData, navigate]);

  // Count non-null files
  const fileCount = Object.values(files).filter(Boolean).length;

  const handleStartProcessing = async () => {
    setError(null);

    // Validate the full intake schema before submitting
    const parsed = intakeSchema.safeParse(formData);
    if (!parsed.success) {
      const firstError = parsed.error.issues[0];
      setError(firstError?.message ?? "הנתונים שהוזנו אינם תקינים. אנא חזרו לטופס ובדקו.");
      return;
    }

    try {
      setSubmitting(true);

      // 1. Submit intake data
      setSubmitPhase("data");
      const response = await submitIntake(parsed.data as IntakeData);
      const jobId = response.job_id;

      // 2. Upload files (only non-null ones)
      const validFiles: Record<string, File> = {};
      for (const [key, file] of Object.entries(files)) {
        if (file) validFiles[key] = file;
      }

      if (Object.keys(validFiles).length > 0) {
        setSubmitPhase("files");
        setUploadProgress(0);
        await uploadFilesWithProgress(jobId, validFiles, setUploadProgress);
      }

      // 3. Update context and clear draft
      setJobId(jobId);
      clearDraft();

      // 4. Navigate to processing
      navigate(`/jobs/${jobId}/processing`);
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "אירעה שגיאה בשליחת הנתונים. אנא נסו שנית.";
      setError(message);
    } finally {
      setSubmitting(false);
      setSubmitPhase(null);
      setUploadProgress(null);
    }
  };

  return (
    <FocusManager focusKey="confirm">
    <div>
      <button
        type="button"
        onClick={() => navigate("/")}
        className="mb-2 flex items-center gap-1.5 text-[0.85rem] text-soil-500 hover:text-olive-700 transition-colors cursor-pointer bg-transparent border-none"
      >
        <span>&rarr;</span>
        <span>חזרה לרשימת הבדיקות</span>
      </button>
    <div className="animate-[cardIn_0.4s_ease-out]">
      <div className="bg-cream border border-[#D8D0C4] rounded-[--radius-lg] sm:rounded-[--radius-xl] p-5 sm:p-7 sm:px-8 shadow-[--shadow-md] relative overflow-hidden">
        {/* Top gradient bar */}
        <div className="absolute top-0 right-0 left-0 h-1 bg-gradient-to-l from-olive-700 via-olive-400 to-wheat-400" />

        <h1 tabIndex={-1} className="outline-none font-heading text-[1.35rem] font-bold text-olive-800 mb-1.5">
          סיכום לפני ניתוח
        </h1>
        <p className="text-[0.9rem] text-soil-600 mb-7 leading-relaxed">
          בדקו את הנתונים לפני שנתחיל בבדיקה
        </p>

        {/* Error banner */}
        {error && (
          <div role="alert" className="mb-5 p-3 bg-error/10 border border-error/30 rounded-[--radius-sm] text-error text-[0.85rem] animate-[alertIn_0.3s_ease-out]">
            {error}
          </div>
        )}

        <ConfirmGrid formData={formData} fileCount={fileCount} />

        {/* Navigation */}
        <div className="flex flex-col-reverse sm:flex-row gap-3 mt-6 sm:mt-8 pt-5 sm:pt-6 border-t border-[#D8D0C4] max-sm:sticky max-sm:bottom-0 max-sm:bg-[rgba(255,253,248,0.95)] max-sm:backdrop-blur-sm max-sm:z-20 max-sm:pb-3 max-sm:-mx-5 max-sm:px-5">
          {/* Back button */}
          <button
            type="button"
            onClick={() => navigate("/upload")}
            disabled={submitting}
            className="px-6 py-3 sm:py-3.5 rounded-[--radius-md] font-semibold text-[0.95rem] sm:text-base bg-transparent text-soil-600 border-[1.5px] border-[#D8D0C4] hover:border-olive-300 hover:bg-olive-50 active:translate-y-0 transition-all cursor-pointer flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span className="text-[1.1em]">&rarr;</span>
            <span>חזרה לעריכה</span>
          </button>

          {/* Start processing button */}
          <button
            type="button"
            onClick={handleStartProcessing}
            disabled={submitting || !isOnline}
            className="sm:ms-auto px-8 py-3 sm:py-3.5 rounded-[--radius-md] font-semibold text-[0.95rem] sm:text-base bg-success text-white shadow-[--shadow-sm] hover:brightness-110 hover:shadow-[--shadow-md] hover:-translate-y-px active:translate-y-0 transition-all cursor-pointer flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? (
              <>
                <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>
                  {submitPhase === "files" && uploadProgress !== null
                    ? `מעלה קבצים... ${uploadProgress}%`
                    : "שולח נתונים..."}
                </span>
              </>
            ) : (
              <span>התחל ניתוח</span>
            )}
          </button>
        </div>
      </div>
    </div>
    </div>
    </FocusManager>
  );
}
