// On-brand loading placeholder (DESIGN_SYSTEM.md §8 motion pass, item 5) —
// replaces bare spinners on list/detail data fetches. `.skeleton` (index.css)
// supplies the gradient; `animate-shimmer` (tailwind.config.js) sweeps it.
// prefers-reduced-motion collapses both to a flat, static fill.
import type { HTMLAttributes } from "react";

export default function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      aria-hidden="true"
      className={["skeleton animate-shimmer rounded-lg motion-reduce:animate-none", className]
        .filter(Boolean)
        .join(" ")}
      {...props}
    />
  );
}
