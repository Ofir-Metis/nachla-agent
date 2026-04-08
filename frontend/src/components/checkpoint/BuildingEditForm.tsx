import { useState } from "react";
import type { Building, BuildingType, BuildingStatus } from "@/types";
import { BUILDING_TYPE_LABELS, BUILDING_STATUS_LABELS } from "@/lib/labels";

interface BuildingEditFormProps {
  building: Building;
  onSave: (updated: Building) => void;
  onCancel: () => void;
}

const BUILDING_TYPES = Object.keys(BUILDING_TYPE_LABELS) as BuildingType[];
const BUILDING_STATUSES = Object.keys(BUILDING_STATUS_LABELS) as BuildingStatus[];

export default function BuildingEditForm({ building, onSave, onCancel }: BuildingEditFormProps) {
  const [name, setName] = useState(building.name);
  const [buildingType, setBuildingType] = useState<BuildingType>(building.building_type);
  const [status, setStatus] = useState<BuildingStatus>(building.status);
  const [mainArea, setMainArea] = useState(String(building.main_area_sqm));

  const handleSave = () => {
    const area = parseFloat(mainArea);
    if (isNaN(area) || area < 0) return;
    // Preserve total_area_sqm — backend recomputes it from sub-areas.
    // Only update main_area_sqm; keep other area components intact.
    const areaDiff = area - building.main_area_sqm;
    onSave({
      ...building,
      name,
      building_type: buildingType,
      status,
      main_area_sqm: area,
      total_area_sqm: building.total_area_sqm + areaDiff,
      user_confirmed: true,
    });
  };

  const selectClass =
    "w-full p-2 px-3 border border-olive-300 rounded-[--radius-sm] bg-white text-soil-800 text-[0.85rem] focus:outline-none focus:ring-2 focus:ring-olive-400";

  return (
    <div
      dir="rtl"
      className="bg-parchment-warm border border-[#D8D0C4] rounded-[--radius-md] p-4 mt-2 animate-[cardIn_0.3s_ease-out]"
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {/* Name */}
        <div>
          <label htmlFor={`edit-name-${building.id}`} className="block text-[0.8rem] font-semibold text-soil-600 mb-1">
            שם מבנה
          </label>
          <input
            id={`edit-name-${building.id}`}
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className={selectClass}
          />
        </div>

        {/* Building Type */}
        <div>
          <label htmlFor={`edit-type-${building.id}`} className="block text-[0.8rem] font-semibold text-soil-600 mb-1">
            סוג מבנה
          </label>
          <select
            id={`edit-type-${building.id}`}
            value={buildingType}
            onChange={(e) => setBuildingType(e.target.value as BuildingType)}
            className={selectClass}
          >
            {BUILDING_TYPES.map((type) => (
              <option key={type} value={type}>
                {BUILDING_TYPE_LABELS[type]}
              </option>
            ))}
          </select>
        </div>

        {/* Status */}
        <div>
          <label htmlFor={`edit-status-${building.id}`} className="block text-[0.8rem] font-semibold text-soil-600 mb-1">
            סטטוס
          </label>
          <select
            id={`edit-status-${building.id}`}
            value={status}
            onChange={(e) => setStatus(e.target.value as BuildingStatus)}
            className={selectClass}
          >
            {BUILDING_STATUSES.map((s) => (
              <option key={s} value={s}>
                {BUILDING_STATUS_LABELS[s]}
              </option>
            ))}
          </select>
        </div>

        {/* Area */}
        <div>
          <label htmlFor={`edit-area-${building.id}`} className="block text-[0.8rem] font-semibold text-soil-600 mb-1">
            שטח עיקרי (מ"ר)
          </label>
          <input
            id={`edit-area-${building.id}`}
            type="number"
            dir="ltr"
            min="0"
            step="0.1"
            value={mainArea}
            onChange={(e) => setMainArea(e.target.value)}
            className={`${selectClass} text-left`}
          />
        </div>
      </div>

      <div className="flex gap-2 mt-4 justify-start">
        <button
          type="button"
          onClick={handleSave}
          className="px-4 py-2 text-[0.82rem] font-semibold rounded-[--radius-sm] bg-olive-700 text-white hover:bg-olive-800 active:scale-[0.98] transition-all cursor-pointer"
        >
          שמור שינויים
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-[0.82rem] font-semibold rounded-[--radius-sm] border border-olive-300 bg-white text-soil-700 hover:bg-olive-50 active:scale-[0.98] transition-all cursor-pointer"
        >
          ביטול
        </button>
      </div>
    </div>
  );
}
