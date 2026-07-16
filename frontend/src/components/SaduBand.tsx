// Sadu band (DESIGN_SYSTEM.md §8.9) — the six triangles map to the six-node
// pipeline (Extract → Forensic → Stress test → Market → Risk model → Record).
// Presentational: renders from a `stages` prop, driven by the caller (live
// GET /status progress in-portal, or a fully-"done" static illustration on
// the pre-portal landing page). A `done`/`total` shorthand covers the simpler
// binary per-application progress rows (mock: mini bands in
// jadwa_sme_screens.html) where every completed stage looks the same and
// there's no live "active" node to highlight.
//
// Stage slots are laid out in READING order, not fixed physical order — §7
// ("the whole layout mirrors") applies here too: stages[0] is always the
// first pipeline step regardless of language, but its physical x position
// flips under RTL so the band visually flows start→end like the rest of the
// page, instead of always left→right.
import { useLang } from "../i18n/LangProvider";

export type SaduStageState = "done" | "active" | "pending";
// "accent" resolves against the ambient portal accent (needs a data-portal
// ancestor); "gold" is the §8.9-sanctioned alternative for brand/hero
// surfaces that have no portal accent (e.g. the pre-portal landing page).
export type SaduTone = "accent" | "gold";
// "default" is the in-portal pipeline size (unchanged geometry); "mini" matches
// the compact per-application progress row (jadwa_sme_screens.html `.mini`).
export type SaduSize = "default" | "mini";

interface CommonProps {
  tone?: SaduTone;
  size?: SaduSize;
  className?: string;
  ariaLabel?: string;
}

type Props =
  | (CommonProps & { stages: SaduStageState[]; done?: never; total?: never })
  | (CommonProps & { stages?: never; done: number; total?: number });

const GEOMETRY: Record<SaduSize, { width: number; gap: number; topY: number; baseY: number; height: number }> = {
  default: { width: 64, gap: 12, topY: 8, baseY: 44, height: 52 },
  mini: { width: 22, gap: 7, topY: 2, baseY: 18, height: 20 },
};

function stagesFromDone(done: number, total: number): SaduStageState[] {
  return Array.from({ length: total }, (_, i) => (i < done ? "done" : "pending"));
}

function Stage({
  state,
  x,
  tone,
  width,
  topY,
  baseY,
}: {
  state: SaduStageState;
  x: number;
  tone: SaduTone;
  width: number;
  topY: number;
  baseY: number;
}) {
  const fill = tone === "gold" ? "var(--gold)" : "var(--accent)";
  const mid = x + width / 2;
  const outline = `M${x} ${baseY} L${mid} ${topY} L${x + width} ${baseY} Z`;
  if (state === "done") {
    return <path d={outline} fill={fill} />;
  }
  if (state === "active") {
    const inset = width * 0.25;
    const innerTopY = topY + (baseY - topY) * 0.5;
    return (
      <>
        <path d={outline} fill="none" stroke={fill} strokeWidth="2" />
        <path d={`M${x + inset} ${baseY} L${mid} ${innerTopY} L${x + width - inset} ${baseY} Z`} fill={fill} />
      </>
    );
  }
  return <path d={outline} fill="none" stroke="var(--line-strong)" strokeWidth="2" />;
}

export default function SaduBand({ tone = "accent", size = "default", className, ariaLabel, ...props }: Props) {
  const { t, dir } = useLang();
  const stages = props.stages ?? stagesFromDone(props.done, props.total ?? 6);
  const { width: stageWidth, gap, topY, baseY, height } = GEOMETRY[size];
  const width = stages.length * stageWidth + Math.max(0, stages.length - 1) * gap;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width={width}
      height={height}
      role="img"
      aria-label={ariaLabel ?? t("sme.home.stagesAriaLabel")}
      className={["motion-reduce:transition-none", className].filter(Boolean).join(" ")}
    >
      {stages.map((state, i) => {
        const slot = dir === "rtl" ? stages.length - 1 - i : i;
        return (
          <Stage
            key={i}
            state={state}
            x={slot * (stageWidth + gap)}
            tone={tone}
            width={stageWidth}
            topY={topY}
            baseY={baseY}
          />
        );
      })}
    </svg>
  );
}
