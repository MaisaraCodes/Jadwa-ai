// Public landing page ("/") — pre-portal (DESIGN_SYSTEM.md §4.1): no
// data-portal, so only core + gold tokens are used; gold CTAs are allowed
// here (everywhere else gold is brand/verification only). RTL default via
// the global LangProvider (AR is the stored default — DESIGN_SYSTEM.md §12).
// Signed-in visitors never see this: LandingOrRedirect (features/auth/
// RequireRole.tsx) sends them straight to their portal.
import { Link } from "react-router-dom";
import { IconBuilding, IconBuildingBank } from "@tabler/icons-react";
import { useLang } from "../../i18n/LangProvider";
import type { StringKey } from "../../i18n/strings";
import { JadwaTileMark, GoldDiamond, JadwaWordmark } from "../../components/JadwaMark";
import ThemeToggle from "../../components/ThemeToggle";
import LangToggle from "../../components/LangToggle";
import SaduBand from "../../components/SaduBand";

const STAGE_LABEL_KEYS: StringKey[] = [
  "sme.home.stage.extract",
  "sme.home.stage.forensic",
  "sme.home.stage.stressTest",
  "sme.home.stage.market",
  "sme.home.stage.riskModel",
  "sme.home.stage.record",
];
const ALL_DONE = STAGE_LABEL_KEYS.map(() => "done" as const);

const CTA_LINK_CLASS =
  "focus:outline-none focus-visible:ring-2 focus-visible:ring-gold focus-visible:ring-offset-2 focus-visible:ring-offset-bg";

export default function LandingPage() {
  const { t } = useLang();

  return (
    <div className="min-h-screen bg-bg">
      <header className="border-b border-line">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <JadwaWordmark />
          <nav className="hidden items-center gap-5 text-sm text-text-2 sm:flex">
            <a href="#how-it-works" className={`hover:text-ink ${CTA_LINK_CLASS}`}>
              {t("landing.nav.howItWorks")}
            </a>
            <Link to="/data" className={`hover:text-ink ${CTA_LINK_CLASS}`}>
              {t("landing.nav.dataSources")}
            </Link>
          </nav>
          <div className="flex items-center gap-2.5">
            <LangToggle />
            <ThemeToggle />
            <Link
              to="/login"
              className={`hidden text-sm font-medium text-ink hover:underline sm:inline ${CTA_LINK_CLASS}`}
            >
              {t("login.signInCta")}
            </Link>
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
        <section className="mx-auto max-w-3xl px-4 py-16 text-center sm:px-6 sm:py-24">
          <div className="mb-6 flex justify-center">
            <JadwaTileMark size={56} />
          </div>
          <h1 className="whitespace-pre-line font-display text-display text-ink sm:text-display-xl">
            {t("login.heroHeadline")}
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-body-sm text-text-2 sm:text-body">
            {t("landing.hero.subline")}
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link
              to="/login"
              className={`rounded-lg bg-gold px-6 py-3 text-sm font-semibold text-on-gold hover:bg-gold-strong ${CTA_LINK_CLASS}`}
            >
              {t("landing.cta.getStarted")}
            </Link>
            <Link
              to="/login"
              className={`rounded-lg border border-line-strong px-6 py-3 text-sm font-medium text-ink hover:bg-surface ${CTA_LINK_CLASS}`}
            >
              {t("login.signInCta")}
            </Link>
          </div>
        </section>

        {/* Dual-audience value prop */}
        <section className="border-y border-line bg-surface py-14">
          <div className="mx-auto grid max-w-5xl grid-cols-1 gap-5 px-4 sm:grid-cols-2 sm:px-6">
            <div className="rounded-xl border border-line bg-bg p-6">
              <IconBuilding size={22} className="text-ink" aria-hidden="true" />
              <h2 className="mt-3 text-title text-ink">{t("landing.value.smeTitle")}</h2>
              <p className="mt-2 text-body-sm text-text-2">{t("landing.value.smeBody")}</p>
            </div>
            <div className="rounded-xl border border-line bg-bg p-6">
              <IconBuildingBank size={22} className="text-ink" aria-hidden="true" />
              <h2 className="mt-3 text-title text-ink">{t("landing.value.bankTitle")}</h2>
              <p className="mt-2 text-body-sm text-text-2">{t("landing.value.bankBody")}</p>
            </div>
          </div>
        </section>

        {/* How it works — Sadu band, gold tone (no portal accent pre-login) */}
        <section id="how-it-works" className="py-14">
          <div className="mx-auto max-w-3xl px-4 text-center sm:px-6">
            <h2 className="font-display text-2xl font-extrabold text-ink sm:text-display">
              {t("landing.pipeline.title")}
            </h2>
            <p className="mt-2 text-body-sm text-text-2">{t("landing.pipeline.subtitle")}</p>

            <div className="mt-8 overflow-x-auto">
              <div className="inline-block">
                <SaduBand stages={ALL_DONE} tone="gold" />
                <div className="mt-2 grid grid-cols-[repeat(6,4rem)] gap-3">
                  {STAGE_LABEL_KEYS.map((key) => (
                    <span key={key} className="text-center text-[11px] text-text-2">
                      {t(key)}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Trust / verdict moment — the one non-mark, non-CTA use of gold */}
        <section className="border-t border-line bg-gold-soft py-12">
          <div className="mx-auto max-w-2xl px-4 text-center sm:px-6">
            <div className="flex items-center justify-center gap-2">
              <GoldDiamond />
              <h2 className="font-display text-xl font-bold text-ink">{t("bank.detail.signOff")}</h2>
            </div>
            <p className="mt-3 text-body-sm text-text-2">{t("landing.trust.body")}</p>
          </div>
        </section>
      </main>

      <footer className="border-t border-line py-8">
        <div className="mx-auto flex max-w-6xl flex-col items-center gap-4 px-4 sm:flex-row sm:justify-between sm:px-6">
          <JadwaWordmark />
          <nav className="flex flex-wrap items-center justify-center gap-4 text-sm text-text-2">
            <a href="#how-it-works" className={`hover:text-ink ${CTA_LINK_CLASS}`}>
              {t("landing.nav.howItWorks")}
            </a>
            <Link to="/data" className={`hover:text-ink ${CTA_LINK_CLASS}`}>
              {t("landing.nav.dataSources")}
            </Link>
            <Link to="/login" className={`hover:text-ink ${CTA_LINK_CLASS}`}>
              {t("login.signInCta")}
            </Link>
          </nav>
          <p className="text-xs text-text-3">
            {t("landing.footer.rights", { year: new Date().getFullYear() })}
          </p>
        </div>
      </footer>
    </div>
  );
}
