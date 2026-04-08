import { useNavigate } from "react-router-dom";
import useWizard from "@/hooks/useWizard";
import { useWizardContext } from "@/context/WizardContext";
import WizardStepper from "@/components/wizard/WizardStepper";
import WizardLayout from "@/components/wizard/WizardLayout";
import StepOwner from "@/components/wizard/StepOwner";
import StepLocation from "@/components/wizard/StepLocation";
import StepLegal from "@/components/wizard/StepLegal";
import StepGoals from "@/components/wizard/StepGoals";
import type { IntakeData } from "@/types";

const STEP_META: Record<number, { title: string; subtitle: string }> = {
  1: { title: "פרטי בעל הנחלה", subtitle: "נתחיל עם הפרטים הבסיסיים של בעל הנחלה" },
  2: { title: "מיקום הנחלה", subtitle: "פרטי המושב, גוש וחלקה" },
  3: { title: "סטטוס משפטי", subtitle: "פרטי ההרשאה וההיוון" },
  4: { title: "מטרות ופרטים נוספים", subtitle: "מה הלקוח מעוניין לבדוק?" },
};

export default function IntakePage() {
  const navigate = useNavigate();
  const { currentStep, completedSteps, nextStep, prevStep } = useWizard();
  const { formData, updateFormData, updateField } = useWizardContext();

  const meta = STEP_META[currentStep];

  return (
    <>
      {/* Cancel — back to dashboard */}
      <button
        type="button"
        onClick={() => navigate("/")}
        className="mb-2 flex items-center gap-1.5 text-[0.85rem] text-soil-500 hover:text-olive-700 transition-colors cursor-pointer bg-transparent border-none"
      >
        <span>&rarr;</span>
        <span>חזרה לרשימת הבדיקות</span>
      </button>

      <WizardStepper currentStep={currentStep} completedSteps={completedSteps} />

      <WizardLayout title={meta.title} subtitle={meta.subtitle} stepKey={currentStep}>
        {currentStep === 1 && (
          <StepOwner
            data={{
              owner_name: formData.owner_name ?? "",
              ownership_type: formData.ownership_type ?? "",
              has_intergenerational_continuity: formData.has_intergenerational_continuity ?? null,
            }}
            onChange={(d) => updateFormData(d as Partial<IntakeData>)}
            onNext={nextStep}
          />
        )}

        {currentStep === 2 && (
          <StepLocation
            data={{
              moshav_name: formData.moshav_name ?? "",
              gush: formData.gush != null ? String(formData.gush) : "",
              helka: formData.helka != null ? String(formData.helka) : "",
              priority_area: formData.priority_area,
            }}
            onChange={(d) =>
              updateFormData({
                moshav_name: d.moshav_name,
                gush: d.gush ? Number(d.gush) : undefined,
                helka: d.helka ? Number(d.helka) : undefined,
                priority_area: d.priority_area,
              } as Partial<IntakeData>)
            }
            onNext={nextStep}
            onBack={prevStep}
          />
        )}

        {currentStep === 3 && (
          <StepLegal
            formData={formData}
            onChange={updateField}
            onNext={nextStep}
            onBack={prevStep}
          />
        )}

        {currentStep === 4 && (
          <StepGoals
            formData={formData}
            onChange={updateField}
            onNext={() => navigate("/upload")}
            onBack={prevStep}
          />
        )}
      </WizardLayout>
    </>
  );
}
