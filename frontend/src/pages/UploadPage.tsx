import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useWizardContext } from "@/context/WizardContext";
import UploadGrid from "@/components/upload/UploadGrid";
import OptionalSection from "@/components/upload/OptionalSection";
import FormNav from "@/components/ui/FormNav";
import FocusManager from "@/components/ui/FocusManager";

export default function UploadPage() {
  const navigate = useNavigate();
  const { formData, files, setFile } = useWizardContext();
  const [permitOptOut, setPermitOptOut] = useState(false);

  // Route guard: redirect to intake if no formData has been filled
  useEffect(() => {
    if (!formData.owner_name && !formData.moshav_name) {
      navigate("/intake", { replace: true });
    }
  }, [formData, navigate]);

  const handleFileChange = (id: string, file: File | null) => {
    setFile(id, file);
  };

  const requiredMet =
    permitOptOut || (!!files.survey_map && !!files.building_permits);

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
          העלו את המסמכים הנדרשים לצורך הבדיקה
        </p>

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
          onNext={() => navigate("/confirm")}
          backLabel="חזרה לטופס"
          nextLabel="בדיקה והמשך"
          showBack
          nextDisabled={!requiredMet}
        />
      </div>
    </div>
    </div>
    </FocusManager>
  );
}
