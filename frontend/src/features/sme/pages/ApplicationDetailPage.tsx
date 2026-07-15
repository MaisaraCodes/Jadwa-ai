// SME portal — ApplicationDetailPage (/sme/applications/:id), the spine of the
// SME journey: draft (upload + analyze) -> processing (live Sadu band) ->
// analysis done (review & correct, wired in a later step) -> locked
// (review_ready/approved/rejected/more_info_needed, wired in a later step).
//
// There's no single GET /applications/:id endpoint (architecture.md §4), so
// "created date" / "document_count" come from GET /applications (the list)
// matched by id, while live status/progress come from the real
// GET /applications/:id/status.
//
// IMPORTANT backend nuance: nothing ever flips `status` from "processing" to
// "review_ready" automatically once the pipeline finishes — only
// POST /applications/:id/submit does that (routers/applications.py). So once
// GET /status reports progress >= 1 while status is still "processing", this
// page treats that locally as "analysis done, ready for the SME to review"
// WITHOUT claiming the server status changed — the header pill keeps showing
// the real "Processing" status until the SME actually submits.
import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { IconArrowLeft, IconSparkles } from "@tabler/icons-react";
import { useLang } from "../../../i18n/LangProvider";
import type { StringKey } from "../../../i18n/strings";
import { ApiError, getApplicationStatus, listApplications, processApplication } from "../../../lib/api";
import type { ApplicationStatusResponse, ApplicationSummaryItem } from "../../../types";
import LifecycleStatusPill from "../../../components/LifecycleStatusPill";
import SaduBand, { type SaduStageState } from "../../../components/SaduBand";
import DocumentUpload from "../DocumentUpload";

const POLL_INTERVAL_MS = 1500;

// Positional mapping: core/pipeline.py's ALL_NODES (the 6 real LangGraph
// nodes, in run order) map 1:1 by position onto the Sadu band's 6 stylized
// stage labels (DESIGN_SYSTEM.md §8.9). The names aren't literal synonyms —
// e.g. devils_advocate_node -> "Stress test" — just the same pipeline slot.
const STAGE_LABEL_KEYS: StringKey[] = [
  "sme.home.stage.extract",
  "sme.home.stage.forensic",
  "sme.home.stage.stressTest",
  "sme.home.stage.market",
  "sme.home.stage.riskModel",
  "sme.home.stage.record",
];

type Phase = "draft" | "processing" | "analysis_done" | "locked";

export default function ApplicationDetailPage() {
  const { applicationId } = useParams();
  const { t, lang } = useLang();

  const [summary, setSummary] = useState<ApplicationSummaryItem | null>(null);
  const [statusInfo, setStatusInfo] = useState<ApplicationStatusResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  const [uploadedThisSession, setUploadedThisSession] = useState(0);
  const [analyzeBusy, setAnalyzeBusy] = useState(false);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!applicationId) return;
    setLoadError(null);
    setNotFound(false);
    try {
      const [{ applications }, status] = await Promise.all([
        listApplications(),
        getApplicationStatus(applicationId),
      ]);
      const found = applications.find((a) => a.application_id === applicationId) ?? null;
      if (!found) {
        setNotFound(true);
        return;
      }
      setSummary(found);
      setStatusInfo(status);
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : t("sme.detail.loadError"));
    }
  }, [applicationId, t]);

  useEffect(() => {
    load();
    // Only re-run on a real navigation to a different application id — `load`
    // itself is stable across re-renders except when `t` changes language.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [applicationId]);

  // Poll GET /status every ~1.5s while the pipeline is actually running
  // (architecture.md §4's "poll every 1-2s"). Keyed on `isProcessing` (the
  // real status field) rather than `progress`, so a tick's own setStatusInfo
  // call doesn't re-arm this effect — the recursive timer decides on its own
  // when to stop, once progress reaches 1.
  const isProcessing = statusInfo?.status === "processing";
  const cancelledRef = useRef(false);
  useEffect(() => {
    cancelledRef.current = false;
    if (!applicationId || !isProcessing) return;

    let timer: ReturnType<typeof setTimeout> | undefined;
    async function tick() {
      try {
        const next = await getApplicationStatus(applicationId!);
        if (cancelledRef.current) return;
        setStatusInfo(next);
        if (next.status === "processing" && next.progress < 1) {
          timer = setTimeout(tick, POLL_INTERVAL_MS);
        }
      } catch {
        if (!cancelledRef.current) timer = setTimeout(tick, POLL_INTERVAL_MS);
      }
    }
    timer = setTimeout(tick, POLL_INTERVAL_MS);

    return () => {
      cancelledRef.current = true;
      if (timer) clearTimeout(timer);
    };
  }, [applicationId, isProcessing]);

  async function onAnalyze() {
    if (!applicationId) return;
    setAnalyzeError(null);
    setAnalyzeBusy(true);
    try {
      await processApplication(applicationId);
      setStatusInfo({ status: "processing", nodes_completed: [], progress: 0 });
    } catch (err) {
      setAnalyzeError(err instanceof ApiError ? err.message : t("sme.detail.analyzeError"));
    } finally {
      setAnalyzeBusy(false);
    }
  }

  if (notFound) {
    return (
      <section>
        <BackLink lang={lang} t={t} />
        <p className="rounded-xl border border-line bg-surface px-4 py-6 text-center text-[13px] text-text-2">
          {t("sme.detail.notFound")}
        </p>
      </section>
    );
  }

  if (loadError) {
    return (
      <section>
        <BackLink lang={lang} t={t} />
        <div className="rounded-xl border border-line bg-surface px-4 py-6 text-center">
          <p className="mb-2.5 text-[13px] text-flag">{loadError}</p>
          <button
            type="button"
            onClick={load}
            className="rounded-lg border border-line-strong px-3 py-1.5 text-xs font-medium text-accent-strong hover:bg-accent-soft focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            {t("sme.detail.retry")}
          </button>
        </div>
      </section>
    );
  }

  if (!summary || !statusInfo || !applicationId) {
    return (
      <section>
        <BackLink lang={lang} t={t} />
        <p className="rounded-xl border border-line bg-surface px-4 py-6 text-center text-[13px] text-text-2">
          {t("sme.detail.loading")}
        </p>
      </section>
    );
  }

  const phase: Phase =
    statusInfo.status === "draft"
      ? "draft"
      : statusInfo.status === "processing"
        ? statusInfo.progress >= 1
          ? "analysis_done"
          : "processing"
        : "locked";

  const hasDocuments = summary.document_count > 0 || uploadedThisSession > 0;
  const nodesCompletedCount = statusInfo.nodes_completed.length;
  const stageStates: SaduStageState[] = STAGE_LABEL_KEYS.map((_, i) =>
    i < nodesCompletedCount ? "done" : i === nodesCompletedCount ? "active" : "pending",
  );
  const currentStageIndex = Math.min(nodesCompletedCount, STAGE_LABEL_KEYS.length - 1);

  return (
    <section>
      <BackLink lang={lang} t={t} />

      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-extrabold text-ink">
            {t("sme.detail.applicationLabel")}{" "}
            <span dir="ltr" className="tabular-nums text-lg font-normal text-text-3" title={applicationId}>
              {applicationId.slice(0, 8)}…
            </span>
          </h1>
          <p className="mt-0.5 text-[12.5px] text-text-2">
            {t("sme.dashboard.colCreated")}:{" "}
            <span dir="ltr" className="tabular-nums">
              {summary.created_at.slice(0, 10)}
            </span>
          </p>
        </div>
        <LifecycleStatusPill status={statusInfo.status} />
      </div>

      {(phase === "draft" || phase === "analysis_done") && (
        <div className="mb-4 rounded-xl border border-line bg-surface px-4 py-3.5">
          <div className="mb-2.5 flex items-center justify-between">
            <span className="text-[13.5px] font-semibold text-ink">{t("sme.home.documentsTitle")}</span>
            {summary.document_count > 0 && (
              <span className="text-[11.5px] text-text-3">
                {t("sme.detail.existingDocsNote", { count: summary.document_count })}
              </span>
            )}
          </div>
          <DocumentUpload
            applicationId={applicationId}
            onUploaded={() => setUploadedThisSession((n) => n + 1)}
          />
        </div>
      )}

      {phase === "draft" && (
        <div className="mb-4 flex flex-col items-start gap-2 rounded-xl border border-line bg-surface px-4 py-3.5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-[13px] font-medium text-ink">{t("sme.detail.analyzeButton")}</p>
            {!hasDocuments && (
              <p className="mt-0.5 text-[11.5px] text-text-3">{t("sme.detail.analyzeNeedsDocs")}</p>
            )}
            {analyzeError && <p className="mt-0.5 text-xs text-flag">{analyzeError}</p>}
          </div>
          <button
            type="button"
            onClick={onAnalyze}
            disabled={!hasDocuments || analyzeBusy}
            className="inline-flex h-10 shrink-0 items-center gap-2 rounded-lg bg-accent px-5 text-sm font-medium text-on-accent disabled:opacity-50 hover:bg-accent-strong focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
          >
            <IconSparkles size={16} aria-hidden="true" />
            {analyzeBusy ? t("sme.detail.analyzeStarting") : t("sme.detail.analyzeButton")}
          </button>
        </div>
      )}

      {phase === "processing" && (
        <div className="mb-4 rounded-xl border border-line bg-surface px-4 py-5 text-center">
          <h2 className="text-title font-semibold text-ink">{t("sme.detail.processingTitle")}</h2>
          <p className="mx-auto mt-1 max-w-sm text-[12.5px] text-text-2">{t("sme.detail.processingHint")}</p>
          <div className="mt-4 flex justify-center overflow-x-auto">
            <SaduBand stages={stageStates} />
          </div>
          <p className="mt-2 text-[12px] text-text-2">
            {t(STAGE_LABEL_KEYS[currentStageIndex])}
            {" · "}
            {t("sme.detail.stageProgress", { done: nodesCompletedCount, total: STAGE_LABEL_KEYS.length })}
          </p>
        </div>
      )}

      {phase === "analysis_done" && (
        <div className="rounded-xl border border-line bg-surface px-4 py-6 text-center">
          <p className="text-[13px] text-ink">{t("sme.detail.analysisCompleteNotice")}</p>
        </div>
      )}

      {phase === "locked" && (
        <div className="rounded-xl border border-line bg-surface px-4 py-6 text-center text-[13px] text-text-2">
          {t("sme.detail.lockedNote")}
        </div>
      )}
    </section>
  );
}

function BackLink({ lang, t }: { lang: string; t: (key: StringKey, vars?: Record<string, string | number>) => string }) {
  return (
    <Link
      to="/sme"
      className="mb-3 inline-flex items-center gap-1.5 text-[12.5px] font-medium text-text-2 hover:text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
    >
      <IconArrowLeft size={14} className={lang === "ar" ? "rotate-180" : ""} aria-hidden="true" />
      {t("review.backLink")}
    </Link>
  );
}
