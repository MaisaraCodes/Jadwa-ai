// Shared authed-portal header — accent mode strip + header bar (DESIGN_SYSTEM.md
// §8.8), used by every authed screen (SME portal, bank dashboard, bank detail).
// Bare mark + live-text wordmark + gold diamond terminal (§2.2/§2.3). Portal
// accent comes from the ambient `data-portal` the page wrapper sets — this
// component never sets it itself, so it stays correct across sme/bank x
// light/dark without forking (§6 one-component rule).
import { NavLink } from "react-router-dom";
import { useAuth } from "../features/auth/AuthProvider";
import { useLang } from "../i18n/LangProvider";
import { JadwaWordmark } from "./JadwaMark";
import ThemeToggle from "./ThemeToggle";
import LangToggle from "./LangToggle";

export interface PortalNavItem {
  to: string;
  label: string;
  end?: boolean;
}

interface PortalHeaderProps {
  label: string;
  nav?: PortalNavItem[];
  containerClassName?: string;
}

export default function PortalHeader({ label, nav, containerClassName = "max-w-6xl" }: PortalHeaderProps) {
  const { user, signOut } = useAuth();
  const { t } = useLang();

  return (
    <>
      <div className="h-[3px] bg-accent" />
      <header className="border-b border-line bg-surface">
        <div className={`mx-auto flex items-center justify-between px-4 py-3 ${containerClassName}`}>
          <div className="flex items-center gap-2.5">
            <JadwaWordmark />
            <span className="h-4 w-px bg-line" />
            <span className="text-[12.5px] text-text-2">{label}</span>
          </div>
          <div className="flex items-center gap-3">
            <LangToggle />
            <ThemeToggle />
            {user?.email && (
              <span className="hidden text-xs text-text-3 sm:inline" dir="ltr" title={user.email}>
                {user.email}
              </span>
            )}
            <button
              type="button"
              onClick={() => signOut()}
              className="rounded-lg border border-line px-2.5 py-1 text-xs font-medium text-text-2 hover:bg-surface-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            >
              {t("auth.signOut")}
            </button>
          </div>
        </div>
        {nav && nav.length > 0 && (
          <nav className={`mx-auto flex gap-1 px-4 ${containerClassName}`}>
            {nav.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.end}
                className={({ isActive }) =>
                  [
                    "border-b-2 px-2 py-2 text-sm font-medium transition-colors motion-reduce:transition-none",
                    isActive ? "border-accent text-accent-strong" : "border-transparent text-text-3 hover:text-text-2",
                  ].join(" ")
                }
              >
                {n.label}
              </NavLink>
            ))}
          </nav>
        )}
      </header>
    </>
  );
}
