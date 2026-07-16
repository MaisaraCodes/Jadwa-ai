// Motion foundation (DESIGN_SYSTEM.md §8/§10) — the one place entrance
// animation behavior is decided. `useReveal` pairs with the `.reveal`
// utility (index.css): it flips `data-revealed` once an element scrolls
// into view, or immediately when reduced-motion / IntersectionObserver
// support says to skip the wait — so nothing ever stays invisible.
import { useEffect, useRef, useState, type RefObject } from "react";

export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(
    () => typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );

  useEffect(() => {
    const mql = window.matchMedia("(prefers-reduced-motion: reduce)");
    const onChange = () => setReduced(mql.matches);
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, []);

  return reduced;
}

export function useReveal<T extends HTMLElement>(): { ref: RefObject<T>; revealed: boolean } {
  const ref = useRef<T>(null);
  const [revealed, setRevealed] = useState(false);
  const reducedMotion = usePrefersReducedMotion();

  useEffect(() => {
    if (reducedMotion) {
      setRevealed(true);
      return;
    }
    const el = ref.current;
    if (!el || typeof IntersectionObserver === "undefined") {
      setRevealed(true);
      return;
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setRevealed(true);
          observer.disconnect();
        }
      },
      { threshold: 0.15, rootMargin: "0px 0px -10% 0px" },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [reducedMotion]);

  return { ref, revealed };
}

// Stagger helper for list/card entrances — caps the delay so a long list
// finishes revealing quickly instead of trickling in one row at a time.
const STAGGER_STEP_MS = 45;
const STAGGER_MAX_STEPS = 8;

export function staggerDelayMs(index: number): number {
  return Math.min(index, STAGGER_MAX_STEPS) * STAGGER_STEP_MS;
}
