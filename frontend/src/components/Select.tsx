// Shared select (DESIGN_SYSTEM.md §8.4) — same field shell as Input/Textarea.
import { forwardRef, useId, type ReactNode, type SelectHTMLAttributes } from "react";

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: ReactNode;
  hint?: ReactNode;
}

const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { label, hint, id, className, children, ...props },
  ref,
) {
  const generatedId = useId();
  const selectId = id ?? generatedId;

  const select = (
    <select
      ref={ref}
      id={selectId}
      className={[
        "h-11 w-full rounded-lg border border-line-strong bg-surface px-3 text-sm text-ink",
        "focus:outline-none focus-visible:border-accent focus-visible:ring-2 focus-visible:ring-accent/30",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      {...props}
    >
      {children}
    </select>
  );

  if (!label && !hint) return select;

  return (
    <div>
      {label && (
        <label htmlFor={selectId} className="mb-1.5 block text-label text-text-2">
          {label}
        </label>
      )}
      {select}
      {hint && <p className="mt-1.5 text-xs text-text-3">{hint}</p>}
    </div>
  );
});

export default Select;
