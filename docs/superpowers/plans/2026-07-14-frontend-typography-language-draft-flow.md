# Frontend Typography, Language, and Draft Flow Implementation Plan

**Spec:** `docs/superpowers/specs/2026-07-14-frontend-visual-hierarchy-refinement.md`

**Goal:** Implement the verified draft-language, analysis-language, and
typography corrections while preserving DreamLoop's FastAPI/Jinja architecture
and local-first data model.

**Architecture:** Keep interface language in the existing `lang` query
parameter and analysis language in the existing analysis row. Preserve an
unsaved analyzed draft through a stateless POST form. Validate analysis language
at the analyzer and persistence boundaries. Use Detail-only cross-language
fallback with explicit language metadata. Replace product-copy font subsets
with reproducibly generated full-cmap WOFF2 files.

**Tech stack:** Python, FastAPI, Jinja, SQLite, plain CSS, pytest, local WOFF2
assets.

---

## Execution Rules

- Execute the three phases sequentially.
- Each phase must be independently testable and committable.
- Do not add a frontend framework, database table, session store, translation
  API, or runtime font dependency.
- Keep downloads, source TTF files, conversion caches, and browser captures
  under `D:\CodexScratch`; do not write temporary assets to C.
- Preserve unrelated user changes. Do not begin a phase commit while unrelated
  paths are already staged.
- Use `apply_patch` for source and documentation edits. Binary font conversion
  and copying may use the commands in Phase 3.

## Preflight

### Task 0: Establish a reviewable baseline

**Files:** None.

- [ ] Run:

```powershell
git status --short --branch
git diff --cached --name-only
```

- [ ] If the index contains work outside the phase being implemented, stop
  before committing. Commit the existing baseline with user approval or use a
  clean worktree; do not unstage or fold unrelated changes into these commits.

- [ ] Run the current suite:

```powershell
uv run --extra dev pytest -q
```

- [ ] Record the baseline result. Do not reinterpret a pre-existing failure as
  a regression from this plan.

---

## Phase 1: Stateless Draft Language Switching

Target commit:

```text
fix: preserve drafts across language changes
```

### Task 1: Add failing route and state-preservation tests

**Files:**

- Modify: `tests/test_web_api.py`

- [ ] Add `test_language_toggles_use_route_aware_paths`.

The test visits Dashboard, Log, Patterns, Gallery, Settings, and a Detail page
and verifies that each `data-lang` destination is a root-relative path for the
current route, not a bare `?lang=...` URL.

- [ ] Add
  `test_draft_language_switch_preserves_state_without_persisting_or_reanalyzing`.

Test sequence:

1. Configure a counting analyzer.
2. POST Chinese dream text and reflections to
   `/drafts/analyze?lang=zh`.
3. Assert the response contains a POST language form targeting
   `/drafts/language`.
4. POST the returned content, reflection JSON, analysis JSON, and original
   analysis language to `/drafts/language` with `lang=en`.
5. Assert status 200, English interface copy, original Chinese dream text,
   original Chinese analysis, and an explicit `zh` analysis label.
6. Assert the analyzer call count remains one.
7. Assert `app.state.loop.list_dreams() == []`.
8. Assert no rendered language destination targets
   `GET /drafts/analyze`.
9. Assert the POST-rendered response marks the draft language form so client
   preference code cannot redirect it to `GET /drafts/language`.

- [ ] Run the focused tests and confirm they fail for the expected missing
  behavior:

```powershell
uv run --extra dev pytest tests/test_web_api.py -q -k "language_toggle or draft_language_switch"
```

### Task 2: Make normal language URLs route-aware

**Files:**

- Modify: `src/dreamloop/web.py`
- Modify: `src/dreamloop/templates/index.html`
- Modify: `src/dreamloop/templates/detail.html`

- [ ] In `render_home`, add:

```python
"language_urls": {
    "zh": _page_url(page, "zh"),
    "en": _page_url(page, "en"),
},
```

Use the existing `_page_url`; do not create a generic URL builder.

- [ ] In `dream_detail`, add:

```python
"language_urls": {
    "zh": _dream_url(dream_id, "zh"),
    "en": _dream_url(dream_id, "en"),
},
```

- [ ] Replace the bare `?lang=...` links in both templates with these
  explicit URLs.

- [ ] Add the same compact two-option language control to Detail beside its
  back link; the current Detail template has no language control, so do not
  leave `language_urls` unused.

- [ ] Preserve `data-lang` and `aria-current`, and make Detail clicks update
  the same `dreamloop.lang` localStorage preference used by the primary-page
  template.

### Task 3: Add the stateless draft-language POST path

**Files:**

- Modify: `src/dreamloop/web.py`
- Modify: `src/dreamloop/templates/index.html`
- Modify: `src/dreamloop/static/style.css`

- [ ] Add one small parser in `web.py` for the existing hidden payload:

```python
def _draft_from_form(
    content: str,
    analysis_json: str,
    analysis_language: str,
    reflections_json: str,
) -> dict[str, Any]:
    ...
```

It must:

- parse both JSON strings;
- require the analysis payload to be an object;
- normalize the analysis using the existing `normalize_analysis`;
- clean reflections using the existing reflection helpers;
- return the same draft shape already consumed by `render_home`;
- raise HTTP 400 for malformed analysis JSON;
- treat malformed reflection JSON as an empty object, matching current save
  behavior.

- [ ] Add one strict form-language helper in `web.py` that accepts only `en`
  or `zh` and raises HTTP 400 otherwise. Use it for every language value on the
  draft POST flow: `analyze_draft.lang`, `save_draft.lang`, the
  `/drafts/language` target `lang`, and submitted `analysis_language`. Keep
  `_lang` for forgiving GET query handling.

- [ ] Add:

```text
POST /drafts/language
```

The route receives `lang: str = Form(...)`, `content`, `analysis_json`,
`analysis_language`, and `reflections_json`, then calls
`render_home(..., page="log", draft=...)`. All five values are form fields; the
target language is not taken from a query string. The route performs no
analyzer call and no database write.

- [ ] When `draft` exists, render the language toggle as one POST form with
two submit buttons:

```html
<button name="lang" value="zh" data-lang="zh">中文</button>
<button name="lang" value="en" data-lang="en">English</button>
```

In both the language-switch form and the save form, carry `content` and both
JSON values in hidden textareas so multiline dream text is preserved exactly.
Carry `analysis_language` in a hidden input. Do not duplicate the analysis in a
query string or localStorage.

- [ ] Mark the form with `data-draft-language-form`. In the existing language
  preference script, preserve the automatic saved-language redirect only for
  ordinary GET pages without `lang`. When this marker is present and the POST
  result URL has no query language, use `document.documentElement.lang` as the
  current language, update localStorage, and do not navigate. This prevents a
  client-side `GET /drafts/language` 405 and preserves the posted draft.

- [ ] Expand the existing `.language-toggle a` styles to cover buttons
without changing control dimensions or focus visibility.

- [ ] Keep the analysis panel in its original language and add a localized
analysis-language badge when `draft.language != lang`.

- [ ] Add explicit English and Chinese translation keys for the analysis
  language label; do not assemble a mixed-language sentence in the template.

- [ ] Add localized save-button copy that names the retained analysis language
  when it differs from the interface language. Keep regeneration explicitly
  targeted at the interface language.

### Task 4: Verify and commit Phase 1

- [ ] Run:

```powershell
uv run --extra dev pytest tests/test_web_api.py -q -k "language or draft"
uv run --extra dev pytest -q
git diff --check
```

- [ ] Inspect the staged paths before committing:

```powershell
git add src/dreamloop/web.py src/dreamloop/templates/index.html src/dreamloop/templates/detail.html src/dreamloop/static/style.css tests/test_web_api.py
git diff --cached --name-only
git diff --cached --check
```

- [ ] Commit only the Phase 1 files:

```powershell
git commit -m "fix: preserve drafts across language changes"
```

---

## Phase 2: Analysis Language Integrity

Target commit:

```text
fix: enforce analysis output language
```

### Task 5: Add language-contract tests

**Files:**

- Modify: `tests/test_ai_config.py`
- Modify: `tests/test_core_workflow.py`
- Modify: `tests/test_web_api.py`

- [ ] Add prompt tests:

- `analysis_system_prompt("en")` contains no CJK characters.
- `build_analysis_user_payload` in English mode adds no CJK scaffolding when
  the supplied dream and reflections are ASCII.
- Chinese user-authored dream text remains byte-for-byte present in an English
  request payload.
- Both language prompts explicitly say the dream input may use another
  language.
- Both language prompts keep JSON keys in English.

- [ ] Add detector tests for:

- predominantly Chinese values;
- predominantly English values;
- English analysis containing a short Chinese dream quote;
- Chinese analysis containing a short English proper name;
- mixed output without a dominant language;
- too little human-readable output.

- [ ] Add provider retry tests by monkeypatching one private request method on
  `OpenAICompatibleAnalyzer`; do not call a network service.

Cover:

1. Matching first response: one provider call.
2. Chinese first response for an English request, then English response: two
   calls and success.
3. Two Chinese responses for an English request: exactly two calls and
   `AnalysisLanguageMismatch`.

- [ ] Add a custom counting analyzer test proving that shared validation does
  not blindly call a non-provider analyzer twice.

- [ ] Add persistence tests proving that mismatched and insufficient analyses
  create no `dream_analyses` row.

- [ ] Add a draft-language POST test proving that a tampered analysis payload
  cannot be relabeled during an interface switch and that content/reflections
  survive the localized error response.

- [ ] If existing short test analyzers become incomplete under the contract,
  lengthen their summaries with meaningful target-language text. Do not add a
  test-only bypass or weaken production thresholds to preserve synthetic
  fixtures.

- [ ] Run and confirm the new tests fail for the expected missing behavior:

```powershell
uv run --extra dev pytest tests/test_ai_config.py tests/test_core_workflow.py tests/test_web_api.py -q -k "language or incomplete or retry"
```

### Task 6: Localize the system prompt and add deterministic validation

**Files:**

- Modify: `src/dreamloop/analysis.py`

- [ ] Add two specific exceptions:

```python
class AnalysisLanguageMismatch(ValueError):
    pass


class AnalysisIncomplete(ValueError):
    pass
```

- [ ] Add a small shared classifier:

```python
def detect_analysis_language(payload: dict[str, Any]) -> str:
    ...


def require_analysis_language(payload: dict[str, Any], language: str) -> None:
    ...
```

Classifier contract:

- recursively collect string values only;
- ignore dictionary keys and any `raw_json` field;
- count CJK characters in `U+3400-U+4DBF` and `U+4E00-U+9FFF`;
- count ASCII Latin letters;
- classify Chinese when there are at least 8 CJK characters and CJK characters
  outnumber Latin letters;
- classify English when there are at least 20 Latin letters and Latin letters
  are at least twice the CJK count;
- otherwise return `unknown`;
- `require_analysis_language` raises `AnalysisIncomplete` for `unknown` and
  `AnalysisLanguageMismatch` for the opposite supported language.

These thresholds intentionally validate a two-language product contract, not
arbitrary natural-language detection.

- [ ] Split the Chinese-only requirements paragraph in
  `analysis_system_prompt` into English and Chinese variants.

- [ ] Add the explicit cross-language-input instruction in the target language.

- [ ] Add a `language` argument to `build_analysis_user_payload` and localize
  only its application-authored headings. Pass the requested language from
  `OpenAICompatibleAnalyzer`; never translate or rewrite the user's dream or
  reflections.

### Task 7: Give corrective retry to the provider that owns messages

**Files:**

- Modify: `src/dreamloop/analysis.py`
- Modify: `src/dreamloop/core.py`

- [ ] Extract the existing OpenAI-compatible request into one private method on
  `OpenAICompatibleAnalyzer`. The method accepts the message list and returns
  parsed JSON.

- [ ] In `OpenAICompatibleAnalyzer.analyze`:

1. Send the normal request.
2. If the result language matches, return it.
3. If it is the opposite language, send one second request with the same
   system/user content plus a concise target-language correction in the system
   message.
4. Validate and return the second result.
5. Do not retry malformed JSON or incomplete output as a language correction.

- [ ] In the existing shared `call_analyzer`, call the analyzer once and then
  run `require_analysis_language` on the returned payload.

This gives web, API, CLI, and pending-analysis paths one final guard while
keeping corrective prompt construction inside the provider implementation.

### Task 8: Protect persistence and expose specific errors

**Files:**

- Modify: `src/dreamloop/core.py`
- Modify: `src/dreamloop/web.py`
- Modify: `src/dreamloop/templates/index.html`
- Modify: `src/dreamloop/templates/detail.html`
- Modify: `tests/test_core_workflow.py`
- Modify: `tests/test_web_api.py`

- [ ] In `DreamLoop._store_analysis`, reject a language outside `en` and `zh`
  instead of passing it through forgiving `normalize_language`, then validate
  normalized data before executing the insert/upsert. This shared persistence
  boundary protects direct core calls as well as hidden draft form submissions.

- [ ] After the shared validator exists, have `_draft_from_form` validate the
  normalized payload against its strict `analysis_language`. Catch mismatch and
  incomplete errors in `/drafts/language`, render the Log page with the specific
  localized error, and preserve content/reflections without an analyzer call or
  database write.

- [ ] Ensure validation ignores the normalized `raw_json` string so JSON keys
  are not counted as English content.

- [ ] Replace the boolean draft analysis error with a small error code or
  pre-localized message. Add distinct translations for:

- provider/general failure;
- wrong output language;
- incomplete output.

- [ ] Catch `AnalysisLanguageMismatch` and `AnalysisIncomplete` explicitly in
  draft analyze, draft language switch, draft save, saved-dream analyze, and API
  analyze routes.

- [ ] Add `request: Request` to draft save so a rejected hidden payload can be
  rendered back on Log with its content and reflections intact. Confirm the
  exception from `_store_analysis` rolls back the surrounding dream insert.

- [ ] Add a direct-core regression test proving
  `add_dream_with_analysis(..., language="fr")` raises and rolls back both the
  dream and analysis inserts.

- [ ] Preserve draft content and reflections on draft errors.

- [ ] Return HTTP 422 from API analyze routes for language/incomplete output,
  while retaining existing 404 and 409 behavior.

- [ ] Use loading copy such as “Analyzing and verifying English output...” /
  “正在分析并核对中文输出……” so one possible corrective retry is disclosed
  without adding streaming or polling.

### Task 9: Handle existing mislabeled rows and Detail fallback

**Files:**

- Modify: `src/dreamloop/core.py`
- Modify: `src/dreamloop/web.py`
- Modify: `src/dreamloop/templates/index.html`
- Modify: `src/dreamloop/templates/detail.html`
- Modify: `tests/test_core_workflow.py`
- Modify: `tests/test_web_api.py`

- [ ] Extend `analysis_from_row` with:

- `detected_language`;
- `language_valid`, true only when detected and stored languages agree;
- `language_mismatch`.

Do not mutate the row.

- [ ] In `list_dreams_with_analysis(language)`, treat a requested-language row
whose detected content is invalid for that label as unavailable for trends,
symbols, themes, dashboard insight, and graph calculations. Preserve separate
invalid/mismatch metadata on the dream so Log can show a specific regenerate
warning.

- [ ] Extend `get_dream` with an explicit keyword-only
  `allow_analysis_fallback: bool = False`. Preserve exact-language behavior for
  every existing caller. Only the Detail route passes `True`.

- [ ] When `allow_analysis_fallback=True`, query both supported analysis rows
  and select:

1. valid requested-language row;
2. valid other-language row as a labeled fallback;
3. mismatched requested-language row with a warning;
4. no analysis.

- [ ] Set explicit dream context fields:

- `requested_analysis_language`;
- `displayed_analysis_language`;
- `analysis_is_fallback`;
- `analysis_language_mismatch`.
- `analysis_actions_enabled`, true only for a valid exact or fallback row.

- [ ] Query the Detail image using `displayed_analysis_language`, not interface
  language, when a valid analysis fallback is displayed.

- [ ] Add a regression test proving API reads and core generation calls retain
  exact-language behavior and do not acquire Detail fallback implicitly.

- [ ] Audit analysis consumers outside the main list: `feedback_summary`,
  similarity calculations, local visual generation, and dream-image prompt
  construction. Aggregate/similarity paths skip invalid rows. Generation paths
  that already support dream-only operation treat an invalid row as absent, so
  they never consume mislabeled analysis while preserving their independent API
  behavior.

- [ ] Show a language badge and mismatch/fallback warning above the Detail and
  Log analysis content.

- [ ] When only a mismatched row is available, render its warning and
  regeneration action but hide feedback, local visual generation, and
  dream-image generation.

- [ ] Keep explicit regeneration targeted at interface `lang`.

### Task 10: Keep analysis-bound actions on the displayed language

**Files:**

- Modify: `src/dreamloop/core.py`
- Modify: `src/dreamloop/web.py`
- Modify: `src/dreamloop/templates/detail.html`
- Modify: `tests/test_core_workflow.py`
- Modify: `tests/test_web_api.py`

- [ ] Add a hidden `analysis_language` field to Detail feedback, local visual,
  and dream-image forms.

- [ ] Keep query `lang` as interface language and redirect language.

- [ ] Reuse the strict form-language helper from Phase 1 for submitted
  `analysis_language`. Do not use `_lang` here because it silently turns invalid
  input into English.

- [ ] In the three Detail form routes, require a valid exact analysis row for
  the submitted `analysis_language` before feedback, local visual, or image
  generation. Return HTTP 409 before any side effect when it is absent or
  mismatched. Do not let these write paths invoke Detail fallback. This guard
  does not change the independent API generation contract.

- [ ] Add a focused `AnalysisUnavailableError(RuntimeError)` in `core.py`. In
  `DreamLoop.add_feedback`, require that the exact
  `(dream_id, analysis_language)` row exists and passes stored-language
  validation before inserting feedback; otherwise raise that error. Map it to
  HTTP 409 in both HTML and API feedback routes, while unsupported ratings stay
  HTTP 400. This keeps feedback truthful at the persistence boundary.

- [ ] Load feedback using `displayed_analysis_language`.

- [ ] Add end-to-end tests:

1. English Detail with only valid Chinese analysis displays the Chinese
   fallback and English UI.
2. Feedback is stored under `zh` and redirects back to `?lang=en`.
3. Local visual and dream-image generation receive `zh`.
4. Regenerate analysis still targets `en`.
5. A bad stored `en` row plus a valid `zh` row selects the valid Chinese
   fallback and exposes regeneration.
6. A bad stored `en` row with no valid alternative exposes regeneration but
   no feedback, visual, or image action.
7. Tampering each Detail form's `analysis_language` to a supported language
   without a valid exact row returns 409 and creates no feedback, visual, or
   image side effect.
8. API feedback against a missing or invalid exact-language row returns 409 and
   creates no feedback row.
9. Feedback summaries and similarity omit invalid stored analyses, while an
   independent API generation call uses dream text without consuming the bad
   analysis or crossing to the other language.

### Task 11: Verify and commit Phase 2

- [ ] Run:

```powershell
uv run --extra dev pytest tests/test_ai_config.py tests/test_core_workflow.py tests/test_web_api.py -q
uv run --extra dev pytest -q
git diff --check
```

- [ ] Inspect the staged Phase 2 paths:

```powershell
git add src/dreamloop/analysis.py src/dreamloop/core.py src/dreamloop/web.py src/dreamloop/templates/index.html src/dreamloop/templates/detail.html tests/test_ai_config.py tests/test_core_workflow.py tests/test_web_api.py
git diff --cached --name-only
git diff --cached --check
```

- [ ] Commit:

```powershell
git commit -m "fix: enforce analysis output language"
```

---

## Phase 3: Full Offline Fonts and Research Atlas Type Scale

Target commit:

```text
style: unify offline typography
```

### Task 12: Pin font sources and add failing asset tests

**Files:**

- Modify: `tests/test_readme_positioning.py`
- Modify: `design-qa.md`

Pinned upstream repository:

```text
https://github.com/google/fonts
commit: 03781cf7a714af8431d14b6f337f923c774429d7
```

Pinned source files:

| Source | Bytes | SHA-256 |
| --- | ---: | --- |
| `NotoSansSC[wght].ttf` | 17,772,300 | `A3041811A78C361B1DE50F953C805E0244951C21C5BD412F7232EF0D899AF0DA` |
| `NotoSerifSC[wght].ttf` | 25,125,512 | `050080D9255A86808F2945BFFAC582B31EF32BC36411CE29563B4961670C66F9` |
| Noto Sans SC `OFL.txt` | 4,388 | `1C05C68C34F9708415AADA51F17E1B0092D2CEA709BF4A94CD38114F9E73D7D9` |
| Noto Serif SC `OFL.txt` | 4,350 | `5E0DA210FB04058A8C0087985D2D456B931C2579811A49655721D3CF0C36B6D6` |

Source URLs:

```text
https://raw.githubusercontent.com/google/fonts/03781cf7a714af8431d14b6f337f923c774429d7/ofl/notosanssc/NotoSansSC%5Bwght%5D.ttf
https://raw.githubusercontent.com/google/fonts/03781cf7a714af8431d14b6f337f923c774429d7/ofl/notoserifsc/NotoSerifSC%5Bwght%5D.ttf
https://raw.githubusercontent.com/google/fonts/03781cf7a714af8431d14b6f337f923c774429d7/ofl/notosanssc/OFL.txt
https://raw.githubusercontent.com/google/fonts/03781cf7a714af8431d14b6f337f923c774429d7/ofl/notoserifsc/OFL.txt
```

- [ ] Add binary hash assertions for the two final WOFF2 files.

- [ ] Replace the old `> 100_000` subset-size assertions.

- [ ] Assert both pinned OFL files are present.

- [ ] Add CSS contract assertions:

- display stack starts with `"Noto Serif SC"`;
- both replaced Noto `@font-face` URLs carry the new asset version token;
- navigation and metadata never declare 10px or 11px;
- no `font-size: clamp(...vw...)` remains;
- the local visual title uses the fixed Research Atlas scale.

- [ ] Update `design-qa.md` to replace the stale product-copy-subset statement
  with pinned source, conversion, cmap, and final hash evidence.

### Task 13: Generate full-cmap WOFF2 files reproducibly

**Files:**

- Replace: `src/dreamloop/static/fonts/noto/NotoSansSC-DreamLoop.woff2`
- Replace: `src/dreamloop/static/fonts/noto/NotoSerifSC-DreamLoop.woff2`
- Replace: `src/dreamloop/static/fonts/noto/OFL.txt`
- Add: `src/dreamloop/static/fonts/noto/OFL-NotoSerifSC.txt`

Use:

```text
fonttools[woff] == 4.63.0
brotli == 1.2.0
```

- [ ] Create and verify a scratch root:

```powershell
$root = [System.IO.Path]::GetFullPath('D:\CodexScratch\DreamLoop-font-build')
if ($root -ne 'D:\CodexScratch\DreamLoop-font-build') { throw 'Unexpected scratch path' }
New-Item -ItemType Directory -Force -Path $root | Out-Null
```

- [ ] Set `UV_CACHE_DIR`, `UV_PYTHON_INSTALL_DIR`, `TEMP`, and `TMP`
under that scratch root before running `uv`:

```powershell
$env:UV_CACHE_DIR = Join-Path $root 'uv-cache'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $root 'uv-python'
$env:TEMP = Join-Path $root 'temp'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force -Path $env:UV_CACHE_DIR, $env:UV_PYTHON_INSTALL_DIR, $env:TEMP | Out-Null
```

- [ ] Download the four pinned source files into the scratch root and verify
their SHA-256 values before conversion.

Use these local names so conversion and license copying are deterministic:

| Upstream file | Scratch name | Repository destination |
| --- | --- | --- |
| `NotoSansSC[wght].ttf` | `NotoSansSC.ttf` | converted to `NotoSansSC-DreamLoop.woff2` |
| `NotoSerifSC[wght].ttf` | `NotoSerifSC.ttf` | converted to `NotoSerifSC-DreamLoop.woff2` |
| Noto Sans SC `OFL.txt` | `OFL-NotoSansSC.txt` | `OFL.txt` |
| Noto Serif SC `OFL.txt` | `OFL-NotoSerifSC.txt` | `OFL-NotoSerifSC.txt` |

- [ ] Convert without subsetting:

```python
from pathlib import Path
from fontTools.ttLib import TTFont

root = Path(r"D:\CodexScratch\DreamLoop-font-build")
for source_name, output_name in [
    ("NotoSansSC.ttf", "NotoSansSC-DreamLoop.woff2"),
    ("NotoSerifSC.ttf", "NotoSerifSC-DreamLoop.woff2"),
]:
    font = TTFont(root / source_name)
    font.flavor = "woff2"
    font.save(root / output_name, reorderTables=False)
```

Run the script with:

```powershell
$fontBuildScript = Join-Path $root 'font-build-script.py'
uv run --with 'fonttools[woff]==4.63.0' --with 'brotli==1.2.0' python $fontBuildScript
```

The temporary `font-build-script.py` belongs in the scratch root, not the
repository.

Expected output:

| Output | Bytes | cmap entries | SHA-256 |
| --- | ---: | ---: | --- |
| `NotoSansSC-DreamLoop.woff2` | 7,782,008 | 30,890 | `F7562D807E6CA894A8200A7C09A46A51389180ABA1998FB4B9FED8707CF8087F` |
| `NotoSerifSC-DreamLoop.woff2` | 11,032,408 | 30,928 | `DE3790AA483D8DB6E8B9C916DC76F2FCBC57D84FF7D21D98F6D2BD905D352666` |

- [ ] Copy only the verified WOFF2 and license outputs into the project font
directory.

- [ ] Delete `D:\CodexScratch\DreamLoop-font-build` after verification using
a checked absolute path.

### Task 14: Apply the fixed Research Atlas type system

**Files:**

- Modify: `src/dreamloop/static/style.css`
- Modify: `src/dreamloop/templates/index.html`
- Modify: `src/dreamloop/templates/detail.html`

- [ ] Remove the product-copy subset comment.

- [ ] Change font roles to:

```css
--font-display: "Noto Serif SC", serif;
--font-body: "Noto Sans SC", sans-serif;
--font-mono: "Cascadia Mono", "Noto Sans SC", monospace;
```

- [ ] Add `?v=20260714-full-cmap` directly to both replaced Noto font `src`
  URLs. Updating only the template's stylesheet query does not invalidate an
  already cached nested WOFF2 URL.

- [ ] Replace every viewport-based font clamp with fixed desktop sizes and
existing responsive media-query overrides:

| Selector/role | Desktop | Mobile |
| --- | ---: | ---: |
| page/topbar title | 48px | 36px |
| Detail title | 40px | 34px |
| major section heading | 28px | 24px |
| card title | 20px | 18px |
| dream prose | 28px | 22px |
| body/report copy | 16px | 16px |
| local visual title | 24px | 21px |
| navigation/metadata | 12px minimum | 12px minimum |

- [ ] Raise all current 10px and 11px metadata rules to 12px. If a heatmap
cell no longer fits, increase its stable cell dimensions rather than shrinking
the label.

- [ ] Keep Chinese labels and navigation on `var(--font-body)`; reserve mono
for numeric/date/provider values.

- [ ] Give local visual-memory titles a 1.25 minimum line height,
  `overflow-wrap: anywhere`, and a stable four-line maximum at both breakpoints.

- [ ] Update the stylesheet cache query in both templates after CSS and font
changes.

### Task 15: Compact visual-memory titles at the normalization boundary

**Files:**

- Modify: `src/dreamloop/visuals.py`
- Modify: `src/dreamloop/core.py`
- Modify: `tests/test_core_workflow.py`
- Modify: `tests/test_web_api.py`

- [ ] In `normalize_visual_memory`, trim the candidate title, take the first
  non-empty segment before a newline or `。！？.!?` sentence terminator, and fall
  back to the trimmed candidate when no segment is found. Cap it at 48 Unicode
  code points by using the first 47 plus `…` when truncation is required.

- [ ] Have `generate_visual_memory` normalize the payload before storing and
returning it. Remove its current 90-character truncation and do not duplicate
title shortening in the generator or template.

- [ ] Add tests for:

- newly generated long Chinese summary;
- newly generated long English summary;
- existing stored legacy visual with a long title;
- Detail and Gallery rendering without the long untrimmed title.

### Task 16: Verify font coverage and visual behavior

- [ ] Run focused and full tests:

```powershell
uv run --extra dev pytest tests/test_readme_positioning.py tests/test_core_workflow.py tests/test_web_api.py -q
uv run --extra dev pytest -q
git diff --check
```

- [ ] Run an ephemeral font cmap check with
  `fonttools[woff]==4.63.0` from a D-drive scratch cache. Verify:

- the two output cmap counts match Task 13;
- both fonts cover every CJK code point in current templates/translations;
- both fonts cover every CJK code point used by Dream #4;
- no runtime/project dependency was added.

- [ ] Start the local server on the first free port:

```powershell
uv run dreamloop web --port 8766
```

Use another port if 8766 is occupied.

- [ ] Check Dashboard, Log, Detail, Patterns, Gallery, and Settings in Chinese
and English at:

- 1440 x 900
- 1024 x 768
- 760 x 900
- 390 x 844
- 360 x 800

- [ ] Verify:

- no overlap, clipping, horizontal overflow, or incoherent wrapping;
- no raw 405/422 framework page during the intended UI flow;
- Dream #4 uses packaged CJK glyphs;
- after `document.fonts.ready`, both Noto faces pass `document.fonts.check` and
  the versioned full-cmap WOFF2 requests return 200 with the Task 13 sizes;
- local visual title remains at most four lines;
- interface and analysis language badges are truthful;
- language switching, regeneration, save, feedback, visual generation, and
  image generation use the expected language;
- no remote font request;
- no browser console error.

- [ ] Store temporary screenshots under
  `D:\CodexScratch\DreamLoop-frontend-qa-2026-07-14`. Add no screenshot to
  the repository unless the user explicitly approves it as a versioned
  reference.

- [ ] Keep those screenshots only through user review, then delete the checked
  D-drive QA directory unless the user asks to retain it.

- [ ] Reuse an existing DreamLoop server when possible. If a QA-only server is
  started, stop it after capture unless it is intentionally left as the single
  user-facing preview; in that case report its URL.

### Task 17: Commit Phase 3

- [ ] Inspect and stage only Phase 3 paths:

```powershell
git add design-qa.md src/dreamloop/static/style.css src/dreamloop/static/fonts/noto src/dreamloop/templates/index.html src/dreamloop/templates/detail.html src/dreamloop/visuals.py src/dreamloop/core.py tests/test_readme_positioning.py tests/test_core_workflow.py tests/test_web_api.py
git diff --cached --name-only
git diff --cached --check
```

- [ ] Confirm the font file sizes and hashes from Task 13.

- [ ] Commit:

```powershell
git commit -m "style: unify offline typography"
```

---

## Final Integrated Verification

- [ ] Run:

```powershell
uv run --extra dev pytest -q
git status --short
git log -3 --oneline
```

- [ ] Confirm the three commits are independently understandable and no
temporary source fonts, conversion scripts, caches, browser captures, database
files, or secrets are tracked.

- [ ] Compare final behavior against every acceptance criterion in the spec.

## Plan Review Record

Five implementation-readiness reviews were applied before this plan was marked
ready:

1. Corrected retry ownership, blocked unknown-language persistence, pinned font
   provenance, and made stored-analysis fallback deterministic.
2. Preserved multiline draft text, introduced strict form-language validation,
   disabled analysis-bound actions for mismatch-only rows, pinned Brotli in the
   executable font command, and added temporary-artifact/server cleanup.
3. Kept core and API reads exact-language by default, limited fallback to an
   explicit Detail option, and required exact analysis rows for feedback and
   Detail-bound generation writes.
4. Aligned spec-versus-plan authority, made route-path and POST-field semantics
   precise, completed the core/test file inventory, defined 409 feedback
   behavior, prevented the localStorage POST-to-GET regression, completed the
   Detail language control, and made visual-title truncation deterministic.
5. Removed Chinese application scaffolding from English provider messages,
   rejected unsupported persistence labels, blocked invalid rows from secondary
   consumers, and corrected the executable D-drive font-build command and cache
   setup.

Review verdict: ready to execute after the Preflight index check. No unresolved
architecture or data-integrity blocker remains.

## Explicitly Skipped

- Automatic translation of an already generated analysis.
- Persistent server-side drafts.
- Automatic mutation of existing mislabeled analysis rows.
- General-purpose language detection.
- Official Google Fonts segmented CSS and hundreds of unicode-range files.
- New visual assets or a committed mockup.

Add any skipped item only after a measured limitation requires it.
