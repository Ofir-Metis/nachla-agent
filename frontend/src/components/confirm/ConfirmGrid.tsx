import type { IntakeData } from "@/types";
import {
  AUTH_TYPE_LABELS,
  CLIENT_GOAL_LABELS,
  OWNERSHIP_TYPE_LABELS,
} from "@/lib/labels";
import ConfirmRow from "./ConfirmRow";

interface ConfirmGridProps {
  formData: Partial<IntakeData>;
  fileCount: number;
}

export default function ConfirmGrid({ formData, fileCount }: ConfirmGridProps) {
  const authLabel = formData.authorization_type
    ? AUTH_TYPE_LABELS[formData.authorization_type] ?? formData.authorization_type
    : "--";

  const goalsLabel =
    formData.client_goals && formData.client_goals.length > 0
      ? formData.client_goals
          .map((g) => CLIENT_GOAL_LABELS[g] ?? g)
          .join(", ")
      : "--";

  const capitalizationTrackLabel: Record<string, string> = {
    "375": "מסלול 375 מ\"ר",
    "33": "מסלול 33%",
    none: "ללא",
  };

  return (
    <div className="grid gap-3">
      <ConfirmRow label="שם בעל הנחלה" value={formData.owner_name || "--"} />
      <ConfirmRow label="מושב" value={formData.moshav_name || "--"} />
      <ConfirmRow
        label="גוש/חלקה"
        value={
          formData.gush != null && formData.helka != null
            ? `${formData.gush}/${formData.helka}`
            : "--"
        }
        isNumeric
      />
      <ConfirmRow
        label="סוג בעלות"
        value={
          formData.ownership_type
            ? OWNERSHIP_TYPE_LABELS[formData.ownership_type] ?? formData.ownership_type
            : "--"
        }
      />
      <ConfirmRow
        label="רצף בין-דורי"
        value={
          formData.has_intergenerational_continuity === true
            ? "כן"
            : formData.has_intergenerational_continuity === false
              ? "לא"
              : "--"
        }
      />
      <ConfirmRow label="סוג הרשאה" value={authLabel} />
      <ConfirmRow
        label="מהוון"
        value={
          formData.is_capitalized === true
            ? "כן"
            : formData.is_capitalized === false
              ? "לא"
              : "--"
        }
      />
      {formData.is_capitalized && formData.capitalization_track && formData.capitalization_track !== "none" && (
        <ConfirmRow
          label="מסלול היוון"
          value={capitalizationTrackLabel[formData.capitalization_track] ?? "--"}
        />
      )}
      <ConfirmRow
        label="בתי מגורים"
        value={
          formData.num_existing_houses != null
            ? String(formData.num_existing_houses)
            : "--"
        }
        isNumeric
      />
      <ConfirmRow label="מטרות" value={goalsLabel} />
      <ConfirmRow
        label="צווי הריסה"
        value={
          formData.has_demolition_orders === true
            ? "כן"
            : formData.has_demolition_orders === false
              ? "לא"
              : "--"
        }
      />
      <ConfirmRow
        label="מסמכים"
        value={fileCount === 0 ? "לא הועלו קבצים" : fileCount === 1 ? "קובץ אחד" : `${fileCount} קבצים`}
        isNumeric
      />
    </div>
  );
}
