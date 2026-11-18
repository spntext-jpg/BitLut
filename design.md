# BitLut design system

Updated: 2026-11-18. Android/Material adaptation of August; see `docs/GUI_AUDIT_2026_11.md` for findings and acceptance checks.

## Palette and hierarchy

Keep the brand palette and bundled Inter Variable. Exact values remain in `AugustTokens.kt`.

| Role | Light | Dark |
|---|---|---|
| Canvas | Canvas `#F7F8FC` | Navy `#151728` |
| Card / hero | Surface `#FFFFFF` | NavyRaised `#1C1E33` |
| Nested quiet surface | Soft `#F2F3F7` | NavySoft `#24263D` |
| Primary content | Ink `#151728` | Surface `#FFFFFF` |
| Secondary content | InkSoft `#292C3E` | DarkSecondaryText `#B8BDCE` |
| Filled primary action | Lime with Ink | Lime with Ink |
| Text action / field focus | PurpleDark | Lime |
| Sync action | Tangerine with Ink | Tangerine with Ink |
| Navigation anchor | Navy | Navy |

`BitLutExpressiveTheme` is the sole theme decision point. `ThemeMode` persists System (default), Light or Dark. `BitPalette.from(MaterialTheme.colorScheme)` adapts existing components; it does not independently sample OS mode. Root surfaces, hero, greeting, values, progress track and stat tiles update immediately. Only the Navy dock/rail remains an intentional constant architectural anchor.

Lime is a filled brand surface, not small text on a white background. Light Material focus/text roles use the existing PurpleDark. Outlined inputs use contrast-bearing outlines; normal cards keep the quieter decorative border.

## Layout and controls

Cards use 24 dp rounding, heroes 32 dp and restrained depth. Ordinary cards are flat with one subtle outline. Keep one dominant metric, clear section hierarchy and generous whitespace. Use readable, scalable type; numbers may fit their measured width with `TextAutoSize`, never a character-count lookup. Avoid truncating data to create symmetry.

Use a minimum 48 dp action target, labelled icon controls, visible focus and standard Material input/radio/chip semantics. Static cards do not animate. Navigation uses short tweens, no spring overshoot. Four destinations remain Today, Workouts, Nutrition, Settings; sync stays in Today’s header. At 600 dp available width the dock becomes a navigation rail. Content is capped at 840 dp and the food editor at 600 dp.

## Screens

- Today: greeting/sync, steps and progress, distance/calories/workout tiles, configured activity/workout cards and a food-intake summary. Eaten calories and macros have their own card and are not mixed with burned calories. Local nutrition remains accessible without Health Connect permission.
- Nutrition: day navigation, daily kcal/macros and optional target, food list grouped by meal, searchable offline catalog with portion preview, custom entries and editable log rows. Deletion offers Undo. Empty, unavailable catalog, invalid input, incomplete macros and storage failures are explicit states. The editor scrolls above the keyboard and preserves form state across recreation.
- Settings: data-source and sync actions, steps goal, theme selection, bounded shared-workout check and local log access.
- Workouts: existing offline training tips retain their behavior.

The catalog distinguishes raw/cooked and other preparation details. Values are per 100 g of edible food, scaled to the entered grams. Custom fields are explicitly whole-portion values and do not silently scale when weight changes. No default personal calorie target is prescribed.

## Accessibility, localization and checks

Control and body copy use resources with EN/RU key/format parity; catalog names carry EN/RU labels. Test TalkBack, 320/360 dp phones, 200% fonts, landscape, split screen, large windows, keyboard, both system themes and manual theme overrides. Theme checks must cover loaded, locked, empty and loading dashboard states. Keep existing cache and missing-metric semantics intact.

Reference baseline, reviewed 2026-11-18: [Android accessibility](https://developer.android.com/design/ui/mobile/guides/foundations/accessibility) (scalable text, contrast, semantics and 48 dp targets); [adaptive app quality](https://developer.android.com/docs/quality-guidelines/adaptive-app-quality/tier-2) (window-aware layout, rails and bounded secondary surfaces). Code inspection does not certify visual quality; device acceptance remains required.
