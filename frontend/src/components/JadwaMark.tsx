// Bare brand mark (DESIGN_SYSTEM.md §2.2) — inline next to the wordmark.
// Letterform inherits currentColor (set `text-ink` or similar on the wrapper);
// the diamond dot stays gold in both themes.
interface Props {
  className?: string;
}

export default function JadwaMark({ className }: Props) {
  return (
    <svg
      viewBox="0 0 100 100"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      className={className}
    >
      <rect x="22" y="24" width="56" height="13" fill="currentColor" />
      <rect x="65" y="37" width="13" height="28" fill="currentColor" />
      <rect x="10" y="52" width="68" height="13" fill="currentColor" />
      <path d="M38 38.5 L43.5 44.5 L38 50.5 L32.5 44.5 Z" fill="var(--gold)" />
    </svg>
  );
}

// Canonical tile mark (§2.1) — self-contained, fixed ivory letterform + gold
// diamond. Used in portal headers (mockups keep this fixed even in a light
// portal); `tileFill` may be a token so the tile itself can still adapt where
// a mockup calls for it (e.g. the bank header uses var(--surface-2)).
export function JadwaTileMark({
  className,
  size = 26,
  tileFill = "#0F1B16",
}: {
  className?: string;
  size?: number;
  tileFill?: string;
}) {
  return (
    <svg viewBox="0 0 100 100" width={size} height={size} aria-hidden="true" className={className}>
      <rect width="100" height="100" rx="24" fill={tileFill} />
      <rect x="22" y="24" width="56" height="13" fill="#F1EDE1" />
      <rect x="65" y="37" width="13" height="28" fill="#F1EDE1" />
      <rect x="10" y="52" width="68" height="13" fill="#F1EDE1" />
      <path d="M38 38.5 L43.5 44.5 L38 50.5 L32.5 44.5 Z" fill="#D6B36A" />
    </svg>
  );
}

// Gold diamond terminal (§2.3) — every wordmark lockup ends with this. 14px viewBox.
export function GoldDiamond({ className = "h-[13px] w-[13px]" }: { className?: string }) {
  return (
    <svg viewBox="0 0 14 14" aria-hidden="true" className={className}>
      <path d="M7 0.5 L13.5 7 L7 13.5 L0.5 7 Z" fill="#D6B36A" />
    </svg>
  );
}

// Full lockup: mark + "Jadwa" wordmark (live text, Zain) + gold diamond terminal.
export function JadwaWordmark({ className }: { className?: string }) {
  return (
    <span className={["inline-flex items-center gap-1.5 text-ink", className].filter(Boolean).join(" ")}>
      <JadwaMark className="h-5 w-5" />
      <span className="font-display text-base font-extrabold">Jadwa</span>
      <GoldDiamond />
    </span>
  );
}
