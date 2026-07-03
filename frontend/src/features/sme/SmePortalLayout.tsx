// SME portal shell — follows the GLOBAL theme + language (dir/lang come only
// from LangProvider on <html>, no per-screen pinning). data-portal="sme"
// (oasis teal) is independent of theme/lang. Header + working sign out +
// theme/lang toggles + <Outlet/> for nested pages.
import { Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthProvider";
import { useLang } from "../../i18n/LangProvider";
import { JadwaTileMark } from "../../components/JadwaMark";
import ThemeToggle from "../../components/ThemeToggle";
import LangToggle from "../../components/LangToggle";

export default function SmePortalLayout() {
  const { user, signOut } = useAuth();
  const { t } = useLang();

  return (
    <div data-portal="sme" className="min-h-screen bg-bg">
      <div className="h-[3px] bg-accent" />
      <header className="flex items-center justify-between border-b border-line bg-surface px-[18px] py-2.5">
        <div className="flex items-center gap-2.5">
          <JadwaTileMark />
          <span className="font-display text-[19px] font-extrabold text-ink">{t("brand.wordmark")}</span>
          <span className="h-4 w-px bg-line" />
          <span className="text-[12.5px] text-text-2">{t("sme.portalLabel")}</span>
        </div>
        <div className="flex items-center gap-3">
          <LangToggle />
          <ThemeToggle />
          <span className="flex items-center gap-2 text-xs text-text-2">
            {t("demo.smeUserName")}
            <span className="flex h-[26px] w-[26px] items-center justify-center rounded-full bg-accent-soft text-xs font-semibold text-accent-strong">
              {t("demo.smeUserInitial")}
            </span>
          </span>
          <button
            type="button"
            onClick={() => signOut()}
            title={user?.email}
            className="rounded-lg border border-line px-2.5 py-1 text-xs font-medium text-text-2 hover:bg-surface-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            {t("auth.signOut")}
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-[18px] py-5">
        <Outlet />
      </main>
    </div>
  );
}
