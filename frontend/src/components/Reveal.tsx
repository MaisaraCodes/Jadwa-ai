// Generic scroll/mount entrance wrapper — fade + small rise via the `.reveal`
// utility (index.css) and useReveal() (lib/motion.ts). For block-level spots
// where an extra wrapper div is layout-safe (landing sections, standalone
// cards). Table rows and other structurally-constrained elements should call
// useReveal() directly instead of wrapping — see BankQueuePage's QueueRow.
import type { HTMLAttributes } from "react";
import { useReveal, staggerDelayMs } from "../lib/motion";

export interface RevealProps extends HTMLAttributes<HTMLDivElement> {
  /** Position in a list — adds a capped stagger delay so entrances read as a
   * sequence instead of firing all at once. Omit for a single element. */
  index?: number;
}

export default function Reveal({ index, className, style, children, ...props }: RevealProps) {
  const { ref, revealed } = useReveal<HTMLDivElement>();
  return (
    <div
      ref={ref}
      data-revealed={revealed}
      // .reveal (index.css) only sets the opacity/transform VALUES — it
      // deliberately doesn't declare `transition` itself (see index.css's
      // comment on why), so this is the one place that must supply the
      // property list. Card.tsx does the same for its own .reveal usage.
      className={["reveal transition-[opacity,transform] duration-base ease-out motion-reduce:transition-none", className]
        .filter(Boolean)
        .join(" ")}
      style={index !== undefined ? { transitionDelay: `${staggerDelayMs(index)}ms`, ...style } : style}
      {...props}
    >
      {children}
    </div>
  );
}
