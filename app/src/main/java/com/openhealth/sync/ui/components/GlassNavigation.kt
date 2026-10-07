package com.openhealth.sync

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsFocusedAsState
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.openhealth.sync.ui.theme.AugustColor
import com.openhealth.sync.ui.theme.AugustMotion
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin
import kotlinx.coroutines.delay

private const val SECRET_TAP_COUNT = 5
private const val SECRET_TAP_WINDOW_MS = 2000L
private val NAV_BAR_OUTER_HORIZONTAL_MARGIN = 24.dp
private val NAV_BAR_OUTER_VERTICAL_MARGIN = 8.dp

// 2026-08-30: navbar rebuild. The previous resize shrank destination
// buttons' HEIGHT (58->46dp) to make them read as secondary next to the
// Refresh action, but a Row.weight(1f) child's *height* has nothing to do
// with how prominent it looks relative to a sibling -- only *width* does,
// and the 46dp fixed height was too short for a 24dp icon + spacer + 10sp
// label to lay out without the label clipping (confirmed: 24 + 3 + ~13
// text line height already exceeds the 36dp inner budget left after 5dp
// top/bottom padding). Fix: every control in the bar now shares one
// common height so nothing clips or looks vertically lopsided; visual
// hierarchy (Refresh reads as the primary action) comes entirely from
// Refresh being wider than a destination button, not taller.
// BITLUT_NAVBAR_REBUILD_2026_08_30
//
// 2026 GUI pass 2: slimmed 64dp -> 56dp (Apple-style thinner bar), with the
// icon tile/spacer/padding all reduced together rather than only the outer
// height, to avoid repeating the exact clipping failure documented above.
// Budget check: 56dp - 2*5dp padding = 46dp inner; content is a 24dp icon
// tile + 3dp spacer + an 11sp label line (~13dp) = 40dp, leaving 6dp slack
// -- comparable margin to the original 64dp design's 8dp slack, not a
// zero-margin fit. Label font size (11sp) is unchanged.
private val NAV_BAR_CONTROL_HEIGHT = 56.dp
private val NAV_BAR_SYNC_ACTION_WIDTH = 84.dp

// BITLUT_NAV_GLYPHS_2026_10_06
// Root cause of the "selected icon turns transparent" regression: the 2026 GUI
// pass 2 (B3) removed the lime tile behind the selected icon but left the
// selected icon tint at AugustColor.LimeInk. LimeInk == Ink == Navy (#151728),
// the exact colour of the bar, so the selected glyph was dark-on-dark
// (WCAG contrast 1.02 - 1.52 against the Navy@0.86 bar, depending on what
// scrolls underneath) in BOTH themes: the bar is Navy in light and dark mode.
// The glyphs are now drawn in code (see AugustNavGlyph) and only ever use
// colours that were measured against the bar, worst case = lightest backdrop
// (white behind the 14% show-through of the translucent bar):
//   Lime #DFFF6A (selected)             10.36:1
//   Lime at 72% alpha (idle)             6.22:1
//   Tangerine #F28500 (pressed)          4.52:1 (WCAG non-text minimum is 3:1)
// Against a black backdrop the same three colours measure 16.25 / 8.74 / 7.08.
private val NAV_GLYPH_SIZE = 24.dp
private val NAV_GLYPH_IDLE_COLOR = AugustColor.Lime.copy(alpha = 0.72f)
// Keeps the orange press highlight on screen briefly after release so a quick
// tap (finger down for ~80ms) is still visible instead of a sub-frame flash.
private const val NAV_GLYPH_FLASH_HOLD_MS = 120L

/** Compact two-destination dock with one explicit sync action. */
@Composable
internal fun AugustBottomNav(
    selected: MainTab,
    onSelected: (MainTab) -> Unit,
    onSecretLogViewerTriggered: () -> Unit = {},
    onRefreshClick: () -> Unit = {}
) {
    var secretTapCount by remember { mutableIntStateOf(0) }
    var lastSecretTapAtMs by remember { mutableLongStateOf(0L) }
    val shellShape = remember { RoundedCornerShape(30.dp) }

    fun onSettingsTabTapped() {
        val now = System.currentTimeMillis()
        secretTapCount = if (now - lastSecretTapAtMs <= SECRET_TAP_WINDOW_MS) secretTapCount + 1 else 1
        lastSecretTapAtMs = now
        if (secretTapCount >= SECRET_TAP_COUNT) {
            secretTapCount = 0
            onSecretLogViewerTriggered()
        }
    }

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .navigationBarsPadding()
            .padding(horizontal = NAV_BAR_OUTER_HORIZONTAL_MARGIN, vertical = NAV_BAR_OUTER_VERTICAL_MARGIN),
        contentAlignment = Alignment.Center
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .shadow(
                    elevation = 12.dp,
                    shape = shellShape,
                    ambientColor = AugustColor.Navy.copy(alpha = 0.35f),
                    spotColor = AugustColor.Navy.copy(alpha = 0.35f)
                )
                .clip(shellShape)
                // 2026 minimalist pass: translucent instead of solid Navy,
                // closer to iOS's translucent (pre-backdrop-blur) tab bar
                // treatment. NOTE: true backdrop blur (blurring whatever
                // scrolls underneath the bar) is not implemented here --
                // Modifier.blur blurs a composable's OWN children, not the
                // content behind it in z-order, so applying it to this Row
                // would blur the nav icons/labels themselves, not the
                // content behind them. Real backdrop blur needs either a
                // captured-layer technique or a library (e.g. Haze, not a
                // current dependency of this project) -- out of scope for
                // this pass. Translucency + a stronger shadow is the
                // honest, dependency-free approximation.
                .background(AugustColor.Navy.copy(alpha = 0.86f))
                .padding(horizontal = 8.dp, vertical = 6.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            AugustDestination(
                modifier = Modifier.weight(1f),
                tab = MainTab.Today,
                selected = selected == MainTab.Today,
                onClick = { onSelected(MainTab.Today) }
            )
            AugustSyncAction(onClick = onRefreshClick)
            AugustDestination(
                modifier = Modifier.weight(1f),
                tab = MainTab.Settings,
                selected = selected == MainTab.Settings,
                onClick = {
                    onSettingsTabTapped()
                    onSelected(MainTab.Settings)
                }
            )
        }
    }
}

@Composable
private fun AugustDestination(
    modifier: Modifier,
    tab: MainTab,
    selected: Boolean,
    onClick: () -> Unit
) {
    val interactionSource = remember { MutableInteractionSource() }
    val pressed by interactionSource.collectIsPressedAsState()
    val focused by interactionSource.collectIsFocusedAsState()
    val shape = remember { RoundedCornerShape(22.dp) }
    var tapFlash by remember { mutableStateOf(false) }
    LaunchedEffect(pressed) {
        if (pressed) {
            tapFlash = true
        } else {
            delay(NAV_GLYPH_FLASH_HOLD_MS)
            tapFlash = false
        }
    }
    val highlighted = pressed || tapFlash
    val label = when (tab) {
        MainTab.Today -> stringResource(R.string.tab_today)
        MainTab.Settings -> stringResource(R.string.tab_settings)
    }

    // 2026 GUI pass 2 (B3, opt-in per user's choice): iOS's native tab bar
    // has no background pill at all -- only a tint/weight change on
    // selection. Previously this button got a white rounded "container"
    // pill behind the whole control PLUS a separate lime tile behind just
    // the icon when selected; both are removed. Selected state is carried
    // by content colour (label switches to AugustColor.Lime, bold weight)
    // and by the glyph itself (AugustNavGlyph: full Lime, heavier stroke,
    // animated). No fill sits behind the control, so every colour used here
    // must be bright enough to read directly on the Navy bar -- see the
    // BITLUT_NAV_GLYPHS_2026_10_06 note above for the measured contrasts.
    val contentColor by animateColorAsState(
        targetValue = if (selected) AugustColor.Lime else AugustColor.DarkSecondaryText,
        animationSpec = tween(AugustMotion.DefaultMs, easing = AugustMotion.StandardEasing),
        label = "destinationContent"
    )
    // A small press depth + asymmetric tilt gives the dock a tactile glass feel.
    // The under-damped return is intentional: it creates one restrained release tremor,
    // while the low amplitude keeps August calm rather than cartoon-like.
    // BITLUT_FINAL_UI_SPRINT_2026_09_11
    val scale by animateFloatAsState(
        targetValue = if (pressed) AugustMotion.DestinationPressScale else 1f,
        animationSpec = spring(
            dampingRatio = AugustMotion.PressSpringDampingRatio,
            stiffness = AugustMotion.PressSpringStiffness
        ),
        label = "destinationPressScale"
    )
    val pressDepth by animateDpAsState(
        targetValue = if (pressed) AugustMotion.PressTranslationDp.dp else 0.dp,
        animationSpec = spring(
            dampingRatio = AugustMotion.PressSpringDampingRatio,
            stiffness = AugustMotion.PressSpringStiffness
        ),
        label = "destinationPressDepth"
    )
    val pressTilt by animateFloatAsState(
        targetValue = if (pressed) {
            if (tab == MainTab.Today) -AugustMotion.DestinationPressTiltDegrees
            else AugustMotion.DestinationPressTiltDegrees
        } else 0f,
        animationSpec = spring(
            dampingRatio = AugustMotion.PressSpringDampingRatio,
            stiffness = AugustMotion.PressSpringStiffness
        ),
        label = "destinationPressTilt"
    )

    Column(
        modifier = modifier
            .height(NAV_BAR_CONTROL_HEIGHT)
            .graphicsLayer {
                scaleX = scale
                scaleY = scale
                translationY = pressDepth.toPx()
                rotationZ = pressTilt
            }
            .clip(shape)
            .border(
                width = if (focused) 2.dp else 0.dp,
                color = if (focused) AugustColor.Purple else Color.Transparent,
                shape = shape
            )
            .semantics { this.selected = selected }
            .clickable(
                interactionSource = interactionSource,
                indication = null,
                role = Role.Tab,
                onClick = onClick
            )
            .padding(horizontal = 6.dp, vertical = 5.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        AugustNavGlyph(tab = tab, selected = selected, highlighted = highlighted)
        Spacer(Modifier.height(3.dp))
        Text(
            text = label,
            color = contentColor,
            fontWeight = if (selected) FontWeight.ExtraBold else FontWeight.SemiBold,
            fontSize = 11.sp,
            maxLines = 1
        )
    }
}

/**
 * Bottom-nav glyphs, drawn on a 24x24 grid so they stay crisp at any density
 * and can animate their own geometry (an ImageVector cannot).
 *
 * Colour: Lime when selected, Lime at 72% when idle (never dark -- the bar is
 * Navy in both themes), Tangerine while pressed and for a short hold after.
 * Motion: selecting overshoots a spring (calendar dot pops, gear turns one
 * tooth); pressing squeezes the dot and kicks the gear / lifts the binders.
 * BITLUT_NAV_GLYPHS_2026_10_06
 */
@Composable
private fun AugustNavGlyph(
    tab: MainTab,
    selected: Boolean,
    highlighted: Boolean
) {
    val color by animateColorAsState(
        targetValue = when {
            highlighted -> AugustColor.Tangerine
            selected -> AugustColor.Lime
            else -> NAV_GLYPH_IDLE_COLOR
        },
        animationSpec = tween(AugustMotion.FastMs, easing = AugustMotion.StandardEasing),
        label = "navGlyphColor"
    )
    val selectProgress by animateFloatAsState(
        targetValue = if (selected) 1f else 0f,
        animationSpec = spring(dampingRatio = 0.5f, stiffness = 420f),
        label = "navGlyphSelect"
    )
    val pressProgress by animateFloatAsState(
        targetValue = if (highlighted) 1f else 0f,
        animationSpec = spring(
            dampingRatio = AugustMotion.PressSpringDampingRatio,
            stiffness = AugustMotion.PressSpringStiffness
        ),
        label = "navGlyphPress"
    )

    Canvas(modifier = Modifier.size(NAV_GLYPH_SIZE)) {
        val unit = size.minDimension / 24f
        // Stroke eases from 1.7 to 2.2 grid units on selection (clamped so the
        // spring overshoot never makes the line balloon).
        val stroke = Stroke(
            width = (1.7f + 0.5f * selectProgress.coerceIn(0f, 1f)) * unit,
            cap = StrokeCap.Round,
            join = StrokeJoin.Round
        )
        when (tab) {
            MainTab.Today -> drawTodayGlyph(color, stroke, unit, selectProgress, pressProgress)
            MainTab.Settings -> drawSettingsGlyph(color, stroke, unit, selectProgress, pressProgress)
        }
    }
}

/** Calendar page with binder rings and a "today" dot. */
private fun DrawScope.drawTodayGlyph(
    color: Color,
    stroke: Stroke,
    unit: Float,
    select: Float,
    press: Float
) {
    drawRoundRect(
        color = color,
        topLeft = Offset(3.5f * unit, 5f * unit),
        size = Size(17f * unit, 15.5f * unit),
        cornerRadius = CornerRadius(4f * unit, 4f * unit),
        style = stroke
    )
    drawLine(
        color = color,
        start = Offset(4f * unit, 10f * unit),
        end = Offset(20f * unit, 10f * unit),
        strokeWidth = stroke.width,
        cap = StrokeCap.Round
    )
    // Binder rings lift slightly while pressed.
    val lift = 1.2f * press * unit
    drawLine(
        color = color,
        start = Offset(8f * unit, 2.8f * unit - lift),
        end = Offset(8f * unit, 6.8f * unit - lift),
        strokeWidth = stroke.width,
        cap = StrokeCap.Round
    )
    drawLine(
        color = color,
        start = Offset(16f * unit, 2.8f * unit - lift),
        end = Offset(16f * unit, 6.8f * unit - lift),
        strokeWidth = stroke.width,
        cap = StrokeCap.Round
    )
    // "Today" dot: grows on selection (spring overshoot = pop), squeezes on press.
    val dotRadius = (1.5f + 0.9f * select - 0.35f * press) * unit
    drawCircle(
        color = color,
        radius = dotRadius.coerceAtLeast(0f),
        center = Offset(12f * unit, 15.25f * unit)
    )
}

/** Eight-tooth gear with a centre hole. */
private fun DrawScope.drawSettingsGlyph(
    color: Color,
    stroke: Stroke,
    unit: Float,
    select: Float,
    press: Float
) {
    val centre = Offset(12f * unit, 12f * unit)
    val gear = Path()
    for (tooth in 0 until GEAR_TEETH) {
        val mid = tooth * (360f / GEAR_TEETH)
        val rootStart = polar(centre, GEAR_ROOT_RADIUS * unit, mid - GEAR_ROOT_HALF_ANGLE)
        val tipStart = polar(centre, GEAR_TIP_RADIUS * unit, mid - GEAR_TIP_HALF_ANGLE)
        val tipEnd = polar(centre, GEAR_TIP_RADIUS * unit, mid + GEAR_TIP_HALF_ANGLE)
        val rootEnd = polar(centre, GEAR_ROOT_RADIUS * unit, mid + GEAR_ROOT_HALF_ANGLE)
        if (tooth == 0) gear.moveTo(rootStart.x, rootStart.y) else gear.lineTo(rootStart.x, rootStart.y)
        gear.lineTo(tipStart.x, tipStart.y)
        gear.lineTo(tipEnd.x, tipEnd.y)
        gear.lineTo(rootEnd.x, rootEnd.y)
    }
    gear.close()
    // One full tooth step (45 degrees) on selection, an extra kick while pressed.
    rotate(45f * select + 35f * press, centre) {
        drawPath(path = gear, color = color, style = stroke)
        drawCircle(color = color, radius = 2.9f * unit, center = centre, style = stroke)
    }
}

private const val GEAR_TEETH = 8
private const val GEAR_TIP_RADIUS = 9.4f
private const val GEAR_ROOT_RADIUS = 7.2f
private const val GEAR_TIP_HALF_ANGLE = 8f
private const val GEAR_ROOT_HALF_ANGLE = 13f

private fun polar(centre: Offset, radius: Float, degrees: Float): Offset {
    val radians = (degrees * PI / 180.0).toFloat()
    return Offset(centre.x + radius * cos(radians), centre.y + radius * sin(radians))
}

@Composable
private fun AugustSyncAction(onClick: () -> Unit) {
    val interactionSource = remember { MutableInteractionSource() }
    val pressed by interactionSource.collectIsPressedAsState()
    val focused by interactionSource.collectIsFocusedAsState()
    val shape = remember { RoundedCornerShape(24.dp) }
    val scale by animateFloatAsState(
        targetValue = if (pressed) AugustMotion.PrimaryPressScale else 1f,
        animationSpec = spring(
            dampingRatio = AugustMotion.PressSpringDampingRatio,
            stiffness = AugustMotion.PressSpringStiffness
        ),
        label = "syncPressScale"
    )
    val pressDepth by animateDpAsState(
        targetValue = if (pressed) AugustMotion.PressTranslationDp.dp else 0.dp,
        animationSpec = spring(
            dampingRatio = AugustMotion.PressSpringDampingRatio,
            stiffness = AugustMotion.PressSpringStiffness
        ),
        label = "syncPressDepth"
    )
    val pressTilt by animateFloatAsState(
        targetValue = if (pressed) AugustMotion.SyncPressTiltDegrees else 0f,
        animationSpec = spring(
            dampingRatio = AugustMotion.PressSpringDampingRatio,
            stiffness = AugustMotion.PressSpringStiffness
        ),
        label = "syncPressTilt"
    )
    val rotation by animateFloatAsState(
        targetValue = if (pressed) AugustMotion.SyncIconPressRotationDegrees else 0f,
        animationSpec = spring(
            dampingRatio = AugustMotion.PressSpringDampingRatio,
            stiffness = AugustMotion.PressSpringStiffness
        ),
        label = "syncPressRotation"
    )
    val fill by animateColorAsState(
        targetValue = if (pressed) AugustColor.TangerineActive else AugustColor.Tangerine,
        animationSpec = tween(AugustMotion.FastMs, easing = AugustMotion.StandardEasing),
        label = "syncFill"
    )

    // Same shared height as AugustDestination (NAV_BAR_CONTROL_HEIGHT) so
    // the whole bar aligns on one baseline; a wider fixed width (rather
    // than a taller box) is what makes this read as the primary action,
    // per the 2026-08-30 navbar rebuild note above.
    Box(
        modifier = Modifier
            .width(NAV_BAR_SYNC_ACTION_WIDTH)
            .height(NAV_BAR_CONTROL_HEIGHT)
            .graphicsLayer {
                scaleX = scale
                scaleY = scale
                translationY = pressDepth.toPx()
                rotationZ = pressTilt
            }
            .clip(shape)
            .background(fill)
            .border(
                width = if (focused) 2.dp else 0.dp,
                color = if (focused) AugustColor.Purple else Color.Transparent,
                shape = shape
            )
            .clickable(
                interactionSource = interactionSource,
                indication = null,
                role = Role.Button,
                onClick = onClick
            ),
        contentAlignment = Alignment.Center
    ) {
        Icon(
            imageVector = Icons.Rounded.Refresh,
            contentDescription = stringResource(R.string.sync_now),
            tint = AugustColor.Ink,
            modifier = Modifier
                .size(32.dp)
                .graphicsLayer { rotationZ = rotation }
        )
    }
}
