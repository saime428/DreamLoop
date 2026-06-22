# Website Product Visuals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the selected realistic DreamLoop project visuals to the running web app, not only to the GitHub README.

**Architecture:** Keep documentation images in `docs/assets`, but copy site-consumed versions into `src/dreamloop/static/images` so FastAPI can serve them through `/static`. Render the workflow visual on the Dashboard and the local-first visual on Settings, with responsive CSS that keeps the app tool-first.

**Tech Stack:** FastAPI, Jinja2 templates, packaged static assets, CSS, pytest.

---

### Task 1: Static Assets And Tests

**Files:**
- Create: `src/dreamloop/static/images/readme-workflow-review.png`
- Create: `src/dreamloop/static/images/readme-local-first-privacy.png`
- Modify: `tests/test_web_api.py`

- [ ] **Step 1: Copy selected images into the app static tree**

Run:

```powershell
New-Item -ItemType Directory -Force -Path src\dreamloop\static\images
Copy-Item docs\assets\readme-workflow-review.png src\dreamloop\static\images\readme-workflow-review.png
Copy-Item docs\assets\readme-local-first-privacy.png src\dreamloop\static\images\readme-local-first-privacy.png
```

Expected: both files exist under `src/dreamloop/static/images`.

- [ ] **Step 2: Add a web rendering test**

Add assertions that `/` includes `/static/images/readme-workflow-review.png`, `/settings` includes `/static/images/readme-local-first-privacy.png`, and both files exist in the package static tree.

- [ ] **Step 3: Run the focused test**

Run:

```powershell
uv run --extra dev pytest tests/test_web_api.py::test_website_surfaces_product_visual_assets -q
```

Expected: it fails before template changes and passes after implementation.

### Task 2: Template And CSS Integration

**Files:**
- Modify: `src/dreamloop/templates/index.html`
- Modify: `src/dreamloop/static/style.css`

- [ ] **Step 1: Render semantic visual cards**

Add one `product-visual-card` after the dashboard hero and one `product-visual-card` in the Settings grid. Use `url_for('static', path='/images/...')` for both images.

- [ ] **Step 2: Style the cards responsively**

Add `product-visual-card` CSS with restrained borders, 16:9 image framing, natural shadow, and mobile-safe spacing. The cards must not dominate the Dashboard or squeeze Settings forms.

- [ ] **Step 3: Verify focused tests and browser render**

Run:

```powershell
uv run --extra dev pytest tests/test_web_api.py::test_website_surfaces_product_visual_assets tests/test_readme_positioning.py -q
```

Then inspect Dashboard and Settings in a browser at desktop and mobile widths.

### Task 3: Commit And Publish

**Files:**
- Modified and created files from Tasks 1-2

- [ ] **Step 1: Commit**

Run:

```powershell
git add docs/superpowers/plans/2026-06-22-website-product-visuals.md src/dreamloop/static/images/readme-workflow-review.png src/dreamloop/static/images/readme-local-first-privacy.png src/dreamloop/templates/index.html src/dreamloop/static/style.css tests/test_web_api.py
git commit -m "Add product visuals to web app"
```

- [ ] **Step 2: Push**

Run:

```powershell
git push origin master
```

Expected: GitHub `master` points to the new commit.
