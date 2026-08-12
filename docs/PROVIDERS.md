# Market data providers

**Verified live on 2026-08-12.** Every endpoint below was actually fetched, not read from
documentation. Captured responses live in `tests/fixtures/`.

Re-verify before trusting this doc after ~3 months. TGJU ships no versioned API contract and
has changed symbol behaviour before.

---

## TL;DR — symbol mapping

| Our instrument | Provider symbol | JSON path (primary endpoint) | Unit as returned | Conversion to canonical |
|---|---|---|---|---|
| `usd_irr_free` | `price_dollar_rl` | `current.price_dollar_rl.p` | **rial (IRR)** | **÷ 10** |
| `gold_18k` | `geram18` | `current.geram18.p` | **rial (IRR)** | **÷ 10** |
| `xau_usd` | `ons` | `current.ons.p` | **USD / troy ounce** | none |
| `emami_coin` | `sekee` | `current.sekee.p` | **rial (IRR)** | **÷ 10** |
| `aed_irt` | `price_aed` | `current.price_aed.p` | **rial (IRR)** | **÷ 10** |
| `eur_irt` | `price_eur` | `current.price_eur.p` | **rial (IRR)** | **÷ 10** |
| `try_irt` | `price_try` | `current.price_try.p` | **rial (IRR)** | **÷ 10** |
| `jpy_irt` | `price_jpy` | `current.price_jpy.p` | **rial per 100 JPY** | **÷ 10 then ÷ 100** |

Primary endpoint is `https://call1.tgju.org/ajax.json` for all eight. The four FX symbols
were verified live on 2026-08-12 alongside the original four.

> **The 10x trap.** TGJU quotes all Iranian instruments in **rial**, while Iranian users,
> news sites and everyday speech quote **toman**. Publishing the raw number as toman is a
> 10x error. `ons` is the only one that needs no conversion.

> **The 100x trap (`price_jpy`).** The yen is quoted **per 100 yen**, not per yen. Read
> per-yen it is a 100x error — an order of magnitude worse than the rial trap, and it does
> not look absurd on inspection the way a billion-toman coin does. Verified arithmetically
> on 2026-08-12: `diff_usd_jpy` = 159.09 and `price_dollar_rl` = 1,878,000 rial, so one yen
> is 1,878,000 / 159.09 = **11,805 rial**. Observed `price_jpy` = 1,176,000 rial, and
> 1,176,000 / 11,805 = **99.62** — i.e. a hundred yen. Confirmed independently by the
> ordering of the FX board: at ~117,600 toman `price_jpy` sits between the euro and the
> dirham, which is impossible for a single yen.
>
> The unit is declared as `rial/100jpy` in the adapter and converted in
> `normalization/units.py`. Canonical storage is toman per **one** yen so every currency
> shares one scale; the report multiplies back to 100 and labels it (§6).

### Cross-checks used to confirm the four new symbols are rial-per-unit

All against the same capture, USD = 187,800 toman:

| Symbol | toman | independent check | agreement |
|---|---|---|---|
| `price_aed` | 51,161 | 187,800 / 3.6725 peg = 51,137 | 0.05% |
| `price_eur` | 216,760 | 1.1543 `diff_eur_usd` × 187,800 = 216,777 | 0.01% |
| `price_try` | 3,910 | 187,800 / 47.756 `diff_usd_try` = 3,932 | 0.6% |
| `price_jpy` | 1,176 per yen | 187,800 / 159.09 `diff_usd_jpy` = 1,180 | 0.4% |

---

## Unit verification (how we know it is rial)

Two independent confirmations, because this is the one thing that will silently ship wrong.

**1. The provider says so.** Each `https://www.tgju.org/profile/<symbol>` page renders an
explicit unit field, `واحد پولی` ("currency unit"):

| Symbol | `واحد پولی` | Meaning |
|---|---|---|
| `price_dollar_rl` | `ریال` | rial |
| `geram18` | `ریال` | rial |
| `sekee` | `ریال` | rial |
| `ons` | `دلار` | USD |

The FAQ block on the dollar page also spells it out inline: `1,878,000 ریال`.
Captured verbatim in `tests/fixtures/tgju_profile_price_dollar_rl.json`.

**2. The arithmetic only works in rial.** Using the values captured at 2026-08-12 10:10 UTC:

- `ons` = 4,393.47 USD/oz → 4393.47 / 31.1035 = **141.25 USD per gram of pure gold**
- 18K is 0.750 fine → 141.25 × 0.75 = **105.94 USD per gram of 18K**
- `price_dollar_rl` = 1,878,000 read as rial → **187,800 toman per USD**
- Implied 18K gram ≈ 105.94 × 187,800 = **≈19.9M toman**
- Observed live 18K (`tgju_gold_irg18` = 197,621,000 rial) → **19.76M toman**, i.e. **0.7% off parity**

Read as toman instead, the observed figure would be 197.6M toman per gram against a ~19.9M
parity — off by exactly an order of magnitude. Same check on the coin: `sekee`
1,894,850,000 rial = 189.5M toman, against an intrinsic of ~192.9M toman
(Emami = 8.133 g at 0.900 fine = 9.76 g of 18K-equivalent), a 1.8% discount. Plausible.
As toman it would be 1.89 **billion** toman per coin. Absurd.

Conversion is exact and lossless: `toman = rial / 10`. Rial values for these instruments are
always multiples of 10, so integer division is safe.

---

## Endpoint 1 — `call1.tgju.org/ajax.json` (PRIMARY)

```
GET https://call1.tgju.org/ajax.json
```

- **Auth:** none. No API key, no token, no cookie.
- **Headers:** none required. Verified working with **no** `User-Agent` header at all, and with
  the default `curl/8.7.1` UA. No browser spoofing needed.
- **HTTPS:** clean. TLS 1.3, HTTP/2, cert `CN=tgju.org` issued by Google Trust Services.
  No custom CA, no cipher pinning, no special TLS handling.
- **Methods:** `GET` and `HEAD` return 200. `POST` returns **405**.
- **Fixture:** `tests/fixtures/tgju_call1_ajax.json`

### Response shape

```jsonc
{
  "current": {                       // 762 symbols keyed by slug
    "price_dollar_rl": {
      "p":  "1,878,000",             // price   (string)
      "h":  "1,880,200",             // day high (string)
      "l":  "1,851,800",             // day low  (string)
      "d":  "0",                     // change  (string)
      "dp": 0,                       // change percent (NUMBER, not string)
      "dt": "",                      // "high" | "low" | "" (direction)
      "t":   "۲۰ مرداد",             // display time, Persian digits
      "t_en": "11 Aug",              // display time, Latin
      "ts":  "2026-08-11 00:00:00"   // machine timestamp  <- use this one
    }
  },
  "tolerance_low":  [ ... ],         // 4 movers, unrelated
  "tolerance_high": [ ... ],
  "last":           [ ... ]
}
```

Price path is `current.<symbol>.p`. Timestamp path is `current.<symbol>.ts`.

### Price string format — NOT uniform, parse defensively

Thousands separators are inconsistent **between symbols in the same response**:

| Symbol | Captured `p` | Separators? | Decimals? |
|---|---|---|---|
| `price_dollar_rl` | `"1,878,000"` | yes | no |
| `geram18` | `"192,056,000"` | yes | no |
| `sekee` | `"1,894,850,000"` | yes | no |
| `ons` | `"4,393.47"` | yes | 2 |
| `tgju_gold_irg18` | `"197621000"` | **no** | no |
| `tether_gold_xaut` | `"4371.50"` | **no** | 2 |

Rule: strip `,` unconditionally, then parse as float (not int — `ons` has decimals).
Never assume a comma is present, and never assume it is absent.

`p`, `h`, `l`, `d` are strings. `dp` is a JSON number. Don't parse them the same way.

### Staleness — the real gotcha

At capture time (2026-08-12 10:10 UTC), of 762 symbols: 205 carried a `ts` of today,
232 carried `2026-08-11 00:00:00`.

Iranian instruments (`price_dollar_rl`, `geram18`, `sekee`) only tick during Tehran market
hours. Outside them, `ts` collapses to **the previous day at midnight** — a date, not a
time — and `d`/`dp` go to `0`. All three of our rial instruments were in exactly that state
when captured. Meanwhile `ons` carried a live second-resolution `ts` of `2026-08-12 10:10:27`.

**Consumers must read `ts` and treat the value as a previous close, not a live quote.**
A `00:00:00` time component is the signal. Do not infer freshness from the request time.

The four FX symbols behave exactly like the other rial instruments: on 2026-08-12 at 15:33
Tehran, `price_aed`, `price_eur`, `price_try` and `price_jpy` all carried
`2026-08-11 00:00:00` while `ons` carried a live second-resolution tick.

> **`00:00:00` is a date, not a closing bell.** TGJU zeroes the clock; it does not report
> when the session actually ended. Anchoring anything on that midnight puts it ~17 hours
> before the prices it describes. `analysis/session.py` moves the marker to
> `[analysis].tehran_session_close` before aligning a world-ounce observation to it, which
> is why v1.1 can pair a closed Iranian session with the ounce that was true at the time
> instead of the one printing right now.

### Rate limits

No documented limit, no `X-RateLimit-*` or `Retry-After` headers. 12 rapid sequential
requests all returned 200.

The response is Cloudflare-edge cached: `cache-control: max-age=300`, `cf-cache-status: HIT`.
One observed HIT had `age: 1151` — i.e. served well past its max-age. Appending a cache-buster
query param (`?cb=<random>`) forces a `MISS` and fresh data.

Practical guidance: **poll at 60s at most, treat data as up to ~5 minutes stale**, and don't
cache-bust on every call — you gain nothing on rial instruments that only move a few times a
day, and it puts you on the origin instead of the edge.

## Endpoint 2 — `call3.tgju.org/ajax.json` (HOT MIRROR)

```
GET https://call3.tgju.org/ajax.json
```

Byte-for-byte equivalent mirror of `call1`. Verified in the same second: identical key set
(762 symbols both), identical values and timestamps for all four target symbols. Same auth
(none), same headers (none), same 405-on-POST, same caching.

Use as a **failover host only**. There is no benefit to querying both — same data. `call2`,
`call4`, `call5` were not tested.

Fixture: `tests/fixtures/tgju_call3_ajax.json`

## Endpoint 3 — `api.tgju.org/.../summary-table-data/<symbol>` (HISTORY, not live)

```
GET https://api.tgju.org/v1/market/indicator/summary-table-data/<symbol>
```

- **Auth:** none. Returns 200 with no key and no `User-Agent`.
- **CORS:** `access-control-allow-origin: *`, so it is browser-callable.
- **Caching:** `cache-control: no-cache` (unlike ajax.json).
- **Fixture:** `tests/fixtures/tgju_api_summary_table_price_dollar_rl.json`

This is **daily OHLC history, not a live quote**. The newest row is the previous session's
close. Do not use it for current price — use `ajax.json`.

```jsonc
{
  "draw": null,
  "recordsTotal": 3925,
  "recordsFiltered": 3925,
  "data": [
    ["1,852,100","1,851,800","1,880,200","1,878,000",
     "<span class=\"high\" dir=\"ltr\">22000</span>",
     "<span class=\"high\" dir=\"ltr\">1.19%</span>",
     "2026/08/11","1405/05/20"]
  ]
}
```

Columns are **positional, unnamed** (DataTables server-side format):

| # | Meaning | Notes |
|---|---|---|
| 0 | open | comma-separated string |
| 1 | low | |
| 2 | high | |
| 3 | **close** | matches `ajax.json` `.p` for that day |
| 4 | change | **HTML string**, must be tag-stripped |
| 5 | change percent | **HTML string**, must be tag-stripped |
| 6 | Gregorian date | `YYYY/MM/DD` |
| 7 | Jalali date | `YYYY/MM/DD` |

Row 0 is newest. Units match `ajax.json` exactly (rial for Iranian symbols, USD for `ons`) —
confirmed: `geram18` row-0 close `192,056,000` equals the `ajax.json` value.

**Payload sizes are large and unbounded.** No pagination parameter was found; the endpoint
returns full history every time:

| Symbol | Rows | Size |
|---|---|---|
| `price_dollar_rl` | 3,925 | 643 KB |
| `geram18` | 3,477 | 604 KB |
| `sekee` | 4,263 | 761 KB |
| `ons` | 12,111 | **2.0 MB** |

Fetch these on a backfill job, not on a polling loop.

## Endpoint 4 — `www.tgju.org/profile/<symbol>` (HTML, evidence only)

```
GET https://www.tgju.org/profile/<symbol>
```

Returns `text/html; charset=UTF-8`, ~880 KB–1.5 MB per page. No auth.

Price is at `span[data-col="info.last_trade.PDrCotVal"]`; the unit is in the `واحد پولی` row.

**Do not scrape this for prices.** It is 7x the payload of `ajax.json` for the same number,
and it is markup that will break on any redesign. Its value here is that it is the only
source that states the **unit** explicitly, which is why it was used for verification and why
the fragments are preserved in `tests/fixtures/tgju_profile_price_dollar_rl.json`.

---

## Fallbacks for `xau_usd`

`xau_usd` is the one instrument with real independent alternatives, since international gold
spot is not Iran-specific.

### Primary fallback — gold-api.com (recommended)

```
GET https://api.gold-api.com/price/XAU
```

- **Auth:** none. No key, no signup, no `User-Agent` required.
- **Response:** 177 bytes, flat, stable.

```json
{"currency":"USD","currencySymbol":"$","exchangeRate":1.0,"name":"Gold",
 "price":4394.399902,"symbol":"XAU","updatedAt":"2026-08-12T06:39:08Z",
 "updatedAtReadable":"a few seconds ago"}
```

- **Price path:** `price` — a **JSON number**, not a string. No separators to strip. Note the
  float noise (`4394.399902`); round for display.
- **Timestamp:** `updatedAt`, ISO-8601 UTC. Clean to parse.
- **Agreement with TGJU:** 4394.40 vs TGJU `ons` 4,393.47 at the same moment — **0.02% apart**.
  Excellent as a cross-check or a substitute.
- **Limits:** none published, no rate-limit headers. Treat as best-effort; it is a free
  service with no SLA and no status page.
- **Fixture:** `tests/fixtures/goldapi_xau_usd.json`

Because the shapes differ (`price` number here vs `current.ons.p` comma-string at TGJU), the
adapter must normalise both to float — do not share a parser.

### Secondary fallback — CoinGecko PAXG (proxy, use with care)

```
GET https://api.coingecko.com/api/v3/simple/price?ids=pax-gold&vs_currencies=usd&include_last_updated_at=true
```

- **Auth:** none on the free tier.
- **Price path:** `["pax-gold"].usd` (number). Captured: `4385.23`.
- **Agreement:** 0.2% below TGJU `ons`.
- **Caveat:** PAX Gold is a *token backed by* gold, not spot itself. It carries its own
  premium/discount and can decouple during crypto-market stress. Use only as a third opinion
  or a liveness sanity check, never as the published `xau_usd`.
- **Limits:** free tier is roughly 5–15 requests/minute and CoinGecko returns **429** when
  exceeded. Back off properly.
- **Fixture:** `tests/fixtures/coingecko_paxg_usd.json`

### Sources tested and rejected

| Source | Result |
|---|---|
| `data-asg.goldprice.org/dbXRates/USD` | **403 Forbidden** — blocks plain clients, needs browser headers. Skipped rather than fight it. |
| `forex-data-feed.swissquote.com/.../XAU/USD` | **Timeout** (8s, no response). |
| `api.metals.live/v1/spot` | **Dead** — connection fails immediately. |

### No independent fallback exists for the rial instruments

This is a genuine limitation, not an oversight.

| Attempted | Result |
|---|---|
| `bonbast.com/json` | Returns `{"rest":"1"}` — requires a per-session token scraped from the page. Not a clean no-key source. |
| `alanchand.com/api/currencies` | **404** — endpoint no longer exists. |

`usd_irr_free`, `gold_18k` and `emami_coin` are therefore **single-sourced on TGJU**, with
`call3` as a host-level mirror only. A TGJU outage or a bad print takes all three down
together, and there is nothing to cross-check a suspicious value against.

Mitigation without a second provider: the internal consistency check from the verification
section above works as a live sanity gate. Gold 18K in toman should stay within a few percent
of `ons / 31.1035 × 0.75 × usd_toman`, and the Emami coin within a few percent of its
9.76 × 18K-gram intrinsic. Alert when either ratio leaves a sane band — that catches both a
10x unit regression and a stale/garbage print, using only data you already fetch.

---

## Limitations summary

1. **Rial vs toman is the highest-risk defect in this integration.** Seven of eight
   instruments need `/10`. Assert on the ratio checks above rather than trusting the field.
   `price_jpy` needs `/100` on top of that — the only symbol not quoted per single unit,
   and the one whose error would be least visible on inspection.
2. **Rial instruments are not live outside Tehran market hours.** Read `ts`; a `00:00:00`
   time component means previous close.
3. **Price string format varies per symbol** in the same response. Always strip commas, always
   parse as float.
4. **No API contract, no versioning, no changelog.** TGJU can change slugs or shapes without
   notice. `price_dollar_rl` / `geram18` / `ons` / `sekee` were all confirmed present and
   correct on 2026-08-12.
5. **Edge caching hides staleness.** `ajax.json` can be served with `age` well past its
   300s `max-age`.
6. **No published rate limits** — which means no guarantees either. Be conservative; 60s
   polling is plenty for instruments that move a few times a day.
7. **Iranian instruments are single-sourced.** No independent free fallback was found. This
   now covers seven symbols rather than three, so a TGJU outage takes the whole FX board
   down with the gold complex. The dirham is a partial mitigation for the *analysis* — it
   reaches a USD figure through a different mechanism — but not for *availability*, since
   it arrives over the same connection.
8. `summary-table-data` returns **full history, up to 2 MB**, on every call. Backfill only.

## Symbols worth knowing (not currently mapped)

Found while verifying; noted so they aren't rediscovered later. All in rial.

| Symbol | What it is | Why it might matter |
|---|---|---|
| `tgju_gold_irg18` | TGJU's own live 18K gold index | **Ticks intraday when `geram18` is frozen at previous close.** Note it returns `p` with no thousands separators. |
| `tgju_gold_irg18_buy` | 18K buy-side | bid/ask spread |
| `geram24` | 24K gold per gram | |
| `sekeb` | Bahar Azadi coin | trades just under Emami, a useful sanity companion |
| `mesghal` | gold per mesghal (4.6083 g) | internally consistent with `geram18 = mesghal / 4.3318` |
| `retail_sekee` / `sekee_real` | retail / "real" Emami quotes | spread against `sekee` |
| `diff_usd_aed` | market USD/AED cross | read 3.6715 on 2026-08-12 vs the 3.6725 peg — useful as a peg-drift monitor, not as the peg itself |
| `diff_usd_jpy`, `diff_eur_usd`, `diff_usd_try` | world crosses | how the per-unit checks above were computed |
| `usdt-irr` | Tether/rial | **dead** — `ts` of 2020-11-11. Any future USDT work needs a different source (EXTENSIONS) |

If `gold_18k` needs to be live rather than previous-close, `tgju_gold_irg18` is the swap —
but it is a slightly different series (TGJU's own index, ~2.9% above `geram18` at capture),
so it is a product decision, not a drop-in.
