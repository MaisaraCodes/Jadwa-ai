// SME portal — SmeSettingsPage (/sme/settings). Layout matches
// design-mocks/jadwa_sme_settings.html: a left settings-nav (Business
// profile / Account / Preferences) beside one visible section at a time.
//
// Business profile section is fully wired to GET/PATCH /api/v1/me/profile.
// cr_number is displayed read-only (server enforces it; never sent in PATCH).
// Account is real: email comes from the Supabase
// session, and password change calls the real supabase.auth.updateUser via
// AuthProvider.updatePassword (straightforward — no current-password
// re-check needed with an existing session). Preferences' language and
// theme are the existing LangProvider/ThemeProvider state, applied
// immediately; the two notification switches are local-only state, since
// there's no notification system to back them yet.
import { useEffect, useState, type FormEvent } from "react";
import { IconBuilding } from "@tabler/icons-react";
import { ApiError, getProfile, patchProfile } from "../../../lib/api";
import type { PatchProfileRequest, SMEProfile } from "../../../types";
import { useAuth } from "../../auth/AuthProvider";
import { useLang, type Lang } from "../../../i18n/LangProvider";
import { useTheme, type Theme } from "../../../lib/theme";
import Button from "../../../components/Button";
import Input from "../../../components/Input";
import Select from "../../../components/Select";
import Textarea from "../../../components/Textarea";
import Switch from "../../../components/Switch";
import SegmentedControl from "../../../components/SegmentedControl";
import BackButton from "../../../components/BackButton";

type Section = "biz" | "account" | "prefs";

const SECTORS = ["logistics", "foodBeverage", "construction", "retail", "manufacturing"] as const;

function SettingsNavButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "rounded-lg px-3.5 py-2.5 text-start text-[15px] font-medium transition-colors motion-reduce:transition-none",
        "focus:outline-none focus-visible:ring-2 focus-visible:ring-accent",
        active ? "bg-accent-soft font-semibold text-accent-strong" : "text-text-2 hover:bg-surface-2",
      ].join(" ")}
    >
      {children}
    </button>
  );
}

function BusinessProfileSection() {
  const { t } = useLang();

  // Live profile — loaded once from GET /api/v1/me/profile.
  const [profile, setProfile] = useState<SMEProfile | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Form fields — reset to profile values on cancel.
  const [name, setName] = useState("");
  const [year, setYear] = useState("");
  const [sector, setSector] = useState<(typeof SECTORS)[number]>(SECTORS[0]);
  const [district, setDistrict] = useState("");
  const [description, setDescription] = useState("");

  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<{ ok: boolean; text: string } | null>(null);

  function applyProfileToForm(p: SMEProfile) {
    setName(p.company_name ?? "");
    setYear(p.established_year != null ? String(p.established_year) : "");
    setSector((SECTORS.find((s) => s === p.sector) ?? SECTORS[0]) as (typeof SECTORS)[number]);
    setDistrict(p.district ?? "");
    setDescription(p.backstory ?? "");
  }

  useEffect(() => {
    getProfile()
      .then((p) => { setProfile(p); applyProfileToForm(p); })
      .catch((err) => {
        setLoadError(err instanceof ApiError ? err.message : t("sme.settings.biz.loadError"));
      });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSave() {
    if (!profile) return;
    setSaving(true);
    setSaveMessage(null);
    try {
      const patch: PatchProfileRequest = {
        company_name: name || undefined,
        sector: sector || undefined,
        district: district || undefined,
        established_year: year ? parseInt(year, 10) : null,
        backstory: description || null,
      };
      const updated = await patchProfile(patch);
      setProfile(updated);
      applyProfileToForm(updated);
      setSaveMessage({ ok: true, text: t("sme.settings.biz.saved") });
    } catch (err) {
      setSaveMessage({
        ok: false,
        text: err instanceof ApiError ? err.message : t("sme.settings.biz.saveError"),
      });
    } finally {
      setSaving(false);
    }
  }

  if (loadError) {
    return (
      <div>
        <h2 className="text-[19px] font-bold text-ink">{t("sme.settings.biz.title")}</h2>
        <p className="mt-4 text-sm text-flag">{loadError}</p>
      </div>
    );
  }

  if (!profile) {
    return (
      <div>
        <h2 className="text-[19px] font-bold text-ink">{t("sme.settings.biz.title")}</h2>
        <p className="mt-4 text-sm text-text-3">{t("sme.settings.biz.loadingProfile")}</p>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-[19px] font-bold text-ink">{t("sme.settings.biz.title")}</h2>
      <p className="mb-6 mt-1 text-sm text-text-2">{t("sme.settings.biz.lead")}</p>

      <div className="mb-5">
        <Input label={t("sme.settings.biz.nameLabel")} value={name} onChange={(e) => setName(e.target.value)} />
      </div>

      <div className="mb-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
        {/* cr_number is enforced read-only server-side — never included in PATCH */}
        <Input
          label={t("sme.settings.biz.crLabel")}
          hint={t("sme.settings.biz.crReadOnly")}
          dir="ltr"
          value={profile.cr_number}
          readOnly
          className="cursor-not-allowed text-text-2"
        />
        <Input
          label={t("sme.settings.biz.yearLabel")}
          dir="ltr"
          inputMode="numeric"
          value={year}
          onChange={(e) => setYear(e.target.value.replace(/\D/g, ""))}
        />
      </div>

      <div className="mb-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Select
          label={t("sme.settings.biz.sectorLabel")}
          value={sector}
          onChange={(e) => setSector(e.target.value as (typeof SECTORS)[number])}
        >
          {SECTORS.map((value) => (
            <option key={value} value={value}>
              {t(`sme.settings.biz.sector.${value}` as const)}
            </option>
          ))}
        </Select>
        <Input
          label={t("sme.settings.biz.districtLabel")}
          value={district}
          onChange={(e) => setDistrict(e.target.value)}
        />
      </div>

      <div className="mb-6">
        <Textarea
          label={t("sme.settings.biz.descriptionLabel")}
          placeholder={t("sme.settings.biz.descriptionPlaceholder")}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>

      {saveMessage && (
        <p className={`mb-3 text-sm ${saveMessage.ok ? "text-pass" : "text-flag"}`}>{saveMessage.text}</p>
      )}

      <div className="flex items-center gap-3 border-t border-line pt-5">
        <Button variant="accent" disabled={saving} onClick={handleSave}>
          {saving ? t("sme.settings.biz.saving") : t("sme.settings.biz.save")}
        </Button>
        <Button
          variant="ghost"
          disabled={saving}
          onClick={() => { applyProfileToForm(profile); setSaveMessage(null); }}
        >
          {t("sme.settings.biz.cancel")}
        </Button>
      </div>
    </div>
  );
}

function AccountSection() {
  const { t } = useLang();
  const { user, updatePassword } = useAuth();
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(false);
    if (newPassword.length < 6) {
      setError(t("sme.settings.account.tooShort"));
      return;
    }
    if (newPassword !== confirmPassword) {
      setError(t("sme.settings.account.mismatch"));
      return;
    }
    setBusy(true);
    try {
      await updatePassword(newPassword);
      setSuccess(true);
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("auth.genericError"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h2 className="text-[19px] font-bold text-ink">{t("sme.settings.account.title")}</h2>
      <p className="mb-6 mt-1 text-sm text-text-2">{t("sme.settings.account.lead")}</p>

      <div className="mb-5">
        <Input
          label={t("sme.settings.account.emailLabel")}
          hint={t("sme.settings.account.emailHint")}
          dir="ltr"
          value={user?.email ?? ""}
          readOnly
          className="cursor-not-allowed text-text-2"
        />
      </div>

      <form onSubmit={onSubmit}>
        <div className="mb-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Input
            label={t("sme.settings.account.newPasswordLabel")}
            type="password"
            minLength={6}
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
          />
          <Input
            label={t("sme.settings.account.confirmPasswordLabel")}
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
          />
        </div>

        {error && <p className="mb-4 text-sm text-flag">{error}</p>}
        {success && <p className="mb-4 text-sm text-pass">{t("sme.settings.account.updated")}</p>}

        <div className="border-t border-line pt-5">
          <Button type="submit" variant="accent" disabled={busy || !newPassword || !confirmPassword}>
            {busy ? t("sme.settings.account.updating") : t("sme.settings.account.update")}
          </Button>
        </div>
      </form>
    </div>
  );
}

function PreferencesRow({
  label,
  hint,
  children,
}: {
  label: string;
  hint: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-line py-4 last:border-b-0">
      <div>
        <div className="text-[15px] font-medium text-ink">{label}</div>
        <div className="mt-0.5 text-[13px] text-text-3">{hint}</div>
      </div>
      {children}
    </div>
  );
}

function PreferencesSection() {
  const { t, lang, setLang } = useLang();
  const { theme, toggle } = useTheme();
  const [statusNotif, setStatusNotif] = useState(true);
  const [decisionNotif, setDecisionNotif] = useState(true);

  return (
    <div>
      <h2 className="text-[19px] font-bold text-ink">{t("sme.settings.prefs.title")}</h2>
      <p className="mb-2 mt-1 text-sm text-text-2">{t("sme.settings.prefs.lead")}</p>

      <PreferencesRow label={t("sme.settings.prefs.languageLabel")} hint={t("sme.settings.prefs.languageHint")}>
        <SegmentedControl<Lang>
          ariaLabel={t("sme.settings.prefs.languageLabel")}
          value={lang}
          onChange={setLang}
          options={[
            { value: "ar", label: t("sme.settings.prefs.languageArabic") },
            { value: "en", label: t("sme.settings.prefs.languageEnglish") },
          ]}
        />
      </PreferencesRow>

      <PreferencesRow label={t("sme.settings.prefs.appearanceLabel")} hint={t("sme.settings.prefs.appearanceHint")}>
        <SegmentedControl<Theme>
          ariaLabel={t("sme.settings.prefs.appearanceLabel")}
          value={theme}
          onChange={(next) => {
            if (next !== theme) toggle();
          }}
          options={[
            { value: "light", label: t("sme.settings.prefs.appearanceLight") },
            { value: "dark", label: t("sme.settings.prefs.appearanceDark") },
          ]}
        />
      </PreferencesRow>

      <PreferencesRow
        label={t("sme.settings.prefs.notifStatusLabel")}
        hint={t("sme.settings.prefs.notifStatusHint")}
      >
        <Switch checked={statusNotif} onCheckedChange={setStatusNotif} ariaLabel={t("sme.settings.prefs.notifStatusLabel")} />
      </PreferencesRow>

      <PreferencesRow
        label={t("sme.settings.prefs.notifDecisionLabel")}
        hint={t("sme.settings.prefs.notifDecisionHint")}
      >
        <Switch
          checked={decisionNotif}
          onCheckedChange={setDecisionNotif}
          ariaLabel={t("sme.settings.prefs.notifDecisionLabel")}
        />
      </PreferencesRow>
    </div>
  );
}

export default function SmeSettingsPage() {
  const { t } = useLang();
  const [section, setSection] = useState<Section>("biz");

  return (
    <section>
      <BackButton to="/sme" label={t("common.back.dashboard")} />

      <h1 className="font-display text-2xl font-extrabold text-ink sm:text-h1">{t("sme.settings.title")}</h1>
      <p className="mt-1 text-[13px] text-text-2">{t("sme.settings.subtitle")}</p>

      <div className="mt-6 flex items-center gap-4 rounded-2xl border border-line bg-surface px-5 py-4">
        <div className="flex h-[52px] w-[52px] flex-none items-center justify-center rounded-xl bg-accent-soft text-accent-strong">
          <IconBuilding size={24} aria-hidden="true" />
        </div>
        <div>
          <div className="text-[17px] font-semibold text-ink">{t("sme.new.businessFallbackName")}</div>
          <div className="mt-0.5 text-[13px] text-text-3">{t("sme.new.businessMetaPending")}</div>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[220px_1fr]">
        <nav className="flex flex-row gap-1 overflow-x-auto lg:flex-col">
          <SettingsNavButton active={section === "biz"} onClick={() => setSection("biz")}>
            {t("sme.settings.nav.business")}
          </SettingsNavButton>
          <SettingsNavButton active={section === "account"} onClick={() => setSection("account")}>
            {t("sme.settings.nav.account")}
          </SettingsNavButton>
          <SettingsNavButton active={section === "prefs"} onClick={() => setSection("prefs")}>
            {t("sme.settings.nav.prefs")}
          </SettingsNavButton>
        </nav>

        <div className="rounded-2xl border border-line bg-surface p-6">
          {section === "biz" && <BusinessProfileSection />}
          {section === "account" && <AccountSection />}
          {section === "prefs" && <PreferencesSection />}
        </div>
      </div>
    </section>
  );
}
