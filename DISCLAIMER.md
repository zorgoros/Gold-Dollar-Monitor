# Disclaimer and data notice

Plain-language notes, not legal advice. If you deploy this publicly or
commercially, check your own jurisdiction's rules.

## Not financial advice

This software computes arithmetic relationships between published prices. It
does not forecast, recommend, or advise. Output is an analytical indicator, not
a valuation, a signal to trade, or a statement of fair value.

Every report carries:

> این گزارش یک شاخص تحلیلی مبتنی بر روابط قیمت است و توصیه خرید یا فروش نیست.
> *(This report is an analytical indicator based on price relationships and is not
> a recommendation to buy or sell.)*

Many jurisdictions regulate investment advice and require a licence to provide
it. Do not add buy/sell recommendations, price targets, or portfolio guidance to
this output unless you are licensed to give them.

The thresholds shipped in `config/default.toml` are **provisional placeholders**
chosen for plausibility, not derived from historical data. Signal confidence is
capped at 0.6 in code for that reason.

## Data sources

Retrieved at runtime from publicly accessible endpoints. Not affiliated with,
endorsed by, or sponsored by any of them.

| Source | Used for | Access |
|---|---|---|
| [TGJU](https://www.tgju.org) | USD, 18K gold, world ounce, Emami coin | public JSON endpoint, no key |
| [gold-api.com](https://api.gold-api.com) | world ounce fallback | public JSON endpoint, no key |

Terms:

- **No redistribution of source data.** This project does not republish, mirror,
  or resell any provider's dataset. It fetches the four values it needs and
  publishes *derived* indicators.
- **Test fixtures** in `tests/fixtures/` are small trimmed samples (a few KB)
  captured once for offline testing, kept only to pin response shapes.
- **Polling is light** — four requests a day at the default schedule, well
  inside any normal fair-use expectation. Do not raise the frequency to a level
  that burdens a free service.
- Provider terms of service can change. If you run this, satisfy yourself that
  your usage complies with theirs. The endpoints were reachable without
  authentication or a stated rate limit when verified on 2026-08-12
  (`docs/PROVIDERS.md`).

## Accuracy

Prices come from third parties and may be wrong, delayed, or stale. Outside
Tehran market hours the Iranian instruments are the **previous close**. The
software labels this rather than hiding it, but it cannot make stale data
fresh. Failed validation blocks publication instead of guessing.

No warranty — see LICENSE.

## Personal data

None is collected, stored, or transmitted. The database holds market prices and
run metadata only. The Telegram bot posts to a channel; it does not read user
messages, and it stores nothing about subscribers.

## Operating a public channel

If you publish these reports to an audience: keep the disclaimer visible, don't
present the output as a forecast, and be aware that publishing market commentary
may itself be regulated where you live.
