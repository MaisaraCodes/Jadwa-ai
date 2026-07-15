// Small-caps section label used across the public marketing pages (mock:
// design-mocks/jadwa_landing_redesign.html `.eyebrow`). Latin gets uppercase +
// letter-spacing; Arabic drops both and steps up a size, per DESIGN_SYSTEM.md
// §3.2 (never uppercase or letter-space Arabic — tracking breaks letter-joining).
// Base tone is gold (brand); pass tone="accent" inside a data-portal scope so
// it reads teal/blue instead (mock: `.sme-accent .eyebrow` / `.bank-accent
// .eyebrow` override the base gold to var(--sme) / var(--bank), which are
// literally the same hex values as this app's existing --accent per portal).
import type { ReactNode } from "react";
import { useLang } from "../i18n/LangProvider";

export default function Eyebrow({
  children,
  tone = "gold",
}: {
  children: ReactNode;
  tone?: "gold" | "accent";
}) {
  const { lang } = useLang();
  return (
    <span
      className={[
        "font-semibold",
        tone === "gold" ? "text-gold" : "text-accent",
        lang === "ar" ? "text-[15px]" : "text-[13px] uppercase tracking-[0.16em]",
      ].join(" ")}
    >
      {children}
    </span>
  );
}
