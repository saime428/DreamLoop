# DreamLoop Frontend Typography, Language, and Draft Flow

Date: 2026-07-14

Status: Ready for implementation

Selected direction: Research Atlas

This document is the product-behavior and acceptance source of truth. The
companion implementation plan at
`docs/superpowers/plans/2026-07-14-frontend-typography-language-draft-flow.md`
defines the execution sequence and must conform to this specification.
Generated Research Atlas mockups are non-binding visual references unless a
specific image is later versioned under `docs/` and linked here.

## 1. Purpose

This specification defines the next DreamLoop frontend correction pass. It
keeps the current local-first product and six-page information architecture,
while fixing three verified problems:

1. User-authored Chinese text can fall back to system fonts and visibly mix
   typefaces.
2. An analysis requested in English can be returned and stored as Chinese.
3. Switching the interface language from an unsaved analysis response produces
   a 405 error.

The selected visual direction is Research Atlas: compact, calm, information
dense, and optimized for repeated reading rather than decorative impact.

## 2. Verified Baseline

The following findings are reproducible and are requirements inputs, not visual
guesses.

### 2.1 Draft language switching

The draft analysis response is rendered at:

```text
POST /drafts/analyze?lang=zh
```

The language links currently use relative URLs such as `?lang=en`. From that
response URL, the browser resolves the English link to:

```text
GET /drafts/analyze?lang=en
```

Only a POST route exists at `/drafts/analyze`, so the request deterministically
returns `405 Method Not Allowed`.

Saving appears to fix the problem only because save redirects to a normal GET
detail page. Saving is not an intended prerequisite for changing the interface
language.

### 2.2 Offline font coverage

The packaged Noto Sans SC and Noto Serif SC files are product-copy subsets. For
the real Dream #4 content and analysis:

- 375 distinct CJK characters are required.
- Each packaged Noto file covers 249 of those characters.
- Each file misses 126 required characters.

The browser therefore has to fall back to an operating-system font for part of
the same text. This is a real mixed-glyph problem in addition to the current
wide size range.

### 2.3 Analysis output language

A controlled request with Chinese dream text and `lang=en` passes
`language="en"` to the analyzer and renders English when the analyzer follows
the contract. Input language does not intentionally select output language.

The current Dream #4 database contains both `zh` and `en` analysis rows, but
the stored `en` row is predominantly Chinese. The application currently trusts
the provider response and stores it under the requested language without
validating the returned language.

The English system prompt also contains 48 CJK characters because one
requirements paragraph is always written in Chinese. This is a verified prompt
defect and a plausible contributor, but one model response cannot prove a
single causal factor. The application-authored user-payload wrapper also adds
Chinese headings in English mode. Provider compliance remains probabilistic,
so prompt cleanup still requires a validated postcondition.

## 3. Product Decisions

### 3.1 Interface and analysis languages are separate

- `lang` controls interface chrome, labels, navigation, and action copy.
- `analysis_language` identifies the language of analysis content.
- Dream input language does not override either setting.
- Changing interface language does not silently translate or regenerate an
  analysis.
- Any displayed analysis whose language differs from the interface must show a
  visible language label.

### 3.2 Unsaved work is not navigation state

- A user may change interface language before saving.
- Switching language must preserve dream text, optional reflections, and the
  current analysis.
- Switching language must not save a dream.
- Switching language must not call an AI provider.
- Regenerating in another language is a separate explicit action.

### 3.3 Stored language labels must be truthful

- A provider response must not be stored as `en` when its values are
  predominantly Chinese, or as `zh` when its values are predominantly
  English.
- Existing mismatched records must not be silently rewritten or deleted.
- Existing mismatches are displayed with a warning and an explicit regenerate
  action.

## 4. Goals

- Adopt Research Atlas as the single frontend direction.
- Give display, body, and metadata typography distinct jobs.
- Package the complete cmap of pinned upstream Noto SC fonts and verify it
  covers the current product copy and real Dream #4 sample.
- Remove the unsaved-draft 405 path without adding persistent draft storage.
- Make requested and actual analysis language agree before persistence.
- Keep saved and unsaved user data intact across interface-language changes.
- Preserve current accessibility, responsive behavior, and local-first privacy.

## 5. Non-Goals

- No JavaScript framework, component library, or client-side router.
- No database migration or new draft/session table.
- No automatic translation service.
- No automatic AI call when the language toggle is used.
- No destructive repair of existing analysis rows.
- No remote fonts, remote UI assets, analytics, or tracking.
- No unrelated dashboard, pattern-analysis, image-provider, or import redesign.

## 6. Visual Direction

Research Atlas uses a compact title region, restrained surfaces, clear data
alignment, and a stronger distinction between narrative and operational text.
It is not a terminal theme and does not make all UI text monospaced.

- Serif is reserved for page titles, dream prose, and principal interpretation
  statements.
- Sans serif owns navigation, controls, labels, section headings, and report
  body text.
- Mono owns dates, counts, provider/model identifiers, percentages, and short
  machine-state values.
- Amber remains the primary action and focus color.
- Violet remains secondary data encoding, not a universal border color.
- Spacing and dividers separate sections before additional card borders.
- No glow, hover lift, glassmorphism, decorative looping motion, or nested
  cards are introduced.

## 7. Typography Requirements

### 7.1 Offline font assets

- Replace the two product-copy Noto subsets with WOFF2 assets containing the
  complete cmap supplied by pinned upstream Noto Sans SC and Noto Serif SC
  font files.
- The implementation plan must pin the upstream repository revision, source
  URLs, SHA-256 checksums, and OFL license before downloading or converting
  either font.
- Keep font files, licenses, and CSS references inside
  `src/dreamloop/static/fonts/`.
- Version the replaced Noto font URLs themselves; changing only the stylesheet
  URL is not sufficient to invalidate a previously cached nested font asset.
- Keep Cascadia Mono for numeric and machine-oriented metadata.
- Do not depend on an installed Windows font for characters present in the
  pinned upstream font cmap.
- Keep `font-display: swap`.
- Record the final asset-size change during implementation review.
- Do not create another product-copy subset. Characters outside the pinned
  upstream cmap, including unsupported rare ideographs or emoji, may use the
  documented operating-system fallback stack.

The preferred stack is:

```css
--font-display: "Noto Serif SC", serif;
--font-body: "Noto Sans SC", sans-serif;
--font-mono: "Cascadia Mono", "Noto Sans SC", monospace;
```

Chinese navigation and prose must not be assigned to the mono role. Mixed
Chinese and numeric metadata may use Noto Sans SC for the label and Cascadia
Mono for the value.

### 7.2 Type scale

Use fixed responsive steps rather than viewport-width font scaling.

| Role | Desktop | Mobile | Typeface |
| --- | ---: | ---: | --- |
| Page title | 48px | 36px | Display |
| Detail dream title | 40px | 34px | Display |
| Major section title | 28px | 24px | Sans |
| Card title | 20px | 18px | Sans or display by content role |
| Dream prose | 28px | 22px | Display |
| Body and report copy | 16px | 16px | Sans |
| Controls | 14px | 14px | Sans |
| Metadata and navigation | 12px minimum | 12px minimum | Sans or mono |

Additional rules:

- Do not use `vw` to scale font size.
- Body and report line height is 1.55 to 1.7.
- Dream prose line height is 1.3 to 1.45.
- Compact labels may not reduce below 12px.
- User-authored text must use `overflow-wrap: anywhere` where it can enter a
  constrained grid or card.

### 7.3 Local visual-memory title

The visual-memory card must not turn a full analysis summary into a display
paragraph.

- Derive the title from the first non-empty sentence of the analysis summary.
- Hard-cap the stored presentation title at 48 Unicode characters.
- Preserve the complete summary in the analysis report.
- Render the title at 24px desktop and 21px mobile with a minimum 1.25 line
  height.
- Keep the title region to at most four visual lines.
- Existing long visual-memory titles may be shortened at render time, but the
  underlying stored analysis must not be modified.

## 8. Analysis Language Requirements

### 8.1 Prompt construction

- The English system prompt and application-authored user-payload labels must
  contain English instructions only. Chinese supplied by the user in the dream
  or reflections remains unchanged.
- The Chinese system prompt may contain Chinese instructions.
- Both prompts must explicitly state that the source dream may be written in
  another language and that all human-readable field values must use the
  requested analysis language.
- JSON keys remain English in both modes.
- Prompt tests must fail if English-mode instructional scaffolding contains CJK
  characters when the supplied dream and reflections are ASCII.

### 8.2 Output-language validation and retry ownership

Final language validation belongs at the shared analyzer-call boundary so web,
API, and core workflows receive the same protection. Corrective retry belongs
inside `OpenAICompatibleAnalyzer`, because that class owns the provider message
construction and can add an actual correction instruction.

- Flatten human-readable response values; do not count JSON keys.
- Evaluate the complete response rather than classifying individual proper
  names or symbols.
- A sufficiently long response is valid only when the requested language is
  dominant.
- A response without enough human-readable text for a reliable whole-report
  decision is an incomplete analysis and must not be persisted.
- `OpenAICompatibleAnalyzer` may retry once with a concise correction that
  names the required language.
- Static and custom analyzers receive one call; the shared boundary validates
  their final result but must not blindly repeat an identical request.
- Never retry more than once.
- If the final response still conflicts, return a specific language-mismatch
  error and do not persist or label it as the requested language.

The retry is part of the user's explicit Analyze action. It may repeat the same
provider transmission once, so the initial loading copy must disclose that
output language will be verified and may be corrected. The current
server-rendered request does not need intermediate progress streaming. This
check is a contract guard, not a general translation or language-detection
system.

### 8.3 Save-time validation

- The draft save route must validate `analysis_json` again because hidden form
  fields are untrusted input.
- The shared analysis persistence boundary must reject language labels outside
  `en` and `zh`; it must not normalize an unsupported write to English.
- A clearly mismatched payload must not be saved under the supplied
  `analysis_language`.
- Invalid or mismatched payloads return to the Log view with the user's dream
  text intact and a specific localized message.
- Valid analysis data continues to use the existing
  `(dream_id, language)` storage model.

### 8.4 Existing records

- Detect obvious stored-language mismatches when preparing an analysis for
  display.
- Show the stored label and detected language, for example:
  `Stored as English / content appears Chinese`.
- Offer regeneration in the active interface language.
- Do not mutate the database until the user explicitly regenerates and saves a
  replacement.

Stored-analysis selection uses this deterministic order:

1. The requested-language row when its detected language is valid.
2. The other supported-language row when it is valid, shown as a labeled
   fallback.
3. The requested-language row when it is mismatched, shown only with an
   explicit mismatch warning and regenerate action.
4. No analysis state when neither row exists or can be rendered safely.

List and aggregate views must not feed an invalid stored-language row into
themes, symbols, trends, feedback summaries, similarity, or graph calculations.
They treat that exact-language row as unavailable and expose a regenerate
warning where the analysis status is shown. A generation path that is designed
to work from dream text without analysis may continue, but it must treat an
invalid analysis row as absent. Cross-language fallback is limited to the
Detail page; exact-language API and core reads never acquire it implicitly.

## 9. Draft Language-Switch Requirements

### 9.1 Normal pages

- Language destinations must be root-relative, route-aware paths.
- Dashboard, Log, Patterns, Gallery, Settings, and Detail must never rely on a
  bare relative `?lang=...` link.
- Detail must expose the same compact Chinese/English language control as the
  five primary pages instead of requiring a trip back to another page.
- Reuse the existing page and dream URL helpers.

### 9.2 Unsaved analyzed draft

When a draft analysis is present, render the language control as a small POST
form targeting a dedicated draft-language route.

The request carries the fields already present in the save form:

- `content`
- `reflections_json`
- `analysis_json`
- `analysis_language`
- target interface `lang`

The route:

1. Validates and normalizes the submitted JSON.
2. Strictly accepts only `en` or `zh` for target and analysis languages;
   invalid POST values return HTTP 400 rather than silently becoming English.
3. Renders the Log page in the target interface language.
4. Restores the dream text and optional reflections.
5. Restores the analysis without changing `analysis_language`.
6. Does not call the analyzer.
7. Does not create or update a dream record.
8. Treats the server-rendered target language as current for local preference
   handling; client code must not redirect the POST result to a GET-only URL.

After language validation is implemented, the route also verifies that the
submitted analysis content agrees with `analysis_language`. A tampered or
invalid payload renders a specific localized error with dream text and
reflections intact; it is never relabeled merely to complete the switch.

If interface and analysis language differ, show:

- An explicit analysis-language badge.
- A regenerate action in the interface language.
- A save action that names the analysis language being saved.

### 9.3 Save after an interface switch

- Save the analysis under its actual validated analysis language.
- Keep the user's selected interface language after the redirect.
- Apply the stored-analysis selection order from section 8.4 and label any
  fallback language explicitly.
- Offer explicit generation in the active interface language.
- Never make a saved analysis appear to have disappeared solely because the
  interface language changed.

When Detail displays a fallback analysis, operations tied to that analysis use
its actual language while `lang` continues to control the interface and
redirect destination:

- Feedback is loaded and saved against the displayed analysis language.
- Local visual-memory generation uses the displayed analysis language.
- Dream-image generation uses the displayed analysis language.
- Explicit analysis regeneration still targets the active interface language.

When only a mismatched row can be displayed, feedback, local visual generation,
and dream-image generation are unavailable because there is no truthfully
labeled analysis row to bind them to. Regeneration remains available.

## 10. Error and Loading States

- Language mismatch is distinct from provider unavailable, malformed JSON, and
  general analysis failure.
- Every error is localized according to interface language.
- A failed retry must leave the dream text and reflections available.
- Loading text must name the requested analysis language when regeneration is
  explicit.
- Existing reduced-motion behavior remains active.
- Language controls remain keyboard accessible and at least 44px high.

## 11. Expected Files

Implementation is expected to remain within the existing ownership boundaries:

- `src/dreamloop/analysis.py`
- `src/dreamloop/core.py`
- `src/dreamloop/web.py`
- `src/dreamloop/templates/index.html`
- `src/dreamloop/templates/detail.html`
- `src/dreamloop/static/style.css`
- `src/dreamloop/static/fonts/noto/`
- `src/dreamloop/visuals.py`
- `tests/test_ai_config.py`
- `tests/test_core_workflow.py`
- `tests/test_web_api.py`
- `tests/test_readme_positioning.py` only if packaged-font assertions change
- `design-qa.md` for pinned font provenance and final browser evidence

No new frontend dependency or persistent-state module is expected.

## 12. Verification Plan

### 12.1 Automated checks

- Chinese input with `lang=en` reaches the analyzer as English.
- English-mode application scaffolding contains no CJK characters when the
  supplied dream and reflections are ASCII.
- A matching English result is accepted without retry.
- A Chinese result requested as English is retried exactly once.
- Two mismatched results produce a language-specific error and create no
  analysis row.
- Save rejects a clearly mismatched language label.
- Draft analysis followed by interface switch returns 200, not 405.
- Draft switch preserves content, reflections, analysis JSON, and original
  analysis language.
- Draft switch performs zero database writes and zero analyzer calls.
- Save after interface switch preserves the selected UI language and displays
  the saved fallback analysis truthfully.
- Visual-memory titles do not exceed 48 Unicode characters.
- The full existing test suite passes.

### 12.2 Browser checks

Verify all six pages in Chinese and English at:

- 1440 x 900
- 1024 x 768
- 760 x 900
- 390 x 844
- 360 x 800

The browser pass must confirm:

- No horizontal overflow, overlap, or clipped controls.
- A reproducible cmap check confirms the packaged fonts cover every CJK
  character in Dream #4; browser rendering uses those packaged fonts.
- Page title, section, body, and metadata roles remain visually distinct.
- The visual-memory card does not become a giant paragraph.
- Analyze, switch UI language, regenerate, save, and switch back all complete
  without a raw framework error page.
- Network inspection shows no remote font request.
- Browser console contains no runtime errors.

## 13. Acceptance Criteria

- This specification controls product behavior and acceptance; the companion
  plan controls execution details, and Research Atlas mockups are non-binding
  references.
- Packaged offline fonts preserve the complete cmap of the pinned upstream
  files and cover current product copy plus Dream #4.
- No navigation or metadata text is smaller than 12px.
- Font size does not scale continuously with viewport width.
- The unsaved-analysis language toggle never returns 405.
- Interface switching preserves unsaved work and makes no AI call.
- English analysis requests cannot be silently persisted as Chinese.
- Existing mismatched data is identified without destructive migration.
- Saving and interface-language selection are independent actions.
- Analysis and interface languages are always visible when they differ.
- No new database table, frontend framework, or remote asset is introduced.
- Automated tests and the browser matrix pass before commit.

## 14. Implementation Order

Implement and review the work as three independently committable phases:

1. Draft flow: add failing 405 tests, make language paths root-relative and
   route-aware, and add the stateless draft-language POST path.
2. Analysis integrity: localize prompts, add provider-owned corrective retry,
   validate final and save-time language, and label existing mismatches.
3. Typography: pin and replace font assets, apply the Research Atlas type
   scale, and shorten visual-memory titles.

Run each phase's focused tests before its commit. Run the full automated suite
and browser matrix after all three phases are integrated.

There are no remaining visual-direction decisions blocking implementation.
