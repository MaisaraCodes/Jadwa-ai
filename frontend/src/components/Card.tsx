// Shared Card primitive (DESIGN_SYSTEM.md §8.2). Plain card, or a report card
// with a forensic-status edge on the START side (logical — mirrors under RTL
// automatically). Edge colour is always the card's forensic status: pass,
// review, or flag — never a decorative choice.
import type { HTMLAttributes } from "react";

export type CardEdge = "pass" | "review" | "flag";

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  edge?: CardEdge;
}

const EDGE_CLASSES: Record<CardEdge, string> = {
  pass: "border-s-pass",
  review: "border-s-review",
  flag: "border-s-flag",
};

export default function Card({ edge, className, ...props }: CardProps) {
  return (
    <div
      className={[
        "rounded-xl border border-line bg-surface p-4",
        edge && `rounded-s-none border-s-[3px] ${EDGE_CLASSES[edge]}`,
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      {...props}
    />
  );
}
