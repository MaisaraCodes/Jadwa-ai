// Bank dashboard shell — falcon blue accent via data-portal="bank" (DESIGN_SYSTEM.md
// §4, §11), independent of the global theme/language. Header comes from the shared
// PortalHeader (§8.8, §6 one-component rule) + <Outlet/>.
import { Outlet } from "react-router-dom";
import { useLang } from "../../i18n/LangProvider";
import PortalHeader from "../../components/PortalHeader";

export default function BankDashboardLayout() {
  const { t } = useLang();

  const nav = [{ to: "/bank", label: t("bank.nav.queue"), end: true }];

  return (
    <div data-portal="bank" className="min-h-screen bg-bg">
      <PortalHeader label={t("bank.dashboardLabel")} nav={nav} />

      <main className="mx-auto max-w-6xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
}
