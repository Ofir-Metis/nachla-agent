import { getDownloadUrl } from "@/lib/api";

interface DownloadGridProps {
  jobId: string;
  downloadTypes: string[];
}

interface DownloadCardDef {
  type: string;
  icon: string;
  label: string;
  format: string;
}

const ALL_CARDS: DownloadCardDef[] = [
  { type: "word", icon: "\uD83D\uDCC4", label: "דוח מקצועי", format: "Word .docx" },
  { type: "excel", icon: "\uD83D\uDCCA", label: "טבלת תחשיבים", format: "Excel .xlsx" },
  { type: "pdf", icon: "\uD83D\uDCCB", label: "סיכום מנהלים", format: "PDF" },
  { type: "audit", icon: "\uD83D\uDCDD", label: "יומן חישובים", format: "JSON" },
];

export default function DownloadGrid({ jobId, downloadTypes }: DownloadGridProps) {
  const available = ALL_CARDS.filter((c) => downloadTypes.includes(c.type));

  const handleDownload = (type: string) => {
    const url = getDownloadUrl(jobId, type);
    const a = document.createElement("a");
    a.href = url;
    a.download = "";
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  return (
    <div dir="rtl" className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 sm:gap-3 mt-5">
      {available.map((card) => (
        <button
          key={card.type}
          type="button"
          onClick={() => handleDownload(card.type)}
          className="p-4 sm:p-5 px-3 sm:px-4 border-[1.5px] border-[#D8D0C4] rounded-[--radius-md] sm:rounded-[--radius-lg] text-center bg-white cursor-pointer
            hover:border-olive-400 hover:bg-olive-50 hover:-translate-y-0.5 hover:shadow-[--shadow-md]
            transition-all duration-200"
        >
          <div className="text-[1.5rem] sm:text-[2rem] mb-1.5 sm:mb-2">{card.icon}</div>
          <div className="font-semibold text-[0.82rem] sm:text-[0.88rem] text-soil-800">{card.label}</div>
          <div className="text-[0.78rem] text-soil-500 mt-0.5">{card.format}</div>
        </button>
      ))}
    </div>
  );
}
