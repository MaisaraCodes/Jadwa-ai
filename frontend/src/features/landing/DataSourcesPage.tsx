// Public data-sources / credibility page ("/data") — pre-portal, same core +
// gold tokens as LandingPage (no data-portal, no --accent). SKELETON pass
// only: structure + honest placeholders, to be filled in once the Oracle
// corpus (architecture.md's saudi_market_oracle_node) is actually ingested.
//
// FRAMING RULE: this is retrieval-augmented generation over a curated corpus
// — "grounded in", "retrieves from", "cites". Never "trained on" (nothing is
// trained or fine-tuned). No fabricated document counts or date ranges —
// every such specific here is a visible "pending ingestion" placeholder.
import { Link } from "react-router-dom";
import {
  IconArrowRight,
  IconBuildingBank,
  IconBuildingStore,
  IconChartBar,
  IconInfoCircle,
  IconPlus,
} from "@tabler/icons-react";
import { useLang } from "../../i18n/LangProvider";
import type { StringKey } from "../../i18n/strings";
import { JadwaWordmark } from "../../components/JadwaMark";
import ThemeToggle from "../../components/ThemeToggle";
import LangToggle from "../../components/LangToggle";

const CTA_LINK_CLASS =
  "focus:outline-none focus-visible:ring-2 focus-visible:ring-gold focus-visible:ring-offset-2 focus-visible:ring-offset-bg";

const RETRIEVAL_STEPS: StringKey[] = [
  "data.retrieval.step.query",
  "data.retrieval.step.embed",
  "data.retrieval.step.retrieve",
  "data.retrieval.step.cite",
];

function CoveragePendingBadge() {
  const { t } = useLang();
  return (
    <span className="inline-flex w-fit items-center gap-1.5 rounded-full border border-line bg-surface-2 px-2.5 py-0.5 text-xs font-medium text-text-2">
      {t("data.sources.coveragePending")}
    </span>
  );
}

function SourceCard({
  icon: Icon,
  nameKey,
  bodyKey,
}: {
  icon: typeof IconBuildingBank;
  nameKey: StringKey;
  bodyKey: StringKey;
}) {
  const { t } = useLang();
  return (
    <div className="flex flex-col rounded-xl border border-line bg-surface p-5">
      <Icon size={22} className="text-ink" aria-hidden="true" />
      <h3 className="mt-3 text-title text-ink">{t(nameKey)}</h3>
      <p className="mt-1.5 flex-1 text-body-sm text-text-2">{t(bodyKey)}</p>
      <div className="mt-3">
        <CoveragePendingBadge />
      </div>
    </div>
  );
}

export default function DataSourcesPage() {
  const { t, lang } = useLang();

  return (
    <div className="min-h-screen bg-bg">
      <header className="border-b border-line">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <Link to="/" className={`rounded-lg ${CTA_LINK_CLASS}`}>
            <JadwaWordmark />
          </Link>
          <div className="flex items-center gap-2.5">
            <LangToggle />
            <ThemeToggle />
            <Link
              to="/login"
              className={`rounded-lg bg-gold px-4 py-2 text-sm font-semibold text-on-gold hover:bg-gold-strong ${CTA_LINK_CLASS}`}
            >
              {t("landing.cta.getStarted")}
            </Link>
          </div>
        </div>
      </header>

      <main>
        {/* Hero */}
        <section className="mx-auto max-w-3xl px-4 py-14 text-center sm:px-6 sm:py-20">
          <h1 className="font-display text-2xl font-extrabold text-ink sm:text-display">{t("data.hero.title")}</h1>
          <p className="mx-auto mt-4 max-w-xl text-body-sm text-text-2 sm:text-body">{t("data.hero.body")}</p>
        </section>

        {/* Source category cards */}
        <section className="border-y border-line bg-surface py-14">
          <div className="mx-auto max-w-5xl px-4 sm:px-6">
            <h2 className="text-center font-display text-xl font-bold text-ink">{t("data.sources.title")}</h2>
            <p className="mx-auto mt-1.5 max-w-md text-center text-body-sm text-text-2">
              {t("data.sources.subtitle")}
            </p>

            <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <SourceCard icon={IconBuildingBank} nameKey="data.source.sama.name" bodyKey="data.source.sama.body" />
              <SourceCard
                icon={IconBuildingStore}
                nameKey="data.source.monshaat.name"
                bodyKey="data.source.monshaat.body"
              />
              <SourceCard icon={IconChartBar} nameKey="data.source.gastat.name" bodyKey="data.source.gastat.body" />

              {/* Room for more — an explicit, honest placeholder tile rather
                  than implying the 3 sources above are the full set. */}
              <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-line bg-bg p-5 text-center">
                <IconPlus size={22} className="text-text-3" aria-hidden="true" />
                <h3 className="mt-3 text-title text-text-2">{t("data.source.more.name")}</h3>
                <p className="mt-1.5 text-body-sm text-text-3">{t("data.source.more.body")}</p>
              </div>
            </div>
          </div>
        </section>

        {/* How retrieval works */}
        <section className="py-14">
          <div className="mx-auto max-w-3xl px-4 text-center sm:px-6">
            <h2 className="font-display text-xl font-bold text-ink">{t("data.retrieval.title")}</h2>
            <p className="mx-auto mt-1.5 max-w-md text-body-sm text-text-2">{t("data.retrieval.subtitle")}</p>

            <div className="mt-8 flex flex-wrap items-center justify-center gap-2 overflow-x-auto">
              {RETRIEVAL_STEPS.map((stepKey, i) => (
                <div key={stepKey} className="flex items-center gap-2">
                  <div className="rounded-lg border border-line bg-surface px-3.5 py-2 text-sm font-medium text-ink">
                    {t(stepKey)}
                  </div>
                  {i < RETRIEVAL_STEPS.length - 1 && (
                    <IconArrowRight
                      size={16}
                      className={`shrink-0 text-text-3 ${lang === "ar" ? "rotate-180" : ""}`}
                      aria-hidden="true"
                    />
                  )}
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Honesty / coverage note — plain, unstyled-as-alarm (informational, not an error) */}
        <section className="border-t border-line bg-surface-2 py-10">
          <div className="mx-auto flex max-w-2xl items-start gap-3 px-4 sm:px-6">
            <IconInfoCircle size={20} className="mt-0.5 shrink-0 text-text-2" aria-hidden="true" />
            <div>
              <h2 className="text-title text-ink">{t("data.honesty.title")}</h2>
              <p className="mt-1.5 text-body-sm text-text-2">{t("data.honesty.body")}</p>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-line py-8">
        <div className="mx-auto flex max-w-6xl flex-col items-center gap-4 px-4 sm:flex-row sm:justify-between sm:px-6">
          <JadwaWordmark />
          <Link to="/" className={`text-sm text-text-2 hover:text-ink ${CTA_LINK_CLASS}`}>
            {t("review.backLink")}
          </Link>
          <p className="text-xs text-text-3">
            {t("landing.footer.rights", { year: new Date().getFullYear() })}
          </p>
        </div>
      </footer>
    </div>
  );
}
