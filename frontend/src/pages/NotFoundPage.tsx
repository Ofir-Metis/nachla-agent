import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <div className="animate-[cardIn_0.4s_ease-out]">
      <div className="bg-cream border border-[#D8D0C4] rounded-[--radius-lg] sm:rounded-[--radius-xl] p-5 sm:p-7 sm:px-8 shadow-[--shadow-md] relative overflow-hidden text-center">
        {/* Top gradient bar */}
        <div className="absolute top-0 right-0 left-0 h-1 bg-gradient-to-l from-olive-700 via-olive-400 to-wheat-400" />

        <h1 className="font-heading text-[1.5rem] font-bold text-olive-800 mt-8 mb-3">
          הדף לא נמצא
        </h1>
        <p className="text-[0.9rem] text-soil-500 mb-8">
          הכתובת שחיפשתם אינה קיימת במערכת.
        </p>

        <Link
          to="/"
          className="inline-block px-6 py-3 rounded-[--radius-md] font-semibold text-base bg-olive-700 text-white hover:bg-olive-600 active:scale-[0.98] transition-all cursor-pointer"
        >
          חזרה לדף הראשי
        </Link>
      </div>
    </div>
  );
}
