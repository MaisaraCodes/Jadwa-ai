// Public data-sources / credibility page ("/data") — same pre-portal core +
// gold tokens and header/section rhythm as LandingPage (no data-portal, no
// --accent). SKELETON pass only: honest structure + placeholders, to be
// filled in once the Oracle corpus (architecture.md's saudi_market_oracle_node)
// is actually ingested.
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
import Eyebrow from "../../components/Eyebrow";

const FOCUS_CLASS =
  "focus:outline-none focus-visible:ring-2 focus-visible:ring-gold focus-visible:ring-offset-2 focus-visible:ring-offset-bg";

const BTN_GOLD = `inline-flex h-10 items-center rounded-lg bg-gold px-[18px] text-sm font-semibold text-on-gold hover:bg-gold-strong ${FOCUS_CLASS}`;

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
    <div className="flex flex-col rounded-2xl border border-line bg-surface p-5">
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
      <div className="h-[3px] bg-gold" />

      <header className="sticky top-0 z-20 border-b border-line bg-[color-mix(in_srgb,var(--bg)_86%,transparent)] backdrop-blur-[10px]">
        <div className="mx-auto grid max-w-[1120px] grid-cols-[1fr_auto] items-center gap-3 px-4 py-3 sm:grid-cols-[1fr_auto_1fr] sm:px-6">
          <Link to="/" className={`rounded-lg ${FOCUS_CLASS}`}>
            <JadwaWordmark markClassName="h-[26px] w-[26px]" textClassName="text-[25px]" diamondClassName="h-[11px] w-[11px]" />
          </Link>

          <nav className="col-start-3 hidden items-center justify-self-center gap-[30px] text-sm text-text-2 sm:flex">
            <Link to="/#platform" className={`hover:text-ink ${FOCUS_CLASS}`}>
              {t("landing.nav.platform")}
            </Link>
            <Link to="/#how-it-works" className={`hover:text-ink ${FOCUS_CLASS}`}>
              {t("landing.nav.howItWorks")}
            </Link>
            <span className="text-ink">{t("landing.nav.dataSources")}</span>
          </nav>

          <div className="col-start-2 flex items-center justify-self-end gap-3.5 sm:col-start-3">
            <LangToggle />
            <ThemeToggle />
            <Link to="/login?mode=signup" className={BTN_GOLD}>
              {t("landing.cta.getStarted")}
            </Link>
          </div>
        </div>
      </header>

      <main>
        {/* Hero */}
        <section className="mx-auto max-w-[800px] px-4 py-16 text-center sm:px-6 sm:py-24">
          <div className="mb-5">
            <Eyebrow>{t("data.hero.eyebrow")}</Eyebrow>
          </div>
          <h1 className="mx-auto max-w-[20ch] font-display text-[clamp(1.875rem,4vw,3.125rem)] font-extrabold leading-[1.12] text-ink">
            {t("data.hero.title")}
          </h1>
          <p className="mx-auto mt-4 max-w-[56ch] text-[17px] text-text-2 sm:text-lg">{t("data.hero.body")}</p>
        </section>

        {/* Source category cards */}
        <section className="border-t border-line">
          <div className="mx-auto max-w-[1120px] px-4 py-16 sm:px-6 sm:py-24">
            <h2 className="text-center font-display text-[clamp(1.5rem,3vw,2rem)] font-bold text-ink">
              {t("data.sources.title")}
            </h2>
            <p className="mx-auto mt-2.5 max-w-md text-center text-base text-text-2">
              {t("data.sources.subtitle")}
            </p>

            <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <SourceCard icon={IconBuildingBank} nameKey="data.source.sama.name" bodyKey="data.source.sama.body" />
              <SourceCard
                icon={IconBuildingStore}
                nameKey="data.source.monshaat.name"
                bodyKey="data.source.monshaat.body"
              />
              <SourceCard icon={IconChartBar} nameKey="data.source.gastat.name" bodyKey="data.source.gastat.body" />

              {/* Room for more — an explicit, honest placeholder tile rather
                  than implying the 3 sources above are the full set. */}
              <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-line-strong bg-bg p-5 text-center">
                <IconPlus size={22} className="text-text-3" aria-hidden="true" />
                <h3 className="mt-3 text-title text-text-2">{t("data.source.more.name")}</h3>
                <p className="mt-1.5 text-body-sm text-text-3">{t("data.source.more.body")}</p>
              </div>
            </div>
          </div>
        </section>

        {/* How retrieval works */}
        <section className="border-t border-line">
          <div className="mx-auto max-w-3xl px-4 py-16 text-center sm:px-6 sm:py-24">
            <h2 className="font-display text-[clamp(1.5rem,3vw,2rem)] font-bold text-ink">
              {t("data.retrieval.title")}
            </h2>
            <p className="mx-auto mt-2.5 max-w-md text-base text-text-2">{t("data.retrieval.subtitle")}</p>

            <div className="mt-9 flex flex-wrap items-center justify-center gap-2.5 overflow-x-auto">
              {RETRIEVAL_STEPS.map((stepKey, i) => (
                <div key={stepKey} className="flex items-center gap-2.5">
                  <div className="rounded-lg border border-line bg-surface px-4 py-2.5 text-sm font-medium text-ink">
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
        <section className="border-t border-line bg-surface-2 py-11">
          <div className="mx-auto flex max-w-2xl items-start gap-3.5 px-4 sm:px-6">
            <IconInfoCircle size={20} className="mt-0.5 shrink-0 text-text-2" aria-hidden="true" />
            <div>
              <h2 className="text-title text-ink">{t("data.honesty.title")}</h2>
              <p className="mt-1.5 text-body-sm text-text-2">{t("data.honesty.body")}</p>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-line py-9">
        <div className="mx-auto flex max-w-[1120px] flex-col items-center gap-4 px-4 sm:flex-row sm:justify-between sm:px-6">
          <JadwaWordmark markClassName="h-[22px] w-[22px]" textClassName="text-[19px]" />
          <nav className="flex flex-wrap items-center justify-center gap-6 text-sm text-text-2">
            <Link to="/#platform" className={`hover:text-ink ${FOCUS_CLASS}`}>
              {t("landing.nav.platform")}
            </Link>
            <Link to="/#how-it-works" className={`hover:text-ink ${FOCUS_CLASS}`}>
              {t("landing.nav.howItWorks")}
            </Link>
            <span className="text-ink">{t("landing.nav.dataSources")}</span>
            <Link to="/login" className={`hover:text-ink ${FOCUS_CLASS}`}>
              {t("login.signInCta")}
            </Link>
          </nav>
          <p className="text-[13px] text-text-3">{t("landing.footer.rights", { year: new Date().getFullYear() })}</p>
        </div>
      </footer>
    </div>
  );
}
