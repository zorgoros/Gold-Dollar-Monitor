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
import { LocaleProvider, useLocale } from "./components/LocaleProvider.jsx";
import { formatNumber, formatPercent, formatTime } from "./format.js";

const RANGES = ["1d", "7d", "30d"];

const PRIMARY_CARDS = new Set(["USD_IRT", "GOLD_18K", "XAU_USD", "EMAMI_COIN"]);

export function Prototype() {
  const [settings, updateSetting] = useDashboardSettings();
  return (
    <LocaleProvider language={settings.language}>
      <HelpProvider><Dashboard settings={settings} updateSetting={updateSetting} /></HelpProvider>
    </LocaleProvider>
  );
}

function Dashboard({ settings, updateSetting }) {
  const [view, setView] = useState("market");
  const [latest, setLatest] = useState(null);
  const [history, setHistory] = useState(null);
  const [range, setRange] = useState("1d");
  const [error, setError] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const { enabled: helpEnabled } = useHelp();
  const { copy, direction, language } = useLocale();

  useEffect(() => {
    document.documentElement.lang = language;
    document.documentElement.dir = direction;
  }, [direction, language]);

  useEffect(() => {
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
    return <main className="center-state unavailable"><WarningCircle weight="duotone" /><h1>{copy.app.unavailableTitle}</h1><p>{copy.app.unavailableBody}</p></main>;
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand"><span className="brand-mark"><TrendUp weight="bold" /></span><div><h1>{copy.app.name}</h1><p>{copy.app.tagline}</p></div></div>
        <nav className="view-tabs" aria-label={`${copy.app.name} ${copy.tabs.market}`} role="tablist">
          <button role="tab" aria-selected={view === "market"} title={copy.hints.marketTab} onClick={() => setView("market")}>{copy.tabs.market}</button>
          <button role="tab" aria-selected={view === "analysis"} title={copy.hints.analysisTab} onClick={() => setView("analysis")}>{copy.tabs.analysis}</button>
        </nav>
        <div className="status-tools">
          <DataStatus status={latest?.data_status} fallbackAt={latest?.as_of} />
          <div className="header-actions"><HelpToggle /><SettingsButton onClick={() => setSettingsOpen(true)} /></div>
        </div>
      </header>

      {helpEnabled && <div className="help-mode-banner">{copy.help.banner}</div>}

      <main>
        {!latest ? <div className="loading-grid">{copy.app.loading}</div> : view === "market" ? (
          <>
            <section className="price-grid" aria-label={copy.cards.region}>{visibleCards.map((card) => <PriceCard key={card.instrument} card={card} />)}</section>
            <section className="market-layout">
              <article className="chart-panel">
                <header className="panel-header"><div><p className="eyebrow">{copy.chart.eyebrow}</p><h2>{copy.chart.title}</h2></div><div className="range-control" aria-label={copy.chart.rangeLabel}>{RANGES.map((key) => <button key={key} aria-pressed={range === key} title={copy.chart.rangeHints[key]} onClick={() => setRange(key)}>{copy.chart.ranges[key]}</button>)}</div></header>
                <MarketChart history={history} loading={historyLoading} tooltipsEnabled={settings.chartTooltips} />
                {history && !history.coverage_complete && <p className="coverage-note"><Clock /> {copy.chart.coverage}</p>}
              </article>
              <aside className="insight-panel">
                <header><span><ChartLineUp weight="duotone" /></span><div><p className="eyebrow">{copy.insight.eyebrow}</p><h2>{copy.insight.title}</h2></div></header>
                {usd?.references?.map((reference) => {
                  const title = reference.name === "gold" ? copy.insight.gold : copy.insight.aed;
                  const body = reference.name === "gold" ? copy.insight.goldHelp : copy.insight.aedHelp;
                  return (
                    <HelpTarget className="reference-row" title={title} body={body} key={reference.name}>
                      <div><span>{title}</span><strong>{formatNumber(reference.implied_value, language)}</strong></div>
                      <b className={reference.gap_pct > 0 ? "positive" : "negative"}>{formatPercent(reference.gap_pct, language)}</b>
                    </HelpTarget>
                  );
                })}
                <p className="insight-copy">{copy.insight.copy}</p>
                <button className="text-button" title={copy.hints.fullAnalysis} onClick={() => setView("analysis")}>{copy.insight.fullAnalysis} <span aria-hidden="true">←</span></button>
              </aside>
            </section>
            {settings.showTable && <section className="detail-table-wrap"><header><div><p className="eyebrow">{copy.table.eyebrow}</p><h2>{copy.table.title}</h2></div><span className="model-tag">{copy.table.model} {latest.model_version}</span></header><div className="table-scroll"><table><thead><tr><th>{copy.table.headers.asset}</th><th>{copy.table.headers.market}</th><th>{copy.table.headers.change}</th><th>{copy.table.headers.reference}</th><th>{copy.table.headers.state}</th></tr></thead><tbody>{tableCards.map((card) => <tr key={card.instrument}><td>{copy.cards.instruments[card.instrument] ?? card.instrument}</td><td>{formatNumber(card.market_value, language)}</td><td>{card.change_since_previous_pct == null ? "—" : formatPercent(card.change_since_previous_pct, language)}</td><td>{card.references?.[0] ? formatNumber(card.references[0].implied_value, language) : "—"}</td><td><span className="quality-dot" /> {copy.table.valid}</td></tr>)}</tbody></table></div></section>}
          </>
        ) : <AnalysisView analysis={latest.analysis} />}
      </main>

      <SiteFooter asOf={formatTime(latest?.as_of, language)} onOpenSettings={() => setSettingsOpen(true)} />
      <SettingsPanel open={settingsOpen} onClose={() => setSettingsOpen(false)} settings={settings} onChange={updateSetting} />
      <HelpDialog />
    </div>
  );
}
