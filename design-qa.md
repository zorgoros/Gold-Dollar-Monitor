# Dashboard Design QA

- Source visual truth: `/Users/mostafasaeedan/.codex/generated_images/01a00560-b1bd-7cb3-ba7d-76d3b524fc85/exec-ebae5628-a79f-470a-9431-920e56c7a17b.png`
- Implementation: `http://127.0.0.1:4173/`
- Browser capture: `/private/tmp/ayar-dashboard-implementation-v2.png`
- Combined comparison: `/private/tmp/ayar-dashboard-comparison-v2.png`
- State: Persian RTL market view with populated bot-generated preview data
- CSS target viewport: 1440 × 1024, device scale factor 1
- Source pixels: 1487 × 1058
- Implementation capture pixels: 1497 × 1317
- Normalization: both images were placed on equal 1497 × 1317 canvases with
  aspect-preserving padding before the side-by-side comparison.

## Full-view comparison

The implementation keeps the selected hierarchy: quiet status header, central
market/analysis switch, four leading values, a dominant comparison chart, a
compact analysis rail, and a detailed table. It uses the same graphite, warm
white, steel blue, gold, jade, and vermilion language without copying the source
component construction. The detailed analysis is a separate interactive view.

## Required fidelity surfaces

- Fonts and typography: Vazirmatn supplies clear Persian hierarchy and tabular
  figures. Small labels remain readable at the tested desktop and mobile sizes.
- Spacing and rhythm: 14 px section gaps, restrained 7 px frames, and a stable
  4/2/1-column responsive progression keep density controlled.
- Colors and tokens: the source palette is mapped to named CSS tokens; there are
  no gradients, glass effects, or color-only status messages.
- Images and assets: the source has no raster imagery. All interface icons use
  Phosphor; the quantitative chart uses Recharts.
- Copy and content: labels are direct Persian UI copy. The two USD reference
  routes remain explicitly separate, and the page states that it is not advice.

Focused-region comparison was not required. The header, cards, chart, analysis
rail, and table are readable in the full-size combined comparison, and the
analysis tab was checked separately through the live DOM.

## Comparison history

### Iteration 1 — blocked

- [P2] The analysis rail appeared on the left while the source hierarchy placed
  it on the right. Fixed by making the two-column composition LTR while keeping
  both child panels RTL.
- [P2] The chart used a zero-based Y scale, which flattened meaningful market
  differences. Fixed with a data-driven domain plus a 1,000-toman margin.
- [P2] The mobile page had horizontal overflow from wide tables. Fixed with a
  contained scrolling table and hidden page-level overflow.

### Iteration 2 — passed

The second browser capture shows the analysis rail on the right, the chart on
the left, a useful 179k–189k scale, and no desktop console warnings or errors.
At 375 × 812, all four cards and both tabs are visible, the document width stays
inside the viewport, and the mobile capture has no persistent-control overflow.

Primary interactions tested: switch `بازار`/`تحلیل`; select the 7-day range;
render API-backed cards; render gated/unavailable states. Console errors and
warnings checked: none.

### Iteration 3 — owner debugging pass passed

- Chart X coordinates and ticks use the requested API `start`/`end` window.
  Partial 7-day and 30-day history stays at its true database position, and the
  incomplete-coverage note remains visible.
- The hover panel renders the Persian calendar date and Tehran clock in separate
  nodes, which prevents bidirectional text from moving the day beside the time.
- The former hard-coded “market active” claim is replaced by API-backed data
  freshness. The help text states that this is not an exchange-hours calendar.
- Contextual help, display settings, the public footer, equal analysis route
  cards, and two short backend-produced conclusions were exercised in-browser.
- At 393 px and 1440 px there is no horizontal document overflow. The three
  route cards have equal measured height and width at each breakpoint. The
  console contains no warnings or errors.

The current fixation set passes. The dashboard task remains active because the
owner requested iterative debugging before design acceptance.

### Iteration 4 — bilingual analysis pass passed

- Persian/RTL and English/LTR switch immediately from Settings and persist for
  the next visit. Labels, values, Tehran dates, controls, help, analysis, and
  footer copy follow the selected language.
- The status guide explains green/current, yellow/latest-close, and red/old
  data. It also states that the indicator is not an official market calendar.
- Dollar, gold, and coin analysis sections render sentences selected by the
  deterministic Python catalog. The browser only selects the requested
  language; it does not calculate or choose a conclusion.
- The footer keeps the dashboard disclaimer and adds the approved MostaHub
  rights line and ZorgOros design credit.
- At 1440 px and 393 px, both directions have no horizontal document overflow.
  The three route cards measure the same height on mobile. A fresh browser
  session has no console warnings or errors.

Verification: 225 Python tests, 17 UI tests, 4 Sites worker tests, Ruff, Ruff
format, mypy, and the production build passed. Vite reports only its existing
non-blocking large-chunk advisory.

## Follow-up polish

- [P3] Real production history will make the line shapes less regular than the
  deterministic preview data used for this review.

final result: passed
