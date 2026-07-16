// Shared entry point — follows the GLOBAL theme + language (no per-screen
// pinning). Pre-portal (DESIGN_SYSTEM.md §4.1): no data-portal on the page
// itself, so only core + gold tokens are used; the primary CTA is gold
// (allowed here only — everywhere else gold is brand/verification only).
// Toggles between signing in and creating an account; account creation asks which
// side you're on (SME or bank). On success, the router sends you to the right home.
import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { IconEye, IconEyeOff } from "@tabler/icons-react";
import { useAuth, type AppRole } from "./AuthProvider";
import { useLang } from "../../i18n/LangProvider";
import LangToggle from "../../components/LangToggle";
import PageFade from "../../components/PageFade";

type Mode = "signin" | "signup";

// Framed variant of the mark used only on this screen (tile follows surface/line
// tokens rather than the fixed canonical tile fill) — matches the mockup exactly.
function FramedMark() {
  return (
    <svg viewBox="0 0 100 100" width="38" height="38" aria-hidden="true">
      <rect width="100" height="100" rx="24" fill="var(--surface)" stroke="var(--line)" strokeWidth="2" />
      <rect x="22" y="24" width="56" height="13" fill="var(--ink)" />
      <rect x="65" y="37" width="13" height="28" fill="var(--ink)" />
      <rect x="10" y="52" width="68" height="13" fill="var(--ink)" />
      <path d="M38 38.5 L43.5 44.5 L38 50.5 L32.5 44.5 Z" fill="var(--gold)" />
    </svg>
  );
}

// Decorative brand Sadu band (gold-only, not tied to pipeline state — distinct
// from components/SaduBand.tsx, which renders live pipeline progress in-portal).
function BrandSaduBand() {
  return (
    <svg viewBox="0 0 280 22" width="220" height="22" aria-hidden="true">
      <path d="M4 20 L16 4 L28 20 Z" fill="var(--gold)" />
      <path d="M36 20 L48 4 L60 20 Z" fill="none" stroke="var(--gold)" strokeWidth="1.5" />
      <path d="M68 20 L80 4 L92 20 Z" fill="var(--gold)" />
      <path d="M100 20 L112 4 L124 20 Z" fill="none" stroke="var(--gold)" strokeWidth="1.5" />
      <path d="M132 20 L144 4 L156 20 Z" fill="var(--gold)" />
      <path d="M164 20 L176 4 L188 20 Z" fill="none" stroke="var(--gold)" strokeWidth="1.5" />
      <path d="M196 20 L208 4 L220 20 Z" fill="var(--gold)" />
    </svg>
  );
}

export default function LoginPage() {
  const { session, role, signIn, signUp } = useAuth();
  const navigate = useNavigate();
  const { t } = useLang();
  const [searchParams] = useSearchParams();

  // Lets the landing page's "Get started" and "Sign in" CTAs point at two
  // distinct destinations (?mode=signup vs the bare /login) instead of both
  // opening the same signin view — the toggle below still works normally
  // from here on.
  const [mode, setMode] = useState<Mode>(searchParams.get("mode") === "signup" ? "signup" : "signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [accountRole, setAccountRole] = useState<AppRole>("sme");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Already signed in → leave the login page.
  useEffect(() => {
    if (session && role) navigate(role === "bank" ? "/bank" : "/sme", { replace: true });
  }, [session, role, navigate]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (mode === "signin") await signIn(email, password);
      else await signUp(email, password, accountRole);
      // Navigation happens in the effect once the session lands.
    } catch (err) {
      setError(err instanceof Error ? err.message : t("auth.genericError"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <PageFade>
    <div className="min-h-screen bg-bg">
      <div className="grid min-h-screen grid-cols-1 sm:grid-cols-2">
        {/* Brand panel — inline-start side */}
        <div className="flex flex-col justify-between border-b border-[#1D2A23] px-8 py-[34px] sm:border-b-0 sm:border-e sm:border-[#1D2A23]">
          <Link
            to="/"
            className="flex w-fit items-center gap-3 rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-gold"
          >
            <FramedMark />
            <span className="font-display text-[22px] font-extrabold text-ink">{t("brand.wordmark")}</span>
          </Link>

          <div className="py-10 sm:py-0">
            <div className="whitespace-pre-line text-start font-display text-[34px] font-extrabold leading-[1.45] text-ink">
              {t("login.heroHeadline")}
            </div>
          </div>

          <div>
            <BrandSaduBand />
            <p className="mt-3.5 text-[11px] leading-[1.6] text-text-3">{t("login.demoNote")}</p>
          </div>
        </div>

        {/* Form panel — inline-end side */}
        <div className="flex flex-col justify-center bg-surface px-8 py-[34px]">
          <div className="mb-[22px] flex justify-end">
            <LangToggle />
          </div>

          <h1 className="font-display text-2xl font-bold text-ink">
            {mode === "signin" ? t("login.signInTitle") : t("login.signUpTitle")}
          </h1>
          <p className="mb-5 mt-1 text-[12.5px] text-text-2">
            {mode === "signin" ? t("login.signInSubtitle") : t("login.signUpSubtitle")}
          </p>

          <form onSubmit={onSubmit}>
            {mode === "signup" && (
              <fieldset className="mb-4">
                <legend className="mb-1.5 block text-xs font-medium text-text-2">
                  {t("login.signingUpAs")}
                </legend>
                <div className="grid grid-cols-2 gap-2" role="radiogroup" aria-label={t("login.signingUpAs")}>
                  {(["sme", "bank"] as AppRole[]).map((r) => {
                    const active = accountRole === r;
                    return (
                      <div key={r} data-portal={r}>
                        <button
                          type="button"
                          role="radio"
                          aria-checked={active}
                          onClick={() => setAccountRole(r)}
                          className={[
                            "w-full rounded-lg border px-3 py-2 text-sm font-medium transition-colors motion-reduce:transition-none focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-1 focus-visible:ring-accent",
                            active
                              ? "border-accent bg-accent-soft text-ink"
                              : "border-line text-text-2 hover:border-accent",
                          ].join(" ")}
                        >
                          {r === "sme" ? t("auth.roleSme") : t("auth.roleBank")}
                        </button>
                      </div>
                    );
                  })}
                </div>
              </fieldset>
            )}

            <label htmlFor="email" className="mb-1.5 block text-xs font-medium text-text-2">
              {t("login.email")}
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              placeholder={t("login.emailPlaceholder")}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mb-3.5 w-full rounded-lg border border-line-strong bg-bg px-3 py-2.5 text-[13px] text-ink placeholder:text-text-3 focus:outline-none focus-visible:border-gold focus-visible:ring-2 focus-visible:ring-gold"
            />

            <label htmlFor="password" className="mb-1.5 block text-xs font-medium text-text-2">
              {t("login.password")}
            </label>
            <div className="mb-5 flex items-center justify-between rounded-lg border border-line-strong bg-bg px-3 py-2.5 text-[13px] focus-within:border-gold focus-within:ring-2 focus-within:ring-gold">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                autoComplete={mode === "signin" ? "current-password" : "new-password"}
                required
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-transparent text-ink placeholder:text-text-3 focus:outline-none"
              />
              <button
                type="button"
                onClick={() => setShowPassword((s) => !s)}
                aria-label={showPassword ? t("login.hidePassword") : t("login.showPassword")}
                className="shrink-0 rounded text-text-3 hover:text-text-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-gold"
              >
                {showPassword ? <IconEyeOff size={15} /> : <IconEye size={15} />}
              </button>
            </div>

            {error && (
              <p className="mb-4 rounded-lg bg-flag-bg px-3 py-2 text-sm text-flag" role="alert">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={busy}
              className="w-full rounded-lg bg-gold py-[11px] text-sm font-semibold text-on-gold hover:bg-gold-strong focus:outline-none focus-visible:ring-2 focus-visible:ring-gold focus-visible:ring-offset-2 focus-visible:ring-offset-surface disabled:opacity-60"
            >
              {busy ? t("auth.workingEllipsis") : mode === "signin" ? t("login.signInCta") : t("login.createAccountCta")}
            </button>
          </form>

          <p className="mt-4 text-center text-xs text-text-3">
            {mode === "signin" ? (
              <>
                {t("login.newSme")}{" "}
                <button
                  type="button"
                  onClick={() => {
                    setMode("signup");
                    setError(null);
                  }}
                  className="rounded text-gold hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-gold"
                >
                  {t("login.createAnAccount")}
                </button>
              </>
            ) : (
              <>
                {t("login.alreadyHaveAccount")}{" "}
                <button
                  type="button"
                  onClick={() => {
                    setMode("signin");
                    setError(null);
                  }}
                  className="rounded text-gold hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-gold"
                >
                  {t("login.signInLink")}
                </button>
              </>
            )}
          </p>
        </div>
      </div>
    </div>
    </PageFade>
  );
}
