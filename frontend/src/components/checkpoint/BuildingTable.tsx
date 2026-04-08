import { useState } from "react";
import type { Building } from "@/types";
import { BUILDING_TYPE_LABELS } from "@/lib/labels";
import StatusBadge from "./StatusBadge";
import BuildingEditForm from "./BuildingEditForm";

interface BuildingTableProps {
  buildings: Building[];
  modifiedIds: Set<number>;
  onBuildingUpdate: (updated: Building) => void;
}

export default function BuildingTable({ buildings, modifiedIds, onBuildingUpdate }: BuildingTableProps) {
  const [editingId, setEditingId] = useState<number | null>(null);

  const handleSave = (updated: Building) => {
    onBuildingUpdate(updated);
    setEditingId(null);
  };

  return (
    <div className="hidden md:block overflow-x-auto" dir="rtl">
      <table className="w-full border-separate border-spacing-0">
        <thead>
          <tr className="bg-olive-50">
            <th scope="col" className="p-3 px-3.5 text-right font-semibold text-olive-800 text-[0.82rem] border-b-2 border-olive-200">
              #
            </th>
            <th scope="col" className="p-3 px-3.5 text-right font-semibold text-olive-800 text-[0.82rem] border-b-2 border-olive-200">
              שם מבנה
            </th>
            <th scope="col" className="p-3 px-3.5 text-right font-semibold text-olive-800 text-[0.82rem] border-b-2 border-olive-200">
              סוג
            </th>
            <th scope="col" className="p-3 px-3.5 text-right font-semibold text-olive-800 text-[0.82rem] border-b-2 border-olive-200">
              שטח
            </th>
            <th scope="col" className="p-3 px-3.5 text-right font-semibold text-olive-800 text-[0.82rem] border-b-2 border-olive-200">
              סטטוס
            </th>
            <th scope="col" className="p-3 px-3.5 text-right font-semibold text-olive-800 text-[0.82rem] border-b-2 border-olive-200">
              <span className="sr-only">עריכה</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {buildings.map((b, idx) => (
            <BuildingRow
              key={b.id}
              building={b}
              index={idx}
              isEditing={editingId === b.id}
              isModified={modifiedIds.has(b.id)}
              onEdit={() => setEditingId(editingId === b.id ? null : b.id)}
              onSave={handleSave}
              onCancel={() => setEditingId(null)}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface BuildingRowProps {
  building: Building;
  index: number;
  isEditing: boolean;
  isModified: boolean;
  onEdit: () => void;
  onSave: (updated: Building) => void;
  onCancel: () => void;
}

function BuildingRow({ building, index, isEditing, isModified, onEdit, onSave, onCancel }: BuildingRowProps) {
  const tdBase = `p-3.5 px-3.5 border-b border-[#D8D0C4] align-middle text-[0.85rem]`;
  const rowBg = isModified ? "bg-wheat-100" : "";

  return (
    <>
      <tr className={`group ${rowBg}`}>
        <td className={`${tdBase} group-hover:bg-olive-50 text-soil-500 font-semibold`}>
          {index + 1}
        </td>
        <td className={`${tdBase} group-hover:bg-olive-50 text-soil-800 font-medium`}>
          {building.name}
        </td>
        <td className={`${tdBase} group-hover:bg-olive-50 text-soil-700`}>
          {BUILDING_TYPE_LABELS[building.building_type] ?? building.building_type}
        </td>
        <td className={`${tdBase} group-hover:bg-olive-50 text-soil-700`} dir="ltr">
          <span>{building.main_area_sqm} מ"ר</span>
        </td>
        <td className={`${tdBase} group-hover:bg-olive-50`}>
          <StatusBadge status={building.status} />
        </td>
        <td className={`${tdBase} group-hover:bg-olive-50`}>
          <button
            type="button"
            onClick={onEdit}
            aria-label={`עריכת מבנה מספר ${index + 1}`}
            className="p-1.5 px-3.5 border border-olive-300 rounded-[--radius-sm] bg-white text-olive-700 text-[0.82rem] hover:bg-olive-50 active:scale-[0.97] transition-all cursor-pointer"
          >
            עריכה
          </button>
        </td>
      </tr>
      {isEditing && (
        <tr>
          <td colSpan={6} className="p-0 px-3.5 pb-3">
            <BuildingEditForm
              building={building}
              onSave={onSave}
              onCancel={onCancel}
            />
          </td>
        </tr>
      )}
    </>
  );
}
