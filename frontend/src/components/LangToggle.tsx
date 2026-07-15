// EN/ع segmented language control (from the login mockup — DESIGN_SYSTEM.md §7,
// §12). Reused on the login form panel and in both portal headers.
import { useLang } from "../i18n/LangProvider";

export default function LangToggle() {
  const { lang, setLang } = useLang();

  return (
    <div className="inline-flex overflow-hidden rounded-lg border border-line-strong text-xs">
      <button
        type="button"
        onClick={() => setLang("en")}
        aria-pressed={lang === "en"}
        className={[
          "px-[9px] py-[5px] font-semibold",
          lang === "en" ? "bg-surface-2 text-ink" : "text-text-3",
        ].join(" ")}
      >
        EN
      </button>
      <button
        type="button"
        onClick={() => setLang("ar")}
        aria-pressed={lang === "ar"}
        className={[
          "px-[9px] py-[5px] font-semibold",
          lang === "ar" ? "bg-surface-2 text-ink" : "text-text-3",
        ].join(" ")}
      >
        ع
      </button>
    </div>
  );
}
