// EN/ع segmented language control (from the login mockup — DESIGN_SYSTEM.md §7,
// §12). Reused on the login form panel and in both portal headers.
import { useLang } from "../i18n/LangProvider";

export default function LangToggle() {
  const { lang, setLang } = useLang();

  return (
    <div className="inline-flex overflow-hidden rounded-[7px] border border-line-strong text-xs">
      <button
        type="button"
        onClick={() => setLang("en")}
        aria-pressed={lang === "en"}
        className={
          lang === "en" ? "bg-line px-3 py-[5px] font-medium text-ink" : "px-3 py-[5px] text-text-2"
        }
      >
        EN
      </button>
      <button
        type="button"
        onClick={() => setLang("ar")}
        aria-pressed={lang === "ar"}
        className={
          lang === "ar" ? "bg-line px-3 py-[5px] font-medium text-ink" : "px-3 py-[5px] text-text-2"
        }
      >
        ع
      </button>
    </div>
  );
}
