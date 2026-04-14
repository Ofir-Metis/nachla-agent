interface GovMapMethodProps {
  gush: number | undefined;
  helka: number | undefined;
  onSwitchMethod: (method: "upload" | "manual") => void;
}

export default function GovMapMethod({ gush, helka, onSwitchMethod }: GovMapMethodProps) {
  return (
    <div className="space-y-4">
      {/* Search info */}
      <div className="p-4 bg-white border border-[#D8D0C4] rounded-[--radius-md]">
        <div className="flex items-center gap-3 mb-3">
          <span className="text-xl">&#x1F50D;</span>
          <div>
            <div className="text-[0.9rem] font-medium text-soil-700">
              חיפוש לפי גוש {gush || "—"} חלקה {helka || "—"}
            </div>
          </div>
        </div>
        <button
          type="button"
          disabled
          className="w-full py-2.5 bg-olive-200 text-olive-500 font-semibold text-[0.9rem] rounded-[--radius-sm] cursor-not-allowed"
        >
          חיפוש ב-GovMap (בפיתוח)
        </button>
      </div>

      {/* Unavailable notice */}
      <div role="alert" className="p-4 bg-wheat-50 border border-wheat-200 rounded-[--radius-md] text-[0.85rem] text-wheat-700">
        <p className="font-medium mb-2">&#x26A0;&#xFE0F; שירות החיפוש האוטומטי אינו זמין כרגע</p>
        <p className="text-soil-500 mb-3">
          חיפוש אוטומטי מ-GovMap נמצא בפיתוח. בינתיים, ניתן להשתמש באחת מהאפשרויות הבאות:
        </p>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => onSwitchMethod("upload")}
            className="px-4 py-2 text-[0.82rem] font-medium bg-olive-700 text-white rounded-[--radius-sm] hover:bg-olive-600 cursor-pointer transition-colors"
          >
            העלאת מסמך
          </button>
          <button
            type="button"
            onClick={() => onSwitchMethod("manual")}
            className="px-4 py-2 text-[0.82rem] font-medium bg-white text-olive-700 border border-olive-300 rounded-[--radius-sm] hover:bg-olive-50 cursor-pointer transition-colors"
          >
            הזנה ידנית
          </button>
        </div>
      </div>
    </div>
  );
}
