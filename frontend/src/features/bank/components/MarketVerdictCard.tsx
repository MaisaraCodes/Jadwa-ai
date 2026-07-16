// Market verdict card — bank application detail page (data-portal="bank", falcon blue).
// Receives the MarketVerdict from GET /bank/applications/{id} — no internal fetch.
// When verdict is null the card shows a "not yet computed" state so the slot
// is never empty-looking. Language rule per DESIGN_SYSTEM.md + data/honesty copy:
// "grounded in / cites its source" — never "trained on" or "AI-generated".
//
// Badge colours: only accent-soft/accent-strong tokens (falcon blue in the bank
// portal) — never the pass/review/flag traffic-light tokens, which are reserved
// exclusively for ForensicStatus (DESIGN_SYSTEM.md §4.1).
import type { MarketVerdict } from "../../../types";
import { useLang } from "../../../i18n/LangProvider";
import type { StringKey } from "../../../i18n/strings";
import { GoldDiamond } from "../../../components/JadwaMark";
import Card from "../../../components/Card";

// Trend badge: growing = accent, stable = neutral, declining = dimmed.
const TREND_CLASS: Record<MarketVerdict["sector_trend"], string> = {
  growing: "bg-accent-soft text-accent-strong font-semibold",
  stable:  "bg-surface-2 text-text-2 font-medium",
  declining: "bg-surface-2 text-text-3 font-medium",
};

// Saturation badge: low (few competitors) = accent, medium = neutral, high = dimmed.
const SAT_CLASS: Record<MarketVerdict["district_saturation"], string> = {
  low:    "bg-accent-soft text-accent-strong font-semibold",
  medium: "bg-surface-2 text-text-2 font-medium",
  high:   "bg-surface-2 text-text-3 font-medium",
};

const TREND_KEY: Record<MarketVerdict["sector_trend"], StringKey> = {
  growing:   "bank.detail.market.trend.growing",
  stable:    "bank.detail.market.trend.stable",
  declining: "bank.detail.market.trend.declining",
};

const SAT_KEY: Record<MarketVerdict["district_saturation"], StringKey> = {
  low:    "bank.detail.market.saturation.low",
  medium: "bank.detail.market.saturation.medium",
  high:   "bank.detail.market.saturation.high",
};

function Badge({ label, className }: { label: string; className: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs ${className}`}
    >
      {label}
    </span>
  );
}

export default function MarketVerdictCard({ verdict }: { verdict: MarketVerdict | null }) {
  const { t } = useLang();

  return (
    <Card className="mb-4">
      <h3 className="mb-3 text-title font-semibold text-ink">{t("bank.detail.marketTitle")}</h3>

      {!verdict ? (
        <p className="text-[13px] text-text-3">{t("bank.detail.market.noData")}</p>
      ) : (
        <>
          {/* Badges row */}
          <div className="mb-4 grid grid-cols-2 gap-3">
            <div className="rounded-xl bg-surface-2 px-3 py-2.5">
              <div className="mb-1.5 text-[11px] font-medium text-text-3">
                {t("bank.detail.market.trendLabel")}
              </div>
              <Badge
                label={t(TREND_KEY[verdict.sector_trend])}
                className={TREND_CLASS[verdict.sector_trend]}
              />
            </div>

            <div className="rounded-xl bg-surface-2 px-3 py-2.5">
              <div className="mb-1.5 text-[11px] font-medium text-text-3">
                {t("bank.detail.market.saturationLabel")}
              </div>
              <Badge
                label={t(SAT_KEY[verdict.district_saturation])}
                className={SAT_CLASS[verdict.district_saturation]}
              />
            </div>
          </div>

          {/* Oracle insight */}
          {verdict.oracle_insight && (
            <div className="mb-3">
              <div className="mb-1 text-[11px] font-medium text-text-3">
                {t("bank.detail.market.insightLabel")}
              </div>
              <p className="text-[13px] leading-[1.7] text-text-2">{verdict.oracle_insight}</p>
            </div>
          )}

          {/* Sources cited */}
          {verdict.sources_cited.length > 0 && (
            <div className="mb-3">
              <div className="mb-1 text-[11px] font-medium text-text-3">
                {t("bank.detail.market.sourcesLabel")}
              </div>
              <ul className="space-y-0.5">
                {verdict.sources_cited.map((src, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-[12px] text-text-3">
                    <span className="mt-[3px] h-1 w-1 flex-none rounded-full bg-accent" aria-hidden="true" />
                    {src}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}

      {/* Brand sign-off — always shown; "grounded in" language per data-honesty rules */}
      <p className="mt-3 flex items-center gap-1.5 border-t border-line pt-3 text-[11px] text-text-3">
        <GoldDiamond className="h-[11px] w-[11px] flex-none" />
        {t("bank.detail.market.groundedNote")}
      </p>
    </Card>
  );
}
