import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useWizardContext } from "@/context/WizardContext";
import { extractDocuments } from "@/lib/api";
import UploadGrid from "@/components/upload/UploadGrid";
import OptionalSection from "@/components/upload/OptionalSection";
import FormNav from "@/components/ui/FormNav";
import FocusManager from "@/components/ui/FocusManager";

type ExtractionPhase = "idle" | "uploading" | "analyzing" | "done" | "error";

function getPhaseLabel(phase: string, elapsed: number): string {
  if (phase === "uploading") return "מעלה מסמכים...";
  if (elapsed < 30) return "מנתח מסמכים באמצעות AI...";
  if (elapsed < 60) return "מזהה מבנים ותב\"עות...";
  if (elapsed < 90) return "מעבד נתונים שנמצאו...";
  return "כמעט סיימנו...";
}

function getPhaseSubtext(phase: string, elapsed: number): string {
  if (phase === "uploading") return "שולח את הקבצים לשרת";
  if (elapsed < 60) return "התהליך עשוי לקחת עד שתי דקות";
  return "עוד רגע מסיימים — אנא המתינו";
}

export default function UploadPage() {
  const navigate = useNavigate();
  const { formData, files, setFile, setExtractedData } = useWizardContext();
  const [permitOptOut, setPermitOptOut] = useState(false);
  const [phase, setPhase] = useState<ExtractionPhase>("idle");
  const [progress, setProgress] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // Route guard
  useEffect(() => {
    if (!formData.owner_name && !formData.moshav_name) {
      navigate("/intake", { replace: true });
    }
  }, [formData, navigate]);

  // Elapsed timer during extraction
  useEffect(() => {
    if (phase !== "uploading" && phase !== "analyzing") return;
    const interval = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(interval);
  }, [phase]);

  const handleFileChange = (id: string, file: File | null) => {
    setFile(id, file);
  };

  const handleExtract = useCallback(async () => {
    setError(null);
    setPhase("uploading");
    setProgress(0);
    setElapsed(0);

    const validFiles: Record<string, File> = {};
    for (const [key, file] of Object.entries(files)) {
      if (file) validFiles[key] = file;
    }

    if (Object.keys(validFiles).length === 0) {
      // No files — skip extraction and go to validate/taba
      navigate("/validate");
      return;
    }

    // Simulated progress for AI analysis phase (30%-90% over ~120 seconds)
    let progressTimer: ReturnType<typeof setInterval> | null = null;

    try {
      const result = await extractDocuments(validFiles, (pct) => {
        setProgress(pct);
        if (pct >= 30 && !progressTimer) {
          setPhase("analyzing");
          // Start gradual progress animation while AI works
          progressTimer = setInterval(() => {
            setProgress((prev) => (prev >= 90 ? 90 : prev + 0.5));
          }, 1000);
        }
      });

      if (progressTimer) clearInterval(progressTimer);
      setProgress(100);
      setPhase("done");
      setExtractedData(result.buildings, result.tabas as unknown as import("@/types").TabaData[], result.warnings);
      navigate("/validate");
    } catch (err) {
      if (progressTimer) clearInterval(progressTimer);
      const message = err instanceof Error ? err.message : "שגיאה בניתוח המסמכים.";
      setError(message);
      setPhase("error");
    }
  }, [files, setExtractedData, navigate]);

  const requiredMet =
    permitOptOut || (!!files.survey_map && !!files.building_permits);

  const isExtracting = phase === "uploading" || phase === "analyzing";

  return (
    <FocusManager focusKey="upload">
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
          העלאת מסמכים
        </h1>
        <p className="text-[0.9rem] text-soil-600 mb-7 leading-relaxed">
          העלו את המסמכים הנדרשים — המערכת תנתח אותם ותזהה את המבנים
        </p>

        {/* Extraction overlay */}
        {isExtracting && (
          <div className="absolute inset-0 bg-cream/95 z-30 flex flex-col items-center justify-center gap-4 p-6 text-center">
            {/* Animated spinner */}
            <div className="relative w-16 h-16">
              <div className="absolute inset-0 border-4 border-olive-200 rounded-full" />
              <div className="absolute inset-0 border-4 border-olive-600 border-t-transparent rounded-full animate-spin" />
            </div>

            <p className="text-[1.1rem] font-semibold text-olive-800">
              {getPhaseLabel(phase, elapsed)}
            </p>
            <p className="text-[0.85rem] text-soil-500 max-w-xs">
              {getPhaseSubtext(phase, elapsed)}
            </p>

            {/* Progress bar */}
            {progress > 0 && progress < 100 && (
              <div className="w-48 h-2 bg-olive-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-olive-600 rounded-full transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
            )}

            {elapsed > 15 && (
              <p className="text-[0.8rem] text-soil-400 mt-2">
                {elapsed} שניות...
              </p>
            )}

            <button
              type="button"
              onClick={() => { setPhase("idle"); setProgress(0); }}
              className="mt-4 text-[0.85rem] text-soil-500 hover:text-error cursor-pointer bg-transparent border-none underline"
            >
              ביטול
            </button>
          </div>
        )}

        {/* Error banner */}
        {error && (
          <div role="alert" className="mb-5 p-3 bg-error/10 border border-error/30 rounded-[--radius-sm] text-error text-[0.85rem] animate-[alertIn_0.3s_ease-out]">
            {error}
          </div>
        )}

        {/* Required uploads */}
        <UploadGrid files={files} onFileChange={handleFileChange} />

        {/* Optional uploads */}
        <OptionalSection files={files} onFileChange={handleFileChange} />

        {/* Permit opt-out */}
        <label className="flex items-center gap-3 mt-6 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={permitOptOut}
            onChange={(e) => setPermitOptOut(e.target.checked)}
            className="w-[18px] h-[18px] accent-olive-600 cursor-pointer"
          />
          <span className="text-[0.88rem] text-soil-600">
            אין ברשותי היתרי בנייה - המשך ללא היתרים
          </span>
        </label>

        {/* Navigation */}
        <FormNav
          onBack={() => navigate("/intake")}
          onNext={handleExtract}
          backLabel="חזרה לטופס"
          nextLabel="ניתוח מסמכים"
          showBack
          nextDisabled={!requiredMet || isExtracting}
        />
      </div>
    </div>
    </div>
    </FocusManager>
  );
}
