// Weakness report card — bank dashboard (data-portal="bank", falcon blue), per
// DESIGN_SYSTEM.md §8.2 (report card), §8.3 (metric card), §9 (status→token table).
// Renders a WeaknessReport (backend/models.py) with no internal fetch — the caller
// already has the record from GET /bank/applications/{id} (architecture.md §4).
//
// WeaknessReport has no ForensicStatus of its own, so the card's status edge is a
// UI cue derived from business_model_score (not a forensic verdict) using the
// named thresholds below: >=70 reads as a strong business model, 40-69 warrants a
// closer look, <40 is a material concern.
import type { WeaknessReport } from "../../../types";
import { useLang } from "../../../i18n/LangProvider";
import type { StringKey } from "../../../i18n/strings";

type ScoreEdge = "pass" | "review" | "flag";

const SCORE_EDGE_PASS_MIN = 70;
const SCORE_EDGE_REVIEW_MIN = 40;

function scoreToEdge(score: number): ScoreEdge {
  if (score >= SCORE_EDGE_PASS_MIN) return "pass";
  if (score >= SCORE_EDGE_REVIEW_MIN) return "review";
  return "flag";
}

const EDGE_BORDER: Record<ScoreEdge, string> = {
  pass: "border-s-pass",
  review: "border-s-review",
  flag: "border-s-flag",
};

const EDGE_TONE: Record<ScoreEdge, { bg: string; text: string; dot: string; labelKey: StringKey }> = {
  pass: { bg: "bg-pass-bg", text: "text-pass", dot: "bg-pass", labelKey: "weakness.edge.pass" },
  review: { bg: "bg-review-bg", text: "text-review", dot: "bg-review", labelKey: "weakness.edge.review" },
  flag: { bg: "bg-flag-bg", text: "text-flag", dot: "bg-flag", labelKey: "weakness.edge.flag" },
};

function EdgePill({ edge }: { edge: ScoreEdge }) {
  const { t } = useLang();
  const tone = EDGE_TONE[edge];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${tone.bg} ${tone.text}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${tone.dot}`} aria-hidden="true" />
      {t(tone.labelKey)}
    </span>
  );
}

function ScoreMetric({ score }: { score: number }) {
  const { t } = useLang();
  return (
    <div className="rounded-xl bg-surface-2 p-3.5">
      <div className="text-xs font-medium text-text-3">{t("weakness.scoreLabel")}</div>
      <div className="mt-1 text-end text-2xl font-semibold tabular-nums text-ink" dir="ltr">
        {score}
        <span className="text-sm font-normal text-text-3">/100</span>
      </div>
    </div>
  );
}

function WeaknessRow({
  rank,
  description,
  mitigation,
}: {
  rank: number;
  description: string;
  mitigation?: string;
}) {
  const { t } = useLang();
  return (
    <li className="border-b border-line py-2 first:pt-0 last:border-b-0 last:pb-0">
      <div className="flex items-start gap-2">
        <span
          className="mt-0.5 inline-flex h-5 w-5 flex-none items-center justify-center rounded-full bg-surface-2 text-[11px] font-medium tabular-nums text-text-2"
          dir="ltr"
          aria-hidden="true"
        >
          {rank}
        </span>
        <div className="min-w-0">
          <p className="text-sm text-ink">{description}</p>
          {mitigation && (
            <p className="mt-1 text-sm text-text-2">
              <span className="font-medium text-text-3">{t("weakness.mitigationInlineLabel")} </span>
              {mitigation}
            </p>
          )}
        </div>
      </div>
    </li>
  );
}

export default function WeaknessReportCard({ report }: { report: WeaknessReport }) {
  const { t } = useLang();
  const edge = scoreToEdge(report.business_model_score);
  const paired =
    report.critical_weaknesses.length > 0 &&
    report.critical_weaknesses.length === report.mitigation_suggestions.length;

  return (
    <div
      className={`rounded-xl rounded-s-none border border-line bg-surface border-s-[3px] ${EDGE_BORDER[edge]} p-4`}
    >
      <div className="mb-3 flex items-center justify-between gap-2">
        <h3 className="text-title font-semibold text-ink">{t("weakness.title")}</h3>
        <EdgePill edge={edge} />
      </div>

      <div className="mb-3">
        <ScoreMetric score={report.business_model_score} />
      </div>

      {report.critical_weaknesses.length === 0 ? (
        <p className="text-sm text-text-2">{t("weakness.emptyState")}</p>
      ) : (
        <ul>
          {report.critical_weaknesses.map((weakness, i) => (
            <WeaknessRow
              key={i}
              rank={i + 1}
              description={weakness}
              mitigation={paired ? report.mitigation_suggestions[i] : undefined}
            />
          ))}
        </ul>
      )}

      {!paired && report.mitigation_suggestions.length > 0 && (
        <div className="mt-3 border-t border-line pt-3">
          <h4 className="mb-2 text-xs font-medium text-text-3">{t("weakness.mitigationsTitle")}</h4>
          <ul>
            {report.mitigation_suggestions.map((mitigation, i) => (
              <li
                key={i}
                className="border-b border-line py-2 text-sm text-text-2 first:pt-0 last:border-b-0 last:pb-0"
              >
                {mitigation}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
