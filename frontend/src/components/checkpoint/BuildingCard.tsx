import type { Building } from "@/types";
import { BUILDING_TYPE_LABELS } from "@/lib/labels";
import StatusBadge from "./StatusBadge";

interface BuildingCardProps {
  building: Building;
  index: number;
  isModified: boolean;
  onEdit: () => void;
}

function borderClass(status: string): string {
  if (status === "deviation") return "border-wheat-300";
  if (status === "no_permit") return "border-terra-400/30";
  if (status === "marked_demolition") return "border-error/40";
  if (status === "building_line_violation") return "border-wheat-300";
  return "border-[#D8D0C4]";
}

export default function BuildingCard({ building, index, isModified, onEdit }: BuildingCardProps) {
  return (
    <div
      dir="rtl"
      className={`p-4 bg-white border-[1.5px] rounded-[--radius-md] ${borderClass(building.status)} ${
        isModified ? "bg-wheat-100" : ""
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <strong className="text-soil-800 text-[0.9rem]">{building.name}</strong>
        <StatusBadge status={building.status} />
      </div>

      <p className="text-[0.85rem] text-soil-500">
        {"סוג: "}
        {BUILDING_TYPE_LABELS[building.building_type] ?? building.building_type}
        {" \u2022 "}
        {"שטח: "}
        <span dir="ltr">{building.main_area_sqm}</span>
        {' מ"ר'}
      </p>

      <button
        type="button"
        onClick={onEdit}
        aria-label={`עריכת מבנה מספר ${index + 1}`}
        className="w-full mt-2.5 p-1.5 px-3.5 border border-olive-300 rounded-[--radius-sm] bg-white text-olive-700 text-[0.82rem] hover:bg-olive-50 active:scale-[0.98] transition-all cursor-pointer"
      >
        עריכה
      </button>
    </div>
  );
}
