# Bedside Amber Frontend Design

Date: 2026-06-18

## Context

DreamLoop v0.1.2 is a local-first dream journal with a six-page web loop:
Dashboard, Log, Detail, Patterns, Gallery, and Settings. The current frontend
works, but its visual language leans heavily on purple-black backgrounds,
neon cyan/violet/rose accents, star fields, radial gradients, glowing dots, and
large soft shadows. This makes the product feel closer to a generic AI dream
dashboard than a private local journal and pattern-discovery tool.

The redesign should improve distinctiveness and trust without changing the
product architecture. DreamLoop is not only a diary. It also has structured AI
analysis, pattern discovery, local visual memory cards, image providers,
feedback, and privacy settings. The visual anchor should therefore be:

> A private research notebook under a bedside lamp.

This preserves warmth and privacy while keeping Dashboard and Patterns clear
enough for repeated tool use.

## Goals

- Remove the generic AI-night-app feeling caused by neon purple, cyan, rose,
  star fields, and heavy glow.
- Make the UI feel local, private, and intentional.
- Preserve the six-page product loop and the existing information density.
- Improve Dashboard screenshot quality for README and release assets.
- Keep the first implementation mostly CSS-only, with no backend or data model
  changes.
- Respect DreamLoop's local-first promise by avoiding default remote font loads.

## Non-Goals

- Do not redesign the navigation, page hierarchy, or backend routes.
- Do not remove Dashboard, Patterns, Gallery, Settings, feedback, or provider
  workflows.
- Do not turn DreamLoop into a purely literary journal UI.
- Do not add Google Fonts or any remote asset dependency by default.
- Do not introduce a full theme switcher UI in this pass.
- Do not regenerate release screenshots until the CSS implementation has been
  reviewed in browser.

## Design Direction

Use a dark warm-ink palette with amber as the primary accent. The result should
feel quiet, tactile, and private. It should also remain a tool: data panels,
heatmaps, provider states, and trend bars must stay easy to scan.

The redesign adopts the name `bedside-amber` as the internal theme direction.
For this pass, it can be implemented as CSS tokens rather than a user-facing
theme setting. The token structure should leave room for later themes such as
`midnight-ink` or `paper-light`.

## Visual System

### Color

Replace the current purple/neon base with warm ink and paper tokens:

- Background: warm ink black, not purple-black and not pure black.
- Panels: dark paper browns, low contrast, matte.
- Text: warm white and muted warm gray.
- Primary accent: amber.
- Success/ready: muted sage.
- Warning/error: rust.
- Neutral hints: clay.

The implementation should prefer semantic aliases over hard-coded one-off
colors. Existing names can be migrated gradually, but new work should use
intentional tokens such as `--ink`, `--paper`, `--amber`, `--sage`, and
`--rust`.

### Backgrounds And Decoration

Remove the global star-field effect. DreamLoop should no longer rely on
"dream equals stars" as its main visual metaphor.

Keep only minimal ambient light:

- Body may use one very subtle warm radial glow near the top.
- Hero surfaces may use one quiet bedside-lamp glow.
- Repeated panels should use flat matte backgrounds, fine borders, and small
  shadows.

Avoid decorative glowing dots, dense star textures, and multi-color radial
layers in cards.

### Typography

Do not load Google Fonts by default.

Use system-first stacks:

- Display: Georgia, Times New Roman, or another local serif fallback.
- Body: Aptos, Segoe UI, system sans-serif.
- Mono: Cascadia Mono, JetBrains Mono, Consolas, monospace.

Lower the display weight where possible so titles feel less poster-like.
Dream text should use the display stack, but italic must be language-aware:

- English dream text may use italic later if the template exposes language or a
  reliable class.
- Chinese dream text should stay upright because browser fake italic often
  looks poor on Windows.

### Components

#### Dashboard

Dashboard should remain the product's public proof point. It should communicate
local-first privacy, pattern discovery, and optional structured analysis within
the first screen.

Adopt the warm palette and remove star textures, but keep the existing layout
and CTA placement. The AI Insight card should feel like a research note, not a
glowing AI panel.

#### Log

Log is the high-frequency capture surface. Keep the current draft-first flow,
reflection prompts, loading state, and save-without-AI fallback. Inputs should
use warm borders and amber focus rings.

#### Detail

Detail should support three modes cleanly:

- Dream text and tags.
- Structured interpretation report and feedback.
- Local visual memory or generated image.

The local visual memory card should become more paper-like: warm surface, fine
border, restrained accent line, no glowing dots. Real generated images should
remain visually dominant when present.

#### Patterns

Patterns must keep its tool feel. Convert heatmaps and trend bars to restrained
single-color systems:

- Heatmap: amber intensity by opacity.
- Mood, symbol, and theme bars: matte amber or related warm semantic color.
- Hover states: subtle border and background changes, not movement or glow.

#### Gallery

Gallery should not become empty or flat. For real generated images, preserve
the image-first presentation. For local visual cards, replace neon gradients
with warm paper surfaces, typographic hierarchy, and a restrained memory-card
treatment.

#### Settings

Settings is part of the privacy trust loop. Provider status, image provider
status, secrets copy, and privacy audit should feel calm and utilitarian.
Use low-saturation status colors and avoid decorative effects.

## Motion

Keep the existing subtle page-enter transition and `prefers-reduced-motion`
support.

Remove or reduce decorative movement:

- No sidebar active-state translation.
- No hover lift.
- Use color, border, and background changes for feedback.

## Accessibility And Local-First Constraints

- Maintain readable contrast across all states.
- Keep keyboard focus visible with amber focus rings.
- Do not add remote fonts, remote images, analytics, or tracking.
- Ensure Chinese and English layouts still fit at common desktop and mobile
  widths.
- Preserve reduced-motion behavior.

## Implementation Plan Preview

The implementation should be split into small CSS-first steps:

1. Add warm ink, paper, amber, sage, rust, and clay tokens.
2. Replace global body background and remove the fixed star overlay.
3. Flatten shared panel surfaces and reduce large shadows.
4. Restyle navigation, buttons, forms, tags, and status states.
5. Convert heatmap and trend visuals to single-color intensity systems.
6. Restyle Gallery and local visual memory cards.
7. Review typography weights and dream-text treatment.
8. Verify Dashboard, Log, Detail, Patterns, Gallery, and Settings in browser.
9. Run tests.
10. Regenerate README screenshot assets only after visual QA passes.

## Verification

Before calling the implementation complete:

- Run the Python test suite with `uv run --extra dev pytest`.
- Open the local web app and inspect the six-page loop.
- Check desktop and mobile widths.
- Confirm there is no default remote font import.
- Confirm the UI no longer uses the old neon star-field treatment.
- Confirm Dashboard and Patterns still read as tools, not only as a diary.
- Update screenshot assets if the visual implementation is accepted.

## Open Decisions

- Whether to expose `bedside-amber` as a real selectable theme now or keep it as
  internal CSS direction for v0.1.x.
- Whether to add bundled local font files in a future release.
- Whether English dream text should get an italic treatment after language-aware
  template classes are available.
