// Bank application detail — layout matches docs/mockups/bank_dashboard_dark_falcon_blue.html;
// follows the GLOBAL theme + language now (no per-screen pinning). data-portal="bank"
// (falcon blue) is independent of theme/lang. Standalone screen (its own header)
// rather than nested in BankDashboardLayout, because the mockup's header
// ("Underwriting desk") differs from the queue's header — still guarded by
// RequireRole role="bank" in App.tsx.
//
// Tabbed per node (architecture.md §1): Overview / Forensic report / Weakness
// report are real, wired to the one GET /bank/applications/{id} call
// (architecture.md §4 — "the ENTIRE dashboard in ONE call"). Market verdict
// stays a disabled tab; the Risk sandbox section (embedded in Overview) stays
// a clearly-labelled disabled placeholder — both are out of scope for this
// refurbish (no /sandbox/recalculate or Oracle UI to build).
//
// The decision action bar (Approve / Request info / Reject) posts to the real
// POST /bank/applications/{id}/decision and reflects the returned status in
// the header's lifecycle pill; it disables itself once a decision is already
// recorded (or before the application has even reached "review_ready").
import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useLang } from "../../../i18n/LangProvider";
import type { StringKey } from "../../../i18n/strings";
import { GoldDiamond } from "../../../components/JadwaMark";
import PortalHeader from "../../../components/PortalHeader";
import LifecycleStatusPill from "../../../components/LifecycleStatusPill";
import ForensicReportCard from "../components/ForensicReportCard";
import WeaknessReportCard from "../components/WeaknessReportCard";
import { ApiError, decideApplication, getBankApplication } from "../../../lib/api";
import type { BankApplicationDetail, BankDecision, DocumentJSON } from "../../../types";

type TabId = "overview" | "forensic" | "weakness" | "market";

const TABS: { id: TabId; labelKey: StringKey; enabled: boolean }[] = [
  { id: "overview", labelKey: "bank.detail.tab.overview", enabled: true },
  { id: "forensic", labelKey: "bank.detail.tab.forensic", enabled: true },
  { id: "weakness", labelKey: "bank.detail.tab.weakness", enabled: true },
  { id: "market", labelKey: "bank.detail.tab.market", enabled: false },
];

const DECIDED_STATUSES = new Set(["approved", "rejected", "more_info_needed"]);

function Badge({
  tone,
  dot = true,
  children,
}: {
  tone: "pass" | "review" | "flag";
  dot?: boolean;
  children: string;
}) {
  const cls =
    tone === "pass" ? "bg-pass-bg text-pass" : tone === "review" ? "bg-review-bg text-review" : "bg-flag-bg text-flag";
  const dotCls = tone === "pass" ? "bg-pass" : tone === "review" ? "bg-review" : "bg-flag";
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11.5px] font-medium ${cls}`}>
      {dot && <span className={`h-1.5 w-1.5 rounded-full ${dotCls}`} />}
      {children}
    </span>
  );
}

function MetricCard({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-line bg-surface px-3.5 py-3">
      <div className="text-[11px] font-medium text-text-3">{label}</div>
      <div className="mt-1">{children}</div>
    </div>
  );
}

function DocumentsListCard({ documents }: { documents: DocumentJSON[] }) {
  const { t } = useLang();

  if (documents.length === 0) {
    return (
      <div className="mb-3.5 rounded-xl border border-line bg-surface px-4 py-6 text-center text-[13px] text-text-2">
        {t("bank.detail.documentsEmpty")}
      </div>
    );
  }

  return (
    <div className="mb-3.5 rounded-xl border border-line bg-surface p-4">
      <h3 className="mb-3 text-title font-semibold text-ink">{t("sme.home.documentsTitle")}</h3>
      <ul className="space-y-2">
        {documents.map((doc) => (
          <li
            key={doc.document_id}
            className="flex items-center justify-between border-b border-surface-2 pb-2 text-[12.5px] last:border-b-0 last:pb-0"
          >
            <div className="min-w-0">
              <p className="font-medium text-ink">{t(`review.type.${doc.type}` as StringKey)}</p>
              <p className="mt-0.5 text-text-2">
                {doc.vendor && <span>{doc.vendor} · </span>}
                <span dir="ltr" className="tabular-nums">
                  {doc.currency} {doc.extracted_amount.toLocaleString("en-US")}
                </span>
                {" · "}
                <span dir="ltr" className="tabular-nums">
                  {doc.date}
                </span>
              </p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function BankApplicationDetailPage() {
  const { applicationId: routeApplicationId } = useParams();
  const applicationId = routeApplicationId ?? "demo"; // mirrors ReviewDocumentsPage's fallback convention
  const { t } = useLang();
  const [activeTab, setActiveTab] = useState<TabId>("overview");

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
        <PortalHeader label={t("bank.detail.deskLabel")} containerClassName="max-w-4xl" />
        <main className="mx-auto max-w-4xl px-[18px] py-[18px]">
          <div className="rounded-xl border border-line bg-surface px-4 py-6 text-center">
            <p className="mb-2.5 text-[13px] text-flag">{loadError}</p>
            <button
              type="button"
              onClick={loadDetail}
              className="rounded-lg border border-line-strong px-3 py-1.5 text-xs font-medium text-accent-strong hover:bg-accent-soft focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            >
              {t("forensic.retry")}
            </button>
          </div>
        </main>
      </div>
    );
  }

  if (!detail) {
    return (
      <div data-portal="bank" className="min-h-screen bg-bg">
        <PortalHeader label={t("bank.detail.deskLabel")} containerClassName="max-w-4xl" />
        <main className="mx-auto max-w-4xl px-[18px] py-[18px]">
          <p className="rounded-xl border border-line bg-surface px-4 py-6 text-center text-[13px] text-text-2">
            {t("forensic.loading")}
          </p>
        </main>
      </div>
    );
  }

  const decisionsLocked = detail.status !== "review_ready";

  return (
    <div data-portal="bank" className="min-h-screen bg-bg">
      <PortalHeader label={t("bank.detail.deskLabel")} containerClassName="max-w-4xl" />

      <main className="mx-auto max-w-4xl px-[18px] py-[18px]">
        <div className="mb-3.5 flex flex-wrap items-end justify-between gap-2">
          <div>
            <div className="font-display text-[21px] font-extrabold text-ink">{detail.sme_profile.company_name}</div>
            <div className="mt-0.5 text-xs text-text-3">
              {t("bank.detail.subtitleNoCr", { sector: detail.sme_profile.sector, district: detail.sme_profile.district })}
              {detail.sme_profile.cr_number && (
                <>
                  {" · "}
                  {t("bank.detail.crLabel")}{" "}
                  <span dir="ltr" className="tabular-nums">
                    {detail.sme_profile.cr_number}
                  </span>
                </>
              )}
            </div>
          </div>
          <LifecycleStatusPill status={detail.status} />
        </div>

        <div role="tablist" className="mb-3.5 flex gap-1 border-b border-line">
          {TABS.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={isActive}
                disabled={!tab.enabled}
                title={tab.enabled ? undefined : t("bank.detail.tab.comingSoon")}
                onClick={() => tab.enabled && setActiveTab(tab.id)}
                className={[
                  "border-b-2 px-3 py-2 text-sm font-medium transition-colors motion-reduce:transition-none",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg",
                  !tab.enabled
                    ? "cursor-not-allowed border-transparent text-text-3/60"
                    : isActive
                      ? "border-accent text-accent-strong"
                      : "border-transparent text-text-2 hover:text-ink",
                ].join(" ")}
              >
                {t(tab.labelKey)}
              </button>
            );
          })}
        </div>

        {activeTab === "overview" && (
          <>
            <DocumentsListCard documents={detail.extracted_documents} />

            <div className="mb-3.5 grid grid-cols-2 gap-2.5 sm:grid-cols-4">
              <MetricCard label={t("bank.detail.metric.reconciled")}>
                <span className="tabular-nums text-[22px] font-semibold text-ink">
                  17<span className="text-[13px] font-normal text-text-3">/20</span>
                </span>
              </MetricCard>
              <MetricCard label={t("bank.detail.metric.businessModel")}>
                <span className="tabular-nums text-[22px] font-semibold text-ink">
                  72<span className="text-[13px] font-normal text-text-3">/100</span>
                </span>
              </MetricCard>
              <MetricCard label={t("bank.detail.metric.sectorTrend")}>
                <Badge tone="pass" dot={false}>
                  {t("bank.detail.growing")}
                </Badge>
              </MetricCard>
              <MetricCard label={t("bank.detail.metric.riskClass")}>
                <Badge tone="review">{t("bank.detail.riskMedium")}</Badge>
              </MetricCard>
            </div>

            {/* Risk sandbox — deliberately OUT OF SCOPE for this refurbish (no
                /sandbox/recalculate UI, no Oracle node): a clearly-labelled
                disabled placeholder, not a live-looking demo. */}
            <div className="mb-3.5 rounded-xl border border-dashed border-line bg-surface-2 px-4 py-5 text-center">
              <span className="text-sm font-semibold text-text-2">{t("bank.detail.sandboxTitle")}</span>
              <p className="mt-1 text-[11.5px] text-text-3">{t("bank.detail.sandboxDisabled")}</p>
            </div>
          </>
        )}

        {activeTab === "forensic" && (
          <div className="mb-3.5">
            {detail.forensic_report === null && (
              <p className="rounded-xl border border-line bg-surface px-4 py-6 text-center text-[13px] text-text-2">
                {t("forensic.notComputed")}
              </p>
            )}
            {detail.forensic_report && <ForensicReportCard report={detail.forensic_report} />}
          </div>
        )}

        {activeTab === "weakness" && (
          <div className="mb-3.5">
            {detail.weakness_report === null && (
              <p className="rounded-xl border border-line bg-surface px-4 py-6 text-center text-[13px] text-text-2">
                {t("weakness.notComputed")}
              </p>
            )}
            {detail.weakness_report && <WeaknessReportCard report={detail.weakness_report} />}
          </div>
        )}

        <div className="rounded-xl border border-line bg-surface px-4 py-3.5">
          {decisionMode === "idle" && (
            <div className="flex flex-wrap items-center gap-2.5">
              <button
                type="button"
                onClick={() => submitDecision("approve")}
                disabled={decisionsLocked || decisionBusy !== null}
                className="inline-flex h-10 items-center gap-2 rounded-lg bg-accent px-5 text-sm font-medium text-on-accent disabled:opacity-50 hover:bg-accent-strong focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
              >
                {decisionBusy === "approve" ? t("bank.detail.deciding") : t("bank.detail.approve")}
              </button>
              <button
                type="button"
                onClick={() => setDecisionMode("request_info_note")}
                disabled={decisionsLocked || decisionBusy !== null}
                className="inline-flex h-10 items-center gap-2 rounded-lg border border-line-strong bg-transparent px-[18px] text-sm text-ink disabled:opacity-50 hover:bg-surface-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              >
                {t("bank.detail.requestInfo")}
              </button>
              <button
                type="button"
                onClick={() => submitDecision("reject")}
                disabled={decisionsLocked || decisionBusy !== null}
                className="inline-flex h-10 items-center gap-2 rounded-lg border border-flag/40 bg-transparent px-[18px] text-sm text-flag disabled:opacity-50 hover:bg-flag-bg focus:outline-none focus-visible:ring-2 focus-visible:ring-flag"
              >
                {decisionBusy === "reject" ? t("bank.detail.deciding") : t("bank.detail.reject")}
              </button>
              <span className="ms-auto flex items-center gap-1.5 text-[11.5px] text-text-3">
                <GoldDiamond />
                {t("bank.detail.signOff")}
              </span>
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
                <button
                  type="button"
                  onClick={() => submitDecision("request_info", note)}
                  disabled={decisionBusy !== null}
                  className="rounded-lg bg-accent px-4 py-1.5 text-xs font-medium text-on-accent disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
                >
                  {decisionBusy === "request_info" ? t("bank.detail.deciding") : t("bank.detail.sendRequest")}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setDecisionMode("idle");
                    setNote("");
                  }}
                  disabled={decisionBusy !== null}
                  className="rounded-lg border border-line-strong px-4 py-1.5 text-xs text-ink hover:bg-surface-2 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                >
                  {t("sme.new.cancel")}
                </button>
              </div>
            </div>
          )}

          {decisionError && <p className="mt-2 text-xs text-flag">{decisionError}</p>}

          {decisionsLocked && (
            <p className="mt-2 text-[11.5px] text-text-3">
              {DECIDED_STATUSES.has(detail.status) ? t("bank.detail.decisionRecorded") : t("bank.detail.notYetSubmitted")}
            </p>
          )}
        </div>
      </main>
    </div>
  );
}
