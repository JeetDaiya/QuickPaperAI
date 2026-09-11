import type { ReactNode } from "react";

interface AuthShellProps {
  badge: string;
  children: ReactNode;
}

/** Shared chrome for Login/Signup/Verify OTP/Reset Password — ported from the four
 * faculty_* Stitch exports, which all use this header + centered card + footer pattern. */
export function AuthShell({ badge, children }: AuthShellProps) {
  return (
    <div className="bg-background text-on-surface min-h-screen flex flex-col justify-between">
      <header className="w-full bg-surface border-b border-outline-variant/60 py-4 px-margin-mobile md:px-margin-desktop">
        <div className="max-w-container-max mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded bg-primary text-on-primary flex items-center justify-center shadow-sm">
              <span className="material-symbols-outlined text-[20px] material-symbols-fill">auto_stories</span>
            </div>
            <div className="flex flex-col">
              <span className="font-headline-md text-headline-md leading-none text-primary tracking-tight font-bold">
                QuickPaperAI
              </span>
              <span className="font-label-sm text-label-sm text-on-surface-variant tracking-wider uppercase">
                Academic Assessment Suite
              </span>
            </div>
          </div>
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded bg-surface-container-low border border-outline-variant text-on-surface-variant">
            <span className="w-2 h-2 rounded-full bg-secondary animate-pulse" />
            <span className="font-label-sm text-label-sm tracking-wider uppercase font-semibold text-secondary">
              {badge}
            </span>
          </div>
        </div>
      </header>

      <main className="flex-1 flex items-center justify-center px-4 py-10 md:py-14">{children}</main>

      <footer className="bg-surface-container-lowest border-t border-dashed border-outline-variant py-8 w-full">
        <div className="w-full flex flex-col items-center justify-center gap-4 px-margin-mobile md:px-margin-desktop text-center">
          <div className="font-label-md text-label-md font-bold text-on-surface">
            © 2024 QuickPaperAI Academic Systems
          </div>
          <div className="flex items-center gap-6">
            <a className="font-label-sm text-label-sm text-on-surface-variant hover:text-primary hover:underline transition-all" href="#privacy">
              Privacy Policy
            </a>
            <span className="text-outline-variant">•</span>
            <a className="font-label-sm text-label-sm text-on-surface-variant hover:text-primary hover:underline transition-all" href="#terms">
              Terms of Service
            </a>
            <span className="text-outline-variant">•</span>
            <a className="font-label-sm text-label-sm text-on-surface-variant hover:text-primary hover:underline transition-all" href="#support">
              Support
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
