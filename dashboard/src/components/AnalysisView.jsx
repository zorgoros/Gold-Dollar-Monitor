import { ArrowLeft, CheckCircle, WarningCircle } from "@phosphor-icons/react";
import { formatNumber, formatPercent } from "../format.js";

function Metric({ label, value, kind = "number" }) {
  return <div className="analysis-metric"><span>{label}</span><strong>{kind === "percent" ? formatPercent(value) : formatNumber(value)}</strong></div>;
}

export function AnalysisView({ analysis }) {
  if (analysis?.state !== "READY") {
    return <section className="unavailable analysis-unavailable"><WarningCircle weight="duotone" /><h2>تحلیل این نوبت در دسترس نیست</h2><p>داده‌های هم‌زمان کافی نیست. قیمت‌های بازار همچنان نمایش داده می‌شوند.</p></section>;
  }
  const m = analysis.metrics;
  return (
    <div className="analysis-view">
      <section className="analysis-lead">
        <p className="eyebrow">نمای تفصیلی</p>
        <h2>تحلیل مسیرهای دلار</h2>
        <p>قیمت بازار با دو مرجع مستقل مقایسه می‌شود. این مسیرها با هم ترکیب نمی‌شوند.</p>
        <div className="analysis-route-grid">
          <div><span>بازار</span><strong>{formatNumber(m.usd_market)}</strong></div>
          <ArrowLeft aria-hidden="true" />
          <div><span>مسیر طلا</span><strong>{formatNumber(m.usd_gold_implied)}</strong><small>{formatPercent(m.usd_gap_pct)}</small></div>
          <div><span>مسیر درهم</span><strong>{formatNumber(m.usd_aed_implied)}</strong><small>{formatPercent(m.aed_usd_gap_pct)}</small></div>
        </div>
      </section>
      <section className="analysis-block">
        <div className="section-title"><div><p className="eyebrow">برابری ارزش</p><h3>تحلیل طلا</h3></div><CheckCircle weight="duotone" /></div>
        <div className="metric-strip"><Metric label="طلای بازار" value={m.gold_18k_market} /><Metric label="ارزش نظری" value={m.gold_18_theoretical} /><Metric label="شکاف" value={m.gold_gap_pct} kind="percent" /></div>
      </section>
      <section className="analysis-block">
        <div className="section-title"><div><p className="eyebrow">ارزش ذاتی داخلی</p><h3>تحلیل سکه</h3></div><WarningCircle weight="duotone" /></div>
        {m.coin_market ? <div className="metric-strip"><Metric label="سکه بازار" value={m.coin_market} /><Metric label="ارزش فلز" value={m.coin_intrinsic_domestic} /><Metric label="حباب داخلی" value={m.coin_premium_domestic_pct} kind="percent" /></div> : <p className="muted-copy">داده سکه در این نوبت موجود نیست.</p>}
      </section>
      <section className="signal-list">
        <h3>نشانه‌های قابل توجه</h3>
        {analysis.signals?.map((signal) => <article key={signal.instrument}><span className={`severity severity--${Math.min(signal.severity, 3)}`}>{signal.severity}</span><div><strong>{signal.summary_fa}</strong><small>اطمینان {formatPercent(signal.confidence * 100)}</small></div></article>)}
      </section>
    </div>
  );
}
