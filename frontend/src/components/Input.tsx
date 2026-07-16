// Shared text input (DESIGN_SYSTEM.md §8.4). Label + hint are optional so the
// same primitive covers a bare input and a fully-labelled field.
import { forwardRef, useId, type InputHTMLAttributes, type ReactNode } from "react";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: ReactNode;
  hint?: ReactNode;
}

const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, hint, id, className, ...props },
  ref,
) {
  const generatedId = useId();
  const inputId = id ?? generatedId;

  const input = (
    <input
      ref={ref}
      id={inputId}
      className={[
        "h-11 w-full rounded-lg border border-line-strong bg-surface px-3 text-sm text-ink",
        "placeholder:text-text-3",
        "focus:outline-none focus-visible:border-accent focus-visible:ring-2 focus-visible:ring-accent/30",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      {...props}
    />
  );

  if (!label && !hint) return input;

  return (
    <div>
      {label && (
        <label htmlFor={inputId} className="mb-1.5 block text-label text-text-2">
          {label}
        </label>
      )}
      {input}
      {hint && <p className="mt-1.5 text-xs text-text-3">{hint}</p>}
    </div>
  );
});

export default Input;
