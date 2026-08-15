import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Prototype } from "./Prototype.jsx";

const latest = {
  state: "READY",
  as_of: "2026-08-12T09:30:00+00:00",
  basis: "LIVE",
  model_version: "1.2",
  data_status: {
    code: "STALE",
    as_of: "2026-08-12T09:30:00+00:00",
    age_seconds: 3600,
    freshness_limit_seconds: 1800,
  },
  cards: [
    {
      instrument: "USD_IRT",
      market_value: 185400,
      change_since_previous_pct: 0.9,
      references: [
        { name: "gold", implied_value: 190672, gap_pct: -2.76 },
        { name: "aed", implied_value: 187821, gap_pct: -1.29 },
      ],
      data_quality: "OK",
    },
    {
      instrument: "GOLD_18K",
      market_value: 19150000,
      change_since_previous_pct: 0.6,
      references: [{ name: "theoretical", implied_value: 19590000, gap_pct: -2.25 }],
      data_quality: "OK",
    },
    {
      instrument: "XAU_USD",
      market_value: 4382,
      change_since_previous_pct: -0.2,
      references: [],
      data_quality: "OK",
    },
    {
      instrument: "EMAMI_COIN",
      market_value: 189485000,
      change_since_previous_pct: 1.1,
      references: [{ name: "metal_content", implied_value: 171200000, gap_pct: 10.68 }],
      data_quality: "OK",
    },
    {
      instrument: "AED_IRT",
      market_value: 51120,
      change_since_previous_pct: 0.1,
      references: [],
      data_quality: "OK",
    },
  ],
  analysis: {
    state: "READY",
    basis: "LIVE",
    reference_at: "2026-08-12T09:30:00+00:00",
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
    signals: [
      {
        instrument: "usd_irr_free",
        classification: "BELOW_REFERENCE",
        severity: 2,
        confidence: 0.82,
        summary_fa: "دلار بازار پایین‌تر از مسیرهای مرجع است.",
        reason_codes: ["GAP_SLIGHT"],
      },
    ],
    summary_fa: ["دلار بازار پایین‌تر از مسیرهای مرجع است."],
    narratives: {
      overview: [
        {
          id: "usd.references.disagree",
          text: {
            fa: "مسیرهای طلا و درهم تصویر یکسانی نشان نمی‌دهند.",
            en: "The gold and dirham paths do not show the same picture.",
          },
        },
      ],
      gold: [
        {
          id: "gold.below_theoretical",
          text: {
            fa: "طلای داخلی پایین‌تر از ارزش نظری مدل است.",
            en: "Domestic gold is below the model value.",
          },
        },
      ],
      coin: [
        {
          id: "coin.positive_premium",
          text: {
            fa: "فاصله مثبت، حباب داخلی سکه را نشان می‌دهد.",
            en: "The positive gap is the domestic coin premium.",
          },
        },
      ],
    },
  },
};

const history = {
  state: "READY",
  range: "1d",
  start: "2026-08-11T09:30:00+00:00",
  end: "2026-08-12T09:30:00+00:00",
  coverage_complete: true,
  series: {
    usd_market: [
      { at: "2026-08-11T09:30:00+00:00", value: 182000 },
      { at: "2026-08-12T09:30:00+00:00", value: 185400 },
    ],
    usd_gold_implied: [
      { at: "2026-08-11T09:30:00+00:00", value: 188000 },
      { at: "2026-08-12T09:30:00+00:00", value: 190672 },
    ],
    usd_aed_implied: [
      { at: "2026-08-11T09:30:00+00:00", value: 186100 },
      { at: "2026-08-12T09:30:00+00:00", value: 187821 },
    ],
  },
};

function mockApi() {
  return vi.fn(async (url) => ({
    ok: true,
    json: async () => (String(url).includes("/history") ? history : latest),
  }));
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  window.localStorage?.clear();
});

describe("Prototype", () => {
  it("renders a Persian RTL market board from the public API", async () => {
    globalThis.fetch = mockApi();
    render(<Prototype />);

    expect(document.documentElement).toHaveAttribute("dir", "rtl");
    expect((await screen.findAllByText("۱۸۵٬۴۰۰")).length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "عیار مارکت" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "قیمت‌های اصلی" }).querySelectorAll("article")).toHaveLength(4);
    expect(screen.getByRole("tab", { name: "بازار" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByText("داده قدیمی")).toBeInTheDocument();
    expect(screen.queryByText("بازار فعال")).not.toBeInTheDocument();
  });

  it("keeps the detailed analysis in a separate view", async () => {
    globalThis.fetch = mockApi();
    render(<Prototype />);
    await screen.findAllByText("۱۸۵٬۴۰۰");

    fireEvent.click(screen.getByRole("tab", { name: "تحلیل" }));

    expect(screen.getByRole("heading", { name: "تحلیل مسیرهای دلار" })).toBeInTheDocument();
    expect(screen.getByText("تحلیل سکه")).toBeInTheDocument();
    expect(screen.getByText("جمع‌بندی تحلیل")).toBeInTheDocument();
    expect(screen.getAllByText("دلار بازار پایین‌تر از مسیرهای مرجع است.").length).toBeGreaterThan(0);
    expect(document.querySelectorAll(".analysis-route-card")).toHaveLength(3);
  });

  it("opens contextual help for a named market concept", async () => {
    globalThis.fetch = mockApi();
    render(<Prototype />);
    await screen.findAllByText("۱۸۵٬۴۰۰");

    fireEvent.click(screen.getByRole("button", { name: "راهنمای صفحه" }));
    fireEvent.click(screen.getByRole("button", { name: "راهنمای مسیر طلا" }));

    expect(screen.getByRole("dialog", { name: "مسیر طلا" })).toHaveTextContent(
      "اونس جهانی",
    );
  });

  it("lets the user hide optional widgets from settings", async () => {
    globalThis.fetch = mockApi();
    render(<Prototype />);
    await screen.findAllByText("۱۸۵٬۴۰۰");

    fireEvent.click(screen.getByRole("button", { name: "تنظیمات" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "نمایش کارت سکه امامی" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "نمایش جدول جزئیات" }));

    expect(screen.queryByText("سکه امامی")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "قیمت، تغییر و کیفیت داده" })).not.toBeInTheDocument();
  });

  it("switches the full dashboard to English and LTR", async () => {
    globalThis.fetch = mockApi();
    render(<Prototype />);
    await screen.findAllByText("۱۸۵٬۴۰۰");

    fireEvent.click(screen.getByRole("button", { name: "تنظیمات" }));
    fireEvent.click(screen.getByRole("radio", { name: "English" }));

    expect(document.documentElement).toHaveAttribute("lang", "en");
    expect(document.documentElement).toHaveAttribute("dir", "ltr");
    expect(screen.getByRole("heading", { name: "Ayar Market" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Market" })).toBeInTheDocument();
    expect(screen.getByText("Old data")).toBeInTheDocument();
    expect(screen.getAllByText("185,400").length).toBeGreaterThan(0);
  });

  it("explains every data-status color in contextual help", async () => {
    globalThis.fetch = mockApi();
    render(<Prototype />);
    await screen.findAllByText("۱۸۵٬۴۰۰");

    fireEvent.click(screen.getByRole("button", { name: "راهنمای صفحه" }));
    fireEvent.click(screen.getByRole("button", { name: "راهنمای وضعیت داده" }));

    const dialog = screen.getByRole("dialog", { name: "وضعیت داده" });
    expect(dialog).toHaveTextContent("سبز");
    expect(dialog).toHaveTextContent("زرد");
    expect(dialog).toHaveTextContent("قرمز");
    expect(dialog).toHaveTextContent("ساعت رسمی");
  });

  it("adds action hints and the approved legal footer", async () => {
    globalThis.fetch = mockApi();
    render(<Prototype />);
    await screen.findAllByText("۱۸۵٬۴۰۰");

    expect(screen.getByRole("button", { name: "تنظیمات" })).toHaveAttribute("title");
    expect(screen.getByRole("button", { name: "۷ روز" })).toHaveAttribute("title");
    expect(screen.getByText(/تمامی حقوق محفوظ است/)).toBeInTheDocument();
    expect(screen.getByText(/ZorgOros/)).toBeInTheDocument();
  });

  it("requests a new history range without reloading the page", async () => {
    const fetchMock = mockApi();
    globalThis.fetch = fetchMock;
    render(<Prototype />);
    await screen.findAllByText("۱۸۵٬۴۰۰");

    fireEvent.click(screen.getByRole("button", { name: "۷ روز" }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("range=7d"), {
        signal: expect.any(AbortSignal),
      }),
    );
  });

  it("shows a simple unavailable state instead of technical diagnostics", async () => {
    globalThis.fetch = vi.fn(async () => ({ ok: false, json: async () => ({}) }));
    render(<Prototype />);

    expect(await screen.findByText("داده بازار در دسترس نیست")).toBeInTheDocument();
    expect(screen.queryByText(/stack|trace|database/i)).not.toBeInTheDocument();
  });
});
