---
name: ui-consistency
description: Fix UI defects everywhere they occur, through shared components, and prove it with measurement instead of eyeballing. Use for any UI fix, restyle or new page, and before claiming a UI change looks right.
---

The same defect kept coming back on another page: one page's tab strip was fixed while a sibling had a
hand-built copy; page sheets were fixed but detail popups were not. Each local fix left the app less consistent.

## Fix everywhere
1. Before fixing, find every place with the same markup or pattern (`git grep` the classes, the structure, the
   component name). The reported page is one sample, not the scope.
2. Fix it in the shared component, or extract one and migrate every caller in the same PR. Export class
   constants or hooks from the shared component instead of copy-paste, so variants cannot drift.
3. Prefer a single layout frame for dialogs and sheets (header, scrolling body, footer, size prop). Never set
   ad-hoc max-height, overflow or width on one instance.
4. Add a governance test that fails when someone bypasses the shared piece (for example, a dialog that sets its
   own max-height).
5. A page-specific fix is fine only when the problem is truly page-specific; say so in the PR.

## Measure, do not eyeball
- Use a headless browser harness that visits every route (not just the sidebar: detail pages and settings
  sub-pages count) at phone width (around 390px) and desktop widths, in light and dark themes.
- Record per route: console errors, elements clipped or beyond the viewport, overlapping elements, horizontal
  scroll, focus order. Compare before and after.
- Log in fresh per run. Apps that rotate refresh tokens revoke a session reused across two browser contexts.
- Run one browser sweep per test account (rate limits are per user) and keep heavy type-check and test jobs
  off the same slot.
- Keep shared tooling in a persistent directory, not in a temp dir someone may clean.

## Also
- Every user-visible string goes through the i18n layer, in every shipped locale.
- Loading, empty and error states use the shared components; no fake or demo data in shipped pages.
- After a front-end deploy, users need a hard refresh; old client bundles call removed endpoints.
