import { useState, useCallback } from "react";
import { extractDocuments } from "@/lib/api";
import UploadSlot from "@/components/upload/UploadSlot";
import type { TabaData } from "@/types";

interface TabaUploadMethodProps {
  onTabasExtracted: (tabas: TabaData[]) => void;
}

export default function TabaUploadMethod({ onTabasExtracted }: TabaUploadMethodProps) {
  const [file, setFile] = useState<File | null>(null);
  const [extracting, setExtracting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const handleExtract = useCallback(async () => {
    if (!file) return;
    setError(null);
    setExtracting(true);

    try {
      const result = await extractDocuments({ taba_document: file }, () => {});
      const tabas = (result.tabas || []) as unknown as TabaData[];

      if (tabas.length === 0) {
        setError('לא זוהו נתוני תב"ע במסמך. נסו להזין ידנית.');
      } else {
        // Mark source
        const tagged = tabas.map((t, i) => ({
          ...t,
          source: "pdf_extraction" as const,
          is_primary: i === 0,
        }));
        onTabasExtracted(tagged);
        setDone(true);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'שגיאה בניתוח המסמך.');
    } finally {
      setExtracting(false);
    }
  }, [file, onTabasExtracted]);

  if (done) {
    return (
      <div className="p-4 bg-success/10 border border-success/30 rounded-[--radius-md] text-[0.9rem] text-success">
        &#x2705; נתוני תב"ע חולצו בהצלחה מהמסמך
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <UploadSlot
        id="taba_pdf"
        icon="&#x1F4CB;"
        label='מסמך תב"ע'
        formats="PDF"
        file={file}
        onFileChange={(_id, f) => { setFile(f); setDone(false); }}
      />

      {error && (
        <div role="alert" className="p-3 bg-error/10 border border-error/30 rounded-[--radius-sm] text-error text-[0.85rem]">
          {error}
        </div>
      )}

      {file && !extracting && (
        <button
          type="button"
          onClick={handleExtract}
          className="w-full py-2.5 bg-olive-700 text-white font-semibold text-[0.9rem] rounded-[--radius-sm] hover:bg-olive-600 cursor-pointer transition-colors"
        >
          חלץ נתוני תב"ע
        </button>
      )}

      {extracting && (
        <div className="flex items-center justify-center gap-3 py-4">
          <span className="inline-block w-5 h-5 border-2 border-olive-300 border-t-olive-700 rounded-full animate-spin" />
          <span className="text-[0.9rem] text-soil-600">מנתח מסמך תב"ע...</span>
        </div>
      )}
    </div>
  );
}
