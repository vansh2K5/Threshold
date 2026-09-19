# Plan: ECC Reference — Command Center Grid

**Task:** "i have the html for ecc make it look more premium" → Direction A (Command Center Grid), chosen by user over Direction B (Machinist's Ledger table refinement).

**Source of truth:** `F:\projects\Mjor-SEM7\skill.md` (Machinist's Blueprint tokens — achromatic palette, Geist fonts, 6/8/12/9999px radii only, shadows on cards only).

**Analysis/plan credited to:** Antigravity (analyzer + architect roles, via ccg-workflow), synthesized here against the actual build pipeline.

## Why a generator, not hand-editing HTML

`ecc-reference.html` (325 KB, 454 rows) is produced by a script, not written by hand:
- `ecc-data-tagged.json` — extracted + categorized data (skills/commands/agents + category tags)
- `generate-ecc-html.js` (scratchpad) — templates that data into the final HTML/CSS/JS

Both live in the session scratchpad: `C:\Users\vansh\AppData\Local\Temp\claude\F--projects-Mjor-SEM7\b70a0729-ca76-4c15-92c8-0694c073168c\scratchpad\`. Editing the generator (not the output file) keeps the 454 rows consistent and lets us regenerate cleanly.

## Design (per Antigravity architect)

Each row becomes a card:
```html
<div class="card" data-search="..." data-cats="...">
  <div class="card-header">
    <code class="cmd">/ecc:command-name</code>
    <span class="hint-text">[argument hint — commands/skills only]</span>
  </div>
  <div class="card-desc">Description text…</div>
</div>
```
Grid: `display:grid; grid-template-columns: repeat(auto-fill, minmax(320px,1fr)); gap: var(--spacing-16); align-items:stretch;`
Card: white bg, `--radius-cards` (12px), `--shadow-subtle`, flex column so `.card-desc` (`flex-grow:1`) keeps row heights aligned; `.card-header` uses `justify-content:space-between` so Agents (no hint) just left-align the badge with no broken layout.

## Implementation steps (in `generate-ecc-html.js`)

1. **Row builders** (`commandRows`, `agentRows`, `skillRows`): change each `<tr>...</tr>` template to a `<div class="card" data-search="..." data-cats="...">` with `.card-header` (code badge + optional `.hint-text`) and `.card-desc`. Keep `data-search`/`data-cats` attributes identical — filtering depends on them.
2. **CSS**: remove `table`/`thead th`/`tbody td`/`tr:hover` rules; add `.grid`, `.card`, `.card-header`, `.hint-text`, `.card-desc` per the architect's spec above, reusing existing tokens only (no new colors/radii/shadows).
3. **Markup**: change each section's `<table><thead>...</thead><tbody id="tbl-x">...</tbody></table>` to a plain `<div id="tbl-x" class="grid">...</div>` (drop the header row — column labels don't apply to a card grid).
4. **JS filter()**: swap `document.getElementById(id).querySelectorAll('tr')` → `.querySelectorAll('.card')`. Everything else (data-search/data-cats checks, counts, `.closest('section')` empty-state toggle) is untouched since `.grid` is still the direct child of `<section>`.
5. Regenerate: `node generate-ecc-html.js "F:/projects/Mjor-SEM7/ecc-reference.html"`.

## Risks (per architect) + mitigation

- Forgetting the `tr` → `.card` selector swap breaks filtering entirely → will verify by scripted row/card count check + manual search/chip test.
- Agents' 2-shape vs Commands/Skills' 3-shape card header → handled naturally by `justify-content:space-between` with one child.
- 454 flex/grid nodes toggling `display:none` → negligible perf cost, no virtualization needed.

## Validation after execution

1. Automated: `<div class="card"` count == 454; script/console sanity check (no broken tags).
2. Manual via Chrome: resize 1440px → mobile width, confirm grid reflows 3→2→1 columns without clipping; type a search term and click a category chip, confirm live filtering + "Showing X of Y" + per-section empty state still work; verify no color/radius/shadow value outside `skill.md`'s token set was introduced.

## Explicitly out of scope

Direction B's table-specific refinements (96px section gap, merged ledger column) — not applicable once the table is replaced by a grid, except section-gap (96px) will still be honored as the spec's true value while we're in the CSS anyway.
