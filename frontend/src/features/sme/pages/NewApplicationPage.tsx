// SME portal — NewApplicationPage (/sme/applications/new). Layout matches
// design-mocks/jadwa_sme_screens.html "New application": a 4-step journey
// stepper (Details active), a form card, and a "what happens next" aside.
//
// POST /applications is the ONLY real call here (routers/applications.py) —
// it creates a draft application, then this page hands off to the detail
// spine which owns document upload + analysis + review + submit.
//
// PENDING BACKEND: amount, term, purpose, and description have no home on
// the application yet (POST /applications only returns application_id +
// status). They're captured in local state for the form to feel complete,
// but never sent — createApplication() is called with no arguments. The
// "confirm your business" card reads GET /me for whatever's real (display
// name); the richer SMEProfile fields (company name, CR number, sector,
// district) have no endpoint at all yet, so that card shows a clear pending
// note instead of a fabricated business name.
import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useLang } from "../../../i18n/LangProvider";
import type { StringKey } from "../../../i18n/strings";
import { ApiError, createApplication, getMe } from "../../../lib/api";
import Button from "../../../components/Button";
import Select from "../../../components/Select";
import Textarea from "../../../components/Textarea";
import BackButton from "../../../components/BackButton";

type StepId = "details" | "documents" | "review" | "submit";
const STEPS: { id: StepId; labelKey: StringKey }[] = [
  { id: "details", labelKey: "sme.new.step.details" },
  { id: "documents", labelKey: "sme.new.step.documents" },
  { id: "review", labelKey: "sme.new.step.review" },
  { id: "submit", labelKey: "sme.new.step.submit" },
];

const TERM_OPTIONS = ["6", "12", "24", "36"] as const;
const PURPOSE_OPTIONS = ["workingCapital", "equipment", "inventory", "expansion", "other"] as const;

function Stepper({ activeId }: { activeId: StepId }) {
  const { t } = useLang();
  const activeIndex = STEPS.findIndex((s) => s.id === activeId);
  return (
    <div className="mb-8 flex items-center gap-2">
      {STEPS.map((step, i) => {
        const isActive = i === activeIndex;
        return (
          <div key={step.id} className="flex items-center gap-2">
            {i > 0 && <span className="h-px w-6 bg-line-strong" />}
            <div className={["flex items-center gap-2 text-sm font-medium", isActive ? "text-ink" : "text-text-3"].join(" ")}>
              <span
                className={[
                  "flex h-[26px] w-[26px] items-center justify-center rounded-full border text-[13px]",
                  isActive ? "border-accent bg-accent text-on-accent" : "border-line-strong",
                ].join(" ")}
              >
                {i + 1}
              </span>
              {t(step.labelKey)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function NewApplicationPage() {
  const { t } = useLang();
  const navigate = useNavigate();

  const [businessName, setBusinessName] = useState<string | null>(null);

  useEffect(() => {
    getMe()
      .then((me) => setBusinessName(me.display_name))
      .catch(() => setBusinessName(null));
  }, []);

  // PENDING BACKEND — captured for the form to feel complete, never sent.
  const [amount, setAmount] = useState("");
  const [term, setTerm] = useState<(typeof TERM_OPTIONS)[number]>("12");
  const [purpose, setPurpose] = useState<(typeof PURPOSE_OPTIONS)[number]>("workingCapital");
  const [description, setDescription] = useState("");

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      // amount/term/purpose/description are PENDING BACKEND — not sent.
      const { application_id } = await createApplication();
      navigate(`/sme/applications/${application_id}`, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("sme.new.error"));
      setBusy(false);
    }
  }

  return (
    <section>
      <BackButton to="/sme" label={t("common.back.dashboard")} />

      <h1 className="font-display text-2xl font-extrabold text-ink sm:text-h1">{t("sme.new.title")}</h1>
      <p className="mt-1 max-w-md text-[13px] text-text-2">{t("sme.new.subtitle")}</p>

      <div className="mt-6">
        <Stepper activeId="details" />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">
        <form onSubmit={onSubmit} className="rounded-2xl border border-line bg-surface p-6">
          <h2 className="text-[19px] font-bold text-ink">{t("sme.new.formTitle")}</h2>
          <p className="mb-6 mt-1 text-sm text-text-2">{t("sme.new.formLead")}</p>

          <div className="mb-6 flex items-center justify-between gap-4 rounded-xl border border-line bg-surface-2 px-4 py-3.5">
            <div>
              <div className="text-[15px] font-semibold text-ink">
                {businessName ?? t("sme.new.businessFallbackName")}
              </div>
              <div className="mt-0.5 text-[13px] text-text-3">{t("sme.new.businessMetaPending")}</div>
            </div>
            <Link to="/sme/settings" className="shrink-0 text-[13px] font-semibold text-accent hover:underline">
              {t("sme.new.editProfile")}
            </Link>
          </div>

          <div className="mb-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1.5 block text-label text-text-2">{t("sme.new.amountLabel")}</label>
              <div className="flex h-11 items-center overflow-hidden rounded-lg border border-line-strong bg-surface focus-within:border-accent focus-within:ring-2 focus-within:ring-accent/30">
                <span className="flex h-full items-center bg-surface-2 px-3.5 text-sm text-text-2">SAR</span>
                <input
                  type="number"
                  min="0"
                  step="1000"
                  dir="ltr"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="0"
                  className="h-full w-full bg-transparent px-3.5 text-sm tabular-nums text-ink focus:outline-none"
                />
              </div>
            </div>

            <Select
              label={t("sme.new.termLabel")}
              value={term}
              onChange={(e) => setTerm(e.target.value as (typeof TERM_OPTIONS)[number])}
            >
              {TERM_OPTIONS.map((value) => (
                <option key={value} value={value}>
                  {t(`sme.new.term.${value}` as StringKey)}
                </option>
              ))}
            </Select>
          </div>

          <div className="mb-5">
            <Select
              label={t("sme.new.purposeLabel")}
              value={purpose}
              onChange={(e) => setPurpose(e.target.value as (typeof PURPOSE_OPTIONS)[number])}
            >
              {PURPOSE_OPTIONS.map((value) => (
                <option key={value} value={value}>
                  {t(`sme.new.purpose.${value}` as StringKey)}
                </option>
              ))}
            </Select>
          </div>

          <div className="mb-6">
            <Textarea
              label={t("sme.new.descriptionLabel")}
              placeholder={t("sme.new.descriptionPlaceholder")}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          {error && <p className="mb-4 text-sm text-flag">{error}</p>}

          <div className="flex items-center gap-3">
            <Button type="submit" variant="accent" size="lg" disabled={busy}>
              {busy ? t("sme.new.submitting") : t("sme.new.submit")}
            </Button>
            <Link
              to="/sme"
              className="inline-flex h-12 items-center rounded-lg border border-line-strong px-7 text-base text-ink hover:bg-surface-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            >
              {t("sme.new.cancel")}
            </Link>
          </div>
        </form>

        <aside className="h-fit rounded-2xl bg-surface-2 p-6">
          <h3 className="mb-4 text-[15px] font-semibold text-ink">{t("sme.new.whatsNextTitle")}</h3>
          <ol className="space-y-0">
            {(["sme.new.whatsNext1", "sme.new.whatsNext2", "sme.new.whatsNext3", "sme.new.whatsNext4"] as StringKey[]).map(
              (key, i) => (
                <li key={key} className="flex gap-3 border-b border-line py-2.5 text-sm text-text-2 last:border-b-0">
                  <span className="flex h-[22px] w-[22px] flex-none items-center justify-center rounded-full bg-accent-soft text-[12px] font-semibold text-accent-strong">
                    {i + 1}
                  </span>
                  {t(key)}
                </li>
              ),
            )}
          </ol>
        </aside>
      </div>
    </section>
  );
}
