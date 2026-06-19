# BitLut UI + Localization Sprint

## Scope

This sprint intentionally does not modify the Huawei Health -> Android Health Connect sync pipeline.
Only presentation, localization, README, and backlog documentation are affected.

## Product shell

BitLut has three top-level tabs:

1. Summary / Сводка
2. History / История
3. Settings / Настройки

Settings is the only place where the user connects Google Health Connect, connects Huawei Health, checks status, and starts sync.

## Localization contract

- `values-ru` is the Russian UI for devices whose system language is Russian.
- `values` is the English fallback for all other locales.
- No mixed-language UI strings are allowed.
- New strings must be added to both XML files.

## Visual direction

BitLut follows a premium Health-style interface:

- Material 3 Expressive
- Inter typography when available, system fallback otherwise
- Large rounded cards, 28-32dp for major cards
- Light mode: `#F2F2F7` system background, `#FFFFFF` cards
- Dark mode: `#0C0C0E` / `#1C1C1E` backgrounds
- Soft shadows in light mode
- Glass-like materials and muted secondary text in dark mode

## Health category colors

- Activity: coral / red
- Sleep: turquoise-purple
- Heart: rich red
- Mindfulness/system states: mint and soft blue

## Next implementation step

Move the remaining `BText` compatibility adapter from `MainActivity.kt` into real Android string resources through `stringResource(...)`.
