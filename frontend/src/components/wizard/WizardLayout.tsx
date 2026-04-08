import type { ReactNode } from "react";
import FocusManager from "@/components/ui/FocusManager";

interface WizardLayoutProps {
  title: string;
  subtitle: string;
  children: ReactNode;
  stepKey: number; // used as animation key
}

export default function WizardLayout({ title, subtitle, children, stepKey }: WizardLayoutProps) {
  return (
    <FocusManager focusKey={stepKey}>
      <div
        key={stepKey}
        className="animate-[cardIn_0.4s_ease-out]"
      >
        <div
          className="bg-cream border border-[#D8D0C4] rounded-[--radius-lg] sm:rounded-[--radius-xl] p-5 sm:p-7 sm:px-8 shadow-[--shadow-md] relative overflow-hidden"
          role="region"
          aria-label="טופס קליטת נחלה"
        >
          {/* Top gradient bar */}
          <div className="absolute top-0 right-0 left-0 h-1 bg-gradient-to-l from-olive-700 via-olive-400 to-wheat-400" />

          <h1
            tabIndex={-1}
            className="font-heading text-[1.35rem] font-bold text-olive-800 mb-1.5 outline-none"
          >
            {title}
          </h1>
          <p className="text-[0.9rem] text-soil-600 mb-5 leading-relaxed">
            {subtitle}
          </p>

          {children}
        </div>
      </div>
    </FocusManager>
  );
}
