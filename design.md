# BitLut Design System

Updated: 2026-09-02

## Direction

BitLut keeps the August v3 palette but moves to a quieter 2026 content-first interface. The reference is the clarity and restraint of the ChatGPT app rather than decorative glassmorphism: clear hierarchy, calm surfaces, grouped controls, generous touch targets and minimal motion.

## Color roles — unchanged

`AugustTokens.kt` (`AugustColor`) is the single source of truth for the exact hex values; this section names the semantic roles.

- Ink `#151728`: core neutral / foreground-on-Lime / dark canvas. Also aliased as Navy in its architectural-anchor/navigation role — same color, two semantic names for two roles.
- Navy Raised `#1C1E33`: dark raised/hero surface.
- Canvas `#F7F8FC`: light background. Surface `#FFFFFF`: white card fill.
- Lime `#DFFF6A`: primary action and hero progress.
- Tangerine `#F28500`: sync action / active toggle signal (Settings toggle "on" track and the bottom nav Refresh fill only; Purple keeps every other focus/selection role).
- Purple `#6E5CF6`: focus and secondary interaction detail.
- Inter Variable remains the app font.

Do not add new colors when an existing semantic role works.

## Surface rules

- Normal cards: flat fill + one subtle outline, 22 dp radius, no routine shadow.
- Hero card: 30 dp radius, restrained shadow only where hierarchy needs it.
- Do not tint every card boundary with an accent.
- Non-clickable cards never scale/lift on touch.
- Use whitespace and typography before adding decoration.

## Buttons and controls

- Primary buttons: Lime + Ink, pill shape, minimum 48 dp height, no glow/shadow.
- Secondary buttons: neutral Surface/Soft/NavySoft, subtle outline, pill shape, minimum 48 dp height.
- One clear primary action per action group. In Settings that is `Sync now`.
- Connect Google, Connect Huawei, Refresh status, Import archive and Health Connect settings are secondary actions in the same grouped card.
- Icon-only controls need a clear content description and a practical touch target.
- Goal +/- controls use quiet round/pill containers; steps is the only editable goal.

## Motion

- 140–200 ms tween for press/color state.
- No bounce/elastic overshoot in standard navigation/buttons.
- Sync icon may use a small rotational press cue, but no exaggerated lift.
- Motion communicates state; it is not decoration.

## Navigation

- Persistent Navy bottom dock.
- Two destinations: Today and Settings.
- Sync remains a center action, not a fake destination.
- Selected destination uses Surface + Lime icon tile.
- Center sync remains Tangerine but is visually integrated (60 dp, restrained motion).

## Dashboard

- Steps + distance remain the pinned hero.
- Other cards use `DashboardCardLayoutPrefs` only for order/visibility.
- Workout cards are type-aware and show only meaningful metrics.
- Missing metrics are omitted rather than replaced with invented zeros.
- Card content should scan top-to-bottom: label -> key value/title -> supporting metrics.

## Settings

- Minimal data-source selector.
- One grouped actions card, buttons only.
- One primary action (`Sync now`), all other actions secondary.
- Steps goal only.
- Workout filter UI stays removed; sync-time `WorkoutFilterPrefs` behavior remains.
- Health Connect settings deep link remains for diagnostics.

## Accessibility and localization

- Keep interactive targets at least 48 dp where practical.
- Icon-only controls require content descriptions.
- EN and RU resource keys must remain in parity in every patch.
- Never hardcode locale-specific UI copy in Kotlin when a resource is appropriate.
