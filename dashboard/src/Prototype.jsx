import { useEffect, useMemo, useState } from "react";
import { ChartLineUp, Clock, TrendUp, WarningCircle } from "@phosphor-icons/react";
import { getHistory, getLatest } from "./api.js";
import { AnalysisView } from "./components/AnalysisView.jsx";
import { DataStatus } from "./components/DataStatus.jsx";
import { HelpDialog, HelpProvider, HelpTarget, HelpToggle, useHelp } from "./components/HelpSystem.jsx";
import { MarketChart } from "./components/MarketChart.jsx";
import { PriceCard } from "./components/PriceCard.jsx";
import { SettingsButton, SettingsPanel, useDashboardSettings } from "./components/SettingsPanel.jsx";
import { SiteFooter } from "./components/SiteFooter.jsx";
import { formatNumber, formatPercent, formatTime } from "./format.js";

const RANGES = [
  { key: "1d", label: "۱ روز" },
  { key: "7d", label: "۷ روز" },
  { key: "30d", label: "۳۰ روز" },
];

const PRIMARY_CARDS = new Set(["USD_IRT", "GOLD_18K", "XAU_USD", "EMAMI_COIN"]);

const REFERENCE_HELP = {
  gold: "ارزش دلاری محاسبه‌شده از قیمت طلای ۱۸ عیار و اونس جهانی است. این مسیر یک مرجع مقایسه است، نه نرخ پیشنهادی خرید یا فروش.",
  aed: "ارزش دلاری محاسبه‌شده از نرخ درهم و برابری ثابت دلار به درهم است. این مسیر مستقل از مسیر طلا محاسبه می‌شود.",
};

export function Prototype() {
  return <HelpProvider><Dashboard /></HelpProvider>;
}

function Dashboard() {
  const [view, setView] = useState("market");
  const [latest, setLatest] = useState(null);
  const [history, setHistory] = useState(null);
  const [range, setRange] = useState("1d");
  const [error, setError] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settings, updateSetting] = useDashboardSettings();
  const { enabled: helpEnabled } = useHelp();

  useEffect(() => {
    document.documentElement.lang = "fa";
    document.documentElement.dir = "rtl";
    const controller = new AbortController();
    getLatest(controller.signal).then(setLatest).catch((reason) => {
      if (reason.name !== "AbortError") setError(true);
    });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setHistoryLoading(true);
    getHistory(range, controller.signal)
      .then(setHistory)
      .catch((reason) => {
        if (reason.name !== "AbortError") setHistory(null);
      })
      .finally(() => setHistoryLoading(false));
    return () => controller.abort();
  }, [range]);

  const usd = useMemo(
    () => latest?.cards?.find((card) => card.instrument === "USD_IRT"),
    [latest],
  );
  const tableCards = useMemo(
    () => latest?.cards?.filter((card) => settings.showCoin || card.instrument !== "EMAMI_COIN") ?? [],
    [latest, settings.showCoin],
  );
  const visibleCards = useMemo(
    () => tableCards.filter((card) => PRIMARY_CARDS.has(card.instrument)),
    [tableCards],
  );

  if (error || latest?.state === "NO_DATA") {
    return <main className="center-state unavailable"><WarningCircle weight="duotone" /><h1>داده بازار در دسترس نیست</h1><p>پس از ثبت اولین داده، داشبورد به‌صورت خودکار آماده می‌شود.</p></main>;
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand"><span className="brand-mark"><TrendUp weight="bold" /></span><div><h1>عیار مارکت</h1><p>نمای هوشمند بازار</p></div></div>
        <nav className="view-tabs" aria-label="نمای داشبورد" role="tablist">
          <button role="tab" aria-selected={view === "market"} onClick={() => setView("market")}>بازار</button>
          <button role="tab" aria-selected={view === "analysis"} onClick={() => setView("analysis")}>تحلیل</button>
        </nav>
        <div className="status-tools">
          <DataStatus status={latest?.data_status} fallbackAt={latest?.as_of} />
          <div className="header-actions"><HelpToggle /><SettingsButton onClick={() => setSettingsOpen(true)} /></div>
        </div>
      </header>

      {helpEnabled && <div className="help-mode-banner">حالت راهنما روشن است. نشان‌های «؟» را برای توضیح هر بخش انتخاب کنید.</div>}

      <main>
        {!latest ? <div className="loading-grid">در حال دریافت داده بازار…</div> : view === "market" ? (
          <>
            <section className="price-grid" aria-label="قیمت‌های اصلی">{visibleCards.map((card) => <PriceCard key={card.instrument} card={card} />)}</section>
            <section className="market-layout">
              <article className="chart-panel">
                <header className="panel-header"><div><p className="eyebrow">مقایسه سه مسیر</p><h2>دلار بازار و ارزش‌های مرجع</h2></div><div className="range-control" aria-label="بازه نمودار">{RANGES.map((item) => <button key={item.key} aria-pressed={range === item.key} onClick={() => setRange(item.key)}>{item.label}</button>)}</div></header>
                <MarketChart history={history} loading={historyLoading} tooltipsEnabled={settings.chartTooltips} />
                {history && !history.coverage_complete && <p className="coverage-note"><Clock /> سابقه کامل این بازه هنوز در پایگاه داده جمع نشده است.</p>}
              </article>
              <aside className="insight-panel">
                <header><span><ChartLineUp weight="duotone" /></span><div><p className="eyebrow">تحلیل کوتاه</p><h2>فاصله قیمت از مرجع</h2></div></header>
                {usd?.references?.map((reference) => {
                  const title = reference.name === "gold" ? "مسیر طلا" : "مسیر درهم";
                  return (
                    <HelpTarget className="reference-row" title={title} body={REFERENCE_HELP[reference.name]} key={reference.name}>
                      <div><span>{title}</span><strong>{formatNumber(reference.implied_value)}</strong></div>
                      <b className={reference.gap_pct > 0 ? "positive" : "negative"}>{formatPercent(reference.gap_pct)}</b>
                    </HelpTarget>
                  );
                })}
                <p className="insight-copy">دو مسیر مستقل هستند. اختلاف آن‌ها جهت فشار بازار را نشان می‌دهد، نه یک نرخ ترکیبی.</p>
                <button className="text-button" onClick={() => setView("analysis")}>مشاهده تحلیل کامل <span aria-hidden="true">←</span></button>
              </aside>
            </section>
            {settings.showTable && <section className="detail-table-wrap"><header><div><p className="eyebrow">جزئیات بازار</p><h2>قیمت، تغییر و کیفیت داده</h2></div><span className="model-tag">مدل {latest.model_version}</span></header><div className="table-scroll"><table><thead><tr><th>دارایی</th><th>قیمت بازار</th><th>تغییر</th><th>مرجع اصلی</th><th>وضعیت</th></tr></thead><tbody>{tableCards.map((card) => <tr key={card.instrument}><td>{card.instrument}</td><td>{formatNumber(card.market_value)}</td><td>{card.change_since_previous_pct == null ? "—" : formatPercent(card.change_since_previous_pct)}</td><td>{card.references?.[0] ? formatNumber(card.references[0].implied_value) : "—"}</td><td><span className="quality-dot" /> معتبر</td></tr>)}</tbody></table></div></section>}
          </>
        ) : <AnalysisView analysis={latest.analysis} />}
      </main>

      <SiteFooter asOf={formatTime(latest?.as_of)} onOpenSettings={() => setSettingsOpen(true)} />
      <SettingsPanel open={settingsOpen} onClose={() => setSettingsOpen(false)} settings={settings} onChange={updateSetting} />
      <HelpDialog />
    </div>
  );
}
