// Public landing page ("/") — pre-portal (DESIGN_SYSTEM.md §4.1): no ambient
// data-portal, so only core + gold tokens apply at the page level; gold CTAs
// are allowed here (everywhere else gold is brand/verification only). RTL
// default via the global LangProvider (AR is the stored default — §12).
// Signed-in visitors never see this: LandingOrRedirect (features/auth/
// RequireRole.tsx) sends them straight to their portal — untouched by this page.
//
// Visual + copy source of truth: design-mocks/jadwa_landing_redesign.html.
// The two dual-audience sections wrap themselves in data-portal="sme"/"bank"
// purely to borrow the existing --accent scoping (§6) for their eyebrow/
// checklist colour — not a claim that the visitor is inside that portal.
import { Link } from "react-router-dom";
import { IconArrowRight } from "@tabler/icons-react";
import { useLang } from "../../i18n/LangProvider";
import type { StringKey } from "../../i18n/strings";
import { GoldDiamond, JadwaWordmark } from "../../components/JadwaMark";
import ThemeToggle from "../../components/ThemeToggle";
import LangToggle from "../../components/LangToggle";
import SaduBand from "../../components/SaduBand";
import Eyebrow from "../../components/Eyebrow";

const STAGE_LABEL_KEYS: StringKey[] = [
  "landing.stage.extract",
  "landing.stage.forensic",
  "landing.stage.stressTest",
  "landing.stage.market",
  "landing.stage.riskModel",
  "landing.stage.record",
];
const ALL_DONE = STAGE_LABEL_KEYS.map(() => "done" as const);

const FOCUS_CLASS =
  "focus:outline-none focus-visible:ring-2 focus-visible:ring-gold focus-visible:ring-offset-2 focus-visible:ring-offset-bg";

const BTN_GOLD = `inline-flex items-center rounded-lg bg-gold px-[18px] font-semibold text-on-gold hover:bg-gold-strong ${FOCUS_CLASS}`;
const BTN_GHOST = `inline-flex items-center rounded-lg border border-line-strong px-[18px] font-medium text-ink hover:bg-surface-2 ${FOCUS_CLASS}`;

function TrustChip({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-[7px] rounded-full border border-line px-[15px] py-[7px] text-[13px] text-text-2 before:h-[5px] before:w-[5px] before:rounded-full before:bg-gold">
      {children}
    </span>
  );
}

function CheckItem({ children }: { children: React.ReactNode }) {
  return (
    <li className="flex items-start gap-3.5 border-b border-line py-5 text-base text-ink last:border-b-0">
      <span className="mt-px flex h-[26px] w-[26px] flex-none items-center justify-center rounded-lg bg-accent-soft text-sm text-accent">
        ✓
      </span>
      {children}
    </li>
  );
}

function LinkGo({ to, children }: { to: string; children: React.ReactNode }) {
  const { lang } = useLang();
  return (
    <Link
      to={to}
      className={`inline-flex items-center gap-[7px] text-[15px] font-semibold text-accent hover:underline ${FOCUS_CLASS}`}
    >
      {children}
      <IconArrowRight size={16} className={lang === "ar" ? "rotate-180" : ""} aria-hidden="true" />
    </Link>
  );
}

export default function LandingPage() {
  const { t, lang } = useLang();
  const heroLeading = lang === "ar" ? "leading-[1.14]" : "leading-[1.04] tracking-[-0.015em]";

  return (
    <div className="min-h-screen bg-bg">
      <div className="h-[3px] bg-gold" />

      <header className="sticky top-0 z-20 border-b border-line bg-[color-mix(in_srgb,var(--bg)_86%,transparent)] backdrop-blur-[10px]">
        <div className="mx-auto grid max-w-[1120px] grid-cols-[1fr_auto] items-center gap-3 px-4 py-3 sm:grid-cols-[1fr_auto_1fr] sm:px-6">
          <Link to="/" className={`rounded-lg ${FOCUS_CLASS}`}>
            <JadwaWordmark markClassName="h-[26px] w-[26px]" textClassName="text-[25px]" diamondClassName="h-[11px] w-[11px]" />
          </Link>

          <nav className="col-start-3 hidden items-center justify-self-center gap-[30px] text-sm text-text-2 sm:flex">
            <a href="#platform" className={`hover:text-ink ${FOCUS_CLASS}`}>
              {t("landing.nav.platform")}
            </a>
            <a href="#how-it-works" className={`hover:text-ink ${FOCUS_CLASS}`}>
              {t("landing.nav.howItWorks")}
            </a>
            <Link to="/data" className={`hover:text-ink ${FOCUS_CLASS}`}>
              {t("landing.nav.dataSources")}
            </Link>
          </nav>

          <div className="col-start-2 flex items-center justify-self-end gap-3.5 sm:col-start-3">
            <LangToggle />
            <ThemeToggle />
            <Link to="/login?mode=signup" className={`${BTN_GOLD} h-10 text-sm`}>
              {t("landing.cta.getStarted")}
            </Link>
          </div>
        </div>
      </header>

      <main>
        {/* Hero */}
        <section className="mx-auto max-w-3xl px-4 py-16 text-center sm:px-6 sm:py-24">
          <div className="mb-6">
            <Eyebrow>{t("landing.hero.eyebrow")}</Eyebrow>
          </div>
          <h1 className={`mx-auto max-w-[15ch] font-display text-[clamp(2.625rem,6.6vw,5.125rem)] font-extrabold text-ink ${heroLeading}`}>
            {t("landing.hero.title")}
            <GoldDiamond className="ms-[0.14em] inline-block h-[0.4em] w-[0.4em] -translate-y-[0.32em]" />
          </h1>
          <p className="mx-auto mt-4 max-w-[56ch] text-[clamp(1.0625rem,2vw,1.25rem)] text-text-2">
            {t("landing.hero.body")}
          </p>
          <div className="mt-10 flex flex-wrap items-center justify-center gap-3.5">
            <Link to="/login?mode=signup" className={`${BTN_GOLD} h-[54px] text-base`}>
              {t("landing.hero.cta")}
            </Link>
            <Link to="/login" className={`${BTN_GHOST} h-[54px] text-base`}>
              {t("login.signInCta")}
            </Link>
          </div>
          <div className="mt-11 flex flex-wrap justify-center gap-2.5">
            <TrustChip>{t("landing.trust.chip.zatca")}</TrustChip>
            <TrustChip>{t("landing.trust.chip.bilingual")}</TrustChip>
            <TrustChip>{t("landing.trust.chip.data")}</TrustChip>
          </div>
        </section>

        {/* The platform */}
        <section id="platform" className="border-t border-line">
          <div className="mx-auto max-w-[800px] px-4 py-16 text-center sm:px-6 sm:py-24">
            <div className="mb-5 block">
              <Eyebrow>{t("landing.platform.eyebrow")}</Eyebrow>
            </div>
            <h2 className="mx-auto max-w-[20ch] font-display text-[clamp(1.875rem,4vw,3.125rem)] font-extrabold leading-[1.12] text-ink">
              {t("landing.platform.title")}
            </h2>
            <p className="mt-[22px] text-lg text-text-2">{t("landing.platform.body1")}</p>
            <p className="mt-[22px] text-lg text-text-2">
              <b className="font-semibold text-ink">{t("landing.platform.body2Lead")}</b>
              {t("landing.platform.body2Rest")}
            </p>
          </div>
        </section>

        {/* How it works — Sadu band, gold tone (no portal accent pre-login) */}
        <section id="how-it-works" className="border-t border-line py-16 sm:py-24">
          <div className="mx-auto max-w-3xl px-4 text-center sm:px-6">
            <svg
              className="mb-11 h-3.5 w-full opacity-90"
              viewBox="0 0 1200 20"
              preserveAspectRatio="none"
              aria-hidden="true"
            >
              <path
                d="M0 18 L30 4 L60 18 L90 4 L120 18 L150 4 L180 18 L210 4 L240 18 L270 4 L300 18 L330 4 L360 18 L390 4 L420 18 L450 4 L480 18 L510 4 L540 18 L570 4 L600 18 L630 4 L660 18 L690 4 L720 18 L750 4 L780 18 L810 4 L840 18 L870 4 L900 18 L930 4 L960 18 L990 4 L1020 18 L1050 4 L1080 18 L1110 4 L1140 18 L1170 4 L1200 18"
                fill="none"
                stroke="var(--gold)"
                strokeWidth="1.5"
              />
            </svg>

            <h2 className="font-display text-[clamp(1.75rem,3.6vw,2.5rem)] font-extrabold text-ink">
              {t("landing.pipeline.title")}
            </h2>
            <p className="mt-2.5 text-base text-text-2">{t("landing.pipeline.subtitle")}</p>

            <div className="mt-9 overflow-x-auto">
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

        {/* For business owners */}
        <section data-portal="sme" className="border-t border-line">
          <div className="mx-auto grid max-w-[1120px] grid-cols-1 items-center gap-8 px-4 py-16 sm:px-6 sm:py-24 md:grid-cols-[1.05fr_0.95fr] md:gap-16">
            <div>
              <div className="mb-[18px] block">
                <Eyebrow tone="accent">{t("landing.sme.eyebrow")}</Eyebrow>
              </div>
              <h2 className="mb-6 font-display text-[clamp(1.75rem,3.6vw,2.75rem)] font-extrabold leading-[1.14] text-ink">
                {t("landing.sme.title")}
              </h2>
              <p className="mb-7 text-[17px] text-text-2">{t("landing.sme.body")}</p>
              <LinkGo to="/login?mode=signup">{t("landing.sme.cta")}</LinkGo>
            </div>
            <div className="rounded-2xl border border-line bg-surface px-[30px] py-3">
              <ul>
                <CheckItem>{t("landing.sme.check1")}</CheckItem>
                <CheckItem>{t("landing.sme.check2")}</CheckItem>
                <CheckItem>{t("landing.sme.check3")}</CheckItem>
                <CheckItem>{t("landing.sme.check4")}</CheckItem>
              </ul>
            </div>
          </div>
        </section>

        {/* For banks */}
        <section data-portal="bank" className="border-t border-line">
          <div className="mx-auto grid max-w-[1120px] grid-cols-1 items-center gap-8 px-4 py-16 sm:px-6 sm:py-24 md:grid-cols-[0.95fr_1.05fr] md:gap-16">
            <div className="order-none md:order-last">
              <div className="mb-[18px] block">
                <Eyebrow tone="accent">{t("landing.bank.eyebrow")}</Eyebrow>
              </div>
              <h2 className="mb-6 font-display text-[clamp(1.75rem,3.6vw,2.75rem)] font-extrabold leading-[1.14] text-ink">
                {t("landing.bank.title")}
              </h2>
              <p className="mb-7 text-[17px] text-text-2">{t("landing.bank.body")}</p>
              <LinkGo to="/login">{t("landing.bank.cta")}</LinkGo>
            </div>
            <div className="rounded-2xl border border-line bg-surface px-[30px] py-3 md:order-first">
              <ul>
                <CheckItem>{t("landing.bank.check1")}</CheckItem>
                <CheckItem>{t("landing.bank.check2")}</CheckItem>
                <CheckItem>{t("landing.bank.check3")}</CheckItem>
                <CheckItem>{t("landing.bank.check4")}</CheckItem>
              </ul>
            </div>
          </div>
        </section>

        {/* Trust / verdict moment — the one non-mark, non-CTA use of gold */}
        <section className="border-y border-[color-mix(in_srgb,var(--gold)_34%,transparent)] bg-gold-soft py-[60px]">
          <div className="mx-auto max-w-2xl px-4 text-center sm:px-6">
            <div className="flex items-center justify-center gap-3">
              <GoldDiamond className="h-[17px] w-[17px]" />
              <span className="font-display text-[clamp(1.5rem,3.2vw,2.125rem)] font-extrabold text-ink">
                {t("landing.verdict.line")}
              </span>
            </div>
            <p className="mx-auto mt-4 max-w-[60ch] text-base text-text-2">{t("landing.trust.body")}</p>
          </div>
        </section>

        {/* Closing */}
        <section className="py-[100px] text-center">
          <div className="mx-auto max-w-[800px] px-4 sm:px-6">
            <h2 className="mb-[18px] font-display text-[clamp(1.875rem,4vw,3rem)] font-extrabold text-ink">
              {t("landing.closing.title")}
            </h2>
            <p className="mb-[34px] text-lg text-text-2">{t("landing.closing.body")}</p>
            <div className="flex flex-wrap items-center justify-center gap-3.5">
              <Link to="/login?mode=signup" className={`${BTN_GOLD} h-[54px] text-base`}>
                {t("landing.cta.getStarted")}
              </Link>
              <Link to="/login" className={`${BTN_GHOST} h-[54px] text-base`}>
                {t("login.signInCta")}
              </Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-line py-9">
        <div className="mx-auto flex max-w-[1120px] flex-col items-center gap-4 px-4 sm:flex-row sm:justify-between sm:px-6">
          <JadwaWordmark markClassName="h-[22px] w-[22px]" textClassName="text-[19px]" />
          <nav className="flex flex-wrap items-center justify-center gap-6 text-sm text-text-2">
            <a href="#platform" className={`hover:text-ink ${FOCUS_CLASS}`}>
              {t("landing.nav.platform")}
            </a>
            <a href="#how-it-works" className={`hover:text-ink ${FOCUS_CLASS}`}>
              {t("landing.nav.howItWorks")}
            </a>
            <Link to="/data" className={`hover:text-ink ${FOCUS_CLASS}`}>
              {t("landing.nav.dataSources")}
            </Link>
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
