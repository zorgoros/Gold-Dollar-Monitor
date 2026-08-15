import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { AnalysisView } from "./AnalysisView.jsx";
import { LocaleProvider } from "./LocaleProvider.jsx";

const analysis = {
  state: "READY",
  metrics: {
    usd_market: 185400,
    usd_gold_implied: 190672,
    usd_gap_pct: -2.76,
    usd_aed_implied: 187821,
    aed_usd_gap_pct: -1.29,
    gold_18k_market: 19150000,
    gold_18_theoretical: 19590000,
    gold_gap_pct: -2.25,
    coin_market: 189485000,
    coin_intrinsic_domestic: 171200000,
    coin_premium_domestic_pct: 10.68,
  },
  signals: [{
    instrument: "usd_irr_free",
    classification: "BELOW_REFERENCE",
    severity: 2,
    confidence: 0.82,
    summary_fa: "دلار بازار پایین‌تر از مسیرهای مرجع است.",
  }],
  summary_fa: ["دلار بازار پایین‌تر از مسیرهای مرجع است."],
  narratives: {
    overview: [{ id: "overview", text: { fa: "جمع‌بندی فارسی مسیرها.", en: "English path conclusion." } }],
    gold: [{ id: "gold", text: { fa: "تحلیل فارسی برابری طلا.", en: "English gold parity analysis." } }],
    coin: [{ id: "coin", text: { fa: "تحلیل فارسی ارزش سکه.", en: "English coin value analysis." } }],
  },
};

function renderAnalysis(language) {
  return render(<LocaleProvider language={language}><AnalysisView analysis={analysis} /></LocaleProvider>);
}

afterEach(cleanup);

describe("AnalysisView", () => {
  it("places deterministic Persian context beside all three analytical sections", () => {
    renderAnalysis("fa");

    expect(screen.getByText("جمع‌بندی فارسی مسیرها.")).toBeInTheDocument();
    expect(screen.getByText("تحلیل فارسی برابری طلا.")).toBeInTheDocument();
    expect(screen.getByText("تحلیل فارسی ارزش سکه.")).toBeInTheDocument();
    expect(screen.getByText("جمع‌بندی تحلیل")).toBeInTheDocument();
    expect(screen.getAllByText("نتیجه تحلیلی")).toHaveLength(2);
  });

  it("uses English narratives, labels, and number formatting in English mode", () => {
    renderAnalysis("en");

    expect(screen.getByRole("heading", { name: "Dollar Path Analysis" })).toBeInTheDocument();
    expect(screen.getByText("English path conclusion.")).toBeInTheDocument();
    expect(screen.getByText("English gold parity analysis.")).toBeInTheDocument();
    expect(screen.getByText("English coin value analysis.")).toBeInTheDocument();
    expect(screen.getAllByText("185,400").length).toBeGreaterThan(0);
    expect(screen.queryByText("دلار بازار پایین‌تر از مسیرهای مرجع است.")).not.toBeInTheDocument();
  });

  it("shows a clear fallback when a section has no selected narrative", () => {
    render(
      <LocaleProvider language="en">
        <AnalysisView analysis={{ ...analysis, narratives: { overview: [], gold: [], coin: [] } }} />
      </LocaleProvider>,
    );

    expect(screen.getAllByText("No reliable analytical conclusion is available for this section.")).toHaveLength(3);
  });
});
