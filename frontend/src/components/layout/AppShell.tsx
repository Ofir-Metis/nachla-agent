import type { ReactNode } from "react";
import AppHeader from "./AppHeader";
import AppFooter from "./AppFooter";

export default function AppShell({ children }: { children: ReactNode }) {
  return (
    <div dir="rtl" className="relative max-w-[800px] mx-auto px-4 sm:px-5 min-h-[100dvh] flex flex-col overflow-x-hidden">
      <AppHeader />
      <main className="flex-1">{children}</main>
      <AppFooter />
    </div>
  );
}
