import { Coins, CurrencyDollar, Diamond, GlobeHemisphereWest } from "@phosphor-icons/react";
import { formatNumber, formatPercent } from "../format.js";

const META = {
  USD_IRT: { label: "دلار آزاد", unit: "تومان", Icon: CurrencyDollar },
  GOLD_18K: { label: "طلای ۱۸ عیار", unit: "تومان", Icon: Diamond },
  XAU_USD: { label: "اونس جهانی", unit: "دلار", Icon: GlobeHemisphereWest },
  EMAMI_COIN: { label: "سکه امامی", unit: "تومان", Icon: Coins },
};

export function PriceCard({ card }) {
  const meta = META[card.instrument] ?? {
    label: card.instrument,
    unit: "",
    Icon: CurrencyDollar,
  };
  const change = card.change_since_previous_pct;
  const tone = change == null ? "neutral" : change >= 0 ? "positive" : "negative";
  return (
    <article className="price-card">
      <header>
        <span className="instrument-icon" aria-hidden="true"><meta.Icon weight="duotone" /></span>
        <span>{meta.label}</span>
        <span className={`change change--${tone}`}>
          {change == null ? "بدون سابقه" : formatPercent(change)}
        </span>
      </header>
      <div className="price-row">
        <strong>{formatNumber(card.market_value)}</strong>
        <small>{meta.unit}</small>
      </div>
      <div className="card-foot">
        <span>{card.data_quality === "OK" ? "داده معتبر" : "آخرین داده"}</span>
        <i aria-hidden="true" />
      </div>
    </article>
  );
}
