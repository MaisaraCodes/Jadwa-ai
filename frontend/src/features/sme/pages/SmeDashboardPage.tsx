// SME portal — SmeDashboardPage ("my loan applications"), the /sme index route.
// GET /applications is a real endpoint (routers/applications.py) — this page is
// its first caller. Status shown is ApplicationStatus (lifecycle), which per
// DESIGN_SYSTEM.md §8.6/§9 always gets the quiet neutral pill — pass/review/flag
// are reserved for ForensicStatus only, never reused here.
//
// Layout matches design-mocks/jadwa_sme_screens.html "Dashboard": metric strip
// + rich application cards (mini Sadu progress, amount, lifecycle pill, action).
//
// Amount comes from ApplicationSummaryItem.amount (now real — migration 004
// and backend/routers/applications.py list handler). "Total requested" sums
// all non-null amounts. Per-card progress is also real: "processing" rows
// call GET /applications/:id/status to read live nodes_completed.
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { IconFileUpload, IconPlus } from "@tabler/icons-react";
import { useLang } from "../../../i18n/LangProvider";
import type { StringKey } from "../../../i18n/strings";
import { ApiError, getApplicationStatus, listApplications } from "../../../lib/api";
import type { ApplicationStatusResponse, ApplicationSummaryItem } from "../../../types";
import LifecycleStatusPill from "../../../components/LifecycleStatusPill";
import SaduBand from "../../../components/SaduBand";
import Card from "../../../components/Card";
import MetricTile from "../../../components/MetricTile";
import Button from "../../../components/Button";
import Skeleton from "../../../components/Skeleton";
import { useReveal, staggerDelayMs } from "../../../lib/motion";

const STAGE_TOTAL = 6;

function cardPhase(
  app: ApplicationSummaryItem,
  liveStatus: ApplicationStatusResponse | undefined,
): { done: number; actionKey: StringKey; to: string } {
  const to = `/sme/applications/${app.application_id}`;
  if (app.status === "draft") {
    return { done: 0, actionKey: "sme.dashboard.action.continue", to };
  }
  if (app.status === "processing") {
    const done = liveStatus?.nodes_completed.length ?? 0;
    const readyToReview = (liveStatus?.progress ?? 0) >= 1;
    return { done, actionKey: readyToReview ? "sme.dashboard.action.reviewAndSubmit" : "sme.dashboard.action.viewProgress", to };
  }
  // review_ready / approved / rejected / more_info_needed: pipeline already ran.
  return { done: STAGE_TOTAL, actionKey: "sme.dashboard.action.view", to };
}

export default function SmeDashboardPage() {
  const { t } = useLang();
  const navigate = useNavigate();

  const [applications, setApplications] = useState<ApplicationSummaryItem[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [liveStatusById, setLiveStatusById] = useState<Record<string, ApplicationStatusResponse>>({});

  const load = useCallback(async () => {
    setLoadError(null);
    setApplications(null);
    setLiveStatusById({});
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

  // Real per-app progress for "processing" rows only (draft has none yet;
  // everything past processing is already fully done) — see file header.
  useEffect(() => {
    const processingIds = (applications ?? [])
      .filter((a) => a.status === "processing")
      .map((a) => a.application_id);
    if (processingIds.length === 0) return;

    let cancelled = false;
    Promise.all(
      processingIds.map((id) =>
        getApplicationStatus(id)
          .then((status) => [id, status] as const)
          .catch(() => null),
      ),
    ).then((results) => {
      if (cancelled) return;
      setLiveStatusById((prev) => {
        const next = { ...prev };
        for (const r of results) if (r) next[r[0]] = r[1];
        return next;
      });
    });
    return () => {
      cancelled = true;
    };
  }, [applications]);

  const metrics = useMemo(() => {
    if (!applications) return null;
    const withAmount = applications.filter((a) => a.amount != null);
    const totalRequested = withAmount.length > 0
      ? withAmount.reduce((sum, a) => sum + (a.amount ?? 0), 0)
      : null;
    return {
      active: applications.filter((a) => a.status === "draft" || a.status === "processing").length,
      inReview: applications.filter((a) => a.status === "review_ready").length,
      approved: applications.filter((a) => a.status === "approved").length,
      totalRequested,
    };
  }, [applications]);

  return (
    <section>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-extrabold text-ink sm:text-h1">{t("sme.dashboard.title")}</h1>
          <p className="mt-1 text-[13px] text-text-2 sm:text-sm">{t("sme.dashboard.subtitle")}</p>
        </div>
        <Button variant="accent" size="lg" onClick={() => navigate("/sme/applications/new")}>
          <IconPlus size={16} aria-hidden="true" />
          {t("sme.dashboard.createApplication")}
        </Button>
      </div>

      {metrics && (
        <div className="mt-6 grid grid-cols-2 gap-3.5 sm:grid-cols-4">
          <MetricTile label={t("sme.dashboard.metric.active")}>
            <span className="text-2xl font-semibold tabular-nums text-ink">{metrics.active}</span>
          </MetricTile>
          <MetricTile label={t("sme.dashboard.metric.inReview")}>
            <span className="text-2xl font-semibold tabular-nums text-ink">{metrics.inReview}</span>
          </MetricTile>
          <MetricTile label={t("sme.dashboard.metric.approved")}>
            <span className="text-2xl font-semibold tabular-nums text-ink">{metrics.approved}</span>
          </MetricTile>
          <MetricTile label={t("sme.dashboard.metric.totalRequested")}>
            {metrics.totalRequested != null ? (
              <span className="text-2xl font-semibold tabular-nums text-ink" dir="ltr">
                {metrics.totalRequested.toLocaleString("en-US")}
              </span>
            ) : (
              <>
                <span className="text-2xl font-semibold tabular-nums text-text-3">—</span>
                <div className="mt-0.5 text-[11px] font-normal text-text-3">{t("sme.dashboard.metric.totalPending")}</div>
              </>
            )}
          </MetricTile>
        </div>
      )}

      {applications === null && !loadError && (
        <div className="mt-6 flex flex-col gap-3.5" role="status">
          <span className="sr-only">{t("sme.dashboard.loading")}</span>
          {[0, 1, 2].map((i) => (
            <Card key={i} className="p-5" aria-hidden="true">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-[1fr_auto_auto] sm:items-center sm:gap-6">
                <div className="min-w-0 space-y-2">
                  <Skeleton className="h-4 w-36" />
                  <Skeleton className="h-3 w-44" />
                </div>
                <Skeleton className="h-11 w-40" />
                <Skeleton className="h-5 w-20 justify-self-end" />
              </div>
              <div className="mt-4 flex items-center justify-between gap-3 border-t border-line pt-3.5">
                <Skeleton className="h-5 w-24 rounded-full" />
                <Skeleton className="h-[34px] w-24" />
              </div>
            </Card>
          ))}
        </div>
      )}

      {loadError && (
        <Card className="mt-6 py-6 text-center">
          <p className="mb-2.5 text-[13px] text-flag">{loadError}</p>
          <Button variant="ghost" size="sm" onClick={load}>
            {t("sme.dashboard.retry")}
          </Button>
        </Card>
      )}

      {applications !== null && applications.length === 0 && (
        <Card className="mt-6 flex flex-col items-center py-12 text-center">
          <IconFileUpload size={30} className="text-accent" aria-hidden="true" />
          <h2 className="mt-3 text-title font-semibold text-ink">{t("sme.dashboard.emptyTitle")}</h2>
          <p className="mt-1 max-w-xs text-sm text-text-2">{t("sme.dashboard.emptyBody")}</p>
          <Button variant="accent" className="mt-4" onClick={() => navigate("/sme/applications/new")}>
            {t("sme.dashboard.createApplication")}
          </Button>
        </Card>
      )}

      {applications !== null && applications.length > 0 && (
        <div className="mt-6 flex flex-col gap-3.5">
          {applications.map((app, index) => {
            const { done, actionKey, to } = cardPhase(app, liveStatusById[app.application_id]);
            return (
              <ApplicationCard
                key={app.application_id}
                app={app}
                index={index}
                done={done}
                actionKey={actionKey}
                to={to}
              />
            );
          })}
        </div>
      )}
    </section>
  );
}

function ApplicationCard({
  app,
  index,
  done,
  actionKey,
  to,
}: {
  app: ApplicationSummaryItem;
  index: number;
  done: number;
  actionKey: StringKey;
  to: string;
}) {
  const { t } = useLang();
  const { ref, revealed } = useReveal<HTMLDivElement>();

  return (
    <Card
      ref={ref}
      data-revealed={revealed}
      className="reveal p-5 hover:border-line-strong"
      style={{ transitionDelay: `${staggerDelayMs(index)}ms` }}
    >
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-[1fr_auto_auto] sm:items-center sm:gap-6">
        <div className="min-w-0">
          <div className="truncate text-[17px] font-semibold text-ink">{t("sme.dashboard.cardTitle")}</div>
          <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[13px] text-text-3">
            <span dir="ltr" className="tabular-nums">
              {app.created_at.slice(0, 10)}
            </span>
            <span>·</span>
            <span dir="ltr" className="tabular-nums">
              {app.document_count}
            </span>
            <span>{t("sme.dashboard.colDocuments")}</span>
          </div>
        </div>

        <SaduBand size="mini" done={done} total={STAGE_TOTAL} />

        <div className="text-end sm:min-w-[110px]">
          {app.amount != null ? (
            <>
              <div className="text-[17px] font-semibold tabular-nums text-ink" dir="ltr">
                {app.amount.toLocaleString("en-US")}
              </div>
              <div className="text-xs text-text-3">SAR</div>
            </>
          ) : (
            <>
              <div className="text-[17px] font-semibold tabular-nums text-text-3">—</div>
              <div className="text-xs text-text-3">{t("sme.dashboard.amountNotSet")}</div>
            </>
          )}
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between gap-3 border-t border-line pt-3.5">
        <LifecycleStatusPill status={app.status} />
        <Link
          to={to}
          className="inline-flex h-[34px] items-center rounded-lg border border-line-strong px-4 text-sm font-medium text-ink transition-colors duration-base ease-out motion-reduce:transition-none hover:bg-surface-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          {t(actionKey)}
        </Link>
      </div>
    </Card>
  );
}
