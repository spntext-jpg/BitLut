package com.openhealth.sync

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.lang.reflect.Field
import java.lang.reflect.Method
import java.util.Locale

@Composable
internal fun MetricBarChartCard(
    palette: BitPalette,
    title: String,
    periodValueLabel: String,
    bars: List<Any?>,
    accent: Color,
    valueFormatter: (Double) -> String
) {
    SoftCard(palette = palette, accent = accent, hero = false, tintWithAccent = true) {
        Text(
            text = title,
            color = palette.text,
            fontWeight = FontWeight.ExtraBold,
            fontSize = 14.sp
        )
        Spacer(Modifier.height(2.dp))
        Text(
            text = periodValueLabel,
            color = palette.secondaryText,
            fontWeight = FontWeight.SemiBold,
            fontSize = 12.sp,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis
        )
        Spacer(Modifier.height(14.dp))

        if (bars.isNotEmpty()) {
            val maxValue = remember(bars) {
                bars.maxOf { metricBarValue(it) }.takeIf { it > 0.0 } ?: 1.0
            }
            val barShape = remember { RoundedCornerShape(999.dp) }
            val barBrush = remember(accent) {
                Brush.verticalGradient(
                    listOf(
                        accent.copy(alpha = 0.98f),
                        accent.copy(alpha = 0.62f)
                    )
                )
            }
            val shineColors = remember {
                listOf(Color.White.copy(alpha = 0.28f), Color.Transparent)
            }

            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(132.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalAlignment = Alignment.Bottom
            ) {
                bars.forEach { bar ->
                    val rawValue = metricBarValue(bar)
                    val fraction = (rawValue / maxValue).toFloat().coerceIn(0.05f, 1f)
                    val valueLabel = valueFormatter(rawValue)
                    val dateLabel = metricBarDateLabel(bar)

                    Column(
                        modifier = Modifier
                            .weight(1f)
                            .fillMaxHeight(),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(
                            text = valueLabel,
                            color = palette.secondaryText,
                            fontWeight = FontWeight.Bold,
                            fontSize = 8.sp,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            modifier = Modifier
                                .height(18.dp)
                                .fillMaxWidth()
                        )

                        Box(
                            modifier = Modifier
                                .height(84.dp)
                                .fillMaxWidth(),
                            contentAlignment = Alignment.BottomCenter
                        ) {
                            Box(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .fillMaxHeight(fraction)
                                    .defaultMinSize(minHeight = 6.dp)
                                    .clip(barShape)
                                    .background(barBrush)
                                    .drawBehind {
                                        drawRect(
                                            brush = Brush.radialGradient(
                                                colors = shineColors,
                                                center = Offset(size.width * 0.35f, 0f),
                                                radius = size.maxDimension * 0.80f
                                            )
                                        )
                                    }
                            )
                        }

                        Spacer(Modifier.height(5.dp))

                        Text(
                            text = dateLabel,
                            color = palette.secondaryText,
                            fontWeight = FontWeight.Bold,
                            fontSize = 8.sp,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            modifier = Modifier
                                .height(18.dp)
                                .fillMaxWidth()
                        )
                    }
                }
            }
        }
    }
}

private fun metricBarValue(bar: Any?): Double {
    if (bar == null) return 0.0

    when (bar) {
        is Number -> return bar.toDouble()
        is Pair<*, *> -> return numericValue(bar.second) ?: numericValue(bar.first) ?: 0.0
        is Map<*, *> -> {
            for (key in VALUE_KEYS) {
                numericValue(bar[key])?.let { return it }
            }
            for ((_, value) in bar) {
                numericValue(value)?.let { return it }
            }
            return 0.0
        }
    }

    for (name in VALUE_KEYS) {
        readableMemberValue(bar, name)?.let { value ->
            numericValue(value)?.let { return it }
        }
    }

    return 0.0
}

private fun metricBarDateLabel(bar: Any?): String {
    if (bar == null) return ""

    when (bar) {
        is Pair<*, *> -> return bar.first?.toString().orEmpty()
        is Map<*, *> -> {
            for (key in LABEL_KEYS) {
                val value = bar[key]?.toString().orEmpty()
                if (value.isNotBlank()) return compactLabel(value)
            }
            return ""
        }
    }

    for (name in LABEL_KEYS) {
        readableMemberValue(bar, name)?.let { value ->
            val label = value.toString()
            if (label.isNotBlank()) return compactLabel(label)
        }
    }

    return ""
}

private fun numericValue(value: Any?): Double? {
    return when (value) {
        is Number -> value.toDouble()
        is String -> value.toDoubleOrNull()
        else -> null
    }
}

private fun readableMemberValue(target: Any, name: String): Any? {
    return readMethodValue(target, getterName(name))
        ?: readMethodValue(target, name)
        ?: readFieldValue(target, name)
}

private fun readMethodValue(target: Any, methodName: String): Any? {
    return runCatching {
        val method: Method = target.javaClass.methods.firstOrNull {
            it.name == methodName && it.parameterCount == 0
        } ?: return null
        method.isAccessible = true
        method.invoke(target)
    }.getOrNull()
}

private fun readFieldValue(target: Any, fieldName: String): Any? {
    return runCatching {
        val field: Field = target.javaClass.declaredFields.firstOrNull {
            it.name == fieldName
        } ?: return null
        field.isAccessible = true
        field.get(target)
    }.getOrNull()
}

private fun getterName(name: String): String {
    if (name.isBlank()) return name
    return "get" + name.substring(0, 1).uppercase(Locale.US) + name.substring(1)
}

private fun compactLabel(raw: String): String {
    return raw
        .removePrefix("DateBased(")
        .removeSuffix(")")
        .substringAfterLast("/")
        .takeLast(10)
}

private val VALUE_KEYS = listOf(
    "value",
    "amount",
    "total",
    "count",
    "steps",
    "distance",
    "distanceMeters",
    "meters",
    "kilometers",
    "minutes",
    "duration",
    "activeMinutes",
    "calories",
    "floors",
    "elevation",
    "elevationGain"
)

private val LABEL_KEYS = listOf(
    "label",
    "dateLabel",
    "dayLabel",
    "periodLabel",
    "date",
    "day",
    "startDate",
    "endDate",
    "period",
    "title",
    "name"
)
