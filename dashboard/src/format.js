const TEHRAN_TIME_ZONE = "Asia/Tehran";
const LOCALE = { fa: "fa-IR", en: "en-US" };

function localeCode(language) {
  return LOCALE[language] ?? LOCALE.fa;
}

export function formatNumber(value, language = "fa") {
  return new Intl.NumberFormat(localeCode(language), { maximumFractionDigits: 0 }).format(value ?? 0);
}

export function formatPercent(value, language = "fa") {
  const formatted = new Intl.NumberFormat(localeCode(language), {
    minimumFractionDigits: 1,
    maximumFractionDigits: 2,
  }).format(value ?? 0);
  const sign = value > 0 ? "+" : "";
  return language === "en" ? `${sign}${formatted}%` : `${sign}${formatted}٪`;
}

export function formatChartDate(value, language = "fa") {
  if (!value) return "—";
  return new Intl.DateTimeFormat(localeCode(language), {
    timeZone: TEHRAN_TIME_ZONE,
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(new Date(value));
}

export function formatClock(value, language = "fa") {
  if (!value) return "—";
  return new Intl.DateTimeFormat(localeCode(language), {
    timeZone: TEHRAN_TIME_ZONE,
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).format(new Date(value));
}

export function formatAxisTime(value, range = "1d", language = "fa") {
  if (!value) return "—";
  if (range === "1d") return formatClock(value, language);
  return new Intl.DateTimeFormat(localeCode(language), {
    timeZone: TEHRAN_TIME_ZONE,
    month: "short",
    day: "numeric",
  }).format(new Date(value));
}

export function formatTime(value, language = "fa") {
  if (!value) return "—";
  return new Intl.DateTimeFormat(localeCode(language), {
    timeZone: TEHRAN_TIME_ZONE,
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    day: "numeric",
    month: "short",
  }).format(new Date(value));
}
