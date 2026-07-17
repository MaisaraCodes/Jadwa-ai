// Route-change transition — a subtle, fast fade + rise (DESIGN_SYSTEM.md §8
// motion pass, item 2). Keying a wrapper div on the current pathname forces
// React to remount it on navigation, replaying the `.page-fade` entrance
// (index.css) each time; content itself never waits on it (no delayed
// interactivity). Reduced motion disables the animation outright (.page-fade
// media query in index.css) — the wrapper is still keyed so no visual gap.
import { useLocation } from "react-router-dom";
import type { ReactNode } from "react";

export default function PageFade({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  return (
    <div key={pathname} className="page-fade">
      {children}
    </div>
  );
}
