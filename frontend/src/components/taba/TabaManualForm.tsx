import { useState } from "react";
import type { TabaData, TabaStatus } from "@/types";

interface TabaManualFormProps {
  onAdd: (taba: TabaData) => void;
}

const STATUS_OPTIONS: { value: TabaStatus; label: string }[] = [
  { value: "approved", label: "מאושרת" },
  { value: "in_process", label: "בתהליך" },
  { value: "deposited", label: "מופקדת" },
];

export default function TabaManualForm({ onAdd }: TabaManualFormProps) {
  const [form, setForm] = useState({
    taba_number: "",
    taba_name: "",
    status: "approved" as TabaStatus,
    approval_date: "",
    plot_size_sqm: "",
    num_units_allowed: "",
    main_area_sqm: "",
    service_area_sqm: "",
    split_allowed: false,
    pool_allowed: false,
  });
  const [errors, setErrors] = useState<string[]>([]);

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
      plot_size_sqm: parseFloat(form.plot_size_sqm),
      num_units_allowed: parseFloat(form.num_units_allowed),
      main_area_sqm: parseFloat(form.main_area_sqm),
      service_area_sqm: parseFloat(form.service_area_sqm || "0"),
      split_allowed: form.split_allowed,
      pool_allowed: form.pool_allowed,
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
    });
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

      {/* Add button */}
      <button type="button" onClick={handleSubmit}
        className="w-full py-2.5 bg-olive-700 text-white font-semibold text-[0.9rem] rounded-[--radius-sm] hover:bg-olive-600 cursor-pointer transition-colors">
        הוסף תב"ע
      </button>
    </div>
  );
}
