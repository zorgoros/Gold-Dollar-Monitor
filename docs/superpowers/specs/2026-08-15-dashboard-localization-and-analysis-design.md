# Dashboard Localization and Analysis Context Design

## Status

- Design: approved by the owner on 2026-08-15.
- Written specification: awaiting owner review before implementation planning.
- Worktree: `.worktrees/dashboard-v1`.
- Branch: `codex/dashboard-v1`.
- Merge and deployment remain out of scope until the dashboard design is
  accepted.

## Goal

Make the dashboard fully usable in Persian and English, add concise hover help
to controls, and make every section of the analysis view explain what its
numbers mean. Analytical wording must remain deterministic and traceable to the
bot's existing metrics and signals.

## Localization boundary

The dashboard uses one page and one component tree for both languages. It does
not create separate Persian and English routes.

- `dashboard/src/locales/fa.js` and `dashboard/src/locales/en.js` own ordinary
  interface copy, help text, labels, units, button hints, footer text, empty
  states, and table headings.
- A small locale provider owns the active language, persists the choice in
  browser storage, and sets the document `lang` and `dir` attributes.
- Persian uses RTL layout and Persian number/date formatting. English uses LTR
  layout and English number/date formatting. Market timestamps remain in the
  Tehran time zone in both languages.
- Language is a real settings control. Changing it updates the visible page
  without a reload.

Analytical conclusions are not ordinary interface copy. They are selected and
rendered in Python as described below.

## Analytical narrative boundary

Premade analytical sentences live in a dedicated Python catalog. A separate
selector chooses a catalog entry from existing analysis outputs.

```text
stored metrics + classifications + reason codes
                    ↓
deterministic narrative selector
                    ↓
bilingual premade sentence catalog
                    ↓
public API: selected Persian and English text
                    ↓
dashboard: display the active language only
```

The selector may read existing metrics, signal classifications, reason codes,
analysis basis, and data availability. It must not calculate a market formula,
define a new threshold, infer a recommendation, or run a second analysis in the
browser.

The public analysis payload adds a stable narrative structure:

```json
{
  "narratives": {
    "overview": [{"id": "...", "text": {"fa": "...", "en": "..."}}],
    "gold": [{"id": "...", "text": {"fa": "...", "en": "..."}}],
    "coin": [{"id": "...", "text": {"fa": "...", "en": "..."}}]
  }
}
```

Narrative IDs remain stable when wording changes. Missing or gated analysis
returns an unavailable state; it never falls back to invented commentary.

## Analysis view

The analysis view has three levels of explanation:

1. `تحلیل مسیرهای دلار` / `Dollar Path Analysis` shows the selected overview
   conclusions after the three equal comparison cards.
2. `برابری ارزش` / `Value Parity` shows a gold narrative below market gold,
   theoretical gold, and their gap. It explains whether domestic gold is below,
   near, or above the model value by using the existing gold signal.
3. `ارزش ذاتی داخلی` / `Domestic Intrinsic Value` shows a coin narrative below
   market price, domestic metal value, and premium. It explains the direction
   of the premium by using the existing coin signal.

The sentences explain the current relationship. They do not give buy or sell
instructions. The existing `نشانه‌های قابل توجه` / `Notable Signals` list
remains available as the detailed evidence layer.

## Control hints and contextual help

Short control hints and conceptual help have different jobs:

- Buttons and icon controls receive translated accessible labels and short
  hover/focus hints that state the action. Text controls do not repeat long
  explanations.
- The `?` mode remains the deeper conceptual-help system. Its data-status topic
  explains all three states and their colors:
  - green: all mandatory live data is inside the strict freshness limit;
  - yellow: recent data uses the last-close basis;
  - red: the stored observation is older than the strict freshness limit.
- The same topic states that the indicator is not an official exchange-hours
  calendar.

Help content is complete in Persian and English. Color is always paired with a
written state name.

## Footer

The footer keeps its current dashboard content:

- Ayar Market identity and description;
- interactive-help, display-settings, and documentation links;
- latest-data timestamp; and
- financial-information disclaimer.

A final legal row adapts the owner-provided MostaHub website line:

- English: `© 2025–2026 MostaHub. All Rights Reserved. Designed by ZorgOros.`
- Persian: `© ۲۰۲۵–۲۰۲۶ MostaHub. تمامی حقوق محفوظ است. طراحی: ZorgOros.`

`MostaHub` links to `https://mostahub.com`. The credit remains `ZorgOros` to
match the owner's website. The legal row must fit the existing restrained
footer hierarchy and must not compete with the market disclaimer.

## Error handling

- An unknown stored locale falls back to Persian.
- Missing English or Persian narrative text is a projection error caught by
  tests; the browser does not silently translate analytical content.
- Missing gold or coin inputs hide only the affected metrics and show a
  localized unavailable explanation.
- Browser storage failure does not block language switching for the current
  session.

## Testing and acceptance

- Unit tests prove that the selector chooses gold and coin narratives from real
  classifications and never exposes a narrative for unavailable analysis.
- Projection tests require stable IDs and both language strings.
- UI tests switch languages and verify `lang`, `dir`, translated controls,
  dates, analysis context, help content, and footer legal text.
- Hover/focus hints are checked on the ambiguous header and range controls.
- Browser QA covers Persian RTL and English LTR at narrow and desktop widths,
  settings persistence, analysis cards, help mode, and footer wrapping.
- The full Python tests, UI tests, Sites tests, build, Ruff, format check, mypy,
  and browser console must pass before the change is committed.

## Non-goals

- No machine translation or AI-written live commentary.
- No new market formula, classification threshold, or recommendation logic.
- No separate language routes, account preference service, deployment, or
  hosting change.
- No merge into `main` until the owner accepts the dashboard.
