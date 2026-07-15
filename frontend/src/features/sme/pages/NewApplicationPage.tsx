// SME portal — NewApplicationPage (/sme/applications/new).
// POST /applications is a real endpoint (routers/applications.py) — creates a
// draft application, then this page hands off to the detail spine which owns
// document upload + analysis + review + submit.
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { IconArrowLeft } from "@tabler/icons-react";
import { useLang } from "../../../i18n/LangProvider";
import { ApiError, createApplication } from "../../../lib/api";

export default function NewApplicationPage() {
  const { t, lang } = useLang();
  const navigate = useNavigate();

  const [amount, setAmount] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const parsed = amount.trim() === "" ? undefined : Number(amount);
      const { application_id } = await createApplication(
        parsed !== undefined && Number.isFinite(parsed) ? parsed : undefined,
      );
      navigate(`/sme/applications/${application_id}`, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("sme.new.error"));
      setBusy(false);
    }
  }

  return (
    <section>
      <Link
        to="/sme"
        className="mb-3 inline-flex items-center gap-1.5 text-[12.5px] font-medium text-text-2 hover:text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
      >
        <IconArrowLeft size={14} className={lang === "ar" ? "rotate-180" : ""} aria-hidden="true" />
        {t("review.backLink")}
      </Link>

      <h1 className="font-display text-2xl font-extrabold text-ink">{t("sme.new.title")}</h1>
      <p className="mb-4 mt-0.5 max-w-md text-[13px] text-text-2">{t("sme.new.subtitle")}</p>

      <form onSubmit={onSubmit} className="max-w-sm rounded-xl border border-line bg-surface px-4 py-4">
        <label className="block text-[12px] font-medium text-text-2">
          {t("sme.new.amountLabel")}
          <input
            type="number"
            min="0"
            step="1000"
            dir="ltr"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="0"
            className="mt-1 w-full rounded-lg border border-line-strong bg-bg px-2.5 py-1.5 text-[13px] tabular-nums text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          />
        </label>
        <p className="mt-1 text-[11.5px] text-text-3">{t("sme.new.amountHint")}</p>

        {error && <p className="mt-3 text-xs text-flag">{error}</p>}

        <div className="mt-4 flex items-center gap-2">
          <button
            type="submit"
            disabled={busy}
            className="inline-flex h-10 items-center gap-2 rounded-lg bg-accent px-5 text-sm font-medium text-on-accent disabled:opacity-50 hover:bg-accent-strong focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
          >
            {busy ? t("sme.new.submitting") : t("sme.new.submit")}
          </button>
          <Link
            to="/sme"
            className="rounded-lg border border-line-strong px-4 py-2 text-sm text-ink hover:bg-surface-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            {t("sme.new.cancel")}
          </Link>
        </div>
      </form>
    </section>
  );
}
