import { useMemo } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatAxisTime, formatChartDate, formatClock, formatNumber, formatTime } from "../format.js";

const LINES = [
  { key: "usd_market", label: "دلار بازار", color: "#f0b83c" },
  { key: "usd_gold_implied", label: "مسیر طلا", color: "#6388e6" },
  { key: "usd_aed_implied", label: "مسیر درهم", color: "#61c985" },
];

export function chartRows(series = {}) {
  const rows = new Map();
  for (const [name, points] of Object.entries(series)) {
    for (const point of points) {
      const row = rows.get(point.at) ?? { at: point.at, timestamp: Date.parse(point.at) };
      row[name] = point.value;
      rows.set(point.at, row);
    }
  }
  return [...rows.values()].sort((a, b) => a.timestamp - b.timestamp);
}

export function historyDomain(history) {
  return [Date.parse(history?.start), Date.parse(history?.end)];
}

export function timeTicks(history, count = 6) {
  const [start, end] = historyDomain(history);
  if (!Number.isFinite(start) || !Number.isFinite(end) || count < 2) return [];
  const step = (end - start) / (count - 1);
  return Array.from({ length: count }, (_, index) => start + step * index);
}

export function ChartTooltip({ active, label, payload, enabled = true }) {
  if (!enabled || !active || !payload?.length) return null;
  return (
    <div className="chart-tooltip" dir="rtl">
      <header>
        <strong data-testid="tooltip-date">{formatChartDate(label)}</strong>
        <span data-testid="tooltip-clock" dir="ltr">{formatClock(label)}</span>
      </header>
      {payload.map((entry) => {
        const line = LINES.find((item) => item.key === entry.dataKey);
        return (
          <div className="chart-tooltip-row" key={entry.dataKey} style={{ color: entry.color }}>
            <span>{line?.label ?? entry.dataKey}</span>
            <b>{formatNumber(entry.value)}</b>
          </div>
        );
      })}
    </div>
  );
}

export function MarketChart({ history, loading, tooltipsEnabled = true }) {
  const rows = useMemo(() => chartRows(history?.series), [history]);
  const domain = useMemo(() => historyDomain(history), [history]);
  const ticks = useMemo(() => timeTicks(history), [history]);
  if (loading) return <div className="chart-state">در حال دریافت روند…</div>;
  if (!rows.length) return <div className="chart-state">برای این بازه داده کافی نیست.</div>;
  return (
    <>
      <div className="chart-canvas" aria-label="نمودار مقایسه مسیرهای دلار">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 14, right: 8, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="#233039" vertical={false} strokeDasharray="2 8" />
            <XAxis
              dataKey="timestamp"
              type="number"
              scale="time"
              domain={domain}
              ticks={ticks}
              allowDataOverflow
              tickCount={6}
              tickFormatter={(value) => formatAxisTime(value, history.range)}
              stroke="#647078"
              tickLine={false}
            />
            <YAxis
              orientation="right"
              domain={[(minimum) => Math.floor(minimum / 1000) * 1000 - 1000, (maximum) => Math.ceil(maximum / 1000) * 1000 + 1000]}
              tickFormatter={(v) => `${Math.round(v / 1000)}k`}
              stroke="#647078"
              tickLine={false}
              width={46}
            />
            <Tooltip content={<ChartTooltip enabled={tooltipsEnabled} />} />
            <Legend formatter={(key) => LINES.find((line) => line.key === key)?.label ?? key} />
            {LINES.map((line) => (
              <Line key={line.key} dataKey={line.key} stroke={line.color} strokeWidth={2.5} dot={false} connectNulls activeDot={{ r: 4 }} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <table className="sr-only-table">
        <caption>داده‌های نمودار</caption>
        <thead><tr><th>زمان</th>{LINES.map((line) => <th key={line.key}>{line.label}</th>)}</tr></thead>
        <tbody>{rows.map((row) => <tr key={row.at}><td>{formatTime(row.at)}</td>{LINES.map((line) => <td key={line.key}>{row[line.key] == null ? "—" : formatNumber(row[line.key])}</td>)}</tr>)}</tbody>
      </table>
    </>
  );
}
