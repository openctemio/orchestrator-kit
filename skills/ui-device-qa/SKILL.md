---
name: ui-device-qa
description: Reproduce and verify UI bugs on phone and desktop with a headless browser - device profiles, screenshots, horizontal-overflow and overlap checks, console errors. Use when someone sends a screenshot of a broken page, or before claiming a UI fix works.
---

1. Reproduce before fixing. Open the same page in Playwright with the device profile closest to the
   report ("iPhone 13", "Pixel 7", desktop 1440). Prefer the WebKit engine for iPhone reports. If WebKit
   cannot launch on the host, say so and use Chromium with the same profile.
2. Capture evidence:
   - a full-page screenshot plus one of the broken region;
   - the console errors;
   - failed requests.
3. Measure instead of eyeballing:
   - horizontal overflow: `el.scrollWidth > el.clientWidth` on the page and every scroll container.
     Overflow of a few pixels lets a finger drag the content sideways, which looks like clipped labels;
   - overlap: compare `getBoundingClientRect()` of the elements that look stacked (icons over counts);
   - more than one element marked current or active;
   - safe areas, and the dynamic toolbar on phones (visual viewport changes that are not a keyboard).
4. Fix in the shared component, so every page gets it. Add an e2e assertion for the measured property
   (no sideways scroll, a single current row) under the phone project.
5. Verify the fix the same way, and state what was not covered (a real device, a real iOS engine).
   Ask the reporter to check on their device after deploy.

Keep the screenshots out of git unless they are visual-test baselines. Never screenshot pages showing
real customer data into public places.
