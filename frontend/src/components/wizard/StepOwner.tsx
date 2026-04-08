import { useState } from "react";
import TextInput from "@/components/ui/TextInput";
import RadioGroup from "@/components/ui/RadioGroup";
import ToggleButtons from "@/components/ui/ToggleButtons";
import FormNav from "@/components/ui/FormNav";
import {
  OWNERSHIP_TYPE_LABELS,
  OWNERSHIP_TYPE_DESCRIPTIONS,
} from "@/lib/labels";
import type { OwnershipType } from "@/types";

interface StepOwnerData {
  owner_name: string;
  ownership_type: OwnershipType | "";
  has_intergenerational_continuity: boolean | null;
}

interface StepOwnerProps {
  data: StepOwnerData;
  onChange: (data: StepOwnerData) => void;
  onNext: () => void;
}

const ownershipOptions = (
  Object.keys(OWNERSHIP_TYPE_LABELS) as OwnershipType[]
).map((key) => ({
  value: key,
  label: OWNERSHIP_TYPE_LABELS[key],
  description: OWNERSHIP_TYPE_DESCRIPTIONS[key],
}));

export default function StepOwner({ data, onChange, onNext }: StepOwnerProps) {
  const [errors, setErrors] = useState<Record<string, string>>({});

  function validate(): boolean {
    const errs: Record<string, string> = {};
    if (!data.owner_name.trim()) errs.owner_name = "שדה חובה";
    if (!data.ownership_type) errs.ownership_type = "נא לבחור סוג בעלות";
    if (data.has_intergenerational_continuity === null)
      errs.has_intergenerational_continuity = "נא לבחור תשובה";
    setErrors(errs);
    return Object.keys(errs).length === 0;
  }

  function handleNext() {
    if (validate()) onNext();
  }

  return (
    <div className="space-y-6">
      <TextInput
        label="שם בעל הנחלה"
        name="owner_name"
        placeholder="לדוגמה: ישראל ישראלי"
        helpText="השם כפי שמופיע בתעודות הבעלות"
        required
        value={data.owner_name}
        onChange={(e) => {
          onChange({ ...data, owner_name: e.target.value });
          if (errors.owner_name) setErrors((p) => ({ ...p, owner_name: "" }));
        }}
        error={errors.owner_name}
      />

      <RadioGroup
        name="ownership_type"
        label="סוג בעלות"
        required
        options={ownershipOptions}
        value={data.ownership_type || undefined}
        onChange={(v) => {
          onChange({ ...data, ownership_type: v as OwnershipType });
          if (errors.ownership_type) setErrors((p) => ({ ...p, ownership_type: "" }));
        }}
        error={errors.ownership_type}
      />

      <ToggleButtons
        name="has_intergenerational_continuity"
        label="האם קיים רצף בין-דורי?"
        helpText="האם הנחלה עוברת מדור לדור באותה משפחה?"
        required
        value={data.has_intergenerational_continuity}
        onChange={(v) => {
          onChange({ ...data, has_intergenerational_continuity: v });
          if (errors.has_intergenerational_continuity)
            setErrors((p) => ({ ...p, has_intergenerational_continuity: "" }));
        }}
        error={errors.has_intergenerational_continuity}
      />

      <FormNav onNext={handleNext} />
    </div>
  );
}
