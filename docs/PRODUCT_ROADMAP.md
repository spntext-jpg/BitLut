# BitLut Product Roadmap

Updated: 2026-10-16

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
| Today | Start screen: greeting, sync button, steps hero, activity and workout cards | Built (stages 1 to 3); awaiting review on a device |
| Workouts | Training tips | Built (stage 4): eight starter tips for the owner to review |
| Nutrition | Food journal and calorie counter | Built (stage 5): manual, local-only journal with a daily total |
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
3. **Header inside the hero (done 2026-10-16).** The greeting row, the
   freshness/sync line and the steps hero share one dark card in every state
   (locked, loading, loaded), so the Sync button never disappears. Built as an
   inset card, not the mockup's full-bleed panel: full-bleed means drawing
   under the status bar and flipping the status-bar icon color as the panel
   scrolls away, which cannot be checked without a device.
4. **Workouts content (done 2026-10-16).** Static, bundled, offline tips (EN +
   RU) in `strings.xml` (`workout_tip_*`), shown as expandable cards by
   `WorkoutsScreen`. No network, no accounts, no health data. The eight starter
   tips are general guidance written as a starting point: the owner should
   review, edit or replace them; adding a tip means one `WorkoutTip` line plus
   two strings per language.
5. **Nutrition (done 2026-10-16).** Manual, local-only food journal with a daily
   calorie total (`NutritionScreen`, `NutritionJournalPrefs`). Decisions as built:
   - Storage is a private SharedPreferences file on the device (one JSON array),
     no new dependency. Nothing is written to Health Connect (that would need a
     new permission, which the constraints above forbid), nothing is uploaded,
     and the app declares `allowBackup="false"`.
   - `CLAUDE.md` (product boundary) and `docs/PRIVACY_POLICY.md` were updated in
     this stage. Still to do by hand, outside the repo: review the AppGallery
     data declarations before the next store release.
   - No food database: manual entry only (name optional, calories 1 to 9999).
   - Left out on purpose: calorie goal, macros, search, editing an entry (delete
     and re-add instead), browsing forward past today.
6. **Docs pass (done 2026-10-16).** `CHANGELOG.md`, `SESSION_HANDOFF.md`,
   `CLAUDE.md`, `CONTEXT.md`, `design.md`, `README.md`, `docs/BACKLOG.md`. The
   README screenshots were not regenerated: they need real captures.

## Open questions

- Do the eight starter Workouts tips ship as written, or does the owner replace
  them first?
- Nutrition: add a daily calorie goal, or compare eaten with burned calories?
- The AppGallery data declarations must be reviewed for the local food journal
  before the next store release (outside the repo).
- Full-bleed hero: revisit only after the inset hero has been seen on a device.
