# Offline nutrition calculator

Updated: 2026-11-18.

## Product behavior

Nutrition searches 200 curated common foods/dishes in English or Russian. The selection spans fruit, vegetables, cooked/dry grains, legumes, meat, fish, dairy, eggs, nuts/oils, prepared meals, snacks and drinks. It is a starter selection rather than a statistically verified worldwide top-200 ranking. Preparation labels distinguish raw, cooked, fried, salted and packaged reference foods. Each selected item previews energy and protein/fat/carbohydrates for an entered gram weight before logging.

Calculation is `reference nutrient per 100 g × edible grams / 100`. Values retain their decimal precision in storage; display alone rounds to the locale’s readable precision. Use the weight of the named preparation: dry rice and cooked rice are different items, and grams are not silently treated as milliliters or an unspecified serving. Zero-energy foods such as water are valid entries.

The user selects breakfast/lunch/dinner/snack and may browse earlier days. Entries can be edited or deleted with Undo. Custom entries accept whole-portion calories, optional weight and optional macros. Their manually entered values do not auto-scale when weight changes. A daily kcal target is optional, user-defined and off by default. This is a food/portion calculator, not a prescribed metabolic or weight-loss plan.

Today and Nutrition subscribe to the same journal and recompute totals after additions, edits, deletion, Undo, resume and date rollover. Eaten calories are presented separately from activity calories burned. Historical entries retain their logged nutrient snapshot even if reference data changes in a later app version.

## Data provenance

`app/src/main/assets/foods_v1.json` contains exactly 200 unique FoodData Central IDs, source descriptions, EN/RU display names, reference weight and kcal/protein/fat/carbohydrate values per 100 g. Data are selected from USDA SR Legacy, final release April 2018 (FDC publication 2019-04-01). This is an archived reference dataset, not a claim that recipes or product formulas are unchanged in November 2026.

The source extraction uses the `food.csv` and `myFoodNutrientPivot.csv` files at the retained mirror commit `matiasmorant/nutrition@0b235d8`, joined by the original description to retain the FDC ID. Exact source file SHA-256 values are embedded in the asset. The values were imported rather than invented or generated from the calorie formula. Calories need not equal exactly 4P+9F+4C because source energy factors and fiber treatment can differ. Food names are localized; the original English preparation description remains accessible in the picker.

USDA composition data are public domain. BitLut adds the curated selection and translations. Recipe/product variability is disclosed in the app. No runtime web lookup, API key, paid database or third-party nutrition tracking is added.

Sources: [USDA data documentation](https://fdc.nal.usda.gov/data-documentation/) and [downloads](https://fdc.nal.usda.gov/download-datasets/). The retained mirror URL and input digests are in the asset for reproducibility.

## Persistence and migration

The private file stays `bitlut_nutrition_journal`, key `entries`. The original ID, local epoch day, meal, name and integer kcal decode directly; kcal now supports decimals. New fields are `grams`, `protein`, `fat`, `carbs`, `foodId`. Missing fields stay null, never inferred from the name or set to fabricated zero. Totals show a notice when macros are incomplete; fully unknown macros show a dash.

Add/edit/delete are serialized across journal instances and use synchronous preference commit on Dispatchers.IO before success is reported. A failed write is visible. Malformed JSON/records produce a storage error and block destructive overwriting; no empty fallback is saved. EN/RU labels, custom Unicode names and decimal comma input are supported. There is no destructive schema reset or migration to a new preference name.

All user nutrition data remain on-device, separate from Huawei and Health Connect. `allowBackup=false` stays in force. No nutrition health permission is requested. Clearing app data/uninstall removes the journal. AppGallery declarations must be reviewed before release.

## Tests and limits

Unit regressions cover 200 unique IDs, banana portion arithmetic, multilingual search, zero-energy water, legacy migration, decimal round-tripping, incomplete macros/day filtering and invalid/corrupt input. Device checks cover keyboard, recreation, large fonts, dark/light mode, midnight/time-zone rollover and immediate Today updates.

Storage remains a small local JSON journal. If multi-year usage makes rewriting the list expensive, profile and introduce a transactional local database with a tested non-destructive migration; do not silently truncate history.
