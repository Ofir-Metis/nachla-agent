import { ErrorBoundary as ReactErrorBoundary, type FallbackProps } from "react-error-boundary";
import type { ReactNode } from "react";
import ErrorState from "./processing/ErrorState";

function ErrorFallback({ error, resetErrorBoundary }: FallbackProps) {
  const message = error instanceof Error ? error.message : String(error);
  return (
    <div className="min-h-[60vh] flex items-center justify-center p-6">
      <ErrorState
        message="אירעה שגיאה בלתי צפויה"
        detail={import.meta.env.DEV ? message : "אנא רעננו את הדף ונסו שנית."}
        onRetry={resetErrorBoundary}
      />
    </div>
  );
}

export default function AppErrorBoundary({ children }: { children: ReactNode }) {
  return (
    <ReactErrorBoundary
      FallbackComponent={ErrorFallback}
      onReset={() => window.location.assign("/")}
    >
      {children}
    </ReactErrorBoundary>
  );
}
