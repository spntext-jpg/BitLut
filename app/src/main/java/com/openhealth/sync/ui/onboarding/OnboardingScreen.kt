package com.openhealth.sync.ui.onboarding

import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
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
import com.openhealth.sync.ui.theme.ElectricIndigo
import com.openhealth.sync.ui.theme.ElectricIndigoLt
import com.openhealth.sync.ui.theme.GlassCard
import com.openhealth.sync.ui.theme.GlassBorder
import com.openhealth.sync.ui.theme.GlassWhite
import com.openhealth.sync.ui.theme.GlowIndigo
import com.openhealth.sync.ui.theme.GlowMint
import com.openhealth.sync.ui.theme.MeshBackground
import com.openhealth.sync.ui.theme.NeonMint
import com.openhealth.sync.ui.theme.TextPrimary
import com.openhealth.sync.ui.theme.TextSecondary
import com.openhealth.sync.ui.theme.VoidBorder
import kotlinx.coroutines.delay

@Composable
fun OnboardingScreen(onContinue: () -> Unit) {
    var visible by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) { delay(100); visible = true }

    val alpha by animateFloatAsState(
        targetValue = if (visible) 1f else 0f,
        animationSpec = tween(800, easing = FastOutSlowInEasing),
        label = "onboardingAlpha"
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
            Spacer(Modifier.height(64.dp))

            // Logo wordmark
            Text(
                text = "BitLut",
                fontSize = 48.sp,
                fontWeight = FontWeight.Black,
                color = TextPrimary,
                letterSpacing = (-2).sp
            )

            Spacer(Modifier.height(8.dp))

            Text(
                text = stringResource(R.string.onboarding_subtitle),
                fontSize = 15.sp,
                color = TextSecondary,
                textAlign = TextAlign.Center,
                lineHeight = 22.sp
            )

            Spacer(Modifier.height(48.dp))

            // Steps glass card
            GlassCard(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(28.dp),
                glowColor = GlowIndigo
            ) {
                Column(modifier = Modifier.padding(28.dp)) {
                    Text(
                        text = stringResource(R.string.onboarding_steps_title),
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary
                    )
                    Spacer(Modifier.height(20.dp))
                    listOf(
                        stringResource(R.string.onboarding_step1),
                        stringResource(R.string.onboarding_step2),
                        stringResource(R.string.onboarding_step3),
                        stringResource(R.string.onboarding_step4),
                        stringResource(R.string.onboarding_step5)
                    ).forEachIndexed { i, step ->
                        OnboardingStep(number = (i + 1).toString(), text = step)
                        if (i < 4) Spacer(Modifier.height(14.dp))
                    }
                }
            }

            Spacer(Modifier.height(16.dp))

            // Import hint card
            GlassCard(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(20.dp),
                glowColor = GlowMint
            ) {
                Row(
                    modifier = Modifier.padding(20.dp),
                    horizontalArrangement = Arrangement.spacedBy(14.dp),
                    verticalAlignment = Alignment.Top
                ) {
                    Text("✦", fontSize = 18.sp, color = NeonMint)
                    Text(
                        text = stringResource(R.string.onboarding_import_hint),
                        fontSize = 14.sp,
                        color = NeonMint,
                        lineHeight = 20.sp,
                        modifier = Modifier.weight(1f)
                    )
                }
            }

            Spacer(Modifier.height(32.dp))

            // CTA button
            Button(
                onClick = onContinue,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(56.dp),
                shape = RoundedCornerShape(18.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = Color.Transparent
                )
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(
                            Brush.horizontalGradient(
                                listOf(ElectricIndigo, ElectricIndigoLt)
                            ),
                            shape = RoundedCornerShape(18.dp)
                        ),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = stringResource(R.string.onboarding_continue),
                        fontSize = 16.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Color.White,
                        letterSpacing = 0.3.sp
                    )
                }
            }

            Spacer(Modifier.height(40.dp))
        }
    }
}

@Composable
private fun OnboardingStep(number: String, text: String) {
    Row(
        horizontalArrangement = Arrangement.spacedBy(14.dp),
        verticalAlignment = Alignment.Top,
        modifier = Modifier.fillMaxWidth()
    ) {
        Box(
            modifier = Modifier
                .size(28.dp)
                .clip(CircleShape)
                .background(
                    Brush.linearGradient(
                        listOf(ElectricIndigo, ElectricIndigoLt)
                    )
                ),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = number,
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold,
                color = Color.White
            )
        }
        Text(
            text = text,
            fontSize = 15.sp,
            color = TextSecondary,
            lineHeight = 22.sp,
            modifier = Modifier
                .weight(1f)
                .padding(top = 3.dp)
        )
    }
}
