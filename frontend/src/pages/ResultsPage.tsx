import { useState, useEffect } from "react";
import { useParams, Navigate, useNavigate } from "react-router-dom";
import type { CostSummary } from "@/types";
import { fetchResults, cloudExport } from "@/lib/api";
import CostCards from "@/components/results/CostCards";
import HivunComparison from "@/components/results/HivunComparison";
import DownloadGrid from "@/components/results/DownloadGrid";
import FocusManager from "@/components/ui/FocusManager";

const DOWNLOAD_TYPES = ["word", "excel", "pdf", "audit"];

const CLOUD_OPTIONS = [
  { id: "gdrive", label: "Google Drive", icon: "☁" },
  { id: "onedrive", label: "OneDrive", icon: "\u{1F4C1}" },
  { id: "all", label: "שמור הכל", icon: "\u{1F4BE}" },
] as const;

export default function ResultsPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  const [results, setResults] = useState<CostSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cloudMessage, setCloudMessage] = useState<string | null>(null);
  const [cloudSaving, setCloudSaving] = useState(false);

  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;

    async function load() {
      try {
        setLoading(true);
        const data = await fetchResults(jobId!);
        if (!cancelled) setResults(data);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "שגיאה בטעינת התוצאות");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [jobId]);

  if (!jobId) return <Navigate to="/" replace />;

  if (loading) {
    return (
      <div className="animate-[cardIn_0.4s_ease-out]">
        <div className="bg-cream border border-[#D8D0C4] rounded-[--radius-lg] sm:rounded-[--radius-xl] p-5 sm:p-7 sm:px-8 shadow-[--shadow-md] relative overflow-hidden">
          <div className="absolute top-0 right-0 left-0 h-1 bg-gradient-to-l from-olive-700 via-olive-400 to-wheat-400" />
          <p className="text-soil-500 text-center py-12">טוען תוצאות...</p>
        </div>
      </div>
    );
  }

  if (error || !results) {
    return (
      <div className="animate-[cardIn_0.4s_ease-out]">
        <div className="bg-cream border border-[#D8D0C4] rounded-[--radius-lg] sm:rounded-[--radius-xl] p-5 sm:p-7 sm:px-8 shadow-[--shadow-md] relative overflow-hidden">
          <div className="absolute top-0 right-0 left-0 h-1 bg-gradient-to-l from-olive-700 via-olive-400 to-wheat-400" />
          <div className="p-3 bg-error/10 border border-error/30 rounded-[--radius-sm] text-error text-[0.85rem]">
            {error ?? "לא ניתן לטעון את התוצאות"}
            <button type="button" onClick={() => window.location.reload()}
              className="mt-3 px-5 py-2 bg-olive-700 text-white rounded-[--radius-sm] text-[0.85rem] font-medium cursor-pointer hover:bg-olive-600">
              נסו שנית
            </button>
          </div>
        </div>
      </div>
    );
  }

  const total =
    results.total_regularization_cost > 0
      ? results.total_regularization_cost
      : results.total_permit_fees + results.total_usage_fees + results.betterment_levy;

  const handleCloudSave = async (target: string) => {
    try {
      setCloudSaving(true);
      setCloudMessage("שומר בענן...");
      const result = await cloudExport(jobId, target as "gdrive" | "onedrive" | "all");
      setCloudMessage(result.message);
      setTimeout(() => setCloudMessage(null), 5000);
    } catch (err) {
      setCloudMessage(err instanceof Error ? err.message : "שגיאה בשמירה בענן");
      setTimeout(() => setCloudMessage(null), 5000);
    } finally {
      setCloudSaving(false);
    }
  };

  return (
    <FocusManager focusKey="results">
    <div>
      <button
        type="button"
        onClick={() => navigate("/")}
        className="mb-2 flex items-center gap-1.5 text-[0.85rem] text-soil-500 hover:text-olive-700 transition-colors cursor-pointer bg-transparent border-none"
      >
        <span>&rarr;</span>
        <span>חזרה לרשימת הבדיקות</span>
      </button>
    <div className="animate-[cardIn_0.4s_ease-out]" dir="rtl">
      <div className="bg-cream border border-[#D8D0C4] rounded-[--radius-lg] sm:rounded-[--radius-xl] p-5 sm:p-7 sm:px-8 shadow-[--shadow-md] relative overflow-hidden">
        {/* Top gradient bar */}
        <div className="absolute top-0 right-0 left-0 h-1 bg-gradient-to-l from-olive-700 via-olive-400 to-wheat-400" />

        <h1 tabIndex={-1} className="outline-none font-heading text-[1.35rem] font-bold text-success mb-1.5">
          הבדיקה הושלמה בהצלחה!
        </h1>
        <p className="text-[0.9rem] text-soil-600 mb-7 leading-relaxed">
          להלן סיכום העלויות המשוערות עבור הסדרת הנחלה.
        </p>

        {/* Cost breakdown */}
        <CostCards
          permitFees={results.total_permit_fees}
          usageFees={results.total_usage_fees}
          bettermentLevy={results.betterment_levy}
          total={total}
        />

        {/* Per-building cost breakdown */}
        {results.building_cards && results.building_cards.length > 0 && (
          <div className="mt-6">
            <h2 className="font-semibold text-[0.95rem] text-soil-800 mb-3">פירוט עלויות לפי מבנה</h2>
            <div className="space-y-2">
              {results.building_cards.map((card: { building_id: number; building_name: string; status_description: string; permit_fees: number; usage_fees: number; betterment_levy: number; total_cost: number; recommendations?: string[] }) => (
                <div key={card.building_id} className="flex items-center justify-between p-3 bg-white border border-[#D8D0C4] rounded-[--radius-sm]">
                  <div className="min-w-0 flex-1">
                    <div className="font-medium text-[0.88rem] text-soil-800 truncate">
                      #{card.building_id} {card.building_name}
                    </div>
                    <div className="text-[0.78rem] text-soil-500 flex gap-3 mt-0.5 flex-wrap">
                      {card.permit_fees > 0 && <span>דמי היתר: {card.permit_fees.toLocaleString()} ₪</span>}
                      {card.usage_fees > 0 && <span>דמי שימוש: {card.usage_fees.toLocaleString()} ₪</span>}
                      {card.betterment_levy > 0 && <span>השבחה: {card.betterment_levy.toLocaleString()} ₪</span>}
                      {card.total_cost === 0 && <span className="text-success">פטור</span>}
                    </div>
                    {card.recommendations && card.recommendations.length > 0 && (
                      <div className="text-[0.75rem] text-soil-400 mt-1">
                        {card.recommendations.map((r, i) => <span key={i}>{r} </span>)}
                      </div>
                    )}
                  </div>
                  <div className="text-[0.95rem] font-semibold text-soil-800 shrink-0 ms-3">
                    {card.total_cost > 0 ? `${card.total_cost.toLocaleString()} ₪` : "—"}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Hivun comparison */}
        <HivunComparison
          hivun375={results.hivun_375_total}
          hivun33={results.hivun_33_total}
        />

        {/* Download section */}
        <h2 className="font-semibold text-[0.95rem] text-soil-800 mt-8 mb-1">
          הורדת דוחות
        </h2>

        <DownloadGrid jobId={jobId!} downloadTypes={DOWNLOAD_TYPES} />

        {/* Cloud storage section */}
        <h2 className="font-semibold text-[0.95rem] text-soil-800 mt-8 mb-3">
          שמירה בענן
        </h2>

        {cloudMessage && (
          <div className="mb-3 p-2.5 bg-olive-50 border border-olive-200 rounded-[--radius-sm] text-olive-700 text-[0.85rem] animate-[alertIn_0.3s_ease-out]">
            {cloudMessage}
          </div>
        )}

        <div className="grid grid-cols-3 gap-2 sm:gap-3">
          {CLOUD_OPTIONS.map((opt) => (
            <button
              key={opt.id}
              type="button"
              onClick={() => handleCloudSave(opt.id)}
              disabled={cloudSaving}
              className="flex flex-col items-center gap-1.5 p-3 bg-wheat-50 border border-wheat-200 rounded-[--radius-md] text-center hover:bg-wheat-100 hover:border-wheat-300 active:scale-[0.97] transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span className="text-xl" aria-hidden="true">{opt.icon}</span>
              <span className="text-[0.82rem] font-medium text-soil-700">{opt.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
    </div>
    </FocusManager>
  );
}
