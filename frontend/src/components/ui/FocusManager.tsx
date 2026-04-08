import { useEffect, useRef, type ReactNode } from "react";

interface FocusManagerProps {
  children: ReactNode;
  /** When this value changes the first h1 inside the container receives focus. */
  focusKey: string | number;
}

/**
 * Wraps a section and moves focus to its first <h1> whenever `focusKey`
 * changes.  The heading must have tabIndex={-1} so it can receive
 * programmatic focus without appearing in the natural tab order.
 */
export default function FocusManager({ children, focusKey }: FocusManagerProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const heading = el.querySelector<HTMLElement>("h1[tabindex]");
    if (heading) {
      heading.focus({ preventScroll: false });
    }
  }, [focusKey]);

  return <div ref={containerRef}>{children}</div>;
}
