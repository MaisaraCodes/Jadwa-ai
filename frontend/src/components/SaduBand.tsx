// Sadu band (DESIGN_SYSTEM.md §8.9) — the six triangles map to the six-node
// pipeline (Extract → Forensic → Stress test → Market → Risk model → Record).
// PRESENTATIONAL ONLY this pass: it renders from a `stages` prop and is not
// wired to a live source.
// TODO(#8+): drive `stages` from GET /status `nodes_completed` once that
// endpoint exists, instead of a prop the caller hardcodes.
export type SaduStageState = "done" | "active" | "pending";

interface Props {
  stages: SaduStageState[];
  className?: string;
}

const STAGE_WIDTH = 64;
const STAGE_GAP = 12;

function Stage({ state, x }: { state: SaduStageState; x: number }) {
  if (state === "done") {
    return <path d={`M${x} 44 L${x + 32} 8 L${x + 64} 44 Z`} fill="var(--accent)" />;
  }
  if (state === "active") {
    return (
      <>
        <path
          d={`M${x} 44 L${x + 32} 8 L${x + 64} 44 Z`}
          fill="none"
          stroke="var(--accent)"
          strokeWidth="2"
        />
        <path d={`M${x + 16} 44 L${x + 32} 26 L${x + 48} 44 Z`} fill="var(--accent)" />
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

export default function SaduBand({ stages, className }: Props) {
  const width = stages.length * STAGE_WIDTH + Math.max(0, stages.length - 1) * STAGE_GAP;
  return (
    <svg
      viewBox={`0 0 ${width} 52`}
      width={width}
      height="52"
      role="img"
      aria-label="Pipeline progress"
      className={["motion-reduce:transition-none", className].filter(Boolean).join(" ")}
    >
      {stages.map((state, i) => (
        <Stage key={i} state={state} x={i * (STAGE_WIDTH + STAGE_GAP)} />
      ))}
    </svg>
  );
}
