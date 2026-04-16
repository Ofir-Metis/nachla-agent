import { useState, useEffect } from "react";
import type { TabaData, TabaStatus } from "@/types";

interface TabaManualFormProps {
  onAdd: (taba: TabaData) => void;
  initialData?: Partial<TabaData>;
  editMode?: boolean;
}

const STATUS_OPTIONS: { value: TabaStatus; label: string }[] = [
  { value: "approved", label: "מאושרת" },
  { value: "in_process", label: "בתהליך" },
  { value: "deposited", label: "מופקדת" },
];

function buildFormState(data?: Partial<TabaData>) {
  return {
    taba_number: data?.taba_number ?? "",
    taba_name: data?.taba_name ?? "",
    status: (data?.status ?? "approved") as TabaStatus,
    approval_date: data?.approval_date ?? "",
    plot_size_sqm: data?.plot_size_sqm != null ? String(data.plot_size_sqm) : "",
    num_units_allowed: data?.num_units_allowed != null ? String(data.num_units_allowed) : "",
    main_area_sqm: data?.main_area_sqm != null ? String(data.main_area_sqm) : "",
    service_area_sqm: data?.service_area_sqm != null ? String(data.service_area_sqm) : "",
    split_allowed: data?.split_allowed ?? false,
    pool_allowed: data?.pool_allowed ?? false,
    plot_id: data?.plot_id ?? "",
    mamad_sqm: data?.mamad_sqm != null ? String(data.mamad_sqm) : "12",
    attached_unit_allowed: data?.attached_unit_allowed ?? true,
    attached_unit_sqm: data?.attached_unit_sqm != null ? String(data.attached_unit_sqm) : "55",
    plach_area_sqm: data?.plach_area_sqm != null ? String(data.plach_area_sqm) : "",
    split_min_plot_sqm: data?.split_min_plot_sqm != null ? String(data.split_min_plot_sqm) : "350",
    coverage_percent: data?.coverage_percent != null ? String(data.coverage_percent) : "",
  };
}

export default function TabaManualForm({ onAdd, initialData, editMode }: TabaManualFormProps) {
  const [form, setForm] = useState(() => buildFormState(initialData));

  // Re-populate form when initialData changes (e.g. user clicks edit on a different taba)
  useEffect(() => {
    if (initialData) {
      setForm(buildFormState(initialData));
    }
  }, [initialData]);
  const [errors, setErrors] = useState<string[]>([]);
  const [showExtra, setShowExtra] = useState(false);

  const update = (key: string, value: string | boolean) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = () => {
    const errs: string[] = [];
    if (!form.taba_number.trim()) errs.push('מספר תב"ע הוא שדה חובה');
    if (!form.taba_name.trim()) errs.push('שם תב"ע הוא שדה חובה');
    if (!form.plot_size_sqm || parseFloat(form.plot_size_sqm) <= 0) errs.push("שטח מגרש חייב להיות חיובי");
    if (!form.num_units_allowed || parseFloat(form.num_units_allowed) <= 0) errs.push("מספר יחידות דיור חייב להיות חיובי");
    if (!form.main_area_sqm || parseFloat(form.main_area_sqm) <= 0) errs.push("שטח עיקרי חייב להיות חיובי");

    if (errs.length > 0) {
      setErrors(errs);
      return;
    }

    const taba: TabaData = {
      taba_number: form.taba_number.trim(),
      taba_name: form.taba_name.trim(),
      status: form.status,
      approval_date: form.approval_date || undefined,
      plot_id: form.plot_id.trim() || undefined,
      plot_size_sqm: parseFloat(form.plot_size_sqm),
      num_units_allowed: parseFloat(form.num_units_allowed),
      main_area_sqm: parseFloat(form.main_area_sqm),
      service_area_sqm: parseFloat(form.service_area_sqm || "0"),
      mamad_sqm: form.mamad_sqm ? parseFloat(form.mamad_sqm) : undefined,
      split_allowed: form.split_allowed,
      split_min_plot_sqm: form.split_allowed && form.split_min_plot_sqm ? parseFloat(form.split_min_plot_sqm) : undefined,
      pool_allowed: form.pool_allowed,
      attached_unit_allowed: form.attached_unit_allowed,
      attached_unit_sqm: form.attached_unit_allowed && form.attached_unit_sqm ? parseFloat(form.attached_unit_sqm) : undefined,
      plach_area_sqm: form.plach_area_sqm ? parseFloat(form.plach_area_sqm) : undefined,
      coverage_percent: form.coverage_percent ? parseFloat(form.coverage_percent) : undefined,
      source: "manual",
      is_primary: true,
    };

    onAdd(taba);
    setErrors([]);
    // Reset form
    setForm({
      taba_number: "", taba_name: "", status: "approved", approval_date: "",
      plot_size_sqm: "", num_units_allowed: "", main_area_sqm: "",
      service_area_sqm: "", split_allowed: false, pool_allowed: false,
      plot_id: "", mamad_sqm: "12", attached_unit_allowed: true,
      attached_unit_sqm: "55", plach_area_sqm: "", split_min_plot_sqm: "350",
      coverage_percent: "",
    });
    setShowExtra(false);
  };

  return (
    <div className="space-y-4">
      {errors.length > 0 && (
        <div role="alert" className="p-3 bg-error/10 border border-error/30 rounded-[--radius-sm] text-error text-[0.85rem]">
          {errors.map((e, i) => <p key={i}>{e}</p>)}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {/* Taba number */}
        <div>
          <label className="block text-[0.82rem] font-medium text-soil-700 mb-1">מספר תב"ע *</label>
          <input type="text" value={form.taba_number} onChange={(e) => update("taba_number", e.target.value)}
            placeholder='לדוגמה: 616-0902908'
            className="w-full px-3 py-2.5 border border-[#D8D0C4] rounded-[--radius-sm] text-[0.88rem] bg-white focus:outline-none focus:border-olive-500 focus:ring-2 focus:ring-olive-500/20" />
        </div>

        {/* Taba name */}
        <div>
          <label className="block text-[0.82rem] font-medium text-soil-700 mb-1">שם תב"ע *</label>
          <input type="text" value={form.taba_name} onChange={(e) => update("taba_name", e.target.value)}
            className="w-full px-3 py-2.5 border border-[#D8D0C4] rounded-[--radius-sm] text-[0.88rem] bg-white focus:outline-none focus:border-olive-500 focus:ring-2 focus:ring-olive-500/20" />
        </div>

        {/* Status */}
        <div>
          <label className="block text-[0.82rem] font-medium text-soil-700 mb-1">סטטוס *</label>
          <div className="flex gap-2">
            {STATUS_OPTIONS.map((opt) => (
              <button key={opt.value} type="button"
                onClick={() => update("status", opt.value)}
                className={`flex-1 py-2 text-[0.82rem] font-medium rounded-[--radius-sm] border cursor-pointer transition-colors ${
                  form.status === opt.value
                    ? "bg-olive-700 text-white border-olive-700"
                    : "bg-white text-soil-600 border-[#D8D0C4] hover:border-olive-300"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Approval date */}
        <div>
          <label className="block text-[0.82rem] font-medium text-soil-700 mb-1">תאריך אישור</label>
          <input type="date" value={form.approval_date} onChange={(e) => update("approval_date", e.target.value)}
            className="w-full px-3 py-2.5 border border-[#D8D0C4] rounded-[--radius-sm] text-[0.88rem] bg-white focus:outline-none focus:border-olive-500 focus:ring-2 focus:ring-olive-500/20" />
        </div>

        {/* Plot size */}
        <div>
          <label className="block text-[0.82rem] font-medium text-soil-700 mb-1">שטח מגרש (מ"ר) *</label>
          <input type="number" inputMode="decimal" value={form.plot_size_sqm} onChange={(e) => update("plot_size_sqm", e.target.value)}
            placeholder="2500"
            className="w-full px-3 py-2.5 border border-[#D8D0C4] rounded-[--radius-sm] text-[0.88rem] bg-white focus:outline-none focus:border-olive-500 focus:ring-2 focus:ring-olive-500/20" />
        </div>

        {/* Units allowed */}
        <div>
          <label className="block text-[0.82rem] font-medium text-soil-700 mb-1">יחידות דיור מותרות *</label>
          <input type="number" inputMode="decimal" value={form.num_units_allowed} onChange={(e) => update("num_units_allowed", e.target.value)}
            placeholder="2"
            className="w-full px-3 py-2.5 border border-[#D8D0C4] rounded-[--radius-sm] text-[0.88rem] bg-white focus:outline-none focus:border-olive-500 focus:ring-2 focus:ring-olive-500/20" />
        </div>

        {/* Main area per unit */}
        <div>
          <label className="block text-[0.82rem] font-medium text-soil-700 mb-1">שטח עיקרי ליח' דיור (מ"ר) *</label>
          <input type="number" inputMode="decimal" value={form.main_area_sqm} onChange={(e) => update("main_area_sqm", e.target.value)}
            placeholder="160"
            className="w-full px-3 py-2.5 border border-[#D8D0C4] rounded-[--radius-sm] text-[0.88rem] bg-white focus:outline-none focus:border-olive-500 focus:ring-2 focus:ring-olive-500/20" />
        </div>

        {/* Service area per unit */}
        <div>
          <label className="block text-[0.82rem] font-medium text-soil-700 mb-1">שטח שירות ליח' דיור (מ"ר)</label>
          <input type="number" inputMode="decimal" value={form.service_area_sqm} onChange={(e) => update("service_area_sqm", e.target.value)}
            placeholder="55"
            className="w-full px-3 py-2.5 border border-[#D8D0C4] rounded-[--radius-sm] text-[0.88rem] bg-white focus:outline-none focus:border-olive-500 focus:ring-2 focus:ring-olive-500/20" />
        </div>
      </div>

      {/* Toggles */}
      <div className="flex gap-6 pt-2">
        <label className="flex items-center gap-2 cursor-pointer select-none">
          <input type="checkbox" checked={form.split_allowed} onChange={(e) => update("split_allowed", e.target.checked)}
            className="w-[18px] h-[18px] accent-olive-600 cursor-pointer" />
          <span className="text-[0.85rem] text-soil-600">פיצול מותר</span>
        </label>
        <label className="flex items-center gap-2 cursor-pointer select-none">
          <input type="checkbox" checked={form.pool_allowed} onChange={(e) => update("pool_allowed", e.target.checked)}
            className="w-[18px] h-[18px] accent-olive-600 cursor-pointer" />
          <span className="text-[0.85rem] text-soil-600">בריכה מותרת</span>
        </label>
      </div>

      {/* Collapsible extra fields */}
      <div className="pt-1">
        <button
          type="button"
          onClick={() => setShowExtra((prev) => !prev)}
          className="flex items-center gap-1.5 text-[0.85rem] text-olive-700 hover:text-olive-900 cursor-pointer bg-transparent border-none font-medium"
        >
          <span className={`inline-block transition-transform duration-200 ${showExtra ? "rotate-90" : ""}`}>&lsaquo;</span>
          <span>פרטים נוספים</span>
        </button>

        {showExtra && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3 pt-3 border-t border-[#D8D0C4]/50">
            {/* Plot ID */}
            <div>
              <label className="block text-[0.82rem] font-medium text-soil-700 mb-1">מזהה מגרש</label>
              <input type="text" value={form.plot_id} onChange={(e) => update("plot_id", e.target.value)}
                placeholder="לדוגמה: מגרש 68"
                className="w-full px-3 py-2.5 border border-[#D8D0C4] rounded-[--radius-sm] text-[0.88rem] bg-white focus:outline-none focus:border-olive-500 focus:ring-2 focus:ring-olive-500/20" />
            </div>

            {/* Mamad sqm */}
            <div>
              <label className="block text-[0.82rem] font-medium text-soil-700 mb-1">שטח ממ"ד ליח' דיור (מ"ר)</label>
              <input type="number" inputMode="decimal" value={form.mamad_sqm} onChange={(e) => update("mamad_sqm", e.target.value)}
                className="w-full px-3 py-2.5 border border-[#D8D0C4] rounded-[--radius-sm] text-[0.88rem] bg-white focus:outline-none focus:border-olive-500 focus:ring-2 focus:ring-olive-500/20" />
            </div>

            {/* Attached unit allowed */}
            <div className="sm:col-span-2">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input type="checkbox" checked={form.attached_unit_allowed} onChange={(e) => update("attached_unit_allowed", e.target.checked)}
                  className="w-[18px] h-[18px] accent-olive-600 cursor-pointer" />
                <span className="text-[0.85rem] text-soil-600">יחידה צמודה מותרת</span>
              </label>
            </div>

            {/* Attached unit sqm — shown when allowed */}
            {form.attached_unit_allowed && (
              <div>
                <label className="block text-[0.82rem] font-medium text-soil-700 mb-1">שטח יחידה צמודה (מ"ר)</label>
                <input type="number" inputMode="decimal" value={form.attached_unit_sqm} onChange={(e) => update("attached_unit_sqm", e.target.value)}
                  className="w-full px-3 py-2.5 border border-[#D8D0C4] rounded-[--radius-sm] text-[0.88rem] bg-white focus:outline-none focus:border-olive-500 focus:ring-2 focus:ring-olive-500/20" />
              </div>
            )}

            {/* Plach area */}
            <div>
              <label className="block text-[0.82rem] font-medium text-soil-700 mb-1">שטח פל"ח מותר (מ"ר)</label>
              <input type="number" inputMode="decimal" value={form.plach_area_sqm} onChange={(e) => update("plach_area_sqm", e.target.value)}
                className="w-full px-3 py-2.5 border border-[#D8D0C4] rounded-[--radius-sm] text-[0.88rem] bg-white focus:outline-none focus:border-olive-500 focus:ring-2 focus:ring-olive-500/20" />
            </div>

            {/* Split min plot sqm — shown when split_allowed */}
            {form.split_allowed && (
              <div>
                <label className="block text-[0.82rem] font-medium text-soil-700 mb-1">שטח מינימלי לפיצול</label>
                <input type="number" inputMode="decimal" value={form.split_min_plot_sqm} onChange={(e) => update("split_min_plot_sqm", e.target.value)}
                  className="w-full px-3 py-2.5 border border-[#D8D0C4] rounded-[--radius-sm] text-[0.88rem] bg-white focus:outline-none focus:border-olive-500 focus:ring-2 focus:ring-olive-500/20" />
              </div>
            )}

            {/* Coverage percent */}
            <div>
              <label className="block text-[0.82rem] font-medium text-soil-700 mb-1">אחוז כיסוי מקסימלי</label>
              <input type="number" inputMode="decimal" value={form.coverage_percent} onChange={(e) => update("coverage_percent", e.target.value)}
                className="w-full px-3 py-2.5 border border-[#D8D0C4] rounded-[--radius-sm] text-[0.88rem] bg-white focus:outline-none focus:border-olive-500 focus:ring-2 focus:ring-olive-500/20" />
            </div>
          </div>
        )}
      </div>

      {/* Add / Update button */}
      <button type="button" onClick={handleSubmit}
        className="w-full py-2.5 bg-olive-700 text-white font-semibold text-[0.9rem] rounded-[--radius-sm] hover:bg-olive-600 cursor-pointer transition-colors">
        {editMode ? 'עדכן תב"ע' : 'הוסף תב"ע'}
      </button>
    </div>
  );
}
