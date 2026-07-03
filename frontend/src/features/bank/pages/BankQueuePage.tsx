// Bank queue — the real pre-scored queue (GET /bank/applications) fills this in
// Phase 2. DEMO: seeded with one row (Rawad Logistics) linking to the application
// detail screen at /bank/applications/demo so the reviewer flow has somewhere to go.
import { Link } from "react-router-dom";
import { useLang } from "../../../i18n/LangProvider";

export default function BankQueuePage() {
  const { t } = useLang();

  return (
    <section>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-title text-ink">{t("bank.nav.queue")}</h1>
          <p className="mt-1 text-sm text-text-2">{t("bank.queue.subtitle")}</p>
        </div>
        <select
          disabled
          title={t("bank.queue.filterTooltip")}
          className="cursor-not-allowed rounded-lg border border-line px-2.5 py-1.5 text-sm text-text-3"
        >
          <option>{t("bank.queue.filterSubmitted")}</option>
        </select>
      </div>

      <div className="mt-6 overflow-hidden rounded-xl border border-line bg-surface">
        <div className="grid grid-cols-5 gap-4 border-b border-line px-4 py-2.5 text-label text-text-3">
          <span className="col-span-2">{t("bank.queue.colBusiness")}</span>
          <span>{t("bank.queue.colSector")}</span>
          <span>{t("bank.queue.colForensic")}</span>
          <span className="text-end">{t("bank.queue.colScore")}</span>
        </div>
        <Link
          to="/bank/applications/demo"
          className="grid grid-cols-5 items-center gap-4 px-4 py-3 text-sm hover:bg-surface-2 focus:outline-none focus-visible:bg-surface-2"
        >
          <span className="col-span-2 font-medium text-ink">{t("bank.demo.company")}</span>
          <span className="text-text-2">{t("bank.demo.sector")}</span>
          <span className="inline-flex w-fit items-center gap-1.5 rounded-full bg-review-bg px-2.5 py-0.5 text-xs font-medium text-review">
            <span className="h-1.5 w-1.5 rounded-full bg-review" />
            {t("bank.demo.reviewNeeded")}
          </span>
          <span className="tabular-nums text-end text-ink">72</span>
        </Link>
      </div>
    </section>
  );
}
