import { Coins, CurrencyDollar, Diamond, GlobeHemisphereWest } from "@phosphor-icons/react";
import { formatNumber, formatPercent } from "../format.js";
import { useLocale } from "./LocaleProvider.jsx";

const META = {
  USD_IRT: { unit: "toman", Icon: CurrencyDollar },
  GOLD_18K: { unit: "toman", Icon: Diamond },
  XAU_USD: { unit: "dollar", Icon: GlobeHemisphereWest },
  EMAMI_COIN: { unit: "toman", Icon: Coins },
};

export function PriceCard({ card }) {
  const { copy, language } = useLocale();
  const meta = META[card.instrument] ?? {
    unit: "",
    Icon: CurrencyDollar,
  };
  const label = copy.cards.instruments[card.instrument] ?? card.instrument;
  const change = card.change_since_previous_pct;
  const tone = change == null ? "neutral" : change >= 0 ? "positive" : "negative";
  return (
    <article className="price-card">
      <header>
        <span className="instrument-icon" aria-hidden="true"><meta.Icon weight="duotone" /></span>
        <span>{label}</span>
        <span className={`change change--${tone}`}>
          {change == null ? copy.cards.noHistory : formatPercent(change, language)}
        </span>
      </header>
      <div className="price-row">
        <strong>{formatNumber(card.market_value, language)}</strong>
        <small>{copy.cards.units[meta.unit] ?? ""}</small>
      </div>
      <div className="card-foot">
        <span>{card.data_quality === "OK" ? copy.cards.valid : copy.cards.latest}</span>
        <i aria-hidden="true" />
      </div>
    </article>
  );
}
