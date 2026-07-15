// SME portal — SmeDashboardPage ("my loan applications"), the /sme index route.
// GET /applications is a real endpoint (routers/applications.py) — this page is
// its first caller. Status shown is ApplicationStatus (lifecycle), which per
// DESIGN_SYSTEM.md §8.6/§9 always gets the quiet neutral pill — pass/review/flag
// are reserved for ForensicStatus only, never reused here.
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { IconFileUpload, IconPlus } from "@tabler/icons-react";
import { useLang } from "../../../i18n/LangProvider";
import { ApiError, listApplications } from "../../../lib/api";
import type { ApplicationSummaryItem } from "../../../types";
import LifecycleStatusPill from "../../../components/LifecycleStatusPill";

export default function SmeDashboardPage() {
  const { t } = useLang();
  const navigate = useNavigate();

  const [applications, setApplications] = useState<ApplicationSummaryItem[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoadError(null);
    setApplications(null);
    try {
      const { applications: apps } = await listApplications();
      setApplications(apps);
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : t("sme.dashboard.loadError"));
    }
  }, [t]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <section>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-extrabold text-ink">{t("sme.dashboard.title")}</h1>
          <p className="mt-0.5 text-[13px] text-text-2">{t("sme.dashboard.subtitle")}</p>
        </div>
        <button
          type="button"
          onClick={() => navigate("/sme/applications/new")}
          className="inline-flex h-10 items-center gap-2 rounded-lg bg-accent px-5 text-sm font-medium text-on-accent hover:bg-accent-strong focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
        >
          <IconPlus size={16} aria-hidden="true" />
          {t("sme.dashboard.createApplication")}
        </button>
      </div>

      {applications === null && !loadError && (
        <p className="mt-4 rounded-xl border border-line bg-surface px-4 py-6 text-center text-[13px] text-text-2">
          {t("sme.dashboard.loading")}
        </p>
      )}

      {loadError && (
        <div className="mt-4 rounded-xl border border-line bg-surface px-4 py-6 text-center">
          <p className="mb-2.5 text-[13px] text-flag">{loadError}</p>
          <button
            type="button"
            onClick={load}
            className="rounded-lg border border-line-strong px-3 py-1.5 text-xs font-medium text-accent-strong hover:bg-accent-soft focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            {t("sme.dashboard.retry")}
          </button>
        </div>
      )}

      {applications !== null && applications.length === 0 && (
        <div className="mt-4 flex flex-col items-center rounded-xl border border-line bg-surface py-12 text-center">
          <IconFileUpload size={30} className="text-accent" aria-hidden="true" />
          <h2 className="mt-3 text-title font-semibold text-ink">{t("sme.dashboard.emptyTitle")}</h2>
          <p className="mt-1 max-w-xs text-sm text-text-2">{t("sme.dashboard.emptyBody")}</p>
          <button
            type="button"
            onClick={() => navigate("/sme/applications/new")}
            className="mt-4 inline-flex h-10 items-center gap-2 rounded-lg bg-accent px-5 text-sm font-medium text-on-accent hover:bg-accent-strong focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
          >
            {t("sme.dashboard.createApplication")}
          </button>
        </div>
      )}

      {applications !== null && applications.length > 0 && (
        <div className="mt-4 overflow-hidden rounded-xl border border-line bg-surface">
          <div className="grid grid-cols-[1fr_auto_auto] items-center gap-4 border-b border-line px-4 py-2.5 text-label text-text-3">
            <span>{t("sme.dashboard.colCreated")}</span>
            <span className="text-end">{t("sme.dashboard.colDocuments")}</span>
            <span className="text-end">{t("sme.dashboard.colStatus")}</span>
          </div>
          {applications.map((app) => (
            <Link
              key={app.application_id}
              to={`/sme/applications/${app.application_id}`}
              className="grid grid-cols-[1fr_auto_auto] items-center gap-4 border-b border-line px-4 py-3 text-sm last:border-b-0 hover:bg-surface-2 focus:outline-none focus-visible:bg-surface-2"
            >
              <span dir="ltr" className="tabular-nums text-ink">
                {app.created_at.slice(0, 10)}
              </span>
              <span dir="ltr" className="tabular-nums text-end text-text-2">
                {app.document_count}
              </span>
              <span className="justify-self-end">
                <LifecycleStatusPill status={app.status} />
              </span>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
