// Shared status pill (DESIGN_SYSTEM.md §8.6, §9) — one component for every
// pill in the product. `tone` is the only choice callers make; pass/review/flag
// stay reserved for ForensicStatus (§4.1, one-to-one) — never repurpose them
// for lifecycle or brand meaning. `neutral` covers lifecycle states
// (draft…approved) and `accent` covers in-progress / informational states.
import type { ReactNode } from "react";

export type StatusTone = "pass" | "review" | "flag" | "neutral" | "accent";

export interface StatusPillProps {
  tone: StatusTone;
  children: ReactNode;
  /** Every mock renders the dot for every tone; set false only to match
   * DESIGN_SYSTEM.md §8.6's quiet lifecycle-pill example exactly. */
  dot?: boolean;
  className?: string;
}

const TONE_CLASSES: Record<StatusTone, string> = {
  pass: "bg-pass-bg text-pass",
  review: "bg-review-bg text-review",
  flag: "bg-flag-bg text-flag",
  neutral: "border border-line bg-surface-2 text-text-2",
  accent: "bg-accent-soft text-accent-strong",
};

const DOT_CLASSES: Record<StatusTone, string> = {
  pass: "bg-pass",
  review: "bg-review",
  flag: "bg-flag",
  neutral: "bg-text-3",
  accent: "bg-accent",
};

export default function StatusPill({ tone, children, dot = true, className }: StatusPillProps) {
  return (
    <span
      className={[
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium",
        TONE_CLASSES[tone],
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {dot && (
        <span className={["h-1.5 w-1.5 rounded-full", DOT_CLASSES[tone]].join(" ")} aria-hidden="true" />
      )}
      {children}
    </span>
  );
}
