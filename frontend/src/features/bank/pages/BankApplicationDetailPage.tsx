// Bank application detail — layout matches docs/mockups/bank_dashboard_dark_falcon_blue.html;
// follows the GLOBAL theme + language now (no per-screen pinning). data-portal="bank"
// (falcon blue) is independent of theme/lang. Standalone screen (its own header)
// rather than nested in BankDashboardLayout, because the mockup's header
// ("Underwriting desk") differs from the queue's header — still guarded by
// RequireRole role="bank" in App.tsx.
//
// DEMO: the whole Rawad Logistics application (metrics, forensic findings, cash-flow
// projection) is hardcoded for this pass. Real data comes from
// GET /bank/applications/{id} (unified_application_record) in Phase 2; the sandbox
// slider will send `deltas` to the risk endpoint and render the returned
// RiskProjection instead of this static SVG.
import { IconShieldSearch } from "@tabler/icons-react";
import { useAuth } from "../../auth/AuthProvider";
import { useLang } from "../../../i18n/LangProvider";
import { JadwaTileMark, GoldDiamond } from "../../../components/JadwaMark";
import ThemeToggle from "../../../components/ThemeToggle";
import LangToggle from "../../../components/LangToggle";

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
  const { signOut } = useAuth();
  const { t, lang } = useLang();

  // DEMO values — localized only where the mockups show a different form per
  // language (currency position); dates/CR numbers keep Western digits (§3.2).
  const submittedDate = lang === "ar" ? "12 أكتوبر 2025" : "12 Oct 2025";
  const zatcaAmount = lang === "ar" ? "1,500.50 ر.س" : "SAR 1,500.50";

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
          <Badge tone="review">{t("bank.demo.reviewNeeded")}</Badge>
        </div>

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

        <div className="mb-3.5 grid grid-cols-1 gap-3 lg:grid-cols-[1.1fr_1fr]">
          {/* Forensic report */}
          <div className="rounded-xl rounded-s-none border border-line border-s-[3px] border-s-flag bg-surface px-4 py-3.5">
            <div className="mb-3 flex items-center gap-2">
              <IconShieldSearch size={17} className="text-text-2" aria-hidden="true" />
              <span className="text-sm font-semibold text-ink">{t("bank.detail.forensicTitle")}</span>
            </div>
            <div className="mb-2 rounded-lg bg-flag-bg px-3 py-2.5">
              <div className="text-[12.5px] font-medium text-flag">{t("bank.detail.finding1Title")}</div>
              <div className="mt-0.5 text-xs leading-[1.6] text-text-2 tabular-nums">
                {t("bank.detail.finding1Body", { amount: zatcaAmount })}
              </div>
            </div>
            <div className="rounded-lg bg-review-bg px-3 py-2.5">
              <div className="text-[12.5px] font-medium text-review">{t("bank.detail.finding2Title")}</div>
              <div className="mt-0.5 text-xs leading-[1.6] text-text-2 tabular-nums">
                {t("bank.detail.finding2Body", { days: 6 })}
              </div>
            </div>
          </div>

          {/* Risk sandbox */}
          <div className="rounded-xl border border-line bg-surface px-4 py-3.5">
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
        </div>

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
