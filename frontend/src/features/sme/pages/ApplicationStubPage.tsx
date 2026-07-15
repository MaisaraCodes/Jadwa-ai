// SME portal — placeholder for /sme/applications/new and /sme/applications/:id.
// Deliberately empty: Prompt 2 fills these in. Not wired to any endpoint.
import { Link } from "react-router-dom";
import { IconArrowLeft } from "@tabler/icons-react";
import { useLang } from "../../../i18n/LangProvider";
import type { StringKey } from "../../../i18n/strings";

export default function ApplicationStubPage({ titleKey }: { titleKey: StringKey }) {
  const { t, lang } = useLang();

  return (
    <section>
      <Link
        to="/sme"
        className="mb-3 inline-flex items-center gap-1.5 text-[12.5px] font-medium text-text-2 hover:text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
      >
        <IconArrowLeft size={14} className={lang === "ar" ? "rotate-180" : ""} aria-hidden="true" />
        {t("review.backLink")}
      </Link>

      <div className="rounded-xl border border-line bg-surface px-4 py-10 text-center">
        <h1 className="font-display text-xl font-extrabold text-ink">{t(titleKey)}</h1>
        <p className="mt-1.5 text-[13px] text-text-2">{t("sme.stub.comingNextBody")}</p>
      </div>
    </section>
  );
}
