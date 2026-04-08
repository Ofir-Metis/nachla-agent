import { formatILS } from "@/lib/format";

interface HivunComparisonProps {
  hivun375?: number;
  hivun33?: number;
}

export default function HivunComparison({ hivun375, hivun33 }: HivunComparisonProps) {
  if (hivun375 == null || hivun33 == null) return null;

  return (
    <div dir="rtl" className="mt-6 p-3 sm:p-4 bg-wheat-50 border border-wheat-200 rounded-[--radius-md]">
      <h3 className="font-semibold text-[0.92rem] text-wheat-700 mb-2">
        השוואת מסלולי היוון
      </h3>

      <div className="flex flex-col sm:flex-row gap-2 sm:gap-3">
        <div className="flex-1 bg-white rounded-[--radius-sm] p-3 text-center">
          <div className="font-semibold text-olive-700 text-[0.85rem]">מסלול 3.75%</div>
          <bdi dir="ltr" className="block font-heading text-[1.1rem] font-bold mt-1 text-soil-800">
            {formatILS(hivun375)}
          </bdi>
        </div>

        <div className="flex-1 bg-white rounded-[--radius-sm] p-3 text-center">
          <div className="font-semibold text-olive-700 text-[0.85rem]">מסלול 33%</div>
          <bdi dir="ltr" className="block font-heading text-[1.1rem] font-bold mt-1 text-soil-800">
            {formatILS(hivun33)}
          </bdi>
        </div>
      </div>
    </div>
  );
}
