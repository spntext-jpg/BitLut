# UI Localization Architecture Cleanup

This sprint removes transitional UI localization maps and standardizes BitLut UI text on Android resources.

## Final rule

UI text must live in:

- `app/src/main/res/values/strings.xml`
- `app/src/main/res/values-ru/strings.xml`

Compose UI should use `stringResource(R.string.key)`. Activity/non-composable Android code should use `getString(R.string.key)`.

## Allowed exceptions

Domain formatting/localization helpers are allowed only outside generic UI text, for example workout-name normalization or date formatting.

## Guardrail

Run:

```bash
python3 scripts/verify_ui_localization_architecture.py
```

The script fails if `BText`, `FinalUiText`, missing string resources, patch artifacts or backup files are present.
