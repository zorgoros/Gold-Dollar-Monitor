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
import { formatNumber, formatTime } from "../format.js";

const LINES = [
  { key: "usd_market", label: "دلار بازار", color: "#f0b83c" },
  { key: "usd_gold_implied", label: "مسیر طلا", color: "#6388e6" },
  { key: "usd_aed_implied", label: "مسیر درهم", color: "#61c985" },
];

function chartRows(series = {}) {
  const rows = new Map();
  for (const [name, points] of Object.entries(series)) {
    for (const point of points) {
      const row = rows.get(point.at) ?? { at: point.at };
      row[name] = point.value;
      rows.set(point.at, row);
    }
  }
  return [...rows.values()].sort((a, b) => a.at.localeCompare(b.at));
}

export function MarketChart({ history, loading }) {
  const rows = useMemo(() => chartRows(history?.series), [history]);
  if (loading) return <div className="chart-state">در حال دریافت روند…</div>;
  if (!rows.length) return <div className="chart-state">برای این بازه داده کافی نیست.</div>;
  return (
    <>
      <div className="chart-canvas" aria-label="نمودار مقایسه مسیرهای دلار">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 14, right: 8, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="#233039" vertical={false} strokeDasharray="2 8" />
            <XAxis dataKey="at" tickFormatter={formatTime} stroke="#647078" tickLine={false} />
            <YAxis
              orientation="right"
              domain={[(minimum) => Math.floor(minimum / 1000) * 1000 - 1000, (maximum) => Math.ceil(maximum / 1000) * 1000 + 1000]}
              tickFormatter={(v) => `${Math.round(v / 1000)}k`}
              stroke="#647078"
              tickLine={false}
              width={46}
            />
            <Tooltip
              labelFormatter={formatTime}
              formatter={(value, name) => [formatNumber(value), LINES.find((line) => line.key === name)?.label]}
              contentStyle={{ background: "#111a20", border: "1px solid #34434c", borderRadius: 6 }}
            />
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
