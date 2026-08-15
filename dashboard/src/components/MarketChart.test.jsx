import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ChartTooltip, chartRows, historyDomain, timeTicks } from "./MarketChart.jsx";

const start = "2026-08-05T09:30:00+00:00";
const end = "2026-08-12T09:30:00+00:00";

describe("MarketChart time semantics", () => {
  it("keeps database timestamps on a numeric axis inside the requested window", () => {
    const rows = chartRows({
      usd_market: [{ at: "2026-08-11T09:30:00+00:00", value: 185400 }],
    });

    expect(rows[0].timestamp).toBe(Date.parse("2026-08-11T09:30:00+00:00"));
    expect(historyDomain({ start, end })).toEqual([Date.parse(start), Date.parse(end)]);
    const ticks = timeTicks({ start, end });
    expect(ticks).toHaveLength(6);
    expect(ticks[0]).toBe(Date.parse(start));
    expect(ticks.at(-1)).toBe(Date.parse(end));
  });

  it("separates the Persian date from the clock in the tooltip", () => {
    render(
      <ChartTooltip
        active
        label={Date.parse("2026-08-11T15:30:00+00:00")}
        payload={[{ dataKey: "usd_market", value: 185400, color: "#f0b83c" }]}
      />,
    );

    const date = screen.getByTestId("tooltip-date");
    expect(date).toHaveTextContent("مرداد");
    expect(date).not.toHaveTextContent(":");
    expect(screen.getByTestId("tooltip-clock")).toHaveTextContent(":");
  });
});
