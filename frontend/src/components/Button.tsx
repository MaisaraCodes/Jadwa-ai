// Shared Button primitive (DESIGN_SYSTEM.md §8.1). One component, four semantic
// variants, three sizes — authored once, correct across both portals and both
// themes because every variant resolves against semantic tokens only (§6
// one-component rule). `gold` stays rare per §4.1 (verification/brand moments,
// pre-portal CTAs) — never a generic in-portal action.
import { forwardRef, type ButtonHTMLAttributes } from "react";

export type ButtonVariant = "accent" | "ghost" | "danger" | "gold";
export type ButtonSize = "sm" | "md" | "lg";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  accent: "bg-accent text-on-accent hover:bg-accent-strong focus-visible:ring-accent",
  ghost: "bg-transparent text-ink border border-line-strong hover:bg-surface-2 focus-visible:ring-accent",
  danger: "bg-transparent text-flag border border-flag/40 hover:bg-flag-bg focus-visible:ring-flag",
  gold: "bg-gold text-on-gold hover:bg-gold-strong focus-visible:ring-gold",
};

const SIZE_CLASSES: Record<ButtonSize, string> = {
  sm: "h-8 gap-1.5 px-3 text-xs",
  md: "h-10 gap-2 px-5 text-sm",
  lg: "h-12 gap-2 px-7 text-base",
};

const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "accent", size = "md", className, type = "button", ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={[
        // Explicit property list (not transition-colors) so the disabled-state
        // opacity change (DESIGN_SYSTEM.md motion pass item 6, "smooth the
        // decision-bar disabling") animates too, not just color/background/border.
        "inline-flex items-center justify-center rounded-lg font-medium transition-[color,background-color,border-color,opacity] duration-base ease-out motion-reduce:transition-none",
        "disabled:cursor-not-allowed disabled:opacity-50",
        "focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-bg",
        SIZE_CLASSES[size],
        VARIANT_CLASSES[variant],
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      {...props}
    />
  );
});

export default Button;
