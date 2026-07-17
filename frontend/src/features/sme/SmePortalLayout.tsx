// SME portal shell — follows the GLOBAL theme + language (dir/lang come only
// from LangProvider on <html>, no per-screen pinning). data-portal="sme"
// (oasis teal) is independent of theme/lang. Header comes from the shared
// PortalHeader (DESIGN_SYSTEM.md §8.8, §6 one-component rule) + <Outlet/>
// for nested pages.
import { Outlet } from "react-router-dom";
import { useLang } from "../../i18n/LangProvider";
import PortalHeader from "../../components/PortalHeader";
import PageFade from "../../components/PageFade";

export default function SmePortalLayout() {
  const { t } = useLang();

  const nav = [
    { to: "/sme", label: t("sme.nav.dashboard"), end: true },
    { to: "/sme/settings", label: t("sme.nav.settings") },
    { to: "/home", label: t("common.nav.home") },
  ];

  return (
    <div data-portal="sme" className="min-h-screen bg-bg">
      <PortalHeader label={t("sme.portalLabel")} nav={nav} containerClassName="max-w-[1080px]" homeTo="/sme" />

      <main className="mx-auto max-w-[1080px] px-[18px] py-6 sm:py-10">
        <PageFade>
          <Outlet />
        </PageFade>
      </main>
    </div>
  );
}
