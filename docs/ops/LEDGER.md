# Ledger — Market-situation

Every idea, gap, bug, and task lives here. One file, so "do we already have
this?" is one search.

**Never hand-write an entry.** Use `pos check` then `pos add` — they enforce
the dedup gate and the ID sequence.

## Format

```
## <TYPE>-<NNN> · <title> · <STATUS>
**Family:** comma,separated,tags        ← the dedup key. Be generous.
**Raised:** YYYY-MM-DD
**Summary:** one line, no more

### Phases
- [ ] P1 — ...
- [ ] P2 — ...

### Notes
```

- **TYPE** — `IDEA` (new scope, UI, rule, layer) · `GAP` (missing piece) ·
  `BUG` (broken behaviour) · `TASK` (agreed unit of work)
- **STATUS** — `OPEN` (captured, not scoped) · `ACTIVE` (phases running) ·
  `DONE` · `MERGED into <ID>` · `DROPPED — <reason>`
- **Phases** appear when the item is settled and scoped, not at capture time.
  An `OPEN` entry may carry a single `P1 — scope it`.

## Entries

## GAP-001 · EXTENSIONS.md and docs/ops/LEDGER.md are two parking lots for the same thing · DONE
**Family:** extensions,ledger,docs,process,duplication
**Raised:** 2026-08-12
**Summary:** EXTENSIONS.md and docs/ops/LEDGER.md are two parking lots for the same thing

### Phases
- [ ] P1 — scope it

### Notes
