// Shared segmented control (mocks: `.segset` in jadwa_sme_settings.html, `.toggle`
// in every header). Generic over the option value type so callers get type
// safety (e.g. Lang, Theme) without redeclaring the visual pattern each time.
export interface SegmentedOption<T extends string> {
  value: T;
  label: string;
}

export interface SegmentedControlProps<T extends string> {
  options: SegmentedOption<T>[];
  value: T;
  onChange: (next: T) => void;
  ariaLabel: string;
  className?: string;
}

export default function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  ariaLabel,
  className,
}: SegmentedControlProps<T>) {
  return (
    <div
      role="radiogroup"
      aria-label={ariaLabel}
      className={[
        "inline-flex overflow-hidden rounded-lg border border-line-strong",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {options.map((opt, i) => {
        const isActive = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={isActive}
            onClick={() => onChange(opt.value)}
            className={[
              "px-4 py-2 text-label font-semibold transition-colors motion-reduce:transition-none",
              "focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-inset",
              i > 0 && "border-s border-line-strong",
              isActive ? "bg-accent text-on-accent" : "bg-transparent text-text-2 hover:bg-surface-2",
            ]
              .filter(Boolean)
              .join(" ")}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
