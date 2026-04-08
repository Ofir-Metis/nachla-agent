const STEP_LABELS = [
  "פרטי בעלים",
  "מיקום הנחלה",
  "סטטוס משפטי",
  "מטרות ופרטים",
];

interface WizardStepperProps {
  currentStep: number; // 1-4
  completedSteps: number[];
}

export default function WizardStepper({ currentStep, completedSteps }: WizardStepperProps) {
  return (
    <div className="flex items-center justify-center mb-4 sm:mb-5" dir="rtl" role="list" aria-label="שלבי הטופס">
      {STEP_LABELS.map((label, idx) => {
        const stepNum = idx + 1;
        const isActive = stepNum === currentStep;
        const isCompleted = completedSteps.includes(stepNum);
        const showConnector = idx < STEP_LABELS.length - 1;

        return (
          <div key={stepNum} className="flex items-center" role="listitem">
            {/* Step circle + label */}
            <div className="flex flex-col items-center">
              <div
                aria-current={isActive ? "step" : undefined}
                className={[
                  "w-9 h-9 sm:w-11 sm:h-11 rounded-full flex items-center justify-center font-heading font-semibold text-xs sm:text-sm transition-all",
                  isActive
                    ? "bg-olive-700 text-white shadow-[0_0_0_4px_rgba(61,90,62,0.15)] scale-[1.08]"
                    : isCompleted
                      ? "bg-olive-400 text-white"
                      : "bg-parchment-warm border-[1.5px] border-[#D8D0C4] text-soil-500",
                ].join(" ")}
              >
                {isCompleted && !isActive ? (
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                    <path d="M3 8.5L6.5 12L13 4" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                ) : (
                  stepNum
                )}
              </div>
              <span
                className={[
                  "text-[0.72rem] sm:text-[0.78rem] mt-1 sm:mt-1.5 whitespace-nowrap hidden sm:block",
                  isActive
                    ? "text-olive-700 font-semibold !block"
                    : "text-soil-500 font-medium",
                ].join(" ")}
              >
                {label}
              </span>
            </div>

            {/* Connector line */}
            {showConnector && (
              <div
                className={[
                  "w-6 sm:w-12 h-0.5 mx-1 sm:mx-2 mt-0 sm:mt-[-1.2rem] rounded-full transition-colors",
                  completedSteps.includes(stepNum) ? "bg-olive-400" : "bg-[#D8D0C4]",
                ].join(" ")}
                aria-hidden="true"
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
