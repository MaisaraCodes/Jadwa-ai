// Shared metric tile (DESIGN_SYSTEM.md §8.3) — a label over a value. The value
// slot is generic `children` (not a forced number), since bank metrics mix
// tabular figures (e.g. reconciliation "17/20") and status pills (e.g. sector
// trend, risk class) in the same tile shape.
import type { HTMLAttributes, ReactNode } from "react";

export interface MetricTileProps extends HTMLAttributes<HTMLDivElement> {
  label: ReactNode;
  children: ReactNode;
}

export default function MetricTile({ label, children, className, ...props }: MetricTileProps) {
  return (
    <div className={["rounded-xl bg-surface-2 p-3.5", className].filter(Boolean).join(" ")} {...props}>
      <div className="text-xs font-medium text-text-3">{label}</div>
      <div className="mt-1">{children}</div>
    </div>
  );
}
