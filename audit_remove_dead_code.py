
#!/usr/bin/env python3
"""
Code audit: revert the rejected glass experiment, rename the last
"Glass 2.0"-named symbols, remove leftover pre-August dead code.

Run this after navbar_neoglassmorphism.py has been applied (it edits the
same files that script touched, plus does a wider dead-code sweep across
the codebase this integration has been building up since phase 1).

Part 1 -- revert the rejected glass experiment:

The neoglassmorphism 2.0 pass (multi-layer tint + specular gradient
border) was rejected on sight as not reading as real glass. That tracks:
without genuine backdrop blur-through -- the Dashboard content actually
blurring as it's visible behind the bar -- tint-and-gradient tricks alone
don't produce what "glassmorphism" visually means, they produce a tinted
panel. Real backdrop blur needs either a shader/blur library (a new
Gradle dependency) or capturing and re-compositing the content layer
behind the Scaffold -- both real, separate decisions, not something to
guess at a third time without any way to see the result. This reverts
the shell's background/border to the flat Navy fill phase 4 shipped, and
removes the now-unused AugustGlass token object and its Brush import.

Part 2 -- rename the last "Glass 2.0"-named symbols:

Phase 4 already rewrote GlassNavigation.kt's internals against the August
spec, but the function names themselves were never touched:
Glass20BottomNavigation, Glass20NavButton, Glass20RefreshButton --
"Glass 2.0" being the literal name of the pre-August aesthetic this whole
integration has been replacing. Renamed to AugustBottomNav, AugustNavButton,
AugustRefreshButton across every call site and doc-comment cross-reference
(verified by grep -- all in this one file plus its one external call site
in FinalBitLutShell.kt).

Part 3 -- remove leftover dead code, each confirmed by direct grep before
removal (not assumed from a name or a one-pass regex sweep):

  - Three fields on HealthAccent (FinalBitLutShell.kt) with zero
    references anywhere in the app: cardLight, cardDark (#1C1C1E), and
    systemLight (#F2F2F7) -- the latter two are literally the old
    pre-August near-black/iOS-gray palette values, left behind when
    phase 1 repointed HealthAccent's other three fields to August tokens
    but never touched these.
  - 32 dead imports in FinalBitLutShell.kt, each individually re-verified
    (not just swept once and trusted) -- including some that looked
    load-bearing at first glance and were specifically double-checked
    before removal: BitLutExpressiveTheme (the actual theme wrapper is
    called from MainActivity.kt with its own separate import -- this
    file never calls it), DashboardViewModel (this file only ever
    receives the already-built DashboardUiState as a plain parameter,
    correct state-hoisting -- the ViewModel class itself is never
    referenced here), ColumnScope and lerp (both genuinely used, but in
    GlassCards.kt, a different file with its own import -- not this one).
    The remaining 29 are drafted-but-never-wired scaffolding from earlier
    sprints: WorkManager/SyncWorker/Constraints/ExistingWorkPolicy/etc.
    (a full manual WorkManager API surface with zero call sites), Toast,
    PermissionController, ActivityResultContracts, and others.

Every removal in this script was verified with `grep -c` against the
literal current file content before being written here, and the file's
brace/paren balance was checked after every edit while building this.

Run from the repo root:
    python3 audit_remove_dead_code.py
"""
import datetime
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUP_DIR = ROOT / ".bitlut_patch_backup" / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

THEME_DIR = "app/src/main/java/com/openhealth/sync/ui/theme"
AUGUST_TOKENS = f"{THEME_DIR}/AugustTokens.kt"
NAV = "app/src/main/java/com/openhealth/sync/ui/components/GlassNavigation.kt"
UI_SHELL = "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt"

TARGET_FILES = [AUGUST_TOKENS, NAV, UI_SHELL]

# The 32 exact dead import lines removed from FinalBitLutShell.kt (part 3).
# Handled as a batch line-removal rather than individual apply_edit calls --
# 32 scattered single-line anchors across ~140 lines of imports would be
# unwieldy and no safer than an exact-line-match removal verified by count.
DEAD_IMPORT_LINES = [
    "import androidx.compose.foundation.layout.defaultMinSize\n",
    "import android.content.Context\n",
    "import android.os.Bundle\n",
    "import android.widget.Toast\n",
    "import androidx.activity.ComponentActivity\n",
    "import androidx.activity.compose.setContent\n",
    "import androidx.activity.result.contract.ActivityResultContracts\n",
    "import androidx.activity.viewModels\n",
    "import androidx.compose.animation.animateColorAsState\n",
    "import androidx.compose.foundation.layout.fillMaxHeight\n",
    "import androidx.compose.foundation.lazy.LazyRow\n",
    "import androidx.compose.material3.MaterialTheme\n",
    "import androidx.compose.runtime.collectAsState\n",
    "import androidx.compose.ui.draw.drawBehind\n",
    "import androidx.health.connect.client.PermissionController\n",
    "import androidx.work.Constraints\n",
    "import androidx.work.ExistingPeriodicWorkPolicy\n",
    "import androidx.work.ExistingWorkPolicy\n",
    "import androidx.work.NetworkType\n",
    "import androidx.work.OneTimeWorkRequestBuilder\n",
    "import androidx.work.PeriodicWorkRequestBuilder\n",
    "import androidx.work.WorkInfo\n",
    "import androidx.work.WorkManager\n",
    "import com.openhealth.sync.data.worker.SyncWorker\n",
    "import com.openhealth.sync.platform.HmsCoreHelper\n",
    "import com.openhealth.sync.ui.DashboardViewModel\n",
    "import com.openhealth.sync.ui.SyncViewModel\n",
    "import com.openhealth.sync.ui.theme.BitLutExpressiveTheme\n",
    "import java.util.concurrent.TimeUnit\n",
    "import androidx.compose.foundation.layout.ColumnScope\n",
    "import androidx.compose.material.icons.rounded.UploadFile\n",
    "import androidx.compose.ui.graphics.lerp\n",
]


def die(msg: str) -> None:
    print(f"!! {msg}")
    sys.exit(1)


def backup_file(rel_path: str) -> None:
    src = ROOT / rel_path
    dst = BACKUP_DIR / rel_path
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def apply_edit(rel_path: str, old: str, new: str, desc: str) -> bool:
    path = ROOT / rel_path
    text = path.read_text(encoding="utf-8")

    old_count = text.count(old)
    if old_count == 0:
        if text.count(new) >= 1:
            print(f"   (already applied, skipping) {desc}")
            return False
        die(f"Anchor not found for '{desc}' in {rel_path}, and patched text "
            f"is also absent. File may have changed since this script was "
            f"written -- aborting rather than guessing.")

    if old_count != 1:
        die(f"Expected exactly 1 occurrence of anchor for '{desc}' in "
            f"{rel_path}, found {old_count}. Aborting rather than guessing "
            f"which one to patch.")

    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"   applied: {desc}")
    return True


def remove_dead_import_lines() -> bool:
    """Idempotent batch removal of the 32 dead import lines. Idempotency is
    line-presence-based (not a fixed expected-count check), so a re-run
    after the lines are already gone is correctly a no-op rather than an
    error."""
    path = ROOT / UI_SHELL
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    dead_set = set(DEAD_IMPORT_LINES)

    present = [l for l in lines if l in dead_set]
    if not present:
        print("   (already applied, skipping) remove 32 dead imports")
        return False

    new_lines = [l for l in lines if l not in dead_set]
    removed = len(lines) - len(new_lines)
    path.write_text("".join(new_lines), encoding="utf-8")
    print(f"   applied: removed {removed} dead import line(s)")
    return True


def main() -> None:
    print("==> Checking target files exist")
    for rel in TARGET_FILES:
        if not (ROOT / rel).exists():
            die(f"Expected file not found: {rel} (run this from the repo root, "
                f"after navbar_neoglassmorphism.py has been applied)")

    print(f"==> Backing up touched files to {BACKUP_DIR.relative_to(ROOT)}")
    for rel in TARGET_FILES:
        backup_file(rel)

    # -- Part 1: revert the rejected glass experiment --------------------
    print("==> Reverting shell background/border to the flat phase-4 Navy fill")
    apply_edit(
        NAV,
        old='''                .clip(shellShape)
                .background(AugustGlass.ShellUndertint)
                .background(Brush.verticalGradient(listOf(AugustGlass.ShellTint, Color.Transparent)))
                .border(
                    width = AugustGlass.ShellBorderWidth,
                    brush = Brush.verticalGradient(listOf(AugustGlass.SpecularTop, AugustGlass.SpecularBottom)),
                    shape = shellShape
                )
                .padding(horizontal = 12.dp, vertical = 8.dp)''',
        new='''                .clip(shellShape)
                .background(AugustColor.Navy.copy(alpha = 0.94f))
                .border(width = 1.dp, color = AugustColor.BorderDark, shape = shellShape)
                .padding(horizontal = 12.dp, vertical = 8.dp)''',
        desc="revert glass shell background/border",
    )

    print("==> Updating file header (glass pass tried and reverted, not active)")
    apply_edit(
        NAV,
        old='''/**
 * August design system integration, phase 4 (see AugustTokens.kt), plus a
 * neoglassmorphism 2.0 pass (2026-08, see AugustGlass in AugustTokens.kt
 * for what that means here and why it's confined to this one file). This
 * file was the app's last and heaviest "Glass 2.0" holdout before phase 4
 * -- a 3-stop translucent gradient shell, two accent-tinted radial glow
 * layers, a specular top-highlight line, a 40dp accent-tinted shadow, an
 * icon that tilted +/-13deg and spun 360deg on tap, and five separate
 * bouncy-spring animations across the two button composables. Phase 4
 * rewrote it against section 9's literal "Mobile nav: Fixed floating bar,
 * dark glass surface" plus the blanket rules already applied elsewhere in
 * this integration: one shadow per component (6.4), no bounce/elastic
 * overshoot and motion that confirms state rather than performing for its
 * own sake (7). This pass keeps every one of those rules -- the shell
 * still has exactly one shadow, buttons still use a plain tween, nothing
 * bounces -- and adds real glass depth on top: a two-layer tinted
 * background instead of one flat translucent color, and a specular
 * gradient-stroke border instead of a flat one.
 *
 * "Dark glass surface" is why this shell is Navy-based regardless of the''',
        new='''/**
 * August design system integration, phase 4 (see AugustTokens.kt). This
 * file was the app's last and heaviest "Glass 2.0" holdout before phase 4
 * -- a 3-stop translucent gradient shell, two accent-tinted radial glow
 * layers, a specular top-highlight line, a 40dp accent-tinted shadow, an
 * icon that tilted +/-13deg and spun 360deg on tap, and five separate
 * bouncy-spring animations across the two button composables. Rewritten
 * against section 9's literal "Mobile nav: Fixed floating bar, dark glass
 * surface" plus the blanket rules already applied elsewhere in this
 * integration: one shadow per component (6.4), no bounce/elastic overshoot
 * and motion that confirms state rather than performing for its own sake
 * (7).
 *
 * A neoglassmorphism 2.0 pass (multi-layer tint, specular gradient border)
 * was tried and reverted (2026-08) -- rejected on sight as not reading as
 * real glass, which tracks: without genuine backdrop blur-through (the
 * Dashboard content actually blurring behind the bar), tint-and-gradient
 * tricks alone don't produce what "glassmorphism" actually means visually,
 * they produce a tinted panel. Real backdrop blur needs either a shader/
 * blur library (a new Gradle dependency) or capturing and re-compositing
 * the content layer behind the Scaffold -- a deliberate, larger decision,
 * not something to guess at a third time without a way to see the result.
 *
 * "Dark glass surface" is why this shell is Navy-based regardless of the''',
        desc="update nav file header (glass pass reverted note)",
    )

    print("==> Removing dead Brush + AugustGlass imports")
    apply_edit(
        NAV,
        old='''import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.unit.dp
import com.openhealth.sync.ui.theme.AugustColor
import com.openhealth.sync.ui.theme.AugustElevation
import com.openhealth.sync.ui.theme.AugustGlass
import com.openhealth.sync.ui.theme.AugustMotion
import com.openhealth.sync.ui.theme.AugustRadius''',
        new='''import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.unit.dp
import com.openhealth.sync.ui.theme.AugustColor
import com.openhealth.sync.ui.theme.AugustElevation
import com.openhealth.sync.ui.theme.AugustMotion
import com.openhealth.sync.ui.theme.AugustRadius''',
        desc="remove Brush, AugustGlass imports",
    )

    print("==> Removing the now-unused AugustGlass token object")
    apply_edit(
        AUGUST_TOKENS,
        old='''}

/**
 * Neoglassmorphism 2.0 recipe for the bottom nav shell (integration
 * addendum, 2026-08). NOT part of the source design doc -- August's own
 * "Mobile nav: dark glass surface" line is one sentence with no numbers
 * attached, and its non-goals explicitly rule out "glass-heavy" as a
 * whole-app default (see AugustTokens.kt's own header, and GlassCards.kt's
 * phase-2 rewrite, which deliberately moved cards AWAY from this exact
 * aesthetic). This object exists because the single named exception is the
 * navigation layer -- current 2026 consensus (checked, not assumed;
 * multiple industry sources through mid-2026, plus Apple's own Liquid
 * Glass developer guidance) converges on the same split this codebase
 * already has: flat/bento as the primary language for content, heavier
 * glass reserved specifically for the floating nav/toolbar layer that
 * sits above content. So this is real glassmorphism, deliberately
 * confined to the one component it's supposed to live on, not a reversion
 * of phase 2's card decision.
 *
 * Two real engineering constraints, checked rather than assumed:
 *   - True backdrop blur (seeing the Dashboard blur THROUGH the bar, the
 *     way iOS Liquid Glass actually works) needs either a capture of the
 *     content layer behind the bar or a third-party shader library --
 *     Compose's own `Modifier.blur()` only blurs a composable's OWN
 *     drawn content, not whatever sits behind it, and only on API 31+
 *     (silently ignored below that, not a crash). Real backdrop-blur is
 *     a separate, larger change (either add a blur library dependency or
 *     plumb a captured background layer through to this composable) --
 *     not something to slip into a nav-bar-only visual pass. What's here
 *     instead is what Liquid Glass actually IS underneath the backdrop
 *     step: multi-layer translucency, a saturation-boosted tint instead
 *     of a flat one, and a specular top-edge highlight -- the same recipe
 *     documented across Apple's own engineering write-ups and 2026 CSS
 *     implementations, minus the one step (real-time backdrop sampling)
 *     that needs a dependency this integration hasn't added.
 *   - `Modifier.border(brush = ...)` (a gradient-stroke border, not a
 *     flat color) is a real, stable, non-experimental Compose Foundation
 *     API -- verified against Compose Foundation's own border() samples
 *     before use, the same way AugustFont's Font() overload should have
 *     been checked against a real signature before phase 5 shipped
 *     instead of after a build broke on it.
 */
internal object AugustGlass {
    /** Base tint: Navy blended 10% toward Accent (computed, not eyeballed --
     * `blend(#15172A, #6E5CF6, 0.10)`), standing in for the saturation
     * boost a true backdrop-blur-through implementation would apply to
     * whatever's actually behind the bar (see this object's header for why
     * that step itself isn't implemented here). At partial alpha so it
     * reads as glass rather than a flat panel. */
    val ShellTint = Color(0xFF1E1E3E).copy(alpha = 0.72f)

    /** Second, lower layer UNDER the tint -- gives the glass real depth
     * instead of one flat translucent wash; this is what makes it read as
     * multi-layer glass rather than "Navy with alpha," the single most
     * common way a glassmorphism attempt ends up looking flat instead of
     * dimensional. */
    val ShellUndertint = AugustColor.Navy.copy(alpha = 0.55f)

    /** Specular top-edge highlight: a gradient stroke, bright at the top
     * corners fading toward transparent, standing in for the light-catching
     * rim every real glass reference (Apple's engineering write-ups, 2026
     * CSS implementations) describes as the detail that reads as "glass"
     * rather than "translucent plastic." */
    val SpecularTop = Color.White.copy(alpha = 0.38f)
    val SpecularBottom = Color.White.copy(alpha = 0.04f)

    val ShellBorderWidth = 1.dp
}

/**
 * Section 4 typography, font family (integration phase 5). Bundled real
 * Inter -- specifically the OFL variable instance from Google's own font
 * repository (github.com/google/fonts, ofl/inter/Inter[opsz,wght].ttf),''',
        new='''}

/**
 * Section 4 typography, font family (integration phase 5). Bundled real
 * Inter -- specifically the OFL variable instance from Google's own font
 * repository (github.com/google/fonts, ofl/inter/Inter[opsz,wght].ttf),''',
        desc="remove AugustGlass token object",
    )

    # -- Part 2: rename Glass20* symbols ----------------------------------
    print("==> Renaming Glass20* symbols to August* (doc comments)")
    apply_edit(
        NAV,
        old=''' * Lives at the [Glass20BottomNavigation] level (not inside
 * [Glass20NavButton]) so it can distinguish which tab was tapped without''',
        new=''' * Lives at the [AugustBottomNav] level (not inside
 * [AugustNavButton]) so it can distinguish which tab was tapped without''',
        desc="rename in secret-tap doc comment",
    )
    apply_edit(
        NAV,
        old="internal fun Glass20BottomNavigation(",
        new="internal fun AugustBottomNav(",
        desc="rename Glass20BottomNavigation -> AugustBottomNav (declaration)",
    )
    apply_edit(
        NAV,
        old='''                Glass20NavButton(
                    tab = MainTab.Today,
                    selected = selected == MainTab.Today,
                    onClick = { onSelected(MainTab.Today) }
                )
                Glass20RefreshButton(onClick = onRefreshClick)
                Glass20NavButton(
                    tab = MainTab.Settings,''',
        new='''                AugustNavButton(
                    tab = MainTab.Today,
                    selected = selected == MainTab.Today,
                    onClick = { onSelected(MainTab.Today) }
                )
                AugustRefreshButton(onClick = onRefreshClick)
                AugustNavButton(
                    tab = MainTab.Settings,''',
        desc="rename call sites in the tab row",
    )
    apply_edit(
        NAV,
        old=" * fill the selected tab in Glass20NavButton -- \"action\" and \"selection\"",
        new=" * fill the selected tab in AugustNavButton -- \"action\" and \"selection\"",
        desc="rename in NavAccent doc comment",
    )
    apply_edit(
        NAV,
        old="private fun Glass20RefreshButton(onClick: () -> Unit) {",
        new="private fun AugustRefreshButton(onClick: () -> Unit) {",
        desc="rename Glass20RefreshButton -> AugustRefreshButton (declaration)",
    )
    apply_edit(
        NAV,
        old="private fun Glass20NavButton(",
        new="private fun AugustNavButton(",
        desc="rename Glass20NavButton -> AugustNavButton (declaration)",
    )

    print("==> Updating the one external call site in FinalBitLutShell.kt")
    apply_edit(
        UI_SHELL,
        old="            Glass20BottomNavigation(",
        new="            AugustBottomNav(",
        desc="update call site",
    )

    # -- Part 3: remove leftover dead code --------------------------------
    print("==> Removing 3 dead HealthAccent fields (cardLight/cardDark/systemLight)")
    apply_edit(
        UI_SHELL,
        old=''' * backing (Lime text/icons on the app's white/light cards fails contrast
 * outright: computed at 1.14:1, versus the ~4.6-6.7:1 the two purple tokens
 * below measure at on both this app's card surfaces), so it's deliberately
 * deferred to the next integration phase rather than shipped unverified.
 */
internal object HealthAccent {
    val activity = AugustColor.Accent
    val violet = AugustColor.AccentDark
    val mind = AugustColor.AccentDark
    val cardLight = Color.White
    val cardDark = Color(0xCC1C1C1E)
    val systemLight = Color(0xFFF2F2F7)''',
        new=''' * backing (Lime text/icons on the app's white/light cards fails contrast
 * outright: computed at 1.14:1, versus the ~4.6-6.7:1 the two purple tokens
 * below measure at on both this app's card surfaces), so it's deliberately
 * deferred to the next integration phase rather than shipped unverified.
 *
 * cardLight/cardDark/systemLight were removed (2026-08 audit): all three
 * were leftover pre-August values (cardDark's #1C1C1E and systemLight's
 * #F2F2F7 are literally the old near-black/iOS-gray palette this
 * integration replaced) with zero references anywhere in the app --
 * verified by grep, not assumed from the names looking unused.
 */
internal object HealthAccent {
    val activity = AugustColor.Accent
    val violet = AugustColor.AccentDark
    val mind = AugustColor.AccentDark''',
        desc="remove dead HealthAccent fields",
    )

    print("==> Removing 32 dead imports (drafted-but-never-wired scaffolding)")
    remove_dead_import_lines()

    print("==> Best-effort compile check")
    gradlew = ROOT / "gradlew"
    if gradlew.exists():
        result = subprocess.run(
            ["./gradlew", ":app:compileDebugKotlin", "--console=plain"],
            cwd=ROOT,
        )
        if result.returncode != 0:
            die("compileDebugKotlin failed -- NOT committing or pushing. "
                "Fix the error above (or paste it back) before re-running.")
        print("==> Compile check passed")
    else:
        print("   gradlew not found -- skipping compile check (unexpected outside "
              "a throwaway sandbox; NOT committing automatically).")
        return

    print("==> git add / commit / push")
    subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
    commit = subprocess.run(
        ["git", "commit", "-m", "Audit: revert glass experiment, rename Glass20* symbols, remove dead code"],
        cwd=ROOT,
    )
    if commit.returncode != 0:
        print("   (nothing to commit -- all edits were likely already applied)")
        return
    subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT, check=True)
    print("==> Done: pushed to origin/main")


if __name__ == "__main__":
    main()
