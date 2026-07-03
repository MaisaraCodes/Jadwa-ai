// SME home — layout/geometry matches docs/mockups/sme_portal_arabic_rtl_light.html;
// follows the GLOBAL theme + language now (no per-screen pinning).
// DEMO: application JDW-2026-0147, its stage state, and the 3 document rows are
// all hardcoded for this pass. Real data (GET /applications/:id, GET /status,
// GET /applications/:id/documents) wires in Phase 2.
import { IconFileInvoice, IconReceipt, IconFileText, IconSparkles } from "@tabler/icons-react";
import { useLang } from "../../../i18n/LangProvider";
import { STRINGS, type StringKey } from "../../../i18n/strings";
import DocumentUpload from "../DocumentUpload";

// Exact 6-stage feasibility-study Sadu band geometry from the mockup: done
// (filled), active (outline + inner triangle), pending (outline only).
// Per DESIGN_SYSTEM.md §8.9/§7: stages lay out start→end, so position is
// mirrored by `dir` while each <text> label stays upright or the text glyph
// would need to be flipped to be readable.
const STAGES = [
  { key: "sme.home.stage.extract" as StringKey, state: "done" as const },
  { key: "sme.home.stage.forensic" as StringKey, state: "done" as const },
  { key: "sme.home.stage.stressTest" as StringKey, state: "active" as const },
  { key: "sme.home.stage.market" as StringKey, state: "pending" as const },
  { key: "sme.home.stage.riskModel" as StringKey, state: "pending" as const },
  { key: "sme.home.stage.record" as StringKey, state: "pending" as const },
];

function FeasibilitySaduBand() {
  const { t, dir } = useLang();
  return (
    <svg viewBox="0 0 640 70" width="100%" height="70" aria-label={t("sme.home.stagesAriaLabel")}>
      {STAGES.map((stage, i) => {
        const x = dir === "rtl" ? 556 - i * 104 : 36 + i * 104;
        const labelColor =
          stage.state === "pending" ? "var(--text-3)" : stage.state === "active" ? "var(--accent)" : "var(--accent-strong)";
        return (
          <g key={stage.key}>
            {stage.state === "done" && <path d={`M${x} 40 L${x + 32} 6 L${x + 64} 40 Z`} fill="var(--accent)" />}
            {stage.state === "active" && (
              <>
                <path
                  d={`M${x} 40 L${x + 32} 6 L${x + 64} 40 Z`}
                  fill="none"
                  stroke="var(--accent)"
                  strokeWidth="2"
                />
                <path d={`M${x + 16} 40 L${x + 32} 23 L${x + 48} 40 Z`} fill="var(--accent)" />
              </>
            )}
            {stage.state === "pending" && (
              <path
                d={`M${x} 40 L${x + 32} 6 L${x + 64} 40 Z`}
                fill="none"
                stroke="var(--line-strong)"
                strokeWidth="2"
              />
            )}
            <text x={x + 32} y="62" textAnchor="middle" fontFamily="Alexandria" fontSize="11" fill={labelColor}>
              {t(stage.key)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function Badge({ tone, children }: { tone: "pass" | "review" | "accent"; children: string }) {
  const cls =
    tone === "pass"
      ? "bg-pass-bg text-pass"
      : tone === "review"
        ? "bg-review-bg text-review"
        : "bg-accent-soft text-accent-strong";
  const dot = tone === "pass" ? "bg-pass" : tone === "review" ? "bg-review" : "bg-accent";
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11.5px] font-medium ${cls}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${dot}`} />
      {children}
    </span>
  );
}

// DEMO document rows — real list comes from GET /applications/:id/documents (Phase 2).
const DEMO_DOCUMENTS = [
  { icon: IconFileInvoice, labelKey: "sme.home.doc.fuelInvoice" as StringKey, status: "pass" as const },
  { icon: IconReceipt, labelKey: "sme.home.doc.zatcaReceipt" as StringKey, amount: "1,500.50", status: "review" as const },
  { icon: IconFileText, labelKey: "sme.home.doc.warehouseLease" as StringKey, status: "pass" as const },
];

const APP_REF = "JDW-2026-0147";

export default function SmeHomePage() {
  const { t, lang } = useLang();
  // Split on the raw {{ref}} token (not the interpolated value) so the
  // reference number can be wrapped in its own dir="ltr" tabular-nums span.
  const [refBefore, refAfter] = STRINGS["sme.home.appStatus"][lang].split("{{ref}}");

  return (
    <section>
      <h1 className="font-display text-2xl font-extrabold text-ink">{t("sme.home.welcome")}</h1>
      <p className="mb-4 mt-0.5 text-[13px] text-text-2">
        {refBefore}
        <span dir="ltr" className="tabular-nums">
          {APP_REF}
        </span>
        {refAfter}
      </p>

      <div className="mb-3.5 rounded-xl border border-line bg-surface px-[18px] py-4">
        <div className="mb-3.5 flex items-center justify-between">
          <span className="text-sm font-semibold text-ink">{t("sme.home.stagesTitle")}</span>
          <Badge tone="accent">{t("sme.home.stagesBadge")}</Badge>
        </div>
        <FeasibilitySaduBand />
      </div>

      <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-[1fr_1.35fr]">
        <DocumentUpload applicationId="JDW-2026-0147" />

        <div className="rounded-xl border border-line bg-surface px-4 py-3.5">
          <div className="mb-2.5 text-[13.5px] font-semibold text-ink">
            {t("sme.home.documentsTitle")} <span className="font-normal text-text-3">(20)</span>
          </div>
          {DEMO_DOCUMENTS.map((doc, i) => (
            <div
              key={doc.labelKey}
              className={[
                "flex items-center justify-between py-2",
                i < DEMO_DOCUMENTS.length - 1 ? "border-b border-surface-2" : "",
              ].join(" ")}
            >
              <span className="flex items-center gap-2 text-[12.5px] text-ink">
                <doc.icon size={15} className="text-text-3" aria-hidden="true" />
                {t(doc.labelKey)}
                {doc.amount &&
                  (lang === "ar" ? (
                    <>
                      {" — "}
                      <span dir="ltr" className="tabular-nums">
                        {doc.amount}
                      </span>{" "}
                      ر.س
                    </>
                  ) : (
                    <>
                      {" — SAR "}
                      <span dir="ltr" className="tabular-nums">
                        {doc.amount}
                      </span>
                    </>
                  ))}
              </span>
              <Badge tone={doc.status}>{doc.status === "pass" ? t("sme.home.doc.matched") : t("sme.home.doc.needsReview")}</Badge>
            </div>
          ))}
          <p className="mt-3 flex items-start gap-1.5 rounded-lg bg-gold-soft px-2.5 py-2 text-[11.5px] leading-[1.7] text-text-2">
            <IconSparkles size={13} className="mt-0.5 shrink-0 text-gold-strong" aria-hidden="true" />
            {t("sme.home.tip")}
          </p>
        </div>
      </div>
    </section>
  );
}
