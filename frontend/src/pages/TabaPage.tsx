import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useWizardContext } from "@/context/WizardContext";
import MethodSelector, { type TabaMethod } from "@/components/taba/MethodSelector";
import GovMapMethod from "@/components/taba/GovMapMethod";
import TabaUploadMethod from "@/components/taba/TabaUploadMethod";
import TabaManualForm from "@/components/taba/TabaManualForm";
import TabaSummaryCard from "@/components/taba/TabaSummaryCard";
import FormNav from "@/components/ui/FormNav";
import FocusManager from "@/components/ui/FocusManager";
import type { TabaData } from "@/types";

export default function TabaPage() {
  const navigate = useNavigate();
  const { formData, extractedTabas, setTabaData, tabaSkipped, setTabaSkipped } = useWizardContext();

  const [method, setMethod] = useState<TabaMethod | null>(null);
  const [tabas, setTabas] = useState<TabaData[]>(extractedTabas);
  const [showSkipWarning, setShowSkipWarning] = useState(false);

  // Route guard
  useEffect(() => {
    if (!formData.owner_name && !formData.moshav_name) {
      navigate("/intake", { replace: true });
    }
  }, [formData, navigate]);

  // Sync from context on mount (if tabas were extracted during upload)
  useEffect(() => {
    if (extractedTabas.length > 0 && tabas.length === 0) {
      setTabas(extractedTabas);
    }
  }, [extractedTabas, tabas.length]);

  const handleAddTaba = (taba: TabaData) => {
    // If this is the first taba, mark it as primary
    if (tabas.length === 0) {
      taba.is_primary = true;
    }
    setTabas((prev) => [...prev, taba]);
  };

  const handleRemoveTaba = (index: number) => {
    setTabas((prev) => {
      const next = prev.filter((_, i) => i !== index);
      // Ensure one is primary
      if (next.length > 0 && !next.some((t) => t.is_primary)) {
        next[0].is_primary = true;
      }
      return next;
    });
  };

  const handleTabasExtracted = (extracted: TabaData[]) => {
    setTabas((prev) => [...prev, ...extracted]);
  };

  const handleNext = () => {
    setTabaData(tabas);
    navigate("/confirm");
  };

  const handleSkipToggle = () => {
    const newSkipped = !tabaSkipped;
    setTabaSkipped(newSkipped);
    if (newSkipped) {
      setShowSkipWarning(true);
    } else {
      setShowSkipWarning(false);
    }
  };

  const canProceed = tabas.length > 0 || tabaSkipped;

  return (
    <FocusManager focusKey="taba">
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
        <div className="absolute top-0 right-0 left-0 h-1 bg-gradient-to-l from-olive-700 via-olive-400 to-wheat-400" />

        <h1 tabIndex={-1} className="outline-none font-heading text-[1.35rem] font-bold text-olive-800 mb-1.5">
          נתוני תב"ע
        </h1>
        <p className="text-[0.9rem] text-soil-600 mb-6 leading-relaxed">
          הזינו את נתוני התב"ע (תוכנית בניין עיר) החלה על הנחלה
        </p>

        {/* Saved tabas */}
        {tabas.length > 0 && (
          <div className="mb-6 space-y-3">
            <h3 className="text-[0.9rem] font-semibold text-olive-700">
              תב"עות שנוספו ({tabas.length})
            </h3>
            {tabas.map((t, i) => (
              <TabaSummaryCard key={`${t.taba_number}-${i}`} taba={t} index={i} onRemove={handleRemoveTaba} />
            ))}
          </div>
        )}

        {/* Method selector */}
        <h3 className="text-[0.9rem] font-semibold text-soil-700 mb-3">
          {tabas.length > 0 ? 'הוסף תב"ע נוספת' : 'בחרו אופן הזנת נתוני תב"ע'}
        </h3>
        <MethodSelector selected={method} onSelect={setMethod} />

        {/* Active method content */}
        {method === "govmap" && (
          <GovMapMethod
            gush={formData.gush}
            helka={formData.helka}
            onSwitchMethod={setMethod}
          />
        )}
        {method === "upload" && (
          <TabaUploadMethod onTabasExtracted={handleTabasExtracted} />
        )}
        {method === "manual" && (
          <TabaManualForm onAdd={handleAddTaba} />
        )}

        {/* Skip option */}
        <div className="mt-6 pt-4 border-t border-[#D8D0C4]">
          <label className="flex items-center gap-3 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={tabaSkipped}
              onChange={handleSkipToggle}
              className="w-[18px] h-[18px] accent-olive-600 cursor-pointer"
            />
            <span className="text-[0.88rem] text-soil-600">
              אין ברשותי נתוני תב"ע — המשך ללא
            </span>
          </label>

          {showSkipWarning && tabaSkipped && (
            <div role="alert" className="mt-3 p-3 bg-wheat-50 border border-wheat-200 rounded-[--radius-sm] text-[0.85rem] text-wheat-700">
              &#x26A0;&#xFE0F; ללא נתוני תב"ע, חישוב ההיוון ופוטנציאל הבנייה עלול להיות חלקי. מומלץ להזין נתונים אלו.
            </div>
          )}
        </div>

        {/* Navigation */}
        <FormNav
          onBack={() => navigate("/validate")}
          onNext={handleNext}
          backLabel="חזרה לאימות מבנים"
          nextLabel="המשך לסיכום"
          showBack
          nextDisabled={!canProceed}
        />
      </div>
    </div>
    </div>
    </FocusManager>
  );
}
