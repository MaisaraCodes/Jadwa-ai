// Bank application detail — layout matches design-mocks/jadwa_bank_screens.html
// "Application detail": a dense fact header + metrics row, a main column
// (forensic report, weakness report, extracted documents) beside a sticky
// aside (decision rail, then the two coming-soon placeholders). Follows the
// GLOBAL theme + language (no per-screen pinning). data-portal="bank"
// (falcon blue) is independent of theme/lang. Standalone screen (its own
// header) rather than nested in BankDashboardLayout, because the mock's
// detail header differs from the queue's — still guarded by RequireRole
// role="bank" in App.tsx.
//
// Forensic report / weakness report are real, wired to the one
// GET /bank/applications/{id} call (architecture.md §4 — "the ENTIRE
// dashboard in ONE call") — ForensicReportCard/WeaknessReportCard are
// untouched. Market verdict and the risk sandbox are out of scope for this
// refurbish (no /sandbox/recalculate UI, no Oracle node): clearly-labelled
// disabled placeholder cards, not live-looking demos.
//
// The decision rail (Approve / Request info / Reject) posts to the real
// POST /bank/applications/{id}/decision and reflects the returned status in
// the header's lifecycle pill; it disables itself once a decision is
// already recorded (or before the application has even reached
// "review_ready").
//
// Amount comes from the real BankApplicationDetail.amount field (Task 2,
// migration 004). Submitted-at still falls back to router state passed by
// BankQueuePage on each row click — it is not a separate endpoint field.
import { useCallback, useEffect, useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import { useLang } from "../../../i18n/LangProvider";
import { GoldDiamond } from "../../../components/JadwaMark";
import PortalHeader from "../../../components/PortalHeader";
import PageFade from "../../../components/PageFade";
import LifecycleStatusPill from "../../../components/LifecycleStatusPill";
import StatusPill, { type StatusTone } from "../../../components/StatusPill";
import Card from "../../../components/Card";
import MetricTile from "../../../components/MetricTile";
import Button from "../../../components/Button";
import BackButton from "../../../components/BackButton";
import ForensicReportCard from "../components/ForensicReportCard";
import WeaknessReportCard from "../components/WeaknessReportCard";
import MarketVerdictCard from "../components/MarketVerdictCard";
import { ApiError, decideApplication, getBankApplication } from "../../../lib/api";
import type { BankApplicationDetail, BankDecision, DocumentJSON } from "../../../types";

const DECIDED_STATUSES = new Set(["approved", "rejected", "more_info_needed"]);
const LOW_CONFIDENCE_THRESHOLD = 0.85;

const FORENSIC_TONE: Record<NonNullable<BankApplicationDetail["forensic_report"]>["overall_status"], StatusTone> = {
  green: "pass",
  yellow: "review",
  red: "flag",
};

function DocumentsListCard({ documents }: { documents: DocumentJSON[] }) {
  const { t } = useLang();

  if (documents.length === 0) {
    return (
      <Card className="mb-4 py-6 text-center text-[13px] text-text-2">{t("bank.detail.documentsEmpty")}</Card>
    );
  }

  return (
    <Card className="mb-4">
      <h3 className="mb-3 text-title font-semibold text-ink">{t("sme.home.documentsTitle")}</h3>
      <ul>
        {documents.map((doc) => {
          const lowConfidence = doc.confidence_score < LOW_CONFIDENCE_THRESHOLD;
          return (
            <li
              key={doc.document_id}
              className="grid grid-cols-[1fr_auto] items-center gap-3 border-b border-line py-3 text-[13px] last:border-b-0"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-1.5 font-medium text-ink">
                  <span
                    className={`h-1.5 w-1.5 flex-none rounded-full ${lowConfidence ? "bg-review" : "bg-pass"}`}
                    aria-hidden="true"
                  />
                  {doc.vendor ?? t(`review.type.${doc.type}`)}
                  {lowConfidence && (
                    <span className="ms-1 text-[11px] font-medium text-review">
                      {t("bank.detail.matchLowConfidence")}
                    </span>
                  )}
                </div>
                <p className="mt-0.5 text-text-3">
                  {t(`review.type.${doc.type}`)}
                  {" · "}
                  <span dir="ltr" className="tabular-nums">
                    {doc.date}
                  </span>
                </p>
              </div>
              <div className="text-end font-semibold tabular-nums text-ink" dir="ltr">
                {doc.extracted_amount.toLocaleString("en-US")}
                <div className="text-[11px] font-normal text-text-3">{doc.currency}</div>
              </div>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

function ComingSoonCard({ title, body, badge }: { title: string; body: string; badge: string }) {
  return (
    <Card className="mb-4 border-dashed text-center">
      <p className="text-[15px] font-semibold text-text-2">{title}</p>
      <p className="mt-1.5 text-[13px] text-text-3">{body}</p>
      <span className="mt-3 inline-block rounded-full border border-line-strong px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.06em] text-text-3">
        {badge}
      </span>
    </Card>
  );
}

export default function BankApplicationDetailPage() {
  const { applicationId: routeApplicationId } = useParams();
  const applicationId = routeApplicationId ?? "demo"; // mirrors ReviewDocumentsPage's fallback convention
  const { t } = useLang();
  const location = useLocation();
  const submittedAt = (location.state as { submittedAt?: string } | null)?.submittedAt;

  const [detail, setDetail] = useState<BankApplicationDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [decisionMode, setDecisionMode] = useState<"idle" | "request_info_note">("idle");
  const [note, setNote] = useState("");
  const [decisionBusy, setDecisionBusy] = useState<BankDecision | null>(null);
  const [decisionError, setDecisionError] = useState<string | null>(null);

  const loadDetail = useCallback(async () => {
    setLoadError(null);
    setDetail(null);
    try {
      setDetail(await getBankApplication(applicationId));
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : t("forensic.loadError"));
    }
  }, [applicationId, t]);

  useEffect(() => {
    loadDetail();
  }, [loadDetail]);

  async function submitDecision(decision: BankDecision, noteValue?: string) {
    setDecisionError(null);
    setDecisionBusy(decision);
    try {
      const res = await decideApplication(applicationId, decision, noteValue);
      setDetail((prev) => (prev ? { ...prev, status: res.status } : prev));
      setDecisionMode("idle");
      setNote("");
    } catch (err) {
      setDecisionError(err instanceof ApiError ? err.message : t("bank.detail.decisionError"));
    } finally {
      setDecisionBusy(null);
    }
  }

  if (loadError) {
    return (
      <div data-portal="bank" className="min-h-screen bg-bg">
        <PortalHeader
          label={t("bank.detail.deskLabel")}
          containerClassName="max-w-[1200px]"
          homeTo="/bank"
          nav={[{ to: "/home", label: t("common.nav.home") }]}
        />
        <main className="mx-auto max-w-[1200px] px-4 py-8">
          <BackButton to="/bank" label={t("common.back.queue")} />
          <Card className="py-6 text-center">
            <p className="mb-2.5 text-[13px] text-flag">{loadError}</p>
            <Button variant="ghost" size="sm" onClick={loadDetail}>
              {t("forensic.retry")}
            </Button>
          </Card>
        </main>
      </div>
    );
  }

  if (!detail) {
    return (
      <div data-portal="bank" className="min-h-screen bg-bg">
        <PortalHeader
          label={t("bank.detail.deskLabel")}
          containerClassName="max-w-[1200px]"
          homeTo="/bank"
          nav={[{ to: "/home", label: t("common.nav.home") }]}
        />
        <main className="mx-auto max-w-[1200px] px-4 py-8">
          <BackButton to="/bank" label={t("common.back.queue")} />
          <Card className="py-6 text-center text-[13px] text-text-2">{t("forensic.loading")}</Card>
        </main>
      </div>
    );
  }

  const decisionsLocked = detail.status !== "review_ready";
  const decided = DECIDED_STATUSES.has(detail.status);

  return (
    <div data-portal="bank" className="min-h-screen bg-bg">
      <PortalHeader
        label={t("bank.detail.deskLabel")}
        containerClassName="max-w-[1200px]"
        homeTo="/bank"
        nav={[{ to: "/home", label: t("common.nav.home") }]}
      />

      <main className="mx-auto max-w-[1200px] px-4 py-6">
        <PageFade>
        <BackButton to="/bank" label={t("common.back.queue")} />

        <div className="mb-5 flex flex-wrap items-start justify-between gap-3 border-b border-line pb-5">
          <div>
            <h1 className="font-display text-[26px] font-extrabold text-ink">{detail.sme_profile.company_name}</h1>
            <div className="mt-1.5 flex flex-wrap items-center gap-x-1.5 text-[13px] text-text-3">
              <span dir="ltr">
                {t("bank.detail.subtitleNoCr", { sector: detail.sme_profile.sector, district: detail.sme_profile.district })}
              </span>
              {detail.sme_profile.cr_number && (
                <>
                  <span>·</span>
                  <span>
                    {t("bank.detail.crLabel")}{" "}
                    <span dir="ltr" className="tabular-nums">
                      {detail.sme_profile.cr_number}
                    </span>
                  </span>
                </>
              )}
              <span>·</span>
              <span>
                {t("bank.detail.submittedLabel")}{" "}
                <span dir="ltr" className="tabular-nums">
                  {submittedAt ? submittedAt.slice(0, 10) : t("bank.detail.amountPending")}
                </span>
              </span>
              <span>·</span>
              <span>
                {t("bank.detail.amountLabel")}{" "}
                <span className="tabular-nums text-text-3/80" dir="ltr">
                  {detail.amount != null
                    ? `${detail.amount.toLocaleString("en-US")} ${t("bank.detail.amountSar")}`
                    : t("bank.detail.amountPending")}
                </span>
              </span>
            </div>
          </div>
          <LifecycleStatusPill status={detail.status} />
        </div>

        <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <MetricTile label={t("bank.detail.metric.reconciled")}>
            {detail.forensic_report ? (
              <span dir="ltr" className="text-2xl font-semibold tabular-nums text-ink">
                {Math.round(detail.forensic_report.reconciliation_rate * 100)}
                <span className="text-sm font-normal text-text-3">%</span>
              </span>
            ) : (
              <span className="text-2xl font-semibold tabular-nums text-text-3">—</span>
            )}
          </MetricTile>
          <MetricTile label={t("bank.detail.metric.businessModel")}>
            {detail.weakness_report ? (
              <span dir="ltr" className="text-2xl font-semibold tabular-nums text-ink">
                {detail.weakness_report.business_model_score}
                <span className="text-sm font-normal text-text-3">/100</span>
              </span>
            ) : (
              <span className="text-2xl font-semibold tabular-nums text-text-3">—</span>
            )}
          </MetricTile>
          <MetricTile label={t("bank.detail.metric.documents")}>
            <span className="text-2xl font-semibold tabular-nums text-ink">{detail.extracted_documents.length}</span>
          </MetricTile>
          <MetricTile label={t("bank.detail.metric.forensic")}>
            {detail.forensic_report ? (
              <StatusPill tone={FORENSIC_TONE[detail.forensic_report.overall_status]}>
                {t(`forensic.status.${detail.forensic_report.overall_status}`)}
              </StatusPill>
            ) : (
              <StatusPill tone="neutral">{t("bank.detail.notComputedShort")}</StatusPill>
            )}
          </MetricTile>
        </div>

        <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_320px]">
          <div>
            {detail.forensic_report === null ? (
              <Card className="mb-4 py-6 text-center text-[13px] text-text-2">{t("forensic.notComputed")}</Card>
            ) : (
              <div className="mb-4">
                <ForensicReportCard report={detail.forensic_report} />
              </div>
            )}

            {detail.weakness_report === null ? (
              <Card className="mb-4 py-6 text-center text-[13px] text-text-2">{t("weakness.notComputed")}</Card>
            ) : (
              <div className="mb-4">
                <WeaknessReportCard report={detail.weakness_report} />
              </div>
            )}

            <DocumentsListCard documents={detail.extracted_documents} />
          </div>

          <div className="lg:sticky lg:top-4 lg:h-fit">
            <Card className="mb-4">
              <h3 className="mb-3 text-title font-semibold text-ink">{t("bank.detail.rail.title")}</h3>

              <div className="mb-3.5 grid grid-cols-2 gap-2.5">
                <div className="rounded-lg bg-surface-2 px-3 py-2.5">
                  <div className="text-[11px] text-text-3">{t("bank.detail.metric.businessModel")}</div>
                  <div dir="ltr" className="mt-0.5 text-lg font-semibold tabular-nums text-ink">
                    {detail.weakness_report ? detail.weakness_report.business_model_score : "—"}
                    <span className="text-xs font-normal text-text-3">/100</span>
                  </div>
                </div>
                <div className="rounded-lg bg-surface-2 px-3 py-2.5">
                  <div className="text-[11px] text-text-3">{t("bank.detail.metric.forensic")}</div>
                  <div className="mt-1">
                    {detail.forensic_report ? (
                      <StatusPill tone={FORENSIC_TONE[detail.forensic_report.overall_status]} className="text-[11px]">
                        {t(`forensic.status.${detail.forensic_report.overall_status}`)}
                      </StatusPill>
                    ) : (
                      <span className="text-sm text-text-3">—</span>
                    )}
                  </div>
                </div>
              </div>

              {decisionMode === "idle" && (
                <div className="flex flex-col gap-2">
                  <Button
                    variant="accent"
                    onClick={() => submitDecision("approve")}
                    disabled={decisionsLocked || decisionBusy !== null}
                  >
                    {decisionBusy === "approve" ? t("bank.detail.deciding") : t("bank.detail.approve")}
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() => setDecisionMode("request_info_note")}
                    disabled={decisionsLocked || decisionBusy !== null}
                  >
                    {t("bank.detail.requestInfo")}
                  </Button>
                  <Button
                    variant="danger"
                    onClick={() => submitDecision("reject")}
                    disabled={decisionsLocked || decisionBusy !== null}
                  >
                    {decisionBusy === "reject" ? t("bank.detail.deciding") : t("bank.detail.reject")}
                  </Button>
                </div>
              )}

              {decisionMode === "request_info_note" && (
                <div className="space-y-2.5">
                  <label className="block text-[12px] font-medium text-text-2">
                    {t("bank.detail.noteLabel")}
                    <textarea
                      value={note}
                      onChange={(e) => setNote(e.target.value)}
                      rows={3}
                      placeholder={t("bank.detail.notePlaceholder")}
                      className="mt-1 w-full rounded-lg border border-line-strong bg-bg px-2.5 py-1.5 text-[13px] text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                    />
                  </label>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="accent"
                      size="sm"
                      onClick={() => submitDecision("request_info", note)}
                      disabled={decisionBusy !== null}
                    >
                      {decisionBusy === "request_info" ? t("bank.detail.deciding") : t("bank.detail.sendRequest")}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setDecisionMode("idle");
                        setNote("");
                      }}
                      disabled={decisionBusy !== null}
                    >
                      {t("sme.new.cancel")}
                    </Button>
                  </div>
                </div>
              )}

              {decisionError && <p className="mt-2 text-xs text-flag">{decisionError}</p>}

              <p className="mt-3.5 flex items-center gap-1.5 text-[11px] text-text-3">
                <GoldDiamond className="h-[11px] w-[11px]" />
                {t("bank.detail.signOff")}
              </p>

              {decisionsLocked && (
                <p className="mt-2 text-[11.5px] text-text-3">
                  {decided ? t("bank.detail.decisionRecorded") : t("bank.detail.notYetSubmitted")}
                </p>
              )}
            </Card>

            <MarketVerdictCard verdict={detail.market_verdict} />
            <ComingSoonCard
              title={t("bank.detail.sandboxTitle")}
              body={t("bank.detail.sandboxBody")}
              badge={t("bank.detail.phase4")}
            />
          </div>
        </div>
      </PageFade>
      </main>
    </div>
  );
}
