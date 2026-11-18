# GUI source audit and refactor

Updated: 2026-11-18. Scope is the supplied source and documentation. No real-device screenshot or rendered acceptance is claimed.

| Issue found | Code change | Device acceptance |
|---|---|---|
| Hero is permanently NavyRaised and stat tiles permanently white | Hero, greeting, metric values and tiles now derive from selected Material roles | Change theme on a populated Today screen without restarting |
| Theme is decided independently in root, palette and accent accessors | One persisted System/Light/Dark selection; palette derives from Material; accents use theme roles | Both OS changes and manual overrides; system bar icon contrast |
| Lime used as light Material primary makes field labels/focus hard to see | Light text/focus uses existing PurpleDark; filled brand buttons retain Lime/Ink | Input, focus, disabled, dialog and error states |
| Card documentation says flat outlines but implementation uses shadows everywhere | Flat cards with subtle outline; restrained hero shadow | Elevation separation in both themes |
| Underdamped navigation springs conflict with motion contract | Short tweens and reduced press depth/tilt; Navy dock stays anchored | Reduced animation settings, repeated navigation |
| Fixed phone navigation stretches onto large windows | Rail from 600 dp available width; bounded content/editor | Split screen, tablet, landscape and resize |
| Journal has calories only and no shared dashboard state | Portion calculator, macros and one observed journal for both screens | Add/edit/delete/Undo and verify Today immediately |
| Settings diagnostics hidden behind repeated taps | Visible local log action and bounded shared-workout check | Reachability, errors, denied read grant |

## Retained concept

Navy architecture, Lime filled actions, Tangerine sync, Purple secondary detail and bundled Inter remain. Four tabs, the dominant steps number, pill controls and existing activity-card preferences remain. Premium quality is pursued through consistent roles, spacing, restrained surfaces and useful states rather than decorative effects.

## Acceptance matrix

Check 320/360 dp and larger windows, EN/RU, default and 200% font scale, light/dark/system override, gesture/three-button navigation, TalkBack and physical keyboard. Cover loaded/locked/loading Today; empty/full Nutrition; catalog unavailable; no search match; invalid/decimal-comma weight; keyboard open; rotated editor; persisted theme after process death; optional background grant denied. Check that spent/eaten calories are distinct and no user data are replaced by placeholders.

Remaining legacy UI typography and workout-grid behavior should be assessed from rendered evidence before further visual changes. This pass does not certify complete accessibility compliance or a modern visual result without device review.
