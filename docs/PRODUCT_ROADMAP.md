# BitLut Product Roadmap

Updated: 2026-10-15

Scope: the app's screen structure and UI direction. Scaling (Huawei user cap)
lives in `docs/SCALING_ROADMAP.md`; sync/Health Connect bugs live in
`docs/BACKLOG.md`. Source code is the source of truth; if this file and the
code disagree, the code wins.

## Direction

BitLut becomes a four-tab app. The Today screen follows the three-variant
mockup (ChatGPT / Claude / Figma Make); the chosen layout is the dark hero
with one dominant number, goal progress, then three supporting numbers,
because it needs no photos.

| Tab | Purpose | Status |
|---|---|---|
| Today | Start screen: greeting, sync button, steps hero, activity and workout cards | Built; conformance to the mockup in progress |
| Workouts | Training tips | Placeholder screen; content in a later sprint |
| Nutrition | Food journal and calorie counter | Placeholder screen; content in a later sprint |
| Settings | Data source, goals, import, diagnostics | Existing |

The navbar's center sync button is gone; sync is a circular button in the Today
header (`AugustSyncAction`).

## Constraints that apply to every stage

- No new Health Connect or Huawei permissions.
- No historical sync beyond the existing 7-day window.
- No advanced-category code paths (sleep, heart rate, SpO2, stress). The
  mockup's heart-rate tile is therefore replaced by today's workout time.
- The app must stay usable on Huawei devices without GMS: no Google-service
  dependencies for UI, fonts or content.

## Stages

1. **Four-tab shell.** `MainTab` gains Workouts and Nutrition; navbar shows four
   destinations (Today, Workouts, Nutrition, Settings) with drawn glyphs; sync
   moves to the Today header; time-of-day greeting replaces the untitled
   header; placeholder screens; EN/RU strings.
2. **Today hero conformance.** Goal pill reads "N% of goal" and uses Lime
   (Tangerine stays reserved for sync and the Settings toggle); no unit chip
   next to the steps number; light stat tiles with a value and a unit.
3. **Today polish (optional, decide after reviewing 1 and 2 on a device).**
   Header inside the hero (full-bleed dark panel as in the mockup). Needs
   status-bar inset handling and a light-theme decision, so it is not
   scheduled until the earlier stages are seen on a real phone.
4. **Workouts content.** Static, bundled, offline tips written by the owner
   (EN + RU). No network, no accounts. Content format and structure to be
   decided when the content exists.
5. **Nutrition.** Local-only food journal and calorie counter. Decisions needed
   before any code:
   - Storage is local to the device. Writing meals to Health Connect would
     need a new permission, which the constraints above forbid.
   - `CLAUDE.md` currently limits production scope to activity and workout
     data; adding a food journal is a product-boundary change that needs an
     explicit update there, in `docs/PRIVACY_POLICY.md`, and in the AppGallery
     data declarations.
   - No bundled or online food database is assumed; manual entry first.
6. **Docs pass.** `CHANGELOG.md`, `SESSION_HANDOFF.md`, `CLAUDE.md` (navbar and
   UI contract), `design.md` (navigation, Tangerine role), README screenshots.
   Done at the end of the sprint, not per stage.

## Open questions

- Should the Workouts and Nutrition placeholders ship in a store release, or
  stay behind a development build until they have content?
- Nutrition: calorie goal per day, or journal only at first?
