// Bank dashboard shell — falcon blue accent via data-portal="bank" (DESIGN_SYSTEM.md
// §4, §11), independent of the global theme/language. Header + sign out +
// theme/lang toggles + <Outlet/>.
import { Outlet, NavLink } from "react-router-dom";
import { useAuth } from "../auth/AuthProvider";
import { useLang } from "../../i18n/LangProvider";
import JadwaMark, { GoldDiamond } from "../../components/JadwaMark";
import ThemeToggle from "../../components/ThemeToggle";
import LangToggle from "../../components/LangToggle";

export default function BankDashboardLayout() {
  const { user, signOut } = useAuth();
  const { t } = useLang();

  const nav = [{ to: "/bank", label: t("bank.nav.queue"), end: true }];

  return (
    <div data-portal="bank" className="min-h-screen bg-bg">
      <div className="h-[3px] bg-accent" />
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2">
            <JadwaMark className="h-6 w-6 text-ink" />
            <span className="font-display text-sm font-extrabold text-ink">{t("brand.wordmark")}</span>
            <GoldDiamond />
            <span className="rounded-full bg-accent-soft px-2 py-0.5 text-xs font-medium text-accent-strong">
              {t("bank.dashboardLabel")}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <LangToggle />
            <ThemeToggle />
            <span className="hidden text-xs text-text-3 sm:inline">{user?.email}</span>
            <button
              type="button"
              onClick={() => signOut()}
              className="rounded-lg border border-line px-2.5 py-1 text-xs font-medium text-text-2 hover:bg-surface-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            >
              {t("auth.signOut")}
            </button>
          </div>
        </div>
        <nav className="mx-auto flex max-w-6xl gap-1 px-4">
          {nav.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) =>
                [
                  "border-b-2 px-2 py-2 text-sm font-medium transition-colors motion-reduce:transition-none",
                  isActive
                    ? "border-accent text-accent-strong"
                    : "border-transparent text-text-3 hover:text-text-2",
                ].join(" ")
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
}
