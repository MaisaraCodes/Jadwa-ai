// Bank queue — the real pre-scored queue, GET /bank/applications?status=submitted
// (architecture.md §4). Layout matches design-mocks/jadwa_bank_screens.html
// "Queue": a KPI strip derived client-side from the list, then a dense
// hairline table with a sticky header.
//
// Amount column reads BankApplicationSummaryItem.amount (now real; see
// backend/routers/bank.py and migration 004).
import { useNavigate } from "react-router-dom";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useLang } from "../../../i18n/LangProvider";
import { ApiError, listBankApplications } from "../../../lib/api";
import type { BankApplicationSummaryItem } from "../../../types";
import MetricTile from "../../../components/MetricTile";
import StatusPill, { type StatusTone } from "../../../components/StatusPill";
import Card from "../../../components/Card";
import Button from "../../../components/Button";
import { useReveal, staggerDelayMs } from "../../../lib/motion";

const FORENSIC_TONE: Record<BankApplicationSummaryItem["forensic_status"], StatusTone> = {
  green: "pass",
  yellow: "review",
  red: "flag",
};

export default function BankQueuePage() {
  const { t } = useLang();

  const [applications, setApplications] = useState<BankApplicationSummaryItem[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoadError(null);
    setApplications(null);
    try {
      const { applications: apps } = await listBankApplications();
      setApplications(apps);
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : t("bank.queue.loadError"));
    }
  }, [t]);

  useEffect(() => {
    load();
  }, [load]);

  const kpis = useMemo(() => {
    if (!applications) return null;
    const scored = applications.filter((a) => a.business_model_score !== null);
    const avgScore =
      scored.length > 0
        ? Math.round(scored.reduce((sum, a) => sum + (a.business_model_score ?? 0), 0) / scored.length)
        : null;
    return {
      inQueue: applications.length,
      flagged: applications.filter((a) => a.forensic_status === "red").length,
      needsReview: applications.filter((a) => a.forensic_status === "yellow").length,
      avgScore,
    };
  }, [applications]);

  return (
    <section>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-extrabold text-ink sm:text-h1">{t("bank.nav.queue")}</h1>
          <p className="mt-1 text-sm text-text-2">{t("bank.queue.subtitle")}</p>
        </div>
        <select
          disabled
          title={t("bank.queue.filterTooltip")}
          className="h-9 cursor-not-allowed rounded-lg border border-line px-2.5 text-sm text-text-3"
        >
          <option>{t("bank.queue.filterSubmitted")}</option>
        </select>
      </div>

      {kpis && (
        <div className="mt-6 grid grid-cols-2 gap-3.5 sm:grid-cols-4">
          <MetricTile label={t("bank.queue.kpi.inQueue")}>
            <span className="text-2xl font-semibold tabular-nums text-ink">{kpis.inQueue}</span>
          </MetricTile>
          <MetricTile label={t("bank.queue.kpi.flagged")}>
            <span className={`text-2xl font-semibold tabular-nums ${kpis.flagged > 0 ? "text-flag" : "text-ink"}`}>
              {kpis.flagged}
            </span>
          </MetricTile>
          <MetricTile label={t("bank.queue.kpi.needsReview")}>
            <span className="text-2xl font-semibold tabular-nums text-ink">{kpis.needsReview}</span>
          </MetricTile>
          <MetricTile label={t("bank.queue.kpi.avgScore")}>
            {kpis.avgScore !== null ? (
              <span className="text-2xl font-semibold tabular-nums text-ink">{kpis.avgScore}</span>
            ) : (
              <span className="text-2xl font-semibold tabular-nums text-text-3">—</span>
            )}
          </MetricTile>
        </div>
      )}

      {applications === null && !loadError && (
        <Card className="mt-6 py-6 text-center text-[13px] text-text-2">{t("bank.queue.loading")}</Card>
      )}

      {loadError && (
        <Card className="mt-6 py-6 text-center">
          <p className="mb-2.5 text-[13px] text-flag">{loadError}</p>
          <Button variant="ghost" size="sm" onClick={load}>
            {t("bank.queue.retry")}
          </Button>
        </Card>
      )}

      {applications !== null && applications.length === 0 && (
        <Card className="mt-6 py-12 text-center">
          <h2 className="text-title font-semibold text-ink">{t("bank.queue.emptyTitle")}</h2>
          <p className="mx-auto mt-1 max-w-xs text-sm text-text-2">{t("bank.queue.emptyBody")}</p>
        </Card>
      )}

      {applications !== null && applications.length > 0 && (
        <div className="mt-6 overflow-x-auto rounded-2xl border border-line bg-surface">
          <table className="w-full min-w-[720px] border-collapse text-sm">
            <thead>
              <tr className="sticky top-0 z-10 bg-surface">
                <th className="border-b border-line px-4 py-2.5 text-start text-label text-text-3">
                  {t("bank.queue.colBusiness")}
                </th>
                <th className="border-b border-line px-4 py-2.5 text-start text-label text-text-3">
                  {t("bank.queue.colSector")}
                </th>
                <th className="border-b border-line px-4 py-2.5 text-start text-label text-text-3">
                  {t("bank.queue.colSubmitted")}
                </th>
                <th className="border-b border-line px-4 py-2.5 text-start text-label text-text-3">
                  {t("bank.queue.colForensic")}
                </th>
                <th className="border-b border-line px-4 py-2.5 text-end text-label text-text-3">
                  {t("bank.queue.colAmount")}
                </th>
                <th className="border-b border-line px-4 py-2.5 text-end text-label text-text-3">
                  {t("bank.queue.colScore")}
                </th>
              </tr>
            </thead>
            <tbody>
              {applications.map((app, index) => (
                <QueueRow key={app.application_id} app={app} index={index} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function QueueRow({ app, index }: { app: BankApplicationSummaryItem; index: number }) {
  const { t } = useLang();
  const navigate = useNavigate();
  const { ref, revealed } = useReveal<HTMLTableRowElement>();

  const to = `/bank/applications/${app.application_id}`;
  const goToDetail = () => navigate(to, { state: { submittedAt: app.submitted_at } });

  return (
    <tr
      ref={ref}
      data-revealed={revealed}
      tabIndex={0}
      role="link"
      onClick={goToDetail}
      onKeyDown={(e) => {
        if (e.key === "Enter") goToDetail();
      }}
      style={{ transitionDelay: `${staggerDelayMs(index)}ms` }}
      className="reveal-fade cursor-pointer transition-[opacity,background-color] duration-base ease-out last:[&>td]:border-b-0 hover:bg-surface-2 focus:outline-none focus-visible:bg-surface-2 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-accent motion-reduce:transition-none"
    >
      <td className="border-b border-line px-4 py-3 font-medium text-ink">{app.sme_name}</td>
      <td className="border-b border-line px-4 py-3 text-text-2">{app.sector}</td>
      <td className="border-b border-line px-4 py-3 tabular-nums text-text-2" dir="ltr">
        {app.submitted_at.slice(0, 10)}
      </td>
      <td className="border-b border-line px-4 py-3">
        <StatusPill tone={FORENSIC_TONE[app.forensic_status]}>{t(`forensic.status.${app.forensic_status}`)}</StatusPill>
      </td>
      <td className="border-b border-line px-4 py-3 text-end tabular-nums text-text-2" dir="ltr">
        {app.amount != null ? app.amount.toLocaleString("en-US") : "—"}
      </td>
      <td className="border-b border-line px-4 py-3 text-end font-semibold tabular-nums text-ink" dir="ltr">
        {app.business_model_score ?? "—"}
      </td>
    </tr>
  );
}
