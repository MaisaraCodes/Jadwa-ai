// Shared authed-portal header — accent mode strip + header bar (DESIGN_SYSTEM.md
// §8.8), used by every authed screen (SME portal, bank dashboard, bank detail).
// Bare mark + live-text wordmark + gold diamond terminal (§2.2/§2.3). Portal
// accent comes from the ambient `data-portal` the page wrapper sets — this
// component never sets it itself, so it stays correct across sme/bank x
// light/dark without forking (§6 one-component rule).
import { NavLink, Link } from "react-router-dom";
import { useAuth } from "../features/auth/AuthProvider";
import { useLang } from "../i18n/LangProvider";
import { JadwaWordmark } from "./JadwaMark";
import ThemeToggle from "./ThemeToggle";
import LangToggle from "./LangToggle";
import Button from "./Button";

export interface PortalNavItem {
  to: string;
  label: string;
  end?: boolean;
}

interface PortalHeaderProps {
  label: string;
  nav?: PortalNavItem[];
  containerClassName?: string;
  /** Where the logo (mark + wordmark) links to — the signed-in user's portal
   * home. Every authed screen sets this so the logo always returns to the
   * portal it's rendered inside of. */
  homeTo: string;
}

export default function PortalHeader({ label, nav, containerClassName = "max-w-6xl", homeTo }: PortalHeaderProps) {
  const { user, signOut } = useAuth();
  const { t } = useLang();

  return (
    <>
      <div className="h-[3px] bg-accent" />
      <header className="border-b border-line bg-surface">
        <div className={`mx-auto flex h-[60px] items-center justify-between px-4 ${containerClassName}`}>
          <div className="flex items-center gap-2.5">
            <Link
              to={homeTo}
              className="rounded-md focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            >
              <JadwaWordmark
                gapClassName="gap-2.5"
                markClassName="h-6 w-6"
                textClassName="text-[22px]"
                diamondClassName="h-[10px] w-[10px]"
              />
            </Link>
            <span className="mx-3.5 h-[22px] w-px bg-line-strong" />
            <span className="text-sm font-medium text-text-2">{label}</span>
          </div>
          <div className="flex items-center gap-3">
            <LangToggle />
            <ThemeToggle />
            {user?.email && (
              <span className="hidden text-[13px] text-text-3 sm:inline" dir="ltr" title={user.email}>
                {user.email}
              </span>
            )}
            <Button variant="ghost" size="sm" onClick={() => signOut()}>
              {t("auth.signOut")}
            </Button>
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
                    "focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-inset",
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
