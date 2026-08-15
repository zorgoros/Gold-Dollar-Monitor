# First Dashboard Design

## Status and merge record

- Status: APPROVED FOR SPECIFICATION; implementation waits for this file's review.
- Worktree: `.worktrees/dashboard-v1`
- Branch: `codex/dashboard-v1`
- Merge target: `main`
- Starting commit: `c54438c` (`Ignore local worktrees`)
- Merge gate: review the API/UI separation, test results, visual verification,
  and this document before merging. Do not merge the entire current main
  checkout; it contains unrelated work.

## Goal

Build the first public-facing, responsive Ayar Market dashboard. It shows the
same calculated market data as the bot in a readable Persian RTL interface.
The dashboard helps a reader answer three questions quickly: what are the
prices now, what changed, and can the data support the displayed analysis.

## Scope

The selected visual direction is ideation option 3, adapted as a hybrid:

- `بازار` is the default, fast-reading market board.
- A small embedded analysis summary gives the current gold-gap state and links
  to the deeper view.
- `تحلیل` is a separate view for comparison charts, independent USD routes,
  signal text, and data-quality context.

The first slice is read-only. It does not include user accounts, trades,
alerts, configuration editing, AI commentary, or deployment. It does not make
buy/sell recommendations.

## Information design

### Market view

1. Header: `عیار مارکت`, active view, a freshness label, and a small data
   quality state.
2. Price tape: USD free market, 18K gold, XAU/USD, and Emami coin. Each item
   shows value, percentage change since the last published price board where
   available, and source time.
3. Comparison chart: USD market versus the gold-implied USD and AED-implied
   USD. The two reference routes remain separately named. They are never
   averaged or shown as a composite.
4. Analysis summary: gold gap classification, value, confidence, and the
   existing Persian signal summary. If the analysis gate fails, it is replaced
   with the same short unavailable state used by reporting.

### Analysis view

1. Gold: 18K market gold versus theoretical 18K gold, gap, current signal,
   and chart range control.
2. USD: market USD versus gold-implied and AED-implied USD as distinct series,
   plus their individual gaps.
3. Coin: Emami market price, domestic-metal value, and domestic coin premium.
   The retired world-route premium remains non-public.
4. Data context: source time, quality state, model version, analysis basis,
   and clear unavailable states.

The default view uses few controls. Range controls reveal more detail only on
request. A missing or short history range is labelled as insufficient; the UI
does not draw invented chart points.

## Data and integrity rules

The existing service already stores sufficient source data:

- immutable snapshots and normalized quote provenance;
- derived metrics, including market values, reference values, and gaps;
- signals with Persian summaries, classifications, confidence, and reasons;
- quote timestamps and quality status; and
- historical metric rows for charts.

The dashboard must use those records as its source of truth. It must never
parse Telegram content, reimplement a formula in JavaScript, or change a
stored metric.

The persisted base analysis is suitable for the market board. The detailed
analysis view must re-use the existing reporting/session alignment path on the
latest snapshot. A closed Tehran session is never compared with an unaligned
live world ounce. If alignment fails, the API returns a structured unavailable
analysis state and the UI renders it plainly.

The present series may not yet contain 7 or 30 full days of data. History
responses include actual coverage, and the UI only enables a range when the
data supports it.

## Architecture and file boundaries

The dashboard has two independent layers:

```text
SQLite snapshots / metrics / signals
        ↓
src/market_monitor/web/        read-only Python projection and HTTP endpoints
        ↓ JSON only
dashboard/                     isolated React and TypeScript UI
```

`web/` owns data projection and HTTP transport. It may depend on repositories,
settings, reporting models, and the established analysis gate. It does not
format Telegram text and does not contain CSS or browser interaction logic.

`dashboard/` owns layout, Persian labels, browser state, chart rendering, and
fetching JSON. It contains no formulas, database calls, provider logic, or
Telegram code.

The web API starts as a dependency-free local read-only service. Its stable
contract is under `/api/v1/`:

- `GET /api/v1/latest` — current market-board cards and the gated analysis
  summary;
- `GET /api/v1/history?metrics=<names>&range=1d|7d|30d` — bounded metric
  points, coverage, and unavailable-series information; and
- `GET /api/v1/health` — latest snapshot time and dashboard data availability.

Vite serves the UI for local review and proxies `/api/v1/` to the Python
service. A later hosting decision can retain the UI unchanged and point it to a
deployed read-only API.

## UX and visual requirements

- RTL Persian by default; values remain readable with a tabular numeral style.
- Dark graphite base, warm off-white type, steel-blue dividers, muted jade for
  positive movement, and restrained vermilion for elevated gaps.
- No gradients, glass effects, decorative gauges, emoji, neon-pink accents, or
  card-inside-card layouts.
- Text and symbols accompany every colour-only state.
- Keyboard-visible controls, sensible focus order, and responsive layouts at
  375px, 768px, 1024px, and 1440px.
- Charts use visible values and labels, accessible legends, a tooltip, and a
  clear selected range. The UI respects reduced-motion preferences.

## Error handling

- No stored snapshot: return a structured unavailable response; show a simple
  no-data screen.
- Optional AED or coin data missing: hide only the affected module and state
  why; do not fail the whole board.
- Analysis gate failed: show the report-safe unavailable state, not stale
  analytical values.
- Bad history request: return a JSON validation error. The UI keeps the last
  valid chart visible and exposes a short error message.

## Testing and acceptance

- Repository/projection tests assert that card payloads preserve distinct USD
  reference routes, expose quality and source time, and never expose the
  retired world coin premium.
- API tests cover latest data, no data, gated analysis, optional-metric absence,
  supported ranges, invalid ranges, and insufficient history.
- Browser checks cover RTL layout, view switching, range changes, chart loading,
  unavailable states, keyboard navigation, and no browser-console errors.
- The full Python suite, Ruff, format check, and mypy must pass.
- Visual verification compares the rendered 1440px dashboard with the selected
  option-3 hierarchy, then checks 1024px, 768px, and 375px for readability.

## Explicit non-goals

- No production deployment or hosting configuration in this slice.
- No public write endpoints, authentication, admin screen, or configuration UI.
- No chart series that lacks stored coverage.
- No new economic formula, threshold, signal model, or AI-derived number.
