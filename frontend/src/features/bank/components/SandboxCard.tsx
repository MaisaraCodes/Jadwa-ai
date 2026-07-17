// Risk Sandbox card — bank application detail page (data-portal="bank", falcon blue).
// The one live, interactive card: six sliders drive a single debounced POST to
// /bank/applications/{id}/sandbox/recalculate; the response drives a 12-month
// cash-flow line chart, a neutral risk-class badge, and a summary line.
//
// Payload discipline (architecture.md §3): the client sends ONLY { deltas }
// (fractions — 0.20 = +20%); the risk_baseline is loaded server-side and never
// travels either direction. On mount we POST all-zero deltas once to obtain the
// baseline projection (dashed comparison line); every slider move updates the
// SOLID line only.
//
// Badge: neutral lifecycle-pill style (DESIGN_SYSTEM §8.6) — NEVER the
// pass/review/flag traffic-light tokens, which are reserved for ForensicStatus
// (§4.1). risk_class is informational, differentiated by icon, not colour.
import { useCallback, useEffect, useRef, useState } from "react";
import { useLang } from "../../../i18n/LangProvider";
import type { StringKey } from "../../../i18n/strings";
import { ApiError, recalculateSandbox } from "../../../lib/api";
import type { RiskClass, RiskProjection, ScenarioDeltas } from "../../../types";
import Card from "../../../components/Card";

const DEBOUNCE_MS = 150;

// Slider metadata. SOURCE OF TRUTH for keys/ranges is
// backend/core/risk_calc_engine.py :: SLIDERS — the frontend can't import Python,
// so the six entries are mirrored here (keys MUST equal ScenarioDeltas fields).
// Backend ranges are FRACTIONS; `min`/`max`/`step`/`default` below are in the
// DISPLAY units the user sees, converted back to fractions at the payload edge.
//   unit "percent" -> display N%, fraction = N/100   (revenue_growth: ±30 -> ±0.30)
//   unit "pp"      -> display N pp, fraction = N/100  (interest_rate: -3..+8 -> -0.03..+0.08)
//   unit "index"   -> display raw fraction, no suffix (oil_price_sensitivity: ±0.50)
type SliderUnit = "percent" | "pp" | "index";

interface SliderMeta {
  key: keyof ScenarioDeltas;
  labelKey: StringKey;
  unit: SliderUnit;
  min: number; // display units
  max: number; // display units
  step: number; // display units
}

const SLIDER_META: SliderMeta[] = [
  // risk_calc_engine.SLIDERS: revenue_growth  -0.30..0.30  unit "%"
  { key: "revenue_growth", labelKey: "bank.detail.sandbox.slider.revenue_growth", unit: "percent", min: -30, max: 30, step: 1 },
  // risk_calc_engine.SLIDERS: cost_increase   -0.20..0.40  unit "%"
  { key: "cost_increase", labelKey: "bank.detail.sandbox.slider.cost_increase", unit: "percent", min: -20, max: 40, step: 1 },
  // risk_calc_engine.SLIDERS: customer_churn   0.00..0.50  unit "%" (one-directional)
  { key: "customer_churn", labelKey: "bank.detail.sandbox.slider.customer_churn", unit: "percent", min: 0, max: 50, step: 1 },
  // risk_calc_engine.SLIDERS: demand_shift    -0.40..0.40  unit "%"
  { key: "demand_shift", labelKey: "bank.detail.sandbox.slider.demand_shift", unit: "percent", min: -40, max: 40, step: 1 },
  // risk_calc_engine.SLIDERS: interest_rate   -0.03..0.08  unit "%" (rate points)
  { key: "interest_rate", labelKey: "bank.detail.sandbox.slider.interest_rate", unit: "pp", min: -3, max: 8, step: 1 },
  // risk_calc_engine.SLIDERS: oil_price_sensitivity -0.50..0.50 unit "index"
  { key: "oil_price_sensitivity", labelKey: "bank.detail.sandbox.slider.oil_price_sensitivity", unit: "index", min: -0.5, max: 0.5, step: 0.05 },
];

const ZERO_DISPLAY: ScenarioDeltas = {
  revenue_growth: 0,
  cost_increase: 0,
  customer_churn: 0,
  demand_shift: 0,
  interest_rate: 0,
  oil_price_sensitivity: 0,
};

const RISK_KEY: Record<RiskClass, StringKey> = {
  low: "bank.detail.sandbox.risk.low",
  medium: "bank.detail.sandbox.risk.medium",
  high: "bank.detail.sandbox.risk.high",
};

// Risk-level arrows (inline SVG, no icon lib — CONVENTIONS forbids new deps):
// higher risk trends up, lower risk trends down, medium is flat. Decorative.
const RISK_ICON: Record<RiskClass, JSX.Element> = {
  low: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-3 w-3 flex-none rtl:-scale-x-100" aria-hidden="true">
      <polyline points="22 17 13.5 8.5 8.5 13.5 2 7" />
      <polyline points="16 17 22 17 22 11" />
    </svg>
  ),
  medium: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="h-3 w-3 flex-none" aria-hidden="true">
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  ),
  high: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-3 w-3 flex-none rtl:-scale-x-100" aria-hidden="true">
      <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
      <polyline points="16 7 22 7 22 13" />
    </svg>
  ),
};

function toFraction(meta: SliderMeta, displayValue: number): number {
  const raw = meta.unit === "index" ? displayValue : displayValue / 100;
  return Math.round(raw * 10000) / 10000; // kill float noise (e.g. 0.30000000004)
}

function buildDeltas(display: ScenarioDeltas): ScenarioDeltas {
  return SLIDER_META.reduce((acc, m) => {
    acc[m.key] = toFraction(m, display[m.key]);
    return acc;
  }, {} as ScenarioDeltas);
}

function formatDelta(meta: SliderMeta, v: number, ppSuffix: string): string {
  const sign = v > 0 ? "+" : ""; // negatives already carry "-"; zero shows none
  if (meta.unit === "index") return `${sign}${v.toFixed(2)}`;
  if (meta.unit === "pp") return `${sign}${v} ${ppSuffix}`;
  return `${sign}${v}%`;
}

function formatSar(v: number): string {
  const abs = Math.abs(v);
  const sign = v < 0 ? "-" : "";
  if (abs >= 1_000_000) return `${sign}${(abs / 1_000_000).toFixed(abs >= 10_000_000 ? 0 : 1)}M`;
  if (abs >= 1_000) return `${sign}${Math.round(abs / 1_000)}K`;
  return `${Math.round(v)}`;
}

// --- chart ------------------------------------------------------------------
const W = 320;
const H = 172;
const PAD_MAIN = 12; // top / non-axis horizontal side
const PAD_BOTTOM = 22; // month labels
const PAD_AXIS = 40; // Y-label gutter

function CashFlowChart({
  months,
  baseline,
  current,
  dir,
  descId,
  desc,
}: {
  months: string[];
  baseline: number[];
  current: number[];
  dir: "rtl" | "ltr";
  descId: string;
  desc: string;
}) {
  const n = current.length;
  const rtl = dir === "rtl";
  // Y-axis gutter sits on the reading-start side: left for LTR, right for RTL.
  const innerLeft = rtl ? PAD_MAIN : PAD_AXIS;
  const innerRight = rtl ? W - PAD_AXIS : W - PAD_MAIN;
  const innerTop = PAD_MAIN;
  const innerBottom = H - PAD_BOTTOM;

  const all = [...baseline, ...current];
  const dataMin = Math.min(...all);
  const dataMax = Math.max(...all);
  const range = dataMax - dataMin || Math.abs(dataMax) || 1;
  const yMin = dataMin - range * 0.1;
  const yMax = dataMax + range * 0.1;

  const xFor = (i: number) => {
    const f = n > 1 ? i / (n - 1) : 0.5;
    return rtl ? innerRight - f * (innerRight - innerLeft) : innerLeft + f * (innerRight - innerLeft);
  };
  const yFor = (v: number) => innerBottom - ((v - yMin) / (yMax - yMin)) * (innerBottom - innerTop);

  const points = (series: number[]) => series.map((v, i) => `${xFor(i).toFixed(1)},${yFor(v).toFixed(1)}`).join(" ");

  const gridFractions = [0, 0.25, 0.5, 0.75, 1];
  const labelAnchor = rtl ? "start" : "end";
  const labelX = rtl ? innerRight + 4 : innerLeft - 4;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-describedby={descId}>
      <desc id={descId}>{desc}</desc>

      {/* horizontal gridlines + Y labels */}
      {gridFractions.map((f) => {
        const yVal = yMax - f * (yMax - yMin);
        const y = yFor(yVal);
        return (
          <g key={f}>
            <line x1={innerLeft} y1={y} x2={innerRight} y2={y} className="text-line" stroke="currentColor" strokeWidth="1" />
            <text x={labelX} y={y + 3} textAnchor={labelAnchor} className="fill-text-3 text-[8px] tabular-nums">
              {formatSar(yVal)}
            </text>
          </g>
        );
      })}

      {/* zero reference line, only when the range crosses zero */}
      {yMin < 0 && yMax > 0 && (
        <line x1={innerLeft} y1={yFor(0)} x2={innerRight} y2={yFor(0)} className="text-line-strong" stroke="currentColor" strokeWidth="1" strokeDasharray="1 2" />
      )}

      {/* baseline (dashed, muted) */}
      <polyline points={points(baseline)} fill="none" className="text-text-3" stroke="currentColor" strokeWidth="1.5" strokeDasharray="4 3" strokeLinejoin="round" strokeLinecap="round" />

      {/* current scenario (solid, accent) */}
      <polyline points={points(current)} fill="none" className="text-accent" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
      {current.map((v, i) => (
        <circle key={i} cx={xFor(i)} cy={yFor(v)} r="1.6" className="fill-accent" />
      ))}

      {/* month labels along X */}
      {months.map((label, i) => (
        <text key={i} x={xFor(i)} y={H - 8} textAnchor="middle" className="fill-text-3 text-[7px] tabular-nums">
          {label}
        </text>
      ))}
    </svg>
  );
}

function Spinner() {
  return (
    <svg viewBox="0 0 24 24" className="h-3.5 w-3.5 animate-spin text-text-3" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="3" className="opacity-25" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

export default function SandboxCard({ applicationId }: { applicationId: string }) {
  const { t, dir } = useLang();

  const [display, setDisplay] = useState<ScenarioDeltas>(ZERO_DISPLAY);
  const [baseline, setBaseline] = useState<RiskProjection | null>(null);
  const [current, setCurrent] = useState<RiskProjection | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [unavailable, setUnavailable] = useState(false);

  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reqSeq = useRef(0);
  const ppSuffix = t("bank.detail.sandbox.unit.pp");

  const runRecalc = useCallback(
    async (next: ScenarioDeltas, isBaseline: boolean) => {
      const id = ++reqSeq.current;
      setLoading(true);
      try {
        const { projection } = await recalculateSandbox(applicationId, buildDeltas(next));
        if (id !== reqSeq.current) return; // a newer request superseded this one
        if (isBaseline) setBaseline(projection);
        setCurrent(projection);
        setError(null);
        setUnavailable(false);
      } catch (err) {
        if (id !== reqSeq.current) return;
        if (err instanceof ApiError && err.status === 404 && err.code === "risk_baseline_unavailable") {
          setUnavailable(true); // compact empty state; card stays visible
        } else {
          // keep the last successful projection; surface an unobtrusive note
          setError(err instanceof ApiError ? err.message : t("bank.detail.sandbox.error"));
        }
      } finally {
        if (id === reqSeq.current) setLoading(false);
      }
    },
    [applicationId, t],
  );

  // On mount: one baseline POST (all deltas = 0).
  useEffect(() => {
    runRecalc(ZERO_DISPLAY, true);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [runRecalc]);

  function onSliderChange(meta: SliderMeta, raw: string) {
    const value = Number(raw);
    const next = { ...display, [meta.key]: value };
    setDisplay(next);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => runRecalc(next, false), DEBOUNCE_MS);
  }

  // Fire immediately on release (pointer/touch/keyboard) — whichever beats the timer.
  function flush() {
    if (timer.current) clearTimeout(timer.current);
    runRecalc(display, false);
  }

  function resetScenario() {
    if (timer.current) clearTimeout(timer.current);
    setDisplay(ZERO_DISPLAY);
    runRecalc(ZERO_DISPLAY, false);
  }

  return (
    <Card className="mb-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h3 className="text-title font-semibold text-ink">{t("bank.detail.sandbox.title")}</h3>
        <div className="flex items-center gap-2">
          {loading && !unavailable && <Spinner />}
          {!unavailable && current && (
            <span className="inline-flex items-center gap-1 rounded-full border border-line bg-surface-2 px-2.5 py-0.5 text-xs font-medium text-text-2">
              {RISK_ICON[current.risk_class]}
              {t(RISK_KEY[current.risk_class])}
            </span>
          )}
        </div>
      </div>

      {unavailable ? (
        // 404 risk_baseline_unavailable — compact empty state; the card is never hidden.
        <div className="rounded-xl border border-dashed border-line-strong px-3 py-8 text-center">
          <p className="text-[13px] leading-[1.9] text-text-3">{t("bank.detail.sandbox.empty")}</p>
        </div>
      ) : (
        <>
          {/* Chart column */}
          <div className={`transition-opacity duration-base ${loading ? "opacity-70" : "opacity-100"}`}>
            {baseline && current ? (
              <>
                <div className="mb-1.5 flex items-center gap-3 text-[10px] text-text-3">
                  <span className="inline-flex items-center gap-1">
                    <span className="inline-block h-0.5 w-4 bg-accent" aria-hidden="true" />
                    {t("bank.detail.sandbox.currentLegend")}
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <span className="inline-block h-0 w-4 border-t border-dashed border-text-3" aria-hidden="true" />
                    {t("bank.detail.sandbox.baselineLegend")}
                  </span>
                </div>
                <CashFlowChart
                  months={current.months}
                  baseline={baseline.cash_flow}
                  current={current.cash_flow}
                  dir={dir}
                  descId={`sandbox-desc-${applicationId}`}
                  desc={`${t("bank.detail.sandbox.chartDesc")} ${current.summary_line}`}
                />
              </>
            ) : (
              <div className="h-[172px] animate-pulse rounded-xl bg-surface-2" aria-hidden="true" />
            )}
          </div>

          {/* Sliders */}
          <div className="mt-3 border-t border-line pt-3">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-[11px] font-medium text-text-3">{t("bank.detail.sandbox.riskLabel")}</span>
              <button
                type="button"
                onClick={resetScenario}
                aria-label={t("bank.detail.sandbox.resetAria")}
                className="rounded-md px-2 py-1 text-[11px] font-medium text-accent hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              >
                {t("bank.detail.sandbox.reset")}
              </button>
            </div>

            <div className="space-y-2.5">
              {SLIDER_META.map((meta) => {
                const value = display[meta.key];
                const labelText = t(meta.labelKey);
                return (
                  <div key={meta.key}>
                    <div className="flex items-baseline justify-between text-[12px]">
                      <label htmlFor={`sandbox-${meta.key}`} className="text-text-2">
                        {labelText}
                      </label>
                      <span dir="ltr" className="tabular-nums text-text-3">
                        {formatDelta(meta, value, ppSuffix)}
                      </span>
                    </div>
                    <input
                      id={`sandbox-${meta.key}`}
                      type="range"
                      min={meta.min}
                      max={meta.max}
                      step={meta.step}
                      value={value}
                      onChange={(e) => onSliderChange(meta, e.target.value)}
                      onPointerUp={flush}
                      onKeyUp={flush}
                      aria-label={`${labelText}: ${formatDelta(meta, value, ppSuffix)}`}
                      className="mt-1 h-1.5 w-full cursor-pointer appearance-none rounded-full bg-surface-2 accent-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                    />
                  </div>
                );
              })}
            </div>
          </div>

          {/* Summary + error */}
          {current && (
            <div className="mt-3 border-t border-line pt-3">
              <div className="mb-1 text-[11px] font-medium text-text-3">{t("bank.detail.sandbox.summaryLabel")}</div>
              {/* leading-[1.9] per DESIGN_SYSTEM §3.2. Backend returns EN-only for now. */}
              <p className="text-[13px] leading-[1.9] text-text-2">{current.summary_line}</p>
            </div>
          )}
          {error && <p className="mt-2 text-[11.5px] text-flag">{error}</p>}
        </>
      )}
    </Card>
  );
}
