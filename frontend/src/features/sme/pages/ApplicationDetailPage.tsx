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
import { useParams } from "react-router-dom";
import { IconFileDownload, IconSparkles } from "@tabler/icons-react";
import { useLang } from "../../../i18n/LangProvider";
import type { StringKey } from "../../../i18n/strings";
import {
  ApiError,
  getApplicationPdf,
  getApplicationStatus,
  getApplicationSummary,
  listApplications,
  processApplication,
  submitApplication,
} from "../../../lib/api";
import type { ApplicationStatusResponse, ApplicationSummaryItem, ApplicationSummaryResponse } from "../../../types";
import LifecycleStatusPill from "../../../components/LifecycleStatusPill";
import SaduBand, { type SaduStageState } from "../../../components/SaduBand";
import Card from "../../../components/Card";
import Button from "../../../components/Button";
import BackButton from "../../../components/BackButton";
import Skeleton from "../../../components/Skeleton";
import DocumentUpload from "../DocumentUpload";
import { DocumentReviewPanel } from "./ReviewDocumentsPage";

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
  const { t } = useLang();

  const [summary, setSummary] = useState<ApplicationSummaryItem | null>(null);
  const [statusInfo, setStatusInfo] = useState<ApplicationStatusResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  const [uploadedThisSession, setUploadedThisSession] = useState(0);
  const [analyzeBusy, setAnalyzeBusy] = useState(false);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);

  const [reviewProgress, setReviewProgress] = useState<{
    allConfirmed: boolean;
    confirmedCount: number;
    total: number;
  } | null>(null);
  const onReviewProgressChange = useCallback(
    (info: { allConfirmed: boolean; confirmedCount: number; total: number }) => setReviewProgress(info),
    [],
  );

  const [submitBusy, setSubmitBusy] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const [summaryInfo, setSummaryInfo] = useState<ApplicationSummaryResponse | null>(null);
  const [summaryError, setSummaryError] = useState(false);

  // The pipeline has produced weakness_report (and therefore a usable
  // business_model_score) once nothing's left in "draft" and, if still
  // "processing", progress has reached 1 — same completion signal `phase`
  // uses below, computed here too since this effect runs before `phase` is
  // in scope (it's declared after the early-return loading/error guards).
  const pipelineDone =
    !!statusInfo && statusInfo.status !== "draft" && (statusInfo.status !== "processing" || statusInfo.progress >= 1);

  useEffect(() => {
    if (!applicationId || !pipelineDone || summaryInfo) return;
    getApplicationSummary(applicationId)
      .then(setSummaryInfo)
      .catch(() => setSummaryError(true));
  }, [applicationId, pipelineDone, summaryInfo]);

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

  async function onSubmit() {
    if (!applicationId) return;
    setSubmitError(null);
    setSubmitBusy(true);
    try {
      await submitApplication(applicationId);
      await load(); // status is now server-confirmed "review_ready" -> phase "locked"
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.message : t("sme.detail.submitError"));
    } finally {
      setSubmitBusy(false);
    }
  }

  if (notFound) {
    return (
      <section>
        <BackButton to="/sme" label={t("common.back.dashboard")} />
        <Card className="py-6 text-center text-[13px] text-text-2">{t("sme.detail.notFound")}</Card>
      </section>
    );
  }

  if (loadError) {
    return (
      <section>
        <BackButton to="/sme" label={t("common.back.dashboard")} />
        <Card className="py-6 text-center">
          <p className="mb-2.5 text-[13px] text-flag">{loadError}</p>
          <Button variant="ghost" size="sm" onClick={load}>
            {t("sme.detail.retry")}
          </Button>
        </Card>
      </section>
    );
  }

  if (!summary || !statusInfo || !applicationId) {
    return (
      <section>
        <BackButton to="/sme" label={t("common.back.dashboard")} />
        <div role="status">
          <span className="sr-only">{t("sme.detail.loading")}</span>
          <div aria-hidden="true">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div className="space-y-2">
                <Skeleton className="h-6 w-56" />
                <Skeleton className="h-3 w-32" />
              </div>
              <Skeleton className="h-5 w-24 rounded-full" />
            </div>
            <Card className="py-8">
              <Skeleton className="mx-auto h-3 w-40" />
              <div className="mx-auto mt-5 flex w-fit gap-3">
                {[0, 1, 2, 3, 4, 5].map((i) => (
                  <Skeleton key={i} className="h-11 w-16" />
                ))}
              </div>
            </Card>
          </div>
        </div>
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
      <BackButton to="/sme" label={t("common.back.dashboard")} />

      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-extrabold text-ink sm:text-h1">
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
        <Card className="mb-4">
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
        </Card>
      )}

      {phase === "draft" && (
        <Card className="mb-4 flex flex-col items-start gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-[13px] font-medium text-ink">{t("sme.detail.analyzeButton")}</p>
            {!hasDocuments && (
              <p className="mt-0.5 text-[11.5px] text-text-3">{t("sme.detail.analyzeNeedsDocs")}</p>
            )}
            {analyzeError && <p className="mt-0.5 text-xs text-flag">{analyzeError}</p>}
          </div>
          <Button variant="accent" onClick={onAnalyze} disabled={!hasDocuments || analyzeBusy} className="shrink-0">
            <IconSparkles size={16} aria-hidden="true" />
            {analyzeBusy ? t("sme.detail.analyzeStarting") : t("sme.detail.analyzeButton")}
          </Button>
        </Card>
      )}

      {phase === "processing" && (
        <Card className="mb-4 text-center">
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
        </Card>
      )}

      {phase === "analysis_done" && (
        <>
          <Card className="mb-4 text-center">
            <p className="text-[13px] text-ink">{t("sme.detail.analysisCompleteNotice")}</p>
          </Card>

          <div className="mb-4">
            <DocumentReviewPanel applicationId={applicationId} onAllConfirmedChange={onReviewProgressChange} />
          </div>

          {summaryInfo && <HealthSummaryCard summary={summaryInfo} />}
          {summaryError && <p className="mb-4 text-center text-xs text-text-3">{t("sme.detail.summaryUnavailable")}</p>}

          <Card className="flex flex-wrap items-center gap-2.5">
            <Button variant="accent" onClick={onSubmit} disabled={!reviewProgress?.allConfirmed || submitBusy}>
              {submitBusy ? t("sme.detail.submitting") : t("sme.detail.submitButton")}
            </Button>
            {submitError && <p className="text-xs text-flag">{submitError}</p>}
          </Card>
        </>
      )}

      {phase === "locked" && (
        <>
          <Card className="mb-4 text-center text-[13px] text-text-2">{t("sme.detail.lockedNote")}</Card>

          {summaryInfo && <HealthSummaryCard summary={summaryInfo} />}
          {summaryError && <p className="mb-4 text-center text-xs text-text-3">{t("sme.detail.summaryUnavailable")}</p>}

          <Card className="flex items-center justify-end">
            <PdfDownloadButton applicationId={applicationId} />
          </Card>
        </>
      )}
    </section>
  );
}

function HealthSummaryCard({ summary }: { summary: ApplicationSummaryResponse }) {
  const { t } = useLang();
  return (
    <Card className="mb-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-[13.5px] font-semibold text-ink">{t("sme.detail.summaryTitle")}</span>
        {summary.business_model_score !== null && (
          <span dir="ltr" className="tabular-nums text-[13px] font-semibold text-ink">
            {summary.business_model_score}
            <span className="text-[11px] font-normal text-text-3">/100</span>
          </span>
        )}
      </div>
      <p className="text-[12.5px] text-text-2">{summary.health_summary}</p>
      {summary.top_risks.length > 0 && (
        <div className="mt-3 rounded-lg bg-gold-soft px-2.5 py-2">
          <p className="mb-1 flex items-center gap-1.5 text-[11.5px] font-medium text-ink">
            <IconSparkles size={13} className="text-gold-strong" aria-hidden="true" />
            {t("sme.detail.strengthenTitle")}
          </p>
          <ul className="list-disc space-y-1 ps-4 text-[11.5px] leading-[1.6] text-text-2">
            {summary.top_risks.map((risk, i) => (
              <li key={i}>{risk}</li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}

// Mirrors the bank detail page's download flow: fetch the short-lived signed
// Storage URL on demand (never cached client-side — it expires) and hand it to
// the browser. The backend builds the report on demand and caches it, so a
// null pdf_url only means there is no analysis to report on yet.
function PdfDownloadButton({ applicationId }: { applicationId?: string }) {
  const { t } = useLang();
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const download = useCallback(async () => {
    if (!applicationId) return;
    setBusy(true);
    setNotice(null);
    try {
      const { pdf_url } = await getApplicationPdf(applicationId);
      if (pdf_url) {
        window.open(pdf_url, "_blank", "noopener");
      } else {
        setNotice(t("sme.detail.pdfNotReady"));
      }
    } catch (err) {
      setNotice(err instanceof ApiError ? err.message : t("sme.detail.pdfError"));
    } finally {
      setBusy(false);
    }
  }, [applicationId, t]);

  return (
    <div className="flex flex-col items-end gap-1.5">
      <Button variant="ghost" size="sm" onClick={download} disabled={busy || !applicationId}>
        <IconFileDownload size={15} aria-hidden="true" />
        {busy ? t("sme.detail.pdfFetching") : t("sme.detail.pdfButton")}
      </Button>
      {notice && <p className="text-[12px] text-text-3">{notice}</p>}
    </div>
  );
}

