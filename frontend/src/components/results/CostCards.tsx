import { formatILS } from "@/lib/format";

interface CostCardsProps {
  permitFees: number;
  usageFees: number;
  bettermentLevy: number;
  total: number;
}

interface CostRowProps {
  label: string;
  value: number;
  isTotal?: boolean;
}

function CostRow({ label, value, isTotal }: CostRowProps) {
  if (isTotal) {
    return (
      <div className="flex items-center justify-between p-3 sm:p-3.5 px-4 sm:px-4.5 bg-olive-700 border border-olive-700 rounded-[--radius-md]">
        <span className="text-[0.85rem] sm:text-[0.9rem] text-olive-200 font-semibold">{label}</span>
        <bdi dir="ltr" className="font-heading text-[1.05rem] sm:text-[1.2rem] font-bold text-white">
          {formatILS(value)}
        </bdi>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-between p-3 sm:p-3.5 px-4 sm:px-4.5 bg-white border border-[#D8D0C4] rounded-[--radius-md]">
      <span className="text-[0.85rem] sm:text-[0.9rem] text-soil-600">{label}</span>
      <bdi dir="ltr" className="font-heading text-[1rem] sm:text-[1.05rem] font-bold text-soil-800">
        {formatILS(value)}
      </bdi>
    </div>
  );
}

export default function CostCards({ permitFees, usageFees, bettermentLevy, total }: CostCardsProps) {
  return (
    <div className="flex flex-col gap-3" dir="rtl">
      <CostRow label="דמי היתר" value={permitFees} />
      <CostRow label="דמי שימוש" value={usageFees} />
      <CostRow label="היטל השבחה" value={bettermentLevy} />
      <CostRow label='סה"כ עלות' value={total} isTotal />
    </div>
  );
}
