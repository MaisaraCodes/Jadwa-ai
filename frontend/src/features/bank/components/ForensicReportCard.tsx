// Forensic report card — bank dashboard (data-portal="bank", falcon blue), per
// DESIGN_SYSTEM.md §8.2 (report card), §8.3 (metric card), §8.6 (status pill), §9
// (pass/review/flag mapping). Renders a ForensicReport (backend/models.py) with no
// internal fetch — the caller already has the record from GET /bank/applications/{id}
// (architecture.md §4).
import type { ForensicReport, Severity } from "../../../types";
import { useLang } from "../../../i18n/LangProvider";
import type { StringKey } from "../../../i18n/strings";

const STATUS_BORDER: Record<ForensicReport["overall_status"], string> = {
  green: "border-s-pass",
  yellow: "border-s-review",
  red: "border-s-flag",
};

const STATUS_TONE: Record<
  ForensicReport["overall_status"],
  { bg: string; text: string; dot: string; labelKey: StringKey }
> = {
  green: { bg: "bg-pass-bg", text: "text-pass", dot: "bg-pass", labelKey: "forensic.status.green" },
  yellow: { bg: "bg-review-bg", text: "text-review", dot: "bg-review", labelKey: "forensic.status.yellow" },
  red: { bg: "bg-flag-bg", text: "text-flag", dot: "bg-flag", labelKey: "forensic.status.red" },
};

const SEVERITY_ORDER: Record<Severity, number> = { high: 0, medium: 1, low: 2 };

const SEVERITY_TONE: Record<Severity, { cls: string; key: StringKey }> = {
  high: { cls: "text-flag", key: "forensic.severity.high" },
  medium: { cls: "text-review", key: "forensic.severity.medium" },
  low: { cls: "text-text-2", key: "forensic.severity.low" },
};

function StatusPill({ status }: { status: ForensicReport["overall_status"] }) {
  const { t } = useLang();
  const tone = STATUS_TONE[status];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${tone.bg} ${tone.text}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${tone.dot}`} aria-hidden="true" />
      {t(tone.labelKey)}
    </span>
  );
}

function ReconciledMetric({ rate }: { rate: number }) {
  const { t } = useLang();
  const pct = Math.round(rate * 100);
  return (
    <div className="rounded-xl bg-surface-2 p-3.5">
      <div className="text-xs font-medium text-text-3">{t("forensic.reconciledLabel")}</div>
      <div className="mt-1 text-end text-2xl font-semibold tabular-nums text-ink" dir="ltr">
        {pct}
        <span className="text-sm font-normal text-text-3">%</span>
      </div>
    </div>
  );
}

function FlagRow({ severity, description }: { severity: Severity; description: string }) {
  const { t } = useLang();
  const tone = SEVERITY_TONE[severity];
  return (
    <li className="border-b border-line py-2 first:pt-0 last:border-b-0 last:pb-0">
      <span className={`text-xs font-medium ${tone.cls}`}>{t(tone.key)}</span>
      <p className="mt-0.5 text-sm text-text-2">{description}</p>
    </li>
  );
}

export default function ForensicReportCard({ report }: { report: ForensicReport }) {
  const { t } = useLang();
  const sortedFlags = [...report.discrepancy_flags].sort(
    (a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity],
  );

  return (
    <div
      className={`rounded-xl rounded-s-none border border-line bg-surface border-s-[3px] ${STATUS_BORDER[report.overall_status]} p-4`}
    >
      <div className="mb-3 flex items-center justify-between gap-2">
        <h3 className="text-title font-semibold text-ink">{t("forensic.title")}</h3>
        <StatusPill status={report.overall_status} />
      </div>

      <div className="mb-3">
        <ReconciledMetric rate={report.reconciliation_rate} />
      </div>

      {sortedFlags.length === 0 ? (
        <p className="text-sm text-text-2">{t("forensic.emptyState")}</p>
      ) : (
        <ul>
          {sortedFlags.map((flag, i) => (
            <FlagRow key={i} severity={flag.severity} description={flag.description} />
          ))}
        </ul>
      )}
    </div>
  );
}
