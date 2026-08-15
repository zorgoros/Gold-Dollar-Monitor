# Dashboard Localization and Analysis Context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add complete Persian/English dashboard localization, deterministic bilingual analysis narratives, control hints, expanded status help, and the MostaHub/ZorgOros legal footer.

**Architecture:** Python selects stable narrative IDs from existing `Signal` classifications and reason codes, then resolves bilingual text from a dedicated catalog. React owns only interface localization and presentation; one locale provider switches copy, number/date formatting, `lang`, and `dir` without duplicating pages or market logic.

**Tech Stack:** Python 3.12+, dataclasses and typed dictionaries, React 19, Vite 6, Vitest, Testing Library, Recharts, CSS logical properties.

## Global Constraints

- Do not add a market formula, threshold, recommendation, or browser-side analysis rule.
- Analytical narratives must be selected from existing classifications, reason codes, basis, and availability.
- Every selected narrative must have stable ID, Persian text, and English text.
- Persian remains the default and uses RTL; English uses LTR. Both use `Asia/Tehran` timestamps.
- Keep UI code under `dashboard/` and Python analysis/projection under `src/market_monitor/`.
- Keep the existing footer content and add `© 2025–2026 MostaHub. All Rights Reserved. Designed by ZorgOros.` with its Persian equivalent.
- Do not merge, push, deploy, or remove `.worktrees/dashboard-v1`.

---

### Task 1: Deterministic bilingual narrative catalog

**Files:**
- Create: `src/market_monitor/analysis/narrative_catalog.py`
- Create: `src/market_monitor/analysis/dashboard_narratives.py`
- Create: `tests/unit/test_dashboard_narratives.py`

**Interfaces:**
- Consumes: `Signal.instrument`, `Signal.classification`, and `Signal.reason_codes`.
- Produces: `select_dashboard_narratives(signals: Sequence[Signal]) -> dict[str, list[dict[str, object]]]` with `overview`, `gold`, and `coin` keys.
- Produces each item as `{"id": str, "text": {"fa": str, "en": str}}`.

- [ ] **Step 1: Write failing selector tests**

```python
from datetime import UTC, datetime

from market_monitor.analysis.dashboard_narratives import select_dashboard_narratives
from market_monitor.domain.enums import Classification, Instrument, ReasonCode
from market_monitor.domain.models import Signal

AT = datetime(2026, 8, 12, 9, 30, tzinfo=UTC)


def make_signal(instrument, classification, reasons=()):
    return Signal(
        instrument=instrument,
        classification=classification,
        severity=1,
        confidence=0.5,
        summary_fa="existing signal",
        reason_codes=list(reasons),
        metrics_used={},
        generated_at=AT,
        model_version="1.2",
    )


def test_selects_bilingual_gold_and_coin_context_from_existing_classifications():
    payload = select_dashboard_narratives(
        [
            make_signal(Instrument.GOLD_18K, Classification.SLIGHTLY_UNDERVALUED),
            make_signal(Instrument.EMAMI_COIN, Classification.EXPENSIVE),
        ]
    )

    assert payload["gold"][0]["id"] == "gold.below_theoretical"
    assert payload["coin"][0]["id"] == "coin.positive_premium"
    assert payload["gold"][0]["text"]["fa"]
    assert payload["gold"][0]["text"]["en"]


def test_usd_overview_reports_reference_disagreement_from_reason_code():
    payload = select_dashboard_narratives(
        [
            make_signal(
                Instrument.USD_IRR_FREE,
                Classification.SLIGHTLY_EXPENSIVE,
                [ReasonCode.GOLD_AND_AED_DISAGREE],
            )
        ]
    )

    assert [item["id"] for item in payload["overview"]] == [
        "usd.references.disagree",
        "usd.market.above_reference",
    ]
```

- [ ] **Step 2: Run the tests and verify the missing-module failure**

Run: `PYTHONPATH=src ../../.venv/bin/python -m pytest -q tests/unit/test_dashboard_narratives.py`

Expected: collection fails because `market_monitor.analysis.dashboard_narratives` does not exist.

- [ ] **Step 3: Implement the bilingual catalog**

```python
# src/market_monitor/analysis/narrative_catalog.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NarrativeTemplate:
    id: str
    fa: str
    en: str

    def payload(self) -> dict[str, object]:
        return {"id": self.id, "text": {"fa": self.fa, "en": self.en}}


CATALOG = {
    "usd.references.disagree": NarrativeTemplate(
        "usd.references.disagree",
        "مسیرهای طلا و درهم تصویر یکسانی از نرخ دلار نشان نمی‌دهند.",
        "The gold and dirham paths do not show the same picture for the dollar rate.",
    ),
    "usd.market.above_reference": NarrativeTemplate(
        "usd.market.above_reference",
        "دلار بازار بالاتر از مرجع طبقه‌بندی شده است؛ این فاصله توصیفی است، نه توصیه معامله.",
        "The market dollar is classified above its reference; this describes a gap and is not trading advice.",
    ),
    "usd.references.agree": NarrativeTemplate(
        "usd.references.agree",
        "مسیرهای طلا و درهم فاصله مشابهی با نرخ دلار بازار نشان می‌دهند.",
        "The gold and dirham paths show a similar gap from the market dollar rate.",
    ),
    "usd.references.gold_only": NarrativeTemplate(
        "usd.references.gold_only",
        "در این نوبت فقط مسیر طلا برای مقایسه با دلار بازار در دسترس است.",
        "Only the gold path is available for comparison with the market dollar in this observation.",
    ),
    "usd.market.below_reference": NarrativeTemplate(
        "usd.market.below_reference",
        "دلار بازار پایین‌تر از مرجع طبقه‌بندی شده است؛ این فاصله توصیفی است، نه توصیه معامله.",
        "The market dollar is classified below its reference; this describes a gap and is not trading advice.",
    ),
    "usd.market.near_reference": NarrativeTemplate(
        "usd.market.near_reference",
        "دلار بازار نزدیک به محدوده مرجع طبقه‌بندی شده است.",
        "The market dollar is classified near its reference range.",
    ),
    "gold.below_theoretical": NarrativeTemplate(
        "gold.below_theoretical",
        "طلای داخلی پایین‌تر از ارزش نظری مدل است و هنوز ورودی‌های دلار و اونس را کامل منعکس نمی‌کند.",
        "Domestic gold is below the model value and does not yet fully reflect the dollar and ounce inputs.",
    ),
    "gold.above_theoretical": NarrativeTemplate(
        "gold.above_theoretical",
        "طلای داخلی بالاتر از ارزش نظری مدل است و نسبت به ورودی‌های دلار و اونس فاصله مثبت دارد.",
        "Domestic gold is above the model value and has a positive gap from the dollar and ounce inputs.",
    ),
    "gold.near_theoretical": NarrativeTemplate(
        "gold.near_theoretical",
        "طلای داخلی نزدیک به ارزش نظری محاسبه‌شده از دلار و اونس است.",
        "Domestic gold is near the theoretical value calculated from the dollar and ounce inputs.",
    ),
    "coin.positive_premium": NarrativeTemplate(
        "coin.positive_premium",
        "قیمت سکه بالاتر از ارزش طلای داخل آن است؛ بخش مثبت فاصله، حباب داخلی را نشان می‌دهد.",
        "The coin price is above its domestic metal value; the positive gap is the domestic premium.",
    ),
    "coin.negative_premium": NarrativeTemplate(
        "coin.negative_premium",
        "قیمت سکه پایین‌تر از ارزش طلای داخل آن است و فاصله داخلی منفی است.",
        "The coin price is below its domestic metal value and the domestic premium is negative.",
    ),
    "coin.near_metal_value": NarrativeTemplate(
        "coin.near_metal_value",
        "قیمت سکه نزدیک به ارزش طلای داخل آن طبقه‌بندی شده است.",
        "The coin price is classified near its domestic metal value.",
    ),
    "data.warning": NarrativeTemplate(
        "data.warning",
        "این تحلیل از ورودی دارای هشدار کیفیت استفاده می‌کند و باید با احتیاط خوانده شود.",
        "This analysis uses an input with a data-quality warning and should be read with caution.",
    ),
}
```

- [ ] **Step 4: Implement the selector with classification groups**

```python
# src/market_monitor/analysis/dashboard_narratives.py
from __future__ import annotations

from collections.abc import Sequence

from ..domain.enums import Classification, Instrument, ReasonCode
from ..domain.models import Signal
from .narrative_catalog import CATALOG

ABOVE = {
    Classification.SLIGHTLY_EXPENSIVE,
    Classification.EXPENSIVE,
    Classification.STRETCHED,
}
BELOW = {
    Classification.SLIGHTLY_UNDERVALUED,
    Classification.UNDERVALUED,
}


def _payload(key: str) -> dict[str, object]:
    return CATALOG[key].payload()


def select_dashboard_narratives(signals: Sequence[Signal]) -> dict[str, list[dict[str, object]]]:
    result = {"overview": [], "gold": [], "coin": []}
    by_instrument = {signal.instrument: signal for signal in signals}
    usd = by_instrument.get(Instrument.USD_IRR_FREE)
    if usd:
        if ReasonCode.STALE_SOURCE in usd.reason_codes:
            result["overview"].append(_payload("data.warning"))
        if ReasonCode.GOLD_AND_AED_DISAGREE in usd.reason_codes:
            result["overview"].append(_payload("usd.references.disagree"))
        elif ReasonCode.GOLD_AND_AED_AGREE in usd.reason_codes:
            result["overview"].append(_payload("usd.references.agree"))
        else:
            result["overview"].append(_payload("usd.references.gold_only"))
        relation = "above_reference" if usd.classification in ABOVE else "below_reference" if usd.classification in BELOW else "near_reference"
        result["overview"].append(_payload(f"usd.market.{relation}"))
    gold = by_instrument.get(Instrument.GOLD_18K)
    if gold:
        relation = "above_theoretical" if gold.classification in ABOVE else "below_theoretical" if gold.classification in BELOW else "near_theoretical"
        result["gold"].append(_payload(f"gold.{relation}"))
    coin = by_instrument.get(Instrument.EMAMI_COIN)
    if coin:
        relation = "positive_premium" if coin.classification in ABOVE else "negative_premium" if coin.classification in BELOW else "near_metal_value"
        result["coin"].append(_payload(f"coin.{relation}"))
    return result
```

- [ ] **Step 5: Run narrative tests**

Run: `PYTHONPATH=src ../../.venv/bin/python -m pytest -q tests/unit/test_dashboard_narratives.py`

Expected: all narrative tests pass.

- [ ] **Step 6: Commit the narrative boundary**

```bash
git add src/market_monitor/analysis/narrative_catalog.py src/market_monitor/analysis/dashboard_narratives.py tests/unit/test_dashboard_narratives.py
git commit -m "Add bilingual analysis narratives"
```

---

### Task 2: Publish narratives through the dashboard projection

**Files:**
- Modify: `src/market_monitor/web/projection.py`
- Modify: `tests/unit/test_dashboard_projection.py`

**Interfaces:**
- Consumes: `select_dashboard_narratives(analysis.signals)` from Task 1.
- Produces: `payload["analysis"]["narratives"]` with `overview`, `gold`, and `coin` arrays.
- Retains `summary_fa` for this branch until all dashboard consumers migrate.

- [ ] **Step 1: Add failing projection assertions**

```python
def test_latest_publishes_bilingual_section_narratives(repo, snapshot, settings):
    repo.save_snapshot(snapshot(aed=True, coin=True))

    payload = DashboardProjection(repo, settings, clock=lambda: AT).latest()

    narratives = payload["analysis"]["narratives"]
    assert narratives["overview"]
    assert narratives["gold"][0]["id"].startswith("gold.")
    assert narratives["coin"][0]["id"].startswith("coin.")
    assert set(narratives["gold"][0]["text"]) == {"fa", "en"}
```

- [ ] **Step 2: Run the projection test and verify the missing-key failure**

Run: `PYTHONPATH=src ../../.venv/bin/python -m pytest -q tests/unit/test_dashboard_projection.py::test_latest_publishes_bilingual_section_narratives`

Expected: FAIL with missing key `narratives`.

- [ ] **Step 3: Add the selector output to ready analysis only**

```python
from ..analysis.dashboard_narratives import select_dashboard_narratives

# Inside the READY analysis payload:
"narratives": select_dashboard_narratives(analysis.signals),
```

Do not add narratives to `UNAVAILABLE` analysis payloads.

- [ ] **Step 4: Run projection and server tests**

Run: `PYTHONPATH=src ../../.venv/bin/python -m pytest -q tests/unit/test_dashboard_projection.py tests/integration/test_dashboard_server.py`

Expected: all tests pass.

- [ ] **Step 5: Commit the API contract**

```bash
git add src/market_monitor/web/projection.py tests/unit/test_dashboard_projection.py
git commit -m "Expose dashboard analysis narratives"
```

---

### Task 3: Locale provider and locale-aware formatting

**Files:**
- Create: `dashboard/src/locales/fa.js`
- Create: `dashboard/src/locales/en.js`
- Create: `dashboard/src/locales/index.js`
- Create: `dashboard/src/components/LocaleProvider.jsx`
- Create: `dashboard/src/components/LocaleProvider.test.jsx`
- Modify: `dashboard/src/format.js`
- Modify: `dashboard/src/components/MarketChart.test.jsx`

**Interfaces:**
- Produces: `useLocale() -> { language, direction, copy }`.
- Produces: `LocaleProvider({ language, children })`.
- Changes formatters to accept `language = "fa"`: `formatNumber`, `formatPercent`, `formatTime`, `formatChartDate`, `formatClock`, and `formatAxisTime`.

- [ ] **Step 1: Write failing locale and formatting tests**

```jsx
import { render, screen } from "@testing-library/react";
import { LocaleProvider, useLocale } from "./LocaleProvider.jsx";

function Probe() {
  const { copy, direction } = useLocale();
  return <span>{copy.app.name}|{direction}</span>;
}

it("provides English copy and LTR direction", () => {
  render(<LocaleProvider language="en"><Probe /></LocaleProvider>);
  expect(screen.getByText("Ayar Market|ltr")).toBeInTheDocument();
});
```

Add formatter assertions:

```js
expect(formatNumber(185400, "en")).toBe("185,400");
expect(formatClock("2026-08-12T09:30:00+00:00", "en")).toMatch(/13:00|1:00/);
expect(formatChartDate("2026-08-12T09:30:00+00:00", "en")).toContain("August");
```

- [ ] **Step 2: Run tests and verify missing-provider/signature failures**

Run: `cd dashboard && npm test -- --run src/components/LocaleProvider.test.jsx src/components/MarketChart.test.jsx`

Expected: FAIL because the provider does not exist and formatters ignore English.

- [ ] **Step 3: Add complete UI dictionaries**

Each locale exports the same nested keys. Include app identity, tabs, status,
cards, chart, insights, table, analysis, settings, help, footer, units, range
labels, unavailable states, and control hints.

```js
// dashboard/src/locales/en.js
export const en = {
  app: { name: "Ayar Market", tagline: "Intelligent market view" },
  tabs: { market: "Market", analysis: "Analysis" },
  ranges: { "1d": "1 day", "7d": "7 days", "30d": "30 days" },
  footer: {
    rights: "© 2025–2026 MostaHub. All Rights Reserved.",
    designedBy: "Designed by ZorgOros.",
  },
};
```

The Persian dictionary must use the same keys and the approved Persian legal
line. Do not include analysis conclusions in these files.

- [ ] **Step 4: Implement provider and locale-aware formatters**

```jsx
const LocaleContext = createContext(null);

export function LocaleProvider({ language, children }) {
  const normalized = language === "en" ? "en" : "fa";
  const value = useMemo(() => ({
    language: normalized,
    direction: normalized === "fa" ? "rtl" : "ltr",
    copy: locales[normalized],
  }), [normalized]);
  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}
```

Use `fa-IR` for Persian and `en-US` for English. Keep `Asia/Tehran` in every
date formatter.

- [ ] **Step 5: Run locale tests**

Run: `cd dashboard && npm test -- --run src/components/LocaleProvider.test.jsx src/components/MarketChart.test.jsx`

Expected: all locale and chart-format tests pass.

- [ ] **Step 6: Commit locale infrastructure**

```bash
git add dashboard/src/locales dashboard/src/components/LocaleProvider.jsx dashboard/src/components/LocaleProvider.test.jsx dashboard/src/format.js dashboard/src/components/MarketChart.test.jsx
git commit -m "Add dashboard locale infrastructure"
```

---

### Task 4: Translate controls, help, cards, chart, and footer

**Files:**
- Modify: `dashboard/src/Prototype.jsx`
- Modify: `dashboard/src/Prototype.test.jsx`
- Modify: `dashboard/src/components/DataStatus.jsx`
- Modify: `dashboard/src/components/HelpSystem.jsx`
- Modify: `dashboard/src/components/MarketChart.jsx`
- Modify: `dashboard/src/components/PriceCard.jsx`
- Modify: `dashboard/src/components/SettingsPanel.jsx`
- Modify: `dashboard/src/components/SiteFooter.jsx`

**Interfaces:**
- Consumes: `useLocale()` and dictionaries from Task 3.
- Adds `settings.language` with values `fa` or `en`.
- Adds translated `title` and `aria-label` values to ambiguous controls.

- [ ] **Step 1: Replace the UI fixture with bilingual narratives and add failing interaction tests**

Add `latest.analysis.narratives` to `Prototype.test.jsx`, then add:

```jsx
it("switches the full dashboard to English and LTR", async () => {
  globalThis.fetch = mockApi();
  render(<Prototype />);
  await screen.findAllByText("۱۸۵٬۴۰۰");

  fireEvent.click(screen.getByRole("button", { name: "تنظیمات" }));
  fireEvent.click(screen.getByRole("radio", { name: "English" }));

  expect(document.documentElement).toHaveAttribute("lang", "en");
  expect(document.documentElement).toHaveAttribute("dir", "ltr");
  expect(screen.getByRole("heading", { name: "Ayar Market" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Market" })).toBeInTheDocument();
  expect(screen.getByText("Old data")).toBeInTheDocument();
});

it("explains every data-status color in contextual help", async () => {
  globalThis.fetch = mockApi();
  render(<Prototype />);
  await screen.findAllByText("۱۸۵٬۴۰۰");
  fireEvent.click(screen.getByRole("button", { name: "راهنمای صفحه" }));
  fireEvent.click(screen.getByRole("button", { name: "راهنمای وضعیت داده" }));
  const dialog = screen.getByRole("dialog", { name: "وضعیت داده" });
  expect(dialog).toHaveTextContent("سبز");
  expect(dialog).toHaveTextContent("زرد");
  expect(dialog).toHaveTextContent("قرمز");
  expect(dialog).toHaveTextContent("ساعت رسمی بازار نیست");
});

it("adds action hints and the approved legal footer", async () => {
  globalThis.fetch = mockApi();
  render(<Prototype />);
  await screen.findAllByText("۱۸۵٬۴۰۰");
  expect(screen.getByRole("button", { name: "تنظیمات" })).toHaveAttribute("title");
  expect(screen.getByRole("button", { name: "۷ روز" })).toHaveAttribute("title");
  expect(screen.getByText(/تمامی حقوق محفوظ است/)).toBeInTheDocument();
  expect(screen.getByText(/ZorgOros/)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the UI tests and verify translation/help/footer failures**

Run: `cd dashboard && npm test -- --run src/Prototype.test.jsx`

Expected: the new tests fail because language radios, translated content,
expanded status help, hints, and the legal row do not exist.

- [ ] **Step 3: Move settings ownership above the locale provider**

```jsx
export function Prototype() {
  const [settings, updateSetting] = useDashboardSettings();
  return (
    <LocaleProvider language={settings.language}>
      <HelpProvider><Dashboard settings={settings} updateSetting={updateSetting} /></HelpProvider>
    </LocaleProvider>
  );
}
```

Add `language: "fa"` to `DEFAULT_SETTINGS`. In an effect, set document `lang`
and `dir` from `useLocale()`.

- [ ] **Step 4: Translate market components and add short control hints**

Replace component literals with `copy` keys. Every icon button, tab, range
button, close control, and footer action receives a translated `aria-label`
where needed and a translated `title` that describes its action. Keep visible
text buttons concise; do not put conceptual analysis into hover hints.

- [ ] **Step 5: Expand status help with named color rows**

Render the help body as localized structured content:

```jsx
<ul className="status-help-list">
  <li><i className="status-swatch status-swatch--live" />{copy.help.status.live}</li>
  <li><i className="status-swatch status-swatch--close" />{copy.help.status.lastClose}</li>
  <li><i className="status-swatch status-swatch--stale" />{copy.help.status.stale}</li>
</ul>
<p>{copy.help.status.notCalendar}</p>
```

- [ ] **Step 6: Add the language radio control and legal footer row**

Use two radios named from localized settings copy. Preserve all current footer
content. Add one subdued row with a `MostaHub` link to `https://mostahub.com`
and plain `ZorgOros` credit text.

- [ ] **Step 7: Run the full UI component tests**

Run: `cd dashboard && npm test -- --run`

Expected: all UI tests pass.

- [ ] **Step 8: Commit bilingual UI and help**

```bash
git add dashboard/src/Prototype.jsx dashboard/src/Prototype.test.jsx dashboard/src/components/DataStatus.jsx dashboard/src/components/HelpSystem.jsx dashboard/src/components/MarketChart.jsx dashboard/src/components/PriceCard.jsx dashboard/src/components/SettingsPanel.jsx dashboard/src/components/SiteFooter.jsx
git commit -m "Add bilingual dashboard controls"
```

---

### Task 5: Render section-specific analysis context

**Files:**
- Modify: `dashboard/src/components/AnalysisView.jsx`
- Create: `dashboard/src/components/AnalysisView.test.jsx`
- Modify: `dashboard/src/styles.css`

**Interfaces:**
- Consumes: `analysis.narratives.overview`, `.gold`, and `.coin`.
- Uses `narrative.text[language]`; it never selects a classification or computes a gap.

- [ ] **Step 1: Write failing analysis-context tests**

```jsx
it("renders localized context for overview, gold parity, and coin metal value", () => {
  render(
    <LocaleProvider language="en">
      <AnalysisView analysis={analysisFixture} />
    </LocaleProvider>,
  );

  expect(screen.getByRole("heading", { name: "Dollar Path Analysis" })).toBeInTheDocument();
  expect(screen.getByText("Domestic gold is below the model value.")).toBeInTheDocument();
  expect(screen.getByText("The positive gap is the domestic premium.")).toBeInTheDocument();
});
```

The fixture must contain complete real payload fields and bilingual narrative
items. Add a second test proving that a missing coin narrative shows the
localized unavailable sentence rather than an invented conclusion.

- [ ] **Step 2: Run the test and verify missing English/context failures**

Run: `cd dashboard && npm test -- --run src/components/AnalysisView.test.jsx`

Expected: FAIL because `AnalysisView` still uses Persian literals and does not
render gold or coin narrative blocks.

- [ ] **Step 3: Add a presentation-only narrative component**

```jsx
function NarrativeContext({ title, narratives = [] }) {
  const { language, copy } = useLocale();
  if (!narratives.length) return <p className="analysis-context-empty">{copy.analysis.contextUnavailable}</p>;
  return (
    <div className="analysis-context">
      <strong>{title}</strong>
      {narratives.map((item) => <p key={item.id}>{item.text[language]}</p>)}
    </div>
  );
}
```

Use it after the route cards, after the gold metric strip, and after the coin
metric strip. Keep the signal list as the evidence layer and localize its
headings and confidence label.

- [ ] **Step 4: Add restrained context styling**

Use one border accent and normal paragraph text. Do not create nested cards or
add a new color system. Use logical properties so both directions work.

- [ ] **Step 5: Run analysis and prototype tests**

Run: `cd dashboard && npm test -- --run src/components/AnalysisView.test.jsx src/Prototype.test.jsx`

Expected: all analysis and dashboard interaction tests pass.

- [ ] **Step 6: Commit analysis context**

```bash
git add dashboard/src/components/AnalysisView.jsx dashboard/src/components/AnalysisView.test.jsx dashboard/src/styles.css
git commit -m "Add analysis section context"
```

---

### Task 6: Full verification, browser QA, and project records

**Files:**
- Modify: `design-qa.md`
- Modify: `docs/ops/LEDGER.md`
- Modify: `docs/ops/HANDOFF.md`
- Modify: `docs/superpowers/specs/2026-08-15-first-dashboard-design.md`

**Interfaces:**
- Verifies the final API and browser behavior; adds no feature behavior.

- [ ] **Step 1: Run the complete Python verification chain**

Run:

```bash
PYTHONPATH=src ../../.venv/bin/python -m pytest -q
../../.venv/bin/ruff check src tests scripts
../../.venv/bin/ruff format --check src tests scripts
PYTHONPATH=src ../../.venv/bin/mypy src
```

Expected: every command exits 0 with no failures.

- [ ] **Step 2: Run the complete dashboard verification chain**

Run:

```bash
cd dashboard
npm test -- --run
npm run test:sites
npm run build
```

Expected: Vitest, Sites tests, and the production build exit 0.

- [ ] **Step 3: Restart the local read-only API and inspect its contract**

Use the fixture database at `/private/tmp/ayar-dashboard-preview-0815.db` and
confirm `/api/v1/latest` contains bilingual `overview`, `gold`, and `coin`
narratives with stable IDs.

- [ ] **Step 4: Browser-test both languages**

At 393 px and 1440 px:

- switch Persian to English and back without reload;
- confirm `lang`, `dir`, translated numbers, dates, tooltips, controls, help,
  analysis contexts, signals, footer, and legal line;
- focus and hover ambiguous controls and read their short hints;
- open data-status help and verify green/yellow/red explanations;
- verify no horizontal document overflow and no console warnings or errors.

- [ ] **Step 5: Update project records**

Mark the current P8 debugging sub-pass complete, add the next owner-review step,
record the bilingual narrative boundary and exact worktree/branch in handoff,
and append the responsive bilingual QA result to `design-qa.md`.

- [ ] **Step 6: Commit records and verification evidence**

```bash
git add design-qa.md docs/ops/LEDGER.md docs/ops/HANDOFF.md docs/superpowers/specs/2026-08-15-first-dashboard-design.md
git commit -m "Record bilingual dashboard verification"
```

- [ ] **Step 7: Confirm isolated branch state**

Run: `git status --short --branch && git log -6 --oneline`

Expected: clean `codex/dashboard-v1`; no merge, push, deployment, or worktree
removal.
