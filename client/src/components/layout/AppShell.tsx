import type { ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { cn } from "@/lib/utils";

interface AppShellProps {
  active: "dashboard" | "generator";
  schoolName?: string;
  onSignOut: () => void;
  children: ReactNode;
}

const navLinkClass =
  "flex items-center gap-3 px-4 py-3 rounded-r-full text-on-surface-variant hover:bg-surface-variant transition-all duration-200 font-label-md text-label-md";
const navLinkActiveClass =
  "flex items-center gap-3 px-4 py-3 rounded-r-full bg-primary-container text-on-primary-container font-bold translate-x-1 transition-transform duration-200 font-label-md text-label-md";

export function AppShell({ active, schoolName = "Your Institution", onSignOut, children }: AppShellProps) {
  return (
    <div className="min-h-screen flex flex-col md:flex-row font-body-md">
      {/* SideNavBar (Desktop) */}
      <nav className="hidden md:flex flex-col h-screen sticky top-0 left-0 bg-surface-container-low border-r border-outline-variant w-64 z-40">
        <div className="p-6">
          <h1 className="font-headline-md text-headline-md text-primary tracking-tight">QuickPaperAI</h1>
          <div className="mt-8 flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-surface-variant flex items-center justify-center overflow-hidden border border-outline-variant font-label-md text-label-md font-bold text-primary">
              {schoolName.slice(0, 2).toUpperCase()}
            </div>
            <div>
              <div className="font-label-md text-label-md font-bold text-on-surface">{schoolName}</div>
              <div className="font-label-sm text-label-sm text-on-surface-variant">Examiner Portal</div>
            </div>
          </div>
          <Link
            to="/generate/setup"
            className="mt-8 w-full bg-primary-container text-on-primary-container font-label-md text-label-md py-3 px-4 rounded-lg stamp-shadow flex items-center justify-center gap-2 hover:opacity-90 transition-opacity"
          >
            <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>
              add
            </span>
            New Exam Paper
          </Link>
        </div>
        <ul className="mt-4 flex-grow px-3 space-y-1">
          <li>
            <Link to="/dashboard" className={active === "dashboard" ? navLinkActiveClass : navLinkClass}>
              <span className="material-symbols-outlined">dashboard</span>
              Dashboard
            </Link>
          </li>
          <li>
            <Link to="/generate/setup" className={active === "generator" ? navLinkActiveClass : navLinkClass}>
              <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>
                auto_stories
              </span>
              Generator
            </Link>
          </li>
        </ul>
        <div className="p-4 mt-auto border-t border-outline-variant">
          <ul className="space-y-1">
            <li>
              <button onClick={onSignOut} className={cn(navLinkClass, "w-full text-left")}>
                <span className="material-symbols-outlined">logout</span>
                Sign Out
              </button>
            </li>
          </ul>
        </div>
      </nav>

      {/* TopNavBar (Mobile) */}
      <header className="md:hidden flex justify-between items-center w-full px-margin-mobile py-4 bg-surface border-b border-outline-variant sticky top-0 z-40">
        <h1 className="font-display-lg text-headline-md-mobile text-primary tracking-tight">QuickPaperAI</h1>
        <button onClick={onSignOut} className="text-on-surface-variant">
          <span className="material-symbols-outlined">logout</span>
        </button>
      </header>

      <main className="flex-grow flex flex-col bg-background overflow-y-auto pb-20 md:pb-0">{children}</main>

      {/* Mobile Bottom Navigation */}
      <div className="md:hidden fixed bottom-0 w-full bg-surface-container-lowest border-t border-outline-variant flex justify-around p-2 z-40 shadow-[0_-2px_10px_rgba(0,0,0,0.05)]">
        <Link to="/dashboard" className="flex flex-col items-center p-2 text-on-surface-variant [&.active]:text-primary [&.active]:font-bold">
          <span className="material-symbols-outlined">dashboard</span>
          <span className="text-[10px] font-label-sm mt-1">Dashboard</span>
        </Link>
        <Link to="/generate/setup" className="flex flex-col items-center p-2 text-on-surface-variant [&.active]:text-primary [&.active]:font-bold">
          <span className="material-symbols-outlined">auto_stories</span>
          <span className="text-[10px] font-label-sm mt-1">Create</span>
        </Link>
      </div>
    </div>
  );
}
