import { en } from "./en.js";
import { fa } from "./fa.js";

export const locales = { fa, en };

export function normalizeLanguage(language) {
  return language === "en" ? "en" : "fa";
}
