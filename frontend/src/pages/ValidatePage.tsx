import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useWizardContext } from "@/context/WizardContext";
import type { Building } from "@/types";
import BuildingTable from "@/components/checkpoint/BuildingTable";
import BuildingCard from "@/components/checkpoint/BuildingCard";
import BuildingEditForm from "@/components/checkpoint/BuildingEditForm";
import FocusManager from "@/components/ui/FocusManager";

export default function ValidatePage() {
  const navigate = useNavigate();
  const { extractedBuildings, extractionWarnings, updateExtractedBuilding } = useWizardContext();

  const [modifiedIds, setModifiedIds] = useState<Set<number>>(new Set());
  const [editingMobileId, setEditingMobileId] = useState<number | null>(null);

  // Redirect if no extraction data
  useEffect(() => {
    if (extractedBuildings.length === 0) {
      navigate("/upload", { replace: true });
    }
  }, [extractedBuildings, navigate]);

  const handleBuildingUpdate = useCallback((updated: Building) => {
    updateExtractedBuilding(updated.id, updated);
    setModifiedIds((prev) => new Set(prev).add(updated.id));
    setEditingMobileId(null);
  }, [updateExtractedBuilding]);

  if (extractedBuildings.length === 0) return null;

  return (
    <FocusManager focusKey="validate">
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
        <div className="absolute top-0 right-0 left-0 h-1 bg-gradient-to-l from-olive-700 via-olive-400 to-wheat-400" />

        <h1 tabIndex={-1} className="outline-none font-heading text-[1.35rem] font-bold text-wheat-700 mb-1.5">
          אימות נתוני מסמכים
        </h1>
        <p className="text-[0.9rem] text-soil-600 mb-4 leading-relaxed">
          המערכת זיהתה {extractedBuildings.length} מבנים מהמסמכים. אנא בדקו שהנתונים נכונים.
        </p>

        {/* Warnings from extraction */}
        {extractionWarnings.length > 0 && (
          <div role="alert" className="mb-5 p-3 bg-wheat-50 border border-wheat-200 rounded-[--radius-sm] text-wheat-700 text-[0.85rem]">
            {extractionWarnings.map((w, i) => (
              <p key={i}>{w}</p>
            ))}
          </div>
        )}

        {/* Desktop table */}
        <BuildingTable
          buildings={extractedBuildings}
          modifiedIds={modifiedIds}
          onBuildingUpdate={handleBuildingUpdate}
        />

        {/* Mobile card list */}
        <div className="md:hidden flex flex-col gap-3">
          {extractedBuildings.map((b, idx) => (
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

        {/* Navigation */}
        <div className="flex flex-col-reverse sm:flex-row gap-3 mt-7 pt-5 border-t border-[#D8D0C4] max-sm:sticky max-sm:bottom-0 max-sm:bg-[rgba(255,253,248,0.95)] max-sm:backdrop-blur-sm max-sm:z-20 max-sm:pb-3 max-sm:-mx-5 max-sm:px-5">
          <button
            type="button"
            onClick={() => navigate("/upload")}
            className="px-6 py-3 sm:py-3.5 rounded-[--radius-md] font-semibold text-[0.95rem] sm:text-base bg-transparent text-soil-600 border-[1.5px] border-[#D8D0C4] hover:border-olive-300 hover:bg-olive-50 transition-all cursor-pointer flex items-center justify-center gap-2"
          >
            <span className="text-[1.1em]">&rarr;</span>
            <span>חזרה למסמכים</span>
          </button>

          <button
            type="button"
            onClick={() => navigate("/taba")}
            className="sm:ms-auto px-8 py-3 sm:py-3.5 rounded-[--radius-md] font-semibold text-[0.95rem] sm:text-base bg-olive-700 text-white shadow-[--shadow-sm] hover:bg-olive-600 hover:shadow-[--shadow-md] hover:-translate-y-px active:translate-y-0 transition-all cursor-pointer flex items-center justify-center gap-2"
          >
            <span>אישור והמשך</span>
            <span className="text-[1.1em]">&larr;</span>
          </button>
        </div>
      </div>
    </div>
    </div>
    </FocusManager>
  );
}
