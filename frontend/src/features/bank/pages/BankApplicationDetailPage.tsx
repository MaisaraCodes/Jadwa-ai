// Bank application detail — layout matches docs/mockups/bank_dashboard_dark_falcon_blue.html;
// follows the GLOBAL theme + language now (no per-screen pinning). data-portal="bank"
// (falcon blue) is independent of theme/lang. Standalone screen (its own header)
// rather than nested in BankDashboardLayout, because the mockup's header
// ("Underwriting desk") differs from the queue's header — still guarded by
// RequireRole role="bank" in App.tsx.
//
// Tabbed per node (architecture.md §1): Overview / Forensic report now, Weakness
// report + Market verdict shown as disabled placeholders until those nodes ship.
// Risk sandbox stays inside Overview for now rather than its own tab.
//
// The forensic tab is wired to the real GET /bank/applications/{id} call
// (architecture.md §4 — "the ENTIRE dashboard in ONE call"). The rest of this
// page (Overview metrics, sandbox chart) is still DEMO/hardcoded pending the
// nodes that produce weakness_report / market_verdict / risk_baseline.
import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useAuth } from "../../auth/AuthProvider";
import { useLang } from "../../../i18n/LangProvider";
import type { StringKey } from "../../../i18n/strings";
import { JadwaTileMark, GoldDiamond } from "../../../components/JadwaMark";
import ThemeToggle from "../../../components/ThemeToggle";
import LangToggle from "../../../components/LangToggle";
import ForensicReportCard from "../components/ForensicReportCard";
import { ApiError, getBankApplication } from "../../../lib/api";
import type { BankApplicationDetail } from "../../../types";

type TabId = "overview" | "forensic" | "weakness" | "market";

const TABS: { id: TabId; labelKey: StringKey; enabled: boolean }[] = [
  { id: "overview", labelKey: "bank.detail.tab.overview", enabled: true },
  { id: "forensic", labelKey: "bank.detail.tab.forensic", enabled: true },
  { id: "weakness", labelKey: "bank.detail.tab.weakness", enabled: false },
  { id: "market", labelKey: "bank.detail.tab.market", enabled: false },
];

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

export default function BankApplicationDetailPage() {
  const { applicationId: routeApplicationId } = useParams();
  const applicationId = routeApplicationId ?? "demo"; // mirrors ReviewDocumentsPage's fallback convention
  const { signOut } = useAuth();
  const { t, lang } = useLang();
  const [activeTab, setActiveTab] = useState<TabId>("overview");

  // DEMO values — localized only where the mockups show a different form per
  // language (currency position); dates/CR numbers keep Western digits (§3.2).
  const submittedDate = lang === "ar" ? "12 أكتوبر 2025" : "12 Oct 2025";

  const [detail, setDetail] = useState<BankApplicationDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

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

  return (
    <div data-portal="bank" className="min-h-screen bg-bg">
      <div className="h-[3px] bg-accent" />
      <header className="flex items-center justify-between border-b border-line bg-surface px-[18px] py-2.5">
        <div className="flex items-center gap-2.5">
          <JadwaTileMark tileFill="var(--surface-2)" />
          <span className="font-display text-[19px] font-extrabold text-ink">{t("brand.wordmark")}</span>
          <span className="h-4 w-px bg-line" />
          <span className="text-[12.5px] text-text-2">{t("bank.detail.deskLabel")}</span>
        </div>
        <div className="flex items-center gap-3">
          <LangToggle />
          <ThemeToggle />
          <span className="flex items-center gap-2 text-xs text-text-2">
            <span className="flex h-[26px] w-[26px] items-center justify-center rounded-full bg-accent-soft text-xs font-semibold text-accent-strong">
              {t("demo.bankUserInitial")}
            </span>
            {t("demo.bankUserName")}
          </span>
          <button
            type="button"
            onClick={() => signOut()}
            className="rounded-lg border border-line px-2.5 py-1 text-xs font-medium text-text-2 hover:bg-surface-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            {t("auth.signOut")}
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-[18px] py-[18px]">
        <div className="mb-3.5 flex flex-wrap items-end justify-between gap-2">
          <div>
            <div className="font-display text-[21px] font-extrabold text-ink">{t("bank.demo.company")}</div>
            <div className="mt-0.5 text-xs text-text-3 tabular-nums">
              {t("bank.detail.subtitle", { cr: "1010482913", date: submittedDate })}
            </div>
          </div>
          {activeTab !== "forensic" && <Badge tone="review">{t("bank.demo.reviewNeeded")}</Badge>}
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

            {/* Risk sandbox */}
            <div className="mb-3.5 rounded-xl border border-line bg-surface px-4 py-3.5">
              <div className="mb-2.5 flex items-center justify-between">
                <span className="text-sm font-semibold text-ink">{t("bank.detail.sandboxTitle")}</span>
                <span className="tabular-nums text-[11px] text-text-3">&lt; 150 ms</span>
              </div>
              <div className="mb-1.5 flex justify-between text-[11.5px] text-text-2">
                <span>{t("bank.detail.fuelCostShock")}</span>
                <span className="tabular-nums font-medium text-ink">+12%</span>
              </div>
              <div className="relative mb-3.5 h-[5px] rounded-full bg-line">
                <div className="h-full w-[64%] rounded-full bg-accent" />
                <div
                  className="absolute -top-1 h-[13px] w-[13px] rounded-full border-2 border-accent bg-bg"
                  style={{ insetInlineStart: "calc(64% - 7px)" }}
                />
              </div>
              <svg viewBox="0 0 300 92" width="100%" height="92" aria-label="Twelve-month cash flow under stress">
                <line x1="0" y1="70" x2="300" y2="70" stroke="var(--line-strong)" strokeWidth="1" strokeDasharray="3 4" />
                <polyline
                  points="4,40 30,44 56,38 82,50 108,46 134,58 160,54 186,66 212,60 238,72 264,64 292,56"
                  fill="none"
                  stroke="var(--accent)"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <circle cx="238" cy="72" r="3.5" fill="var(--review)" />
                <circle cx="292" cy="56" r="3.5" fill="var(--accent)" />
                <text x="4" y="86" fontFamily="Alexandria" fontSize="11" fill="var(--text-3)">
                  {t("bank.detail.monthNov")}
                </text>
                <text x="270" y="86" fontFamily="Alexandria" fontSize="11" fill="var(--text-3)">
                  {t("bank.detail.monthOct")}
                </text>
              </svg>
              <p className="mt-2 text-[11.5px] leading-[1.6] text-text-2 tabular-nums">
                {t("bank.detail.bufferCaption", { buffer: "1.0", month: 10 })}
              </p>
            </div>
          </>
        )}

        {activeTab === "forensic" && (
          <div className="mb-3.5">
            {detail === null && !loadError && (
              <p className="rounded-xl border border-line bg-surface px-4 py-6 text-center text-[13px] text-text-2">
                {t("forensic.loading")}
              </p>
            )}

            {loadError && (
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
            )}

            {detail && detail.forensic_report === null && (
              <p className="rounded-xl border border-line bg-surface px-4 py-6 text-center text-[13px] text-text-2">
                {t("forensic.notComputed")}
              </p>
            )}

            {detail?.forensic_report && <ForensicReportCard report={detail.forensic_report} />}
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            type="button"
            title={t("bank.detail.notWiredTitle")}
            className="rounded-lg bg-accent px-5 py-2.5 text-sm font-semibold text-on-accent"
          >
            {t("bank.detail.approve")}
          </button>
          <button
            type="button"
            title={t("bank.detail.notWiredTitle")}
            className="rounded-lg border border-line-strong px-[18px] py-2.5 text-sm text-ink"
          >
            {t("bank.detail.requestInfo")}
          </button>
          <button
            type="button"
            title={t("bank.detail.notWiredTitle")}
            className="rounded-lg border border-[#4A2320] px-[18px] py-2.5 text-sm text-flag"
          >
            {t("bank.detail.reject")}
          </button>
          <span className="ms-auto flex items-center gap-1.5 text-[11.5px] text-text-3">
            <GoldDiamond />
            {t("bank.detail.signOff")}
          </span>
        </div>
      </main>
    </div>
  );
}
