// Shared textarea (DESIGN_SYSTEM.md §8.4) — same field shell as Input/Select.
import { forwardRef, useId, type ReactNode, type TextareaHTMLAttributes } from "react";

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: ReactNode;
  hint?: ReactNode;
}

const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { label, hint, id, className, rows = 3, ...props },
  ref,
) {
  const generatedId = useId();
  const textareaId = id ?? generatedId;

  const textarea = (
    <textarea
      ref={ref}
      id={textareaId}
      rows={rows}
      className={[
        "min-h-[88px] w-full resize-y rounded-lg border border-line-strong bg-surface px-3 py-3 text-sm text-ink",
        "placeholder:text-text-3",
        "focus:outline-none focus-visible:border-accent focus-visible:ring-2 focus-visible:ring-accent/30",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      {...props}
    />
  );

  if (!label && !hint) return textarea;

  return (
    <div>
      {label && (
        <label htmlFor={textareaId} className="mb-1.5 block text-label text-text-2">
          {label}
        </label>
      )}
      {textarea}
      {hint && <p className="mt-1.5 text-xs text-text-3">{hint}</p>}
    </div>
  );
});

export default Textarea;
