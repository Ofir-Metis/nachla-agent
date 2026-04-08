import { useState, useEffect } from "react";
import TextInput from "@/components/ui/TextInput";
import FormNav from "@/components/ui/FormNav";
import { MOSHAV_PRIORITY_MAP, PRIORITY_AREA_LABELS } from "@/lib/labels";
import type { PriorityArea } from "@/types";

const MOSHAV_LIST = [
  "נהלל",
  "כפר ורבורג",
  "בית חרות",
  "גן יאשיה",
  "כפר יהושע",
  "נחלת יהודה",
  "עין ורד",
  "גבעת עדה",
  "כפר הרואה",
  "בניאמינה",
  "פרדס חנה",
  "זכרון יעקב",
];

interface StepLocationData {
  moshav_name: string;
  gush: string;
  helka: string;
  priority_area?: PriorityArea;
}

interface StepLocationProps {
  data: StepLocationData;
  onChange: (data: StepLocationData) => void;
  onNext: () => void;
  onBack: () => void;
}

export default function StepLocation({ data, onChange, onNext, onBack }: StepLocationProps) {
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [showOverride, setShowOverride] = useState(false);

  // Auto-detect priority area when moshav name changes
  const detectedArea = MOSHAV_PRIORITY_MAP[data.moshav_name.trim()] as PriorityArea | undefined;

  useEffect(() => {
    if (detectedArea && !showOverride && data.priority_area !== detectedArea) {
      onChange({ ...data, priority_area: detectedArea });
    }
  }, [detectedArea, showOverride]); // eslint-disable-line react-hooks/exhaustive-deps

  const displayArea: PriorityArea | undefined = data.priority_area ?? detectedArea;

  function validate(): boolean {
    const errs: Record<string, string> = {};
    if (!data.moshav_name.trim()) errs.moshav_name = "שדה חובה";

    const gushNum = Number(data.gush);
    if (!data.gush.trim()) {
      errs.gush = "שדה חובה";
    } else if (!Number.isInteger(gushNum) || gushNum <= 0) {
      errs.gush = "מספר גוש חייב להיות חיובי";
    }

    const helkaNum = Number(data.helka);
    if (!data.helka.trim()) {
      errs.helka = "שדה חובה";
    } else if (!Number.isInteger(helkaNum) || helkaNum <= 0) {
      errs.helka = "מספר חלקה חייב להיות חיובי";
    }

    setErrors(errs);
    return Object.keys(errs).length === 0;
  }

  function handleNext() {
    if (validate()) onNext();
  }

  return (
    <div className="space-y-6">
      <TextInput
        label="שם המושב"
        name="moshav_name"
        placeholder="לדוגמה: נהלל"
        helpText="התחילו להקליד והשם יושלם אוטומטית"
        required
        value={data.moshav_name}
        onChange={(e) => {
          onChange({ ...data, moshav_name: e.target.value });
          if (errors.moshav_name) setErrors((p) => ({ ...p, moshav_name: "" }));
        }}
        error={errors.moshav_name}
        datalistOptions={MOSHAV_LIST}
      />

      {/* Priority area display */}
      {displayArea && (
        <div className="bg-olive-50 border border-olive-200 rounded-[--radius-sm] p-2.5 text-[0.85rem]">
          <span className="text-olive-700 font-medium">
            {"אזור עדיפות: "}
            {PRIORITY_AREA_LABELS[displayArea]}
          </span>
          {!showOverride && (
            <button
              type="button"
              onClick={() => setShowOverride(true)}
              className="text-[0.8rem] text-olive-600 underline hover:text-olive-800 transition-colors cursor-pointer me-3"
            >
              לא נכון? שנה ידנית
            </button>
          )}
          {showOverride && (
            <div className="mt-2 flex flex-wrap gap-2">
              {(["none", "A", "B", "frontline"] as PriorityArea[]).map((opt) => (
                <label
                  key={opt}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded border cursor-pointer transition-colors text-[0.82rem] ${
                    data.priority_area === opt
                      ? "bg-olive-100 border-olive-400 text-olive-800 font-medium"
                      : "bg-white border-olive-200 text-soil-600 hover:border-olive-300"
                  }`}
                >
                  <input
                    type="radio"
                    name="priority_area"
                    value={opt}
                    checked={data.priority_area === opt}
                    onChange={() => onChange({ ...data, priority_area: opt })}
                    className="sr-only"
                  />
                  {PRIORITY_AREA_LABELS[opt]}
                </label>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex-1">
          <TextInput
            label="גוש"
            name="gush"
            placeholder="1234"
            helpText="מספר הגוש כפי שמופיע בנסח טאבו"
            required
            inputMode="numeric"
            dir="ltr"
            style={{ textAlign: "center" }}
            value={data.gush}
            onChange={(e) => {
              onChange({ ...data, gush: e.target.value });
              if (errors.gush) setErrors((p) => ({ ...p, gush: "" }));
            }}
            error={errors.gush}
          />
        </div>
        <div className="flex-1">
          <TextInput
            label="חלקה"
            name="helka"
            placeholder="56"
            required
            inputMode="numeric"
            dir="ltr"
            style={{ textAlign: "center" }}
            value={data.helka}
            onChange={(e) => {
              onChange({ ...data, helka: e.target.value });
              if (errors.helka) setErrors((p) => ({ ...p, helka: "" }));
            }}
            error={errors.helka}
          />
        </div>
      </div>

      <FormNav onNext={handleNext} onBack={onBack} showBack />
    </div>
  );
}
