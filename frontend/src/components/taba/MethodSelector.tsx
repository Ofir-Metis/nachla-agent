export type TabaMethod = "govmap" | "upload" | "manual";

interface MethodCardProps {
  id: TabaMethod;
  icon: string;
  title: string;
  subtitle: string;
  badge?: string;
  selected: boolean;
  onSelect: (id: TabaMethod) => void;
}

function MethodCard({ id, icon, title, subtitle, badge, selected, onSelect }: MethodCardProps) {
  return (
    <button
      type="button"
      onClick={() => onSelect(id)}
      className={`
        relative p-4 rounded-[--radius-md] border-2 text-right cursor-pointer transition-all
        ${selected
          ? "border-olive-600 bg-olive-50 ring-2 ring-olive-600/20"
          : "border-[#D8D0C4] bg-white hover:border-olive-300 hover:bg-olive-50/30"
        }
      `}
    >
      {badge && (
        <span className="absolute top-2 left-2 text-[0.65rem] font-medium px-2 py-0.5 rounded-full bg-wheat-100 text-wheat-700 border border-wheat-200">
          {badge}
        </span>
      )}
      <div className="text-2xl mb-2">{icon}</div>
      <div className="font-semibold text-[0.92rem] text-olive-800 mb-1">{title}</div>
      <div className="text-[0.78rem] text-soil-500 leading-relaxed">{subtitle}</div>
    </button>
  );
}

interface MethodSelectorProps {
  selected: TabaMethod | null;
  onSelect: (method: TabaMethod) => void;
}

export default function MethodSelector({ selected, onSelect }: MethodSelectorProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
      <MethodCard
        id="govmap"
        icon="&#x1F30D;"
        title="שליפה מ-GovMap"
        subtitle='חיפוש תב"עות אוטומטי לפי גוש וחלקה'
        badge="בפיתוח"
        selected={selected === "govmap"}
        onSelect={onSelect}
      />
      <MethodCard
        id="upload"
        icon="&#x1F4C4;"
        title='העלאת מסמך תב"ע'
        subtitle="העלו PDF — המערכת תחלץ את הנתונים"
        selected={selected === "upload"}
        onSelect={onSelect}
      />
      <MethodCard
        id="manual"
        icon="&#x270F;&#xFE0F;"
        title="הזנה ידנית"
        subtitle='מלאו את פרטי התב"ע ידנית'
        selected={selected === "manual"}
        onSelect={onSelect}
      />
    </div>
  );
}
