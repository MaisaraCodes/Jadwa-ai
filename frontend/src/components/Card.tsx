// Shared Card primitive (DESIGN_SYSTEM.md §8.2). Plain card, or a report card
// with a forensic-status edge on the START side (logical — mirrors under RTL
// automatically). Edge colour is always the card's forensic status: pass,
// review, or flag — never a decorative choice.
import { forwardRef, type HTMLAttributes } from "react";

export type CardEdge = "pass" | "review" | "flag";

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  edge?: CardEdge;
}

const EDGE_CLASSES: Record<CardEdge, string> = {
  pass: "border-s-pass",
  review: "border-s-review",
  flag: "border-s-flag",
};

// forwardRef so callers can attach the useReveal() entrance observer (or any
// other ref) directly to the card's own element — no extra wrapper div.
const Card = forwardRef<HTMLDivElement, CardProps>(function Card({ edge, className, ...props }, ref) {
  return (
    <div
      ref={ref}
      className={[
        "rounded-xl border border-line bg-surface p-4 transition-[border-color,box-shadow] duration-base ease-out motion-reduce:transition-none",
        edge && `rounded-s-none border-s-[3px] ${EDGE_CLASSES[edge]}`,
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      {...props}
    />
  );
});

export default Card;
