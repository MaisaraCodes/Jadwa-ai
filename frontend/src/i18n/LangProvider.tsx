// Global language state (DESIGN_SYSTEM.md §7, §12). Persists an explicit user
// choice in localStorage under 'lang'; defaults to Arabic (AR is primary for
// SME, per §12). dir/lang are applied ONLY here, on document.documentElement —
// components never set their own dir/lang.
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { STRINGS, type StringKey } from "./strings";

export type Lang = "ar" | "en";
const STORAGE_KEY = "lang";

function readStored(): Lang {
  return localStorage.getItem(STORAGE_KEY) === "en" ? "en" : "ar";
}

function apply(lang: Lang) {
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
}

export function initLang(): void {
  apply(readStored());
}

interface LangValue {
  lang: Lang;
  dir: "rtl" | "ltr";
  setLang: (lang: Lang) => void;
  t: (key: StringKey, vars?: Record<string, string | number>) => string;
}

const LangContext = createContext<LangValue | null>(null);

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(readStored);

  useEffect(() => {
    apply(lang);
  }, [lang]);

  const value = useMemo<LangValue>(() => {
    function setLang(next: Lang) {
      localStorage.setItem(STORAGE_KEY, next);
      setLangState(next);
    }
    function t(key: StringKey, vars?: Record<string, string | number>): string {
      const template: string = STRINGS[key][lang];
      if (!vars) return template;
      return Object.entries(vars).reduce(
        (acc, [name, val]) => acc.split(`{{${name}}}`).join(String(val)),
        template,
      );
    }
    return { lang, dir: lang === "ar" ? "rtl" : "ltr", setLang, t };
  }, [lang]);

  return <LangContext.Provider value={value}>{children}</LangContext.Provider>;
}

export function useLang(): LangValue {
  const ctx = useContext(LangContext);
  if (!ctx) throw new Error("useLang must be used inside <LangProvider>.");
  return ctx;
}
