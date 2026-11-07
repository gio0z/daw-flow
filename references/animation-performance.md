# Animation Performance Reference

Shared optional reference for `daw-review` (Stage 2 Performance) and `daw-verify` (Web UI surface). It adds no module, route stage, generator, or runtime dependency. Animation claims stay evidence-bound; this reference defines how to inventory, inspect, and measure them.

---

## 1. When To Use

Apply only when the changed diff includes animated UI (CSS transitions/animations, Web Animations API, canvas or SVG animation, scroll-driven motion, JS-driven transform/opacity), or when an explicit animation audit was requested.

Otherwise record N/A and apply no animation gates: `animation-performance: N/A — no animated UI changed and no audit requested`.

---

## 2. Bounded Inventory

Bound inspection to the changed diff or the explicitly audited surface. For each animation in scope record: location, trigger, animated properties, duration/easing, whether it is essential or decorative, and cleanup wiring (pause/cancel/unmount). An animation with no recorded trigger or cleanup is an open finding, not a pass. Never expand into an unsolicited whole-codebase animation sweep.

---

## 3. Static Cost Checklist

Static review estimates plausible cost; it never proves a runtime frame rate.

- **Compositor-eligible `transform`/`opacity`:** Cheapest to render in all browsers and the safest default. Motion's performance guide confirms these operate on a layer in every modern browser. Treat acceleration as progressive enhancement, not a guarantee: each browser has different rules for when an actually-composited animation is hardware accelerated (e.g. historically, percentage-based transforms in Chrome were not accelerated). Measure before claiming offloading.
- **Conditional compositor behavior:** `filter`, `background-color`, `clip-path`, and SVG are browser- and version-dependent: Chrome and Firefox handle `filter` and SVG on the compositor, and support for `background-color`/`clip-path` has been arriving unevenly. Cite nothing as universally composited; verify per target browser.
- **Paint properties:** `box-shadow`, `border-radius`, and similar styles can skip layout yet require an expensive paint. Repaint cost is proportional to layer size: smaller layers are cheaper, and `will-change: transform` can hint a new layer, but each layer costs GPU space, so use sparingly.
- **Layout properties:** `width`, `height`, `top`, `padding`, etc. force layout, repaint, and recomposite of affected elements, and are usually discouraged. They are not always un-smooth: layout animations can be smooth when the element's layout is isolated (e.g. `position: absolute`, few children, no knock-on effects), per Motion. A single layout write is not inherently layout thrashing; thrashing is read/write alternation (read a size, write a style, read again) forcing synchronous layout per iteration. Flag the pattern, not the property alone.
- **No invented gates:** Do not impose arbitrary thresholds (e.g. "must pause after 700ms", "must start below 50% viewport height") unless the authoritative task contract states them.
- **Semantics preservation:** Never blindly replace animated `width`/`height` with `scale`: `scale` does not change layout box, wrapping, overflow, or hit targets, so it changes semantics. Remediation must preserve semantics, layout, and text.

---

## 4. Runtime Measurement

Every runtime animation claim needs a reproducible before/after trace:

- **Record the test context:** browser and version, OS/device, viewport and pixel ratio, CPU throttling (or "none"), network throttling (or "none"), power state when known, exact interaction path, and revision under test plus the baseline revision.
- **Capture a frame timeline** for the full interaction (e.g. Performance panel trace with frame durations and long tasks); report distribution (median, p95) rather than a single average. Without a baseline, report numbers as observations, not improvements.
- **Refresh-rate-aware budget:** state the measured refresh rate and derive the budget as `1000 / Hz` milliseconds: about 16.7 ms at 60 Hz and 8.3 ms at 120 Hz. The 16.7 ms figure is the 60 Hz case, not a universal pass threshold. Judge frame times against the budget for the recorded rate.
- **Browser caveat:** results transfer only within the recorded browser/device; cross-browser claims need cross-browser traces.

---

## 5. Reduced Motion And Lifecycle

- **Genuine runtime check:** a `prefers-reduced-motion` rule in CSS is not proof. With the preference enabled, run the actual interaction and confirm no sliding, scaling, parallax, auto-scroll, or looping remains except essential motion. Check CSS and JS layers: media-query rules plus JS-driven animation (rAF loops, WAAPI, libraries, scroll handlers).
- **Live preference change:** toggle the preference while the page is open; running animations must stop or adapt without reload.
- **Cleanup where relevant:** pause, cancel, or clean up on offscreen (IntersectionObserver or equivalent), unmount, tab hide, and interruption by a new trigger. Leaked loops or listeners are findings. One-shot transitions on persistent elements may record a documented N/A instead of forced cleanup machinery.

---

## 6. Findings, Roles, And Metric Limits

- **Evidence status per finding:** `passed`, `failing`, `blocked` (environment/capability missing), or `unexercised` (not run, or mock/static-only for a runtime claim). Static-only findings are `unexercised` for runtime claims.
- **Read-only roles preserved:** `daw-review` and `daw-verify` record findings and evidence; neither implements fixes. Remediation routes through the existing build path and must preserve semantics, layout, and text.
- **Lighthouse / CLS / TBT:** lab scores for load, layout stability, and main-thread blocking; they are not proof of animation frame rate and do not exercise reduced-motion. Supporting context only — the §4 frame trace is the animation evidence.

---

## 7. Accessibility: Exact Applicability

- **WCAG 2.2.2 Pause, Stop, Hide (Level A):** moving, blinking, or scrolling information that starts automatically, lasts more than 5 seconds, and appears alongside other content needs a pause/stop/hide mechanism unless the movement is essential. Auto-updating information that starts automatically alongside other content needs pause/stop/hide or update-frequency control unless essential; this branch has no 5-second threshold. Loaders have no blanket duration exemption: assess parallel content and any essential-activity exception.
- **WCAG 2.3.3 Animation from Interactions (Level AAA):** motion animation triggered by interaction can be disabled unless essential to the functionality or information conveyed. Being interactive alone is not an exception. Cite it as an AAA consideration, never an AA requirement.
- **Flashing is separate:** assess WCAG 2.3.1 Three Flashes or Below Threshold (Level A), which permits no more than three flashes in any one-second period or flashes below the general-flash and red-flash thresholds. Reduced motion alone does not prove flashing safety. Document why any motion claimed as essential is genuinely essential.

---

## 8. Primary Sources

- Motion performance: https://motion.dev/docs/performance
- web.dev animations guide: https://web.dev/articles/animations-guide
- WCAG 2.2.2 Pause, Stop, Hide: https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html
- WCAG 2.3.3 Animation from Interactions: https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html
- WCAG 2.3.1 Three Flashes or Below Threshold (flashing, separate criterion): https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html

Primary-source reference only; adopted from the cited guidance without any local-workspace generator, and no benchmarking was performed as part of adoption.
