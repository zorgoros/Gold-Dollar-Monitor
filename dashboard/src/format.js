const integer = new Intl.NumberFormat("fa-IR", { maximumFractionDigits: 0 });
const decimal = new Intl.NumberFormat("fa-IR", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 2,
});

export const formatNumber = (value) => integer.format(value ?? 0);
export const formatPercent = (value) => `${value > 0 ? "+" : ""}${decimal.format(value ?? 0)}٪`;

export function formatTime(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("fa-IR", {
    timeZone: "Asia/Tehran",
    hour: "2-digit",
    minute: "2-digit",
    day: "numeric",
    month: "short",
  }).format(new Date(value));
}
