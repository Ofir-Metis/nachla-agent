import type { TabaData } from "@/types";

const STATUS_LABELS: Record<string, string> = {
  approved: "מאושרת",
  in_process: "בתהליך",
  deposited: "מופקדת",
};

const SOURCE_LABELS: Record<string, string> = {
  manual: "הזנה ידנית",
  pdf_extraction: "חולץ מ-PDF",
  govmap: "GovMap",
};

const STATUS_COLORS: Record<string, string> = {
  approved: "bg-success/15 text-success border-success/30",
  in_process: "bg-wheat-100 text-wheat-700 border-wheat-200",
  deposited: "bg-olive-100 text-olive-700 border-olive-200",
};

interface TabaSummaryCardProps {
  taba: TabaData;
  index: number;
  onRemove: (index: number) => void;
}

export default function TabaSummaryCard({ taba, index, onRemove }: TabaSummaryCardProps) {
  return (
    <div className="p-4 bg-white border border-[#D8D0C4] rounded-[--radius-md] relative">
      {/* Remove button */}
      <button
        type="button"
        onClick={() => onRemove(index)}
        className="absolute top-2 left-2 w-7 h-7 flex items-center justify-center text-soil-400 hover:text-error hover:bg-error/10 rounded-full cursor-pointer transition-colors bg-transparent border-none text-[1.1rem]"
        title="הסרה"
      >
        &#x2715;
      </button>

      {/* Header */}
      <div className="flex items-start gap-3 mb-3">
        <div className="min-w-0 flex-1">
          <div className="font-semibold text-[0.95rem] text-olive-800 truncate">
            {taba.taba_name}
          </div>
          <div className="text-[0.8rem] text-soil-500 mt-0.5">
            {taba.taba_number}
          </div>
        </div>
        <span className={`text-[0.72rem] font-medium px-2 py-0.5 rounded-full border shrink-0 ${STATUS_COLORS[taba.status] || ""}`}>
          {STATUS_LABELS[taba.status] || taba.status}
        </span>
      </div>

      {/* Details grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[0.8rem]">
        <div>
          <span className="text-soil-400">מגרש:</span>{" "}
          <span className="text-soil-700">{taba.plot_size_sqm} מ"ר</span>
        </div>
        <div>
          <span className="text-soil-400">יח' דיור:</span>{" "}
          <span className="text-soil-700">{taba.num_units_allowed}</span>
        </div>
        <div>
          <span className="text-soil-400">עיקרי:</span>{" "}
          <span className="text-soil-700">{taba.main_area_sqm} מ"ר</span>
        </div>
        <div>
          <span className="text-soil-400">שירות:</span>{" "}
          <span className="text-soil-700">{taba.service_area_sqm} מ"ר</span>
        </div>
      </div>

      {/* Tags */}
      <div className="flex gap-2 mt-2 text-[0.72rem]">
        {taba.split_allowed && (
          <span className="px-2 py-0.5 bg-olive-50 text-olive-600 rounded-full">פיצול מותר</span>
        )}
        {taba.pool_allowed && (
          <span className="px-2 py-0.5 bg-olive-50 text-olive-600 rounded-full">בריכה מותרת</span>
        )}
        <span className="px-2 py-0.5 bg-parchment-warm text-soil-500 rounded-full">
          {SOURCE_LABELS[taba.source] || taba.source}
        </span>
      </div>
    </div>
  );
}
