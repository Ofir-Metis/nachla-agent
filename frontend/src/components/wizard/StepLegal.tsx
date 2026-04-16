import { useEffect, useState } from "react";
import type { IntakeData, AuthorizationType, CapitalizationTrack } from "@/types";
import RadioGroup from "@/components/ui/RadioGroup";
import ToggleButtons from "@/components/ui/ToggleButtons";
import TextInput from "@/components/ui/TextInput";
import FormNav from "@/components/ui/FormNav";
import {
  AUTH_TYPE_LABELS,
  AUTH_TYPE_DESCRIPTIONS,
} from "@/lib/labels";

interface StepLegalProps {
  formData: Partial<IntakeData>;
  onChange: <K extends keyof IntakeData>(field: K, value: IntakeData[K]) => void;
  onNext: () => void;
  onBack: () => void;
}

const authOptions = (
  ["bar_reshut", "chocher", "choze_chachira_mehuvon"] as const
).map((key) => ({
  value: key,
  label: AUTH_TYPE_LABELS[key],
  description: AUTH_TYPE_DESCRIPTIONS[key],
}));

const trackOptions = [
  {
    value: "375" as const,
    label: "מסלול 3.75%",
    description: "תשלום שנתי מופחת עם אפשרות לשדרוג עתידי",
  },
  {
    value: "33" as const,
    label: "מסלול 33%",
    description: "רכישה מלאה של זכויות הבנייה",
  },
];

export default function StepLegal({
  formData,
  onChange,
  onNext,
  onBack,
}: StepLegalProps) {
  const [showTrack, setShowTrack] = useState(!!formData.is_capitalized);
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (formData.is_capitalized === undefined) return;
    if (formData.is_capitalized) {
      setShowTrack(true);
    } else {
      setShowTrack(false);
      onChange("capitalization_track", "none" as CapitalizationTrack);
    }
  }, [formData.is_capitalized]); // eslint-disable-line react-hooks/exhaustive-deps

  const validate = (): boolean => {
    const errs: Record<string, string> = {};
    if (!formData.authorization_type) {
      errs.authorization_type = "נא לבחור סוג הרשאה";
    }
    if (formData.is_capitalized === undefined || formData.is_capitalized === null) {
      errs.is_capitalized = "נא לבחור תשובה";
    }
    if (formData.is_capitalized && (!formData.capitalization_track || formData.capitalization_track === "none")) {
      errs.capitalization_track = "כאשר המשק מהוון, יש לבחור מסלול היוון";
    }
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleNext = () => {
    if (validate()) onNext();
  };

  return (
    <div className="space-y-7">
      <RadioGroup
        name="authorization_type"
        label="סוג הרשאה"
        required
        value={formData.authorization_type ?? ""}
        onChange={(val) => {
          onChange("authorization_type", val as AuthorizationType);
          setErrors((prev) => ({ ...prev, authorization_type: "" }));
        }}
        options={authOptions}
        error={errors.authorization_type}
      />

      <ToggleButtons
        name="is_capitalized"
        label="האם המשק מהוון?"
        value={formData.is_capitalized ?? null}
        onChange={(val) => {
          onChange("is_capitalized", val);
          setErrors((prev) => ({ ...prev, is_capitalized: "" }));
        }}
        error={errors.is_capitalized}
      />

      {/* Conditional capitalization track section */}
      <div
        className="overflow-hidden transition-all duration-300 ease-in-out"
        style={{
          maxHeight: showTrack ? "400px" : "0px",
          opacity: showTrack ? 1 : 0,
        }}
      >
        <div className="pt-1">
          <RadioGroup
            name="capitalization_track"
            label="מסלול היוון"
            required
            value={formData.capitalization_track === "none" ? "" : (formData.capitalization_track ?? "")}
            onChange={(val) => {
              onChange("capitalization_track", val as CapitalizationTrack);
              setErrors((prev) => ({ ...prev, capitalization_track: "" }));
            }}
            options={trackOptions}
            error={errors.capitalization_track}
          />
        </div>
      </div>

      {/* Conditional prior permit fees section — only for 33% track */}
      <div
        className="overflow-hidden transition-all duration-300 ease-in-out"
        style={{
          maxHeight: formData.capitalization_track === "33" ? "400px" : "0px",
          opacity: formData.capitalization_track === "33" ? 1 : 0,
        }}
      >
        <div className="pt-1 space-y-4">
          <h3 className="text-[0.95rem] font-semibold text-olive-800">
            דמי היתר שנרכשו בעבר
          </h3>
          <TextInput
            label={'סכום ששולם (ש"ח)'}
            name="prior_permit_fees_purchased"
            placeholder="0"
            helpText="הזינו 0 אם לא רכשתם דמי היתר בעבר"
            dir="ltr"
            inputMode="numeric"
            style={{ textAlign: "center" }}
            value={formData.prior_permit_fees_purchased?.toString() ?? ""}
            onChange={(e) => {
              const val = e.target.value;
              onChange(
                "prior_permit_fees_purchased",
                val === "" ? undefined as unknown as number : Number(val),
              );
            }}
          />
          <TextInput
            label="שנת רכישה"
            name="prior_permit_fees_date"
            placeholder="2015"
            helpText="רק רכישות לאחר 2009 מנוכות מחישוב 33%"
            dir="ltr"
            inputMode="numeric"
            style={{ textAlign: "center" }}
            value={formData.prior_permit_fees_date?.toString() ?? ""}
            onChange={(e) => {
              const val = e.target.value;
              onChange(
                "prior_permit_fees_date",
                val === "" ? undefined as unknown as number : Number(val),
              );
            }}
          />
        </div>
      </div>

      <TextInput
        label="מועצה אזורית"
        name="regional_council"
        placeholder="לדוגמה: עמק יזרעאל"
        helpText="שם המועצה האזורית (לחישוב עלויות פיתוח)"
        value={formData.regional_council ?? ""}
        onChange={(e) => {
          onChange("regional_council", e.target.value || undefined as unknown as string);
        }}
      />

      <FormNav onBack={onBack} onNext={handleNext} showBack />
    </div>
  );
}
