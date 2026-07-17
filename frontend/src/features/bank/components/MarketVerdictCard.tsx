// Market verdict card — bank application detail page (data-portal="bank", falcon blue).
// Receives the MarketVerdict from GET /bank/applications/{id} — no internal fetch.
// When verdict is null the card shows a "not yet computed" state so the slot
// is never empty-looking. Language rule per DESIGN_SYSTEM.md + data/honesty copy:
// "grounded in / cites its source" — never "trained on" or "AI-generated".
//
// Badges: neutral lifecycle-pill style only (DESIGN_SYSTEM.md §8.6) — never
// the pass/review/flag traffic-light tokens, which are reserved exclusively
// for ForensicStatus (§4.1). Trend is differentiated by icon, not colour.
import type { MarketVerdict } from "../../../types";
import { useLang } from "../../../i18n/LangProvider";
import type { StringKey } from "../../../i18n/strings";
import { GoldDiamond } from "../../../components/JadwaMark";
import Card from "../../../components/Card";

// Both badges use the neutral lifecycle-pill style (DESIGN_SYSTEM §8.6):
// the market verdict is informational, not a fraud verdict, so it never
// borrows accent emphasis or the pass/review/flag tokens (§4.1). The trend
// icon, not colour, differentiates the states.
const PILL_CLASS = "bg-surface-2 text-text-2 border border-line font-medium";

// Decorative trend icons (inline SVG — the existing cards use no icon
// library, and CONVENTIONS forbid new deps): growing = trending-up,
// stable = minus, declining = trending-down.
const TREND_ICON: Record<MarketVerdict["sector_trend"], JSX.Element> = {
  growing: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-3 w-3 flex-none rtl:-scale-x-100" aria-hidden="true">
      <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
      <polyline points="16 7 22 7 22 13" />
    </svg>
  ),
  stable: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="h-3 w-3 flex-none" aria-hidden="true">
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  ),
  declining: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-3 w-3 flex-none rtl:-scale-x-100" aria-hidden="true">
      <polyline points="22 17 13.5 8.5 8.5 13.5 2 7" />
      <polyline points="16 17 22 17 22 11" />
    </svg>
  ),
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

function Badge({ label, icon }: { label: string; icon?: JSX.Element }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs ${PILL_CLASS}`}
    >
      {icon}
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
                icon={TREND_ICON[verdict.sector_trend]}
              />
            </div>

            <div className="rounded-xl bg-surface-2 px-3 py-2.5">
              <div className="mb-1.5 text-[11px] font-medium text-text-3">
                {t("bank.detail.market.saturationLabel")}
              </div>
              <Badge label={t(SAT_KEY[verdict.district_saturation])} />
            </div>
          </div>

          {/* Oracle insight */}
          {verdict.oracle_insight && (
            <div className="mb-3">
              <div className="mb-1 text-[11px] font-medium text-text-3">
                {t("bank.detail.market.insightLabel")}
              </div>
              {/* leading-[1.9] per DESIGN_SYSTEM §3.2 (Arabic prose) — never truncated */}
              <p className="text-[13px] leading-[1.9] text-text-2">{verdict.oracle_insight}</p>
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
