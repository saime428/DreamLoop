# Bedside Amber Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert DreamLoop's current neon dream-dashboard frontend into a warm `bedside-amber` visual system while preserving the six-page local-first product loop.

**Architecture:** Keep the existing FastAPI/Jinja structure and implement the redesign primarily in `src/dreamloop/static/style.css`. Use lightweight template cleanup only to remove unused star-field markup and warm the fallback local visual colors. Add CSS/template regression tests to protect the local-first and non-neon constraints.

**Tech Stack:** Python, pytest, FastAPI, Jinja templates, plain CSS.

---

## Current Backup

- Backup branch: `codex/backup-before-bedside-amber-20260618`
- Working branch: `codex/bedside-amber-frontend`
- Backup commit: `95772ba`

## Files

- Modify: `tests/test_readme_positioning.py`
  - Add regression tests for no remote fonts, no star-field selectors/markup, warm theme tokens, and warm local visual fallbacks.
- Modify: `src/dreamloop/static/style.css`
  - Replace neon tokens with warm ink/paper/amber tokens.
  - Remove global star-field styling and heavy glow.
  - Restyle shared panels, navigation, forms, buttons, heatmap, trend bars, Gallery, Detail, Settings, and report surfaces.
- Modify: `src/dreamloop/templates/index.html`
  - Remove decorative `<div class="star-field">` elements.
  - Replace old neon fallback visual colors with warm bedside-amber fallbacks.
- Modify: `src/dreamloop/templates/detail.html`
  - Remove decorative `<div class="star-field">` and local visual glowing-dot markup.
- Optional after browser QA: `docs/assets/dashboard-screenshot.png`
  - Regenerate only if the new visual direction is accepted in browser.

## Task 1: Add Visual Regression Tests

**Files:**
- Modify: `tests/test_readme_positioning.py`

- [ ] **Step 1: Add failing tests for the visual-system contract**

Add this code to `tests/test_readme_positioning.py`:

```python
def test_dashboard_css_uses_bedside_amber_tokens_without_remote_fonts():
    css = Path("src/dreamloop/static/style.css").read_text(encoding="utf-8")

    assert "--ink: #1a1714" in css
    assert "--paper: #2a2520" in css
    assert "--amber: #d4a574" in css
    assert "--sage: #8ba87a" in css
    assert "--rust: #c47a5a" in css
    assert "fonts.googleapis" not in css
    assert "@import url(" not in css
    assert "--violet" not in css
    assert "--cyan" not in css
    assert "--rose" not in css


def test_frontend_removes_neon_starfield_treatment():
    css = Path("src/dreamloop/static/style.css").read_text(encoding="utf-8")
    index = Path("src/dreamloop/templates/index.html").read_text(encoding="utf-8")
    detail = Path("src/dreamloop/templates/detail.html").read_text(encoding="utf-8")

    assert "body::before" not in css
    assert ".star-field" not in css
    assert "star-field" not in index
    assert "star-field" not in detail
    assert "#8e63ff" not in css
    assert "#52e7d2" not in css
    assert "#ff6ba8" not in css
```

- [ ] **Step 2: Run tests and verify they fail for the current frontend**

Run:

```bash
uv run --extra dev pytest tests/test_readme_positioning.py -q
```

Expected: the new tests fail because the current CSS still uses neon tokens,
remote-font protection is not the issue but `--violet`, `--cyan`, `--rose`,
`body::before`, `.star-field`, and old colors still exist.

- [ ] **Step 3: Commit the failing tests only**

```bash
git add tests/test_readme_positioning.py
git commit -m "test: guard bedside amber visual system"
```

## Task 2: Replace Global Visual Tokens And Backgrounds

**Files:**
- Modify: `src/dreamloop/static/style.css`

- [ ] **Step 1: Replace `:root` with bedside-amber tokens**

Use these values:

```css
:root {
  color-scheme: dark;
  --ink: #1a1714;
  --ink-2: #221e1a;
  --paper: #2a2520;
  --paper-2: #332d27;
  --text: #e8e0d4;
  --text-soft: #c4b8a8;
  --muted: #8a7f72;
  --quiet: #6b6155;
  --amber: #d4a574;
  --amber-2: #e8c089;
  --amber-dim: #9a7b56;
  --sage: #8ba87a;
  --rust: #c47a5a;
  --clay: #a67c6a;
  --line: rgba(212, 165, 116, 0.15);
  --line-strong: rgba(212, 165, 116, 0.3);
  --shadow: rgba(40, 30, 20, 0.5);
  --font-display: Georgia, "Times New Roman", serif;
  --font-body: "Noto Sans SC", "Segoe UI", system-ui, sans-serif;
  --font-mono: "Cascadia Mono", "JetBrains Mono", Consolas, monospace;
}
```

- [ ] **Step 2: Replace body and html backgrounds**

Set `html` to `background: var(--ink);` and `body` to a single subtle warm
radial glow plus `var(--ink)`. Delete the `body::before` block entirely.

- [ ] **Step 3: Remove `.star-field` CSS blocks**

Delete `.star-field` and `.star-field::before`. Keep `.constellation-sky` as a
generic overflow/isolation helper if existing layout still uses it.

- [ ] **Step 4: Update shared fonts**

Replace repeated literal font stacks with `var(--font-display)`,
`var(--font-body)`, and `var(--font-mono)` where touching nearby rules.

## Task 3: Restyle Shared Surfaces And Controls

**Files:**
- Modify: `src/dreamloop/static/style.css`

- [ ] **Step 1: Flatten shared panel surfaces**

Change the shared surface block for `.hero-panel`, `.dashboard-hero`,
`.insight-card`, `.gallery-card`, `.detail-hero`, `.panel`, `.stat-card`,
`.dream-compose`, `.analysis-panel`, and `.status-strip > div` to use:

```css
border: 1px solid var(--line);
border-radius: 8px;
background: var(--paper);
box-shadow: 0 1px 3px var(--shadow);
```

- [ ] **Step 2: Add quiet hero ambience**

Give `.dashboard-hero`, `.hero-panel`, `.primary-workbench`, and `.detail-hero`
a restrained warm overlay with pseudo-elements or background layers that do not
use old neon colors.

- [ ] **Step 3: Restyle sidebar and brand mark**

Use solid `var(--ink-2)` sidebar background, no backdrop blur, no glow. Use an
amber ring and dot for `.brand-orbit`. Active nav should use an amber left
border, not cyan box-shadow or translation.

- [ ] **Step 4: Restyle buttons and links**

Use amber-filled primary buttons and transparent bordered secondary buttons.
Danger buttons use rust.

- [ ] **Step 5: Restyle forms and focus rings**

Inputs, textareas, and selects use warm borders and amber focus rings:

```css
textarea:focus,
input:focus,
select:focus {
  border-color: var(--amber-dim);
  box-shadow: 0 0 0 3px rgba(212, 165, 116, 0.12);
  outline: none;
}
```

## Task 4: Restyle Data Views And Status States

**Files:**
- Modify: `src/dreamloop/static/style.css`

- [ ] **Step 1: Convert heatmap to amber opacity levels**

Use `var(--paper)` for level 0 and amber rgba values for levels 1 through 4.

- [ ] **Step 2: Convert trend bars to matte amber**

Replace the cyan/violet/rose gradient in `.spectrum-track i` and `.symbol-row i`
with `background: var(--amber);`.

- [ ] **Step 3: Convert analysis and status colors**

Use sage for ready, amber for pending, rust for unavailable/warning, with
low-opacity backgrounds and borders.

- [ ] **Step 4: Restyle report callouts**

Use amber or sage left borders and warm paper backgrounds for `.analysis-summary`,
`.insight-callout`, `.interpretation-list article`, and `.reality-focus`.

## Task 5: Restyle Gallery And Local Visual Cards

**Files:**
- Modify: `src/dreamloop/static/style.css`
- Modify: `src/dreamloop/templates/index.html`
- Modify: `src/dreamloop/templates/detail.html`

- [ ] **Step 1: Remove star-field markup from templates**

Remove these decorative elements wherever they appear:

```html
<div class="star-field" aria-hidden="true"></div>
```

- [ ] **Step 2: Warm local visual fallback colors**

In `index.html`, replace fallback values:

```html
#69f0d7 -> #8ba87a
#8e63ff -> #d4a574
#ff6ba8 -> #c47a5a
```

- [ ] **Step 3: Remove glowing-dot local visual markup**

In `detail.html`, remove the `.visual-sky` block inside local visual memory
cards. Real image cards keep their `<img>`.

- [ ] **Step 4: Replace visual-card gradients**

Replace `.gallery-card::before` and `.local-visual-card::before` neon gradient
logic with warm paper treatments. Use a single fine amber line for
`.local-visual-card::before`.

## Task 6: Verify And Commit Implementation

**Files:**
- Verify all modified files.

- [ ] **Step 1: Run focused CSS/template tests**

```bash
uv run --extra dev pytest tests/test_readme_positioning.py -q
```

Expected: all tests in the file pass.

- [ ] **Step 2: Run full test suite**

```bash
uv run --extra dev pytest
```

Expected: all tests pass.

- [ ] **Step 3: Browser QA**

Start the app:

```bash
uv run dreamloop demo --reset
uv run dreamloop web
```

Inspect Dashboard, Log, Detail, Patterns, Gallery, and Settings at desktop and
mobile widths. Verify that no page is visually blank, text fits, and the UI
still feels like a useful dashboard/pattern tool.

- [ ] **Step 4: Commit implementation**

```bash
git add src/dreamloop/static/style.css src/dreamloop/templates/index.html src/dreamloop/templates/detail.html tests/test_readme_positioning.py
git commit -m "Refine frontend with bedside amber theme"
```

## Task 7: Screenshot Decision

**Files:**
- Optional modify: `docs/assets/dashboard-screenshot.png`

- [ ] **Step 1: Decide whether screenshot should be regenerated now**

If browser QA shows the new visual direction is accepted, regenerate the
Dashboard screenshot. If not, keep the old screenshot until another review pass.

- [ ] **Step 2: Commit screenshot only if regenerated**

```bash
git add docs/assets/dashboard-screenshot.png
git commit -m "Update dashboard screenshot for bedside amber theme"
```
