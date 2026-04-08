import type { BuildingStatus } from "@/types";
import { BUILDING_STATUS_LABELS } from "@/lib/labels";

interface StatusBadgeProps {
  status: BuildingStatus;
}

const STATUS_STYLES: Record<BuildingStatus, string> = {
  compliant: "bg-success/10 text-success",
  deviation: "bg-warning/10 text-warning",
  no_permit: "bg-error/10 text-error",
  marked_demolition: "bg-error/10 text-error",
  building_line_violation: "bg-warning/10 text-warning",
};

export default function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[0.78rem] font-semibold ${STATUS_STYLES[status]}`}
    >
      {BUILDING_STATUS_LABELS[status] ?? status}
    </span>
  );
}
