# BitLut Design System

Updated: 2026-10-16

## Direction

BitLut keeps the August v3 palette but moves to a quieter 2026 content-first interface. The reference is the clarity and restraint of the ChatGPT app rather than decorative glassmorphism: clear hierarchy, calm surfaces, grouped controls, generous touch targets and minimal motion.

## Color roles — unchanged

`AugustTokens.kt` (`AugustColor`) is the single source of truth for the exact hex values; this section names the semantic roles.

- Ink `#151728`: core neutral / foreground-on-Lime / dark canvas. Also aliased as Navy in its architectural-anchor/navigation role — same color, two semantic names for two roles.
- Navy Raised `#1C1E33`: dark raised/hero surface.
- Canvas `#F7F8FC`: light background. Surface `#FFFFFF`: white card fill.
- Lime `#DFFF6A`: primary action, hero progress, the hero goal pill and icon chips (always with an Ink icon).
- Tangerine `#F28500`: sync action / active toggle signal (the Today-header sync button and its in-progress spinner, the source-not-connected notice, and the Settings toggle "on" track; Purple keeps every other focus/selection role).
- Tangerine is an active-state shape/indicator, not small foreground copy on Canvas. Pair it with Ink/Surface semantic text when a label is required; this preserves the palette while meeting readable light/dark contrast.
- Purple `#6E5CF6`: focus and secondary interaction detail.
- Inter Variable remains the app font.

Do not add new colors when an existing semantic role works.

## Surface rules

- Normal cards: flat fill + one subtle outline, 22 dp radius, no routine shadow.
- Dark root canvas stays Navy; DarkPanel/NavyRaised are surfaces above it. Do not gradient the root into a card surface, which erases layer separation at the bottom of the screen.
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
- Focus styling must observe the same `MutableInteractionSource` used by the actual Material control; a decorative wrapper source does not receive focus events.
- Goal +/- controls use quiet round/pill containers; steps is the only editable goal.

## Motion

- 140–200 ms tween for press/color state.
- No bounce/elastic overshoot in standard navigation/buttons.
- Sync icon may use a small rotational press cue, but no exaggerated lift.
- Status transitions that share one semantic slot should crossfade inside a reserved-height container instead of adding/removing layout rows.
- Motion communicates state; it is not decoration.

## Navigation

- Persistent Navy bottom dock.
- Four destinations: Today, Workouts, Nutrition, Settings. Labels auto-size from 11sp to 9sp.
- Sync is not in the dock: it is a round Tangerine button in the Today header.
- Selected destination is tint-only (Lime icon and label), no background pill.

## Dashboard

- The pinned hero is one dark card holding the greeting row (edit-layout and sync buttons), the freshness/sync line, steps with the goal, a progress bar and three light stat tiles (distance, calories, workout minutes).
- Other cards use `DashboardCardLayoutPrefs` only for order/visibility.
- Workout cards are type-aware and show only meaningful metrics.
- Missing metrics are omitted rather than replaced with invented zeros.
- Card content should scan top-to-bottom: label -> key value/title -> supporting metrics.

## Workouts and Nutrition

- Workouts: a title, one intro line, expandable tip cards (Lime icon chip, one expanded at a time) and a short "general information" note.
- Nutrition: a title, a day navigator (backwards only), a total card, one card per meal that has entries, and a primary "Add food" button opening a dialog (meal choice, calories, optional name). Empty days show a short empty state; a footer line states that data stays on the device.

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
