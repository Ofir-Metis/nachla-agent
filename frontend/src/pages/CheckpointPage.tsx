import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import type { Building } from "@/types";
import { fetchBuildings, confirmClassification } from "@/lib/api";
import BuildingTable from "@/components/checkpoint/BuildingTable";
import BuildingCard from "@/components/checkpoint/BuildingCard";
import BuildingEditForm from "@/components/checkpoint/BuildingEditForm";
import FocusManager from "@/components/ui/FocusManager";

export default function CheckpointPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  const [buildings, setBuildings] = useState<Building[]>([]);
  const [modifiedIds, setModifiedIds] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [editingMobileId, setEditingMobileId] = useState<number | null>(null);

  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;

    async function load() {
      try {
        setLoading(true);
        const data = await fetchBuildings(jobId!);
        if (!cancelled) setBuildings(data);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "שגיאה בטעינת המבנים");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [jobId]);

  const handleBuildingUpdate = useCallback((updated: Building) => {
    setBuildings((prev) =>
      prev.map((b) => (b.id === updated.id ? updated : b))
    );
    setModifiedIds((prev) => new Set(prev).add(updated.id));
    setEditingMobileId(null);
  }, []);

  const handleConfirm = async () => {
    if (!jobId) return;
    try {
      setSubmitting(true);
      const confirmedBuildings = buildings.map((b) => ({ ...b, user_confirmed: true }));
      await confirmClassification(jobId, confirmedBuildings);
      navigate(`/jobs/${jobId}/processing`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "שגיאה באישור הסיווג");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <FocusManager focusKey="checkpoint-loading">
        <div className="animate-[cardIn_0.4s_ease-out]">
          <div className="bg-cream border border-[#D8D0C4] rounded-[--radius-lg] sm:rounded-[--radius-xl] p-5 sm:p-7 sm:px-8 shadow-[--shadow-md] relative overflow-hidden">
            <div className="absolute top-0 right-0 left-0 h-1 bg-gradient-to-l from-olive-700 via-olive-400 to-wheat-400" />
            <h1 tabIndex={-1} className="outline-none sr-only">טוען נתוני מבנים</h1>
            <p className="text-soil-500 text-center py-12">טוען נתוני מבנים...</p>
          </div>
        </div>
      </FocusManager>
    );
  }

  return (
    <FocusManager focusKey="checkpoint">
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

        <h1 tabIndex={-1} className="outline-none font-heading text-[1.35rem] font-bold text-wheat-700 mb-1.5">
          נדרש אישור: סיווג מבנים
        </h1>
        <p className="text-[0.9rem] text-soil-600 mb-7 leading-relaxed">
          זיהינו {buildings.length} מבנים בנחלה. אנא בדקו שהסיווג נכון.
        </p>

        {error && (
          <div className="mb-5 p-3 bg-error/10 border border-error/30 rounded-[--radius-sm] text-error text-[0.85rem] animate-[alertIn_0.3s_ease-out]">
            {error}
          </div>
        )}

        {/* Desktop table */}
        <BuildingTable
          buildings={buildings}
          modifiedIds={modifiedIds}
          onBuildingUpdate={handleBuildingUpdate}
        />

        {/* Mobile card list */}
        <div className="md:hidden flex flex-col gap-3">
          {buildings.map((b, idx) => (
            <div key={b.id}>
              <BuildingCard
                building={b}
                index={idx}
                isModified={modifiedIds.has(b.id)}
                onEdit={() => setEditingMobileId(editingMobileId === b.id ? null : b.id)}
              />
              {editingMobileId === b.id && (
                <BuildingEditForm
                  building={b}
                  onSave={handleBuildingUpdate}
                  onCancel={() => setEditingMobileId(null)}
                />
              )}
            </div>
          ))}
        </div>

        {/* Approve button */}
        <button
          type="button"
          onClick={handleConfirm}
          disabled={submitting}
          className="mt-7 w-full md:w-auto px-8 py-3 text-[0.95rem] font-semibold rounded-[--radius-md] bg-success text-white hover:bg-success/90 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed transition-all cursor-pointer"
        >
          {submitting ? "מאשר..." : "אישור הסיווג והמשך"}
        </button>
      </div>
    </div>
    </div>
    </FocusManager>
  );
}
