# Frontend Design QA

Run date: 2026-07-14

## Scope

- Pages: Dashboard, Log, Detail, Patterns, Gallery, and Settings.
- Languages: Chinese and English.
- Viewports: 1440 x 900, 1024 x 768, 760 x 900, 390 x 844, and 360 x 800.
- Data: the current local Dream #4 record, including its stored Chinese analysis and local visual memory.

## Result

No actionable P0, P1, or P2 visual or interaction issue remains. The exact Chrome viewport matrix covered 60 page/language/size combinations with zero horizontal overflow, escaped elements, unexpected text clipping, raw framework errors, or titles above four lines. A second in-app-browser pass produced the same zero-failure result.

The adversarial browser pass found and corrected two issues before this result was recorded:

1. At 1024px, the Patterns symbol row required 288px inside a 266px content track. Its text and meter tracks now shrink safely while the count column remains fixed.
2. A non-empty draft language switch preserved its content but left the address at the POST-only `/drafts/language` route. The returned page now replaces that history entry with `/log?lang=...`, so refresh is a normal GET instead of a 405.

## Visual Review

- Desktop Log keeps capture and analysis at equal prominence without oversized result copy.
- Desktop Detail limits the local visual-memory title to four lines and keeps the analysis card readable below the hero.
- Patterns retains a stable two-column hierarchy at 1024px; labels wrap without pushing meters or counts outside their cards.
- Mobile Log uses one column, a compact top navigation, full-width language controls, and readable analysis rows.
- Mobile Detail keeps Dream #4, the language control, visual memory, and primary actions in a coherent order at 360px.
- Chinese navigation and interface labels use the sans face; display headings use the serif face. The hierarchy is consistent across both languages.

## Typography And Assets

- Cascadia Mono, Noto Sans SC, and Noto Serif SC are served only from local static files.
- The page asset inventory reported three local font resources and zero remote resources.
- Computed styles resolve body copy to `Noto Sans SC` and display headings to `Noto Serif SC` on all 60 cases.
- Both Noto files preserve the complete cmap from Google Fonts commit `03781cf7a714af8431d14b6f337f923c774429d7` and were converted with timestamp recalculation disabled.
- Noto Sans SC: 30,890 cmap entries, 7,782,072 bytes, SHA-256 `AEF8C34277AFAD81ECD0227138A830263C0CAEA65B7AEA66D1195395F097B55A`.
- Noto Serif SC: 30,928 cmap entries, 11,032,420 bytes, SHA-256 `4EE9B0921EC9BD3F8B04587C7BC66C62731045E89D74EEC054F37FC7A2D26383`.
- Local HTTP HEAD checks returned 200 and the expected byte count for both versioned WOFF2 URLs.
- An independent cmap scan found zero missing CJK code points across templates, translations, and Dream #4.
- Both upstream OFL license files are stored in `src/dreamloop/static/fonts/noto/`.

The browser automation read-only world exposes `document.fonts.status` but masks the font-face collection and `load()` method. Runtime loading was therefore verified through observed font resource entries, exact HTTP responses, computed families, rendered screenshots, and an empty browser console instead of treating the masked `document.fonts.check()` result as application behavior.

## Interaction Evidence

- A blank English Log page switches to Chinese through a 303 redirect with no raw 405 or JSON error page.
- A typed Chinese draft switches to the English interface without saving, keeps the exact textarea content, and finishes at `/log?lang=en`.
- Refresh after that switch remains on the GET route and does not produce a framework error.
- Existing Chinese analysis shown in the English interface is labeled as a mismatch and offers explicit English regeneration instead of silently relabeling the content.
- Analyzer retry, language enforcement, save, feedback, visual generation, and image-language routing are covered with deterministic test doubles; browser QA did not call an external AI or image provider.
- Browser console inspection returned no warnings or errors.

## Automated Verification

- Full test suite: 156 passed.
- Focused typography, draft-language, visual-title, and API tests: 116 passed.
- Source distribution and wheel build: passed; the wheel contains both full WOFF2 files and both OFL licenses at the verified sizes.
- Exact responsive browser matrix: 60 cases, 0 failures.
- Independent responsive browser matrix: 60 cases, 0 failures.
- Temporary screenshots were created under `D:\CodexScratch\DreamLoop-frontend-qa-2026-07-14`, inspected, and removed after verification.
- The only test warning is the existing Starlette/httpx deprecation warning.

## Residual Coverage Boundary

The two browser matrices are recorded execution evidence, not a committed
end-to-end browser suite. The repository tests verify the server-rendered
`replaceState` script and CSS contracts, but CI does not replay the URL refresh
flow or pixel/layout checks. Those behaviors require another browser QA pass
when the language-switch script or responsive layout changes.

Final result: passed.
