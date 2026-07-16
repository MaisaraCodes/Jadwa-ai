// Shared back control (DESIGN_SYSTEM.md §8.1 tertiary style) — the one
// component every flow page (a page reached by navigating deeper, never a
// portal's top-level page) uses to return to its parent. Chevron sits on the
// logical start side and mirrors in RTL; never render this on a portal's
// top-level page (SME dashboard, bank queue).
import { Link } from "react-router-dom";
import { IconArrowLeft } from "@tabler/icons-react";
import { useLang } from "../i18n/LangProvider";

interface BackButtonProps {
  to: string;
  label: string;
  className?: string;
}

export default function BackButton({ to, label, className = "mb-4" }: BackButtonProps) {
  const { lang } = useLang();
  return (
    <Link
      to={to}
      aria-label={label}
      className={`inline-flex items-center gap-1.5 text-sm font-medium text-accent hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-accent ${className}`}
    >
      <IconArrowLeft size={14} className={lang === "ar" ? "rotate-180" : ""} aria-hidden="true" />
      {label}
    </Link>
  );
}
