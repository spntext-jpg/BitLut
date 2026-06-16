package com.openhealth.sync.ui.onboarding

import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.openhealth.sync.R
import com.openhealth.sync.ui.theme.Blue
import com.openhealth.sync.ui.theme.GlassCard
import com.openhealth.sync.ui.theme.GlowBlue
import com.openhealth.sync.ui.theme.GlowPurple
import com.openhealth.sync.ui.theme.MeshBackground
import com.openhealth.sync.ui.theme.Orange
import com.openhealth.sync.ui.theme.Purple
import com.openhealth.sync.ui.theme.TextPrimary
import com.openhealth.sync.ui.theme.TextSecondary
import kotlinx.coroutines.delay

@Composable
fun OnboardingScreen(onContinue: () -> Unit) {
    var visible by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) { delay(120); visible = true }
    val alpha by animateFloatAsState(
        targetValue = if (visible) 1f else 0f,
        animationSpec = tween(700, easing = FastOutSlowInEasing),
        label = "onboardAlpha"
    )

    Box(modifier = Modifier.fillMaxSize()) {
        MeshBackground()
        Column(
            modifier = Modifier
                .fillMaxSize()
                .alpha(alpha)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Spacer(Modifier.height(72.dp))
            Text("BitLut", fontSize = 52.sp, fontWeight = FontWeight.Black, color = TextPrimary, letterSpacing = (-2).sp)
            Spacer(Modifier.height(6.dp))
            Text(stringResource(R.string.onboarding_subtitle), fontSize = 15.sp, color = TextSecondary, textAlign = TextAlign.Center, lineHeight = 22.sp)
            Spacer(Modifier.height(48.dp))

            GlassCard(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(24.dp), glowColor = GlowBlue) {
                Column(modifier = Modifier.padding(24.dp)) {
                    Text(stringResource(R.string.onboarding_steps_title), fontSize = 18.sp, fontWeight = FontWeight.Bold, color = TextPrimary)
                    Spacer(Modifier.height(20.dp))
                    listOf(
                        stringResource(R.string.onboarding_step1),
                        stringResource(R.string.onboarding_step2),
                        stringResource(R.string.onboarding_step3),
                        stringResource(R.string.onboarding_step4),
                        stringResource(R.string.onboarding_step5)
                    ).forEachIndexed { i, step ->
                        OnboardingStepRow((i + 1).toString(), step)
                        if (i < 4) Spacer(Modifier.height(14.dp))
                    }
                }
            }

            Spacer(Modifier.height(14.dp))

            GlassCard(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(20.dp), glowColor = GlowPurple) {
                Row(modifier = Modifier.padding(18.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.Top) {
                    Text("✦", fontSize = 16.sp, color = Orange)
                    Text(stringResource(R.string.onboarding_import_hint), fontSize = 14.sp, color = Orange, lineHeight = 20.sp, modifier = Modifier.weight(1f))
                }
            }

            Spacer(Modifier.height(36.dp))

            Button(
                onClick = onContinue,
                modifier = Modifier.fillMaxWidth().height(54.dp),
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(containerColor = Color.Transparent),
                contentPadding = PaddingValues(0.dp)
            ) {
                Box(
                    modifier = Modifier.fillMaxSize().background(Brush.horizontalGradient(listOf(Blue, Purple))),
                    contentAlignment = Alignment.Center
                ) {
                    Text(stringResource(R.string.onboarding_continue), fontSize = 16.sp, fontWeight = FontWeight.SemiBold, color = Color.White)
                }
            }

            Spacer(Modifier.height(40.dp))
        }
    }
}

@Composable
private fun OnboardingStepRow(number: String, text: String) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(14.dp), verticalAlignment = Alignment.Top) {
        Box(
            modifier = Modifier.size(28.dp).clip(CircleShape).background(Brush.horizontalGradient(listOf(Blue, Purple))),
            contentAlignment = Alignment.Center
        ) {
            Text(number, fontSize = 12.sp, fontWeight = FontWeight.Bold, color = Color.White)
        }
        Text(text, fontSize = 14.sp, color = TextSecondary, lineHeight = 21.sp, modifier = Modifier.weight(1f).padding(top = 3.dp))
    }
}
