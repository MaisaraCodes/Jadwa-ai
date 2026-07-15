// Shared toggle switch (mock: jadwa_sme_settings.html `.switch`). Thumb position
// uses a logical inset (`start-*`) rather than `translate-x`, so it mirrors
// correctly under RTL with no per-direction override. Icon-only control — the
// visible row label lives outside it, so `ariaLabel` is required (§10).
export interface SwitchProps {
  checked: boolean;
  onCheckedChange: (next: boolean) => void;
  ariaLabel: string;
  disabled?: boolean;
  className?: string;
}

export default function Switch({ checked, onCheckedChange, ariaLabel, disabled, className }: SwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={ariaLabel}
      disabled={disabled}
      onClick={() => onCheckedChange(!checked)}
      className={[
        "relative inline-flex h-[25px] w-11 flex-none items-center rounded-full transition-colors motion-reduce:transition-none",
        "focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg",
        "disabled:cursor-not-allowed disabled:opacity-50",
        checked ? "bg-accent" : "bg-line-strong",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <span
        aria-hidden="true"
        className={[
          "absolute top-[3px] h-[19px] w-[19px] rounded-full bg-white transition-[inset-inline-start] duration-150 motion-reduce:transition-none",
          checked ? "start-[22px]" : "start-[3px]",
        ].join(" ")}
      />
    </button>
  );
}
