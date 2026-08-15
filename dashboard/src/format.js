const integer = new Intl.NumberFormat("fa-IR", { maximumFractionDigits: 0 });
const decimal = new Intl.NumberFormat("fa-IR", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 2,
});

export const formatNumber = (value) => integer.format(value ?? 0);
export const formatPercent = (value) => `${value > 0 ? "+" : ""}${decimal.format(value ?? 0)}٪`;

const TEHRAN_TIME_ZONE = "Asia/Tehran";

export function formatChartDate(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("fa-IR", {
    timeZone: TEHRAN_TIME_ZONE,
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(new Date(value));
}

export function formatClock(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("fa-IR", {
    timeZone: TEHRAN_TIME_ZONE,
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).format(new Date(value));
}

export function formatAxisTime(value, range = "1d") {
  if (!value) return "—";
  if (range === "1d") return formatClock(value);
  return new Intl.DateTimeFormat("fa-IR", {
    timeZone: TEHRAN_TIME_ZONE,
    month: "short",
    day: "numeric",
  }).format(new Date(value));
}

export function formatTime(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("fa-IR", {
    timeZone: TEHRAN_TIME_ZONE,
    hour: "2-digit",
    minute: "2-digit",
    day: "numeric",
    month: "short",
  }).format(new Date(value));
}
