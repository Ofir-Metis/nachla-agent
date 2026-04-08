import { useWizardContext } from "@/context/WizardContext";

export default function AppHeader() {
  const { jobId } = useWizardContext();

  return (
    <header className="flex items-center gap-3 sm:gap-3.5 py-3 sm:py-4 border-b border-[#D8D0C4] mb-4 sm:mb-5">
      <div className="w-10 h-10 sm:w-12 sm:h-12 bg-gradient-to-br from-olive-700 to-olive-500 rounded-[--radius-md] flex items-center justify-center shrink-0 shadow-[--shadow-sm]">
        <svg className="w-6 h-6 sm:w-7 sm:h-7 fill-white" viewBox="0 0 24 24">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
        </svg>
      </div>
      <div className="min-w-0">
        <div className="font-heading text-[1.15rem] sm:text-[1.35rem] font-bold text-olive-800 tracking-tight truncate">
          בדיקת התכנות נחלות
        </div>
        <div className="text-[0.78rem] sm:text-[0.82rem] text-soil-500 mt-px hidden sm:block">
          מערכת חכמה לניתוח נחלות חקלאיות
        </div>
      </div>
      <div className="ms-auto flex items-center gap-2 sm:gap-3 shrink-0">
        {jobId && (
          <span
            title="מסונכרן עם Monday.com"
            className="inline-block w-2 h-2 rounded-full bg-success shrink-0"
            aria-label="מסונכרן עם Monday.com"
          />
        )}
        <a
          href="tel:*9696"
          className="flex items-center gap-1.5 px-3 sm:px-4 py-2 bg-wheat-50 border border-wheat-200 rounded-full text-[0.78rem] sm:text-[0.82rem] text-wheat-700 font-medium hover:bg-wheat-100 hover:border-wheat-300 transition-all no-underline whitespace-nowrap"
        >
          <span>&#128222;</span>
          <span className="hidden sm:inline">צריכים עזרה?</span>
          <span className="sm:hidden">עזרה</span>
        </a>
      </div>
    </header>
  );
}
