import { createContext, useContext, useMemo } from "react";
import { locales, normalizeLanguage } from "../locales/index.js";

const LocaleContext = createContext(null);

export function LocaleProvider({ language, children }) {
  const normalized = normalizeLanguage(language);
  const value = useMemo(
    () => ({
      language: normalized,
      direction: normalized === "fa" ? "rtl" : "ltr",
      copy: locales[normalized],
    }),
    [normalized],
  );
  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale() {
  const context = useContext(LocaleContext);
  if (!context) throw new Error("useLocale must be used inside LocaleProvider");
  return context;
}
