import { CheckCircle, WarningCircle } from "@phosphor-icons/react";
import { formatNumber, formatPercent } from "../format.js";
import { useLocale } from "./LocaleProvider.jsx";

function Metric({ label, value, kind = "number" }) {
  const { language } = useLocale();
  const formatted = kind === "percent"
    ? formatPercent(value, language)
    : formatNumber(value, language);
  return <div className="analysis-metric"><span>{label}</span><strong>{formatted}</strong></div>;
}

/**
 * Renders only narratives selected by the deterministic backend. The UI does
 * not infer a market conclusion from numbers or thresholds.
 */
function NarrativeContext({ narratives = [], label }) {
  const { copy, language } = useLocale();
  const text = narratives
    .map((narrative) => narrative?.text?.[language])
    .filter(Boolean);
  return (
    <div className="analysis-context">
      <strong>{label ?? copy.analysis.context}</strong>
      {text.length
        ? text.map((sentence) => <p key={sentence}>{sentence}</p>)
        : <p>{copy.analysis.contextUnavailable}</p>}
    </div>
  );
}

export function AnalysisView({ analysis }) {
  const { copy, language } = useLocale();
  if (analysis?.state !== "READY") {
    return <section className="unavailable analysis-unavailable"><WarningCircle weight="duotone" /><h2>{copy.analysis.unavailableTitle}</h2><p>{copy.analysis.unavailableBody}</p></section>;
  }
  const m = analysis.metrics;
  const narratives = analysis.narratives ?? {};
  return (
    <div className="analysis-view">
      <section className="analysis-lead">
        <p className="eyebrow">{copy.analysis.detailEyebrow}</p>
        <h2>{copy.analysis.pathsTitle}</h2>
        <p>{copy.analysis.pathsIntro}</p>
        <div className="analysis-route-grid">
          <div className="analysis-route-card"><span>{copy.analysis.market}</span><strong>{formatNumber(m.usd_market, language)}</strong><small>{copy.analysis.registeredRate}</small></div>
          <div className="analysis-route-card"><span>{copy.analysis.goldPath}</span><strong>{formatNumber(m.usd_gold_implied, language)}</strong><small>{formatPercent(m.usd_gap_pct, language)} {copy.analysis.marketGap}</small></div>
          <div className="analysis-route-card"><span>{copy.analysis.aedPath}</span><strong>{formatNumber(m.usd_aed_implied, language)}</strong><small>{formatPercent(m.aed_usd_gap_pct, language)} {copy.analysis.marketGap}</small></div>
        </div>
        <NarrativeContext narratives={narratives.overview} label={copy.analysis.conclusion} />
      </section>
      <section className="analysis-block">
        <div className="section-title"><div><p className="eyebrow">{copy.analysis.goldEyebrow}</p><h3>{copy.analysis.goldTitle}</h3></div><CheckCircle weight="duotone" /></div>
        <div className="metric-strip"><Metric label={copy.analysis.marketGold} value={m.gold_18k_market} /><Metric label={copy.analysis.theoretical} value={m.gold_18_theoretical} /><Metric label={copy.analysis.gap} value={m.gold_gap_pct} kind="percent" /></div>
        <NarrativeContext narratives={narratives.gold} />
      </section>
      <section className="analysis-block">
        <div className="section-title"><div><p className="eyebrow">{copy.analysis.coinEyebrow}</p><h3>{copy.analysis.coinTitle}</h3></div><WarningCircle weight="duotone" /></div>
        {m.coin_market ? <div className="metric-strip"><Metric label={copy.analysis.coinMarket} value={m.coin_market} /><Metric label={copy.analysis.metalValue} value={m.coin_intrinsic_domestic} /><Metric label={copy.analysis.domesticPremium} value={m.coin_premium_domestic_pct} kind="percent" /></div> : <p className="muted-copy">{copy.analysis.noCoin}</p>}
        <NarrativeContext narratives={narratives.coin} />
      </section>
      <section className="signal-list">
        <h3>{copy.analysis.notable}</h3>
        {analysis.signals?.map((signal, index) => {
          const signalText = language === "fa"
            ? signal.summary_fa
            : copy.analysis.classifications?.[signal.classification] ?? signal.classification;
          return <article key={`${signal.instrument}-${index}`}><span className={`severity severity--${Math.min(signal.severity, 3)}`}>{signal.severity}</span><div><strong>{signalText}</strong><small>{copy.analysis.confidence} {formatPercent(signal.confidence * 100, language)}</small></div></article>;
        })}
      </section>
    </div>
  );
}
