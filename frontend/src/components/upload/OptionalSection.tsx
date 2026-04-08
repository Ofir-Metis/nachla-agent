import { useState } from "react";
import UploadSlot from "./UploadSlot";

interface OptionalSectionProps {
  files: Record<string, File | null>;
  onFileChange: (id: string, file: File | null) => void;
}

export default function OptionalSection({ files, onFileChange }: OptionalSectionProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="mt-5 border border-[#D8D0C4] rounded-[--radius-md] overflow-hidden">
      {/* Header */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full p-3.5 px-4 bg-parchment-warm font-semibold text-[0.88rem] text-soil-600 cursor-pointer flex justify-between items-center border-none"
      >
        <span>&#x1F4C1; מסמכים נוספים (אופציונלי)</span>
        <span
          className="transition-transform duration-200"
          style={{ transform: open ? "rotate(180deg)" : "rotate(0deg)" }}
        >
          &#x25BC;
        </span>
      </button>

      {/* Body */}
      {open && (
        <div className="p-4 grid grid-cols-1 sm:grid-cols-2 gap-3.5">
          <UploadSlot
            id="lease"
            icon="&#x1F4DC;"
            label="חוזה חכירה"
            formats="PDF, תמונה (JPG, PNG, TIFF)"
            file={files.lease ?? null}
            onFileChange={onFileChange}
          />
          <UploadSlot
            id="appraisal"
            icon="&#x1F4C8;"
            label="שומת מקרקעין"
            formats="PDF, תמונה (JPG, PNG, TIFF)"
            file={files.appraisal ?? null}
            onFileChange={onFileChange}
          />
        </div>
      )}
    </div>
  );
}
