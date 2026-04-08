import { useState } from "react";
import type { IntakeData, ClientGoal } from "@/types";
import NumericStepper from "@/components/ui/NumericStepper";
import CardCheckbox from "@/components/ui/CardCheckbox";
import AlertWarning from "@/components/ui/AlertWarning";
import ToggleButtons from "@/components/ui/ToggleButtons";
import FormNav from "@/components/ui/FormNav";
import {
  CLIENT_GOAL_LABELS,
  CLIENT_GOAL_DESCRIPTIONS,
  CLIENT_GOAL_ICONS,
} from "@/lib/labels";

interface StepGoalsProps {
  formData: Partial<IntakeData>;
  onChange: <K extends keyof IntakeData>(field: K, value: IntakeData[K]) => void;
  onNext: () => void;
  onBack: () => void;
}

const goalKeys: ClientGoal[] = ["regularization", "capitalization", "split", "all"];

export default function StepGoals({
  formData,
  onChange,
  onNext,
  onBack,
}: StepGoalsProps) {
  const selectedGoals = formData.client_goals ?? [];
  const [errors, setErrors] = useState<Record<string, string>>({});

  const toggleGoal = (value: string) => {
    const goal = value as ClientGoal;
    const current = [...selectedGoals];
    const idx = current.indexOf(goal);
    if (idx >= 0) {
      current.splice(idx, 1);
    } else {
      current.push(goal);
    }
    onChange("client_goals", current);
    setErrors((prev) => ({ ...prev, client_goals: "" }));
  };

  const showSplitWarning =
    formData.authorization_type === "bar_reshut" &&
    (selectedGoals.includes("split") || selectedGoals.includes("all"));

  const showDemolitionWarning = formData.has_demolition_orders === true;

  const validate = (): boolean => {
    const errs: Record<string, string> = {};
    if (selectedGoals.length === 0) {
      errs.client_goals = "יש לבחור לפחות מטרה אחת";
    }
    if (formData.has_demolition_orders === undefined || formData.has_demolition_orders === null) {
      errs.has_demolition_orders = "נא לבחור תשובה";
    }
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleNext = () => {
    if (validate()) onNext();
  };

  return (
    <div className="space-y-7">
      <NumericStepper
        label="מספר בתי מגורים קיימים"
        helpText="כמה בתי מגורים קיימים כיום במשק?"
        required
        value={formData.num_existing_houses ?? 0}
        onChange={(val) => onChange("num_existing_houses", val)}
      />

      <div className="space-y-2">
        <label className="block text-lg font-semibold text-soil-800">
          מטרות הבדיקה
          <span className="text-terra-500 ms-0.5">*</span>
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {goalKeys.map((key) => (
            <CardCheckbox
              key={key}
              value={key}
              label={CLIENT_GOAL_LABELS[key]}
              description={CLIENT_GOAL_DESCRIPTIONS[key]}
              icon={CLIENT_GOAL_ICONS[key]}
              selected={selectedGoals.includes(key)}
              onClick={toggleGoal}
            />
          ))}
        </div>
        {errors.client_goals && (
          <p className="text-[0.82rem] text-error font-medium mt-1">{errors.client_goals}</p>
        )}

        <AlertWarning
          visible={showSplitWarning}
          message={'שימו לב: בר רשות לא יכול לפצל ללא הסדרת חוזה חכירה מול רמ"י. הבדיקה תכלול את עלות ההסדרה.'}
        />
      </div>

      <ToggleButtons
        name="has_demolition_orders"
        label="האם קיימים צווי הריסה?"
        value={formData.has_demolition_orders ?? null}
        onChange={(val) => {
          onChange("has_demolition_orders", val);
          setErrors((prev) => ({ ...prev, has_demolition_orders: "" }));
        }}
        error={errors.has_demolition_orders}
      />

      <AlertWarning
        visible={showDemolitionWarning}
        message="צווי הריסה משפיעים על אפשרויות ההסדרה ועל סדר העדיפויות. הבדיקה תתייחס לכך."
      />

      <FormNav
        onBack={onBack}
        onNext={handleNext}
        showBack
        nextLabel="המשך להעלאת מסמכים"
      />
    </div>
  );
}
