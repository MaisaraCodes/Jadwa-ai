// Sadu band (DESIGN_SYSTEM.md §8.9) — the six triangles map to the six-node
// pipeline (Extract → Forensic → Stress test → Market → Risk model → Record).
// Presentational: renders from a `stages` prop, driven by the caller (live
// GET /status progress in-portal, or a fully-"done" static illustration on
// the pre-portal landing page).
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

interface Props {
  stages: SaduStageState[];
  tone?: SaduTone;
  className?: string;
}

const STAGE_WIDTH = 64;
const STAGE_GAP = 12;

function Stage({ state, x, tone }: { state: SaduStageState; x: number; tone: SaduTone }) {
  const fill = tone === "gold" ? "var(--gold)" : "var(--accent)";
  if (state === "done") {
    return <path d={`M${x} 44 L${x + 32} 8 L${x + 64} 44 Z`} fill={fill} />;
  }
  if (state === "active") {
    return (
      <>
        <path d={`M${x} 44 L${x + 32} 8 L${x + 64} 44 Z`} fill="none" stroke={fill} strokeWidth="2" />
        <path d={`M${x + 16} 44 L${x + 32} 26 L${x + 48} 44 Z`} fill={fill} />
      </>
    );
  }
  return (
    <path
      d={`M${x} 44 L${x + 32} 8 L${x + 64} 44 Z`}
      fill="none"
      stroke="var(--line-strong)"
      strokeWidth="2"
    />
  );
}

export default function SaduBand({ stages, tone = "accent", className }: Props) {
  const { t, dir } = useLang();
  const width = stages.length * STAGE_WIDTH + Math.max(0, stages.length - 1) * STAGE_GAP;
  return (
    <svg
      viewBox={`0 0 ${width} 52`}
      width={width}
      height="52"
      role="img"
      aria-label={t("sme.home.stagesAriaLabel")}
      className={["motion-reduce:transition-none", className].filter(Boolean).join(" ")}
    >
      {stages.map((state, i) => {
        const slot = dir === "rtl" ? stages.length - 1 - i : i;
        return <Stage key={i} state={state} x={slot * (STAGE_WIDTH + STAGE_GAP)} tone={tone} />;
      })}
    </svg>
  );
}
