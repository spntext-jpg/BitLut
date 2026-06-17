package com.openhealth.sync.util

import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

/**
 * Small runtime localization bridge for legacy Compose code that still uses String values.
 * New screens should prefer Android string resources, but this keeps the current shell
 * AI-readable and safe while we finish resource-based localization screen by screen.
 */
object L10n {
    private val isRu: Boolean
        get() = Locale.getDefault().language.equals("ru", ignoreCase = true)

    private val ru = mapOf(
        "Dashboard" to "Главная",
        "Sync" to "Синхронизация",
        "Huawei Import" to "Импорт Huawei",
        "Import" to "Импорт",
        "Settings" to "Настройки",
        "Google Health" to "Google Health",
        "Google Health Connect" to "Google Health Connect",
        "Connect Google Health" to "Подключите Google Health",
        "Connect Google Health Connect" to "Подключить Google Health Connect",
        "Refresh" to "Обновить",
        "Refresh data" to "Обновить данные",
        "Sync status" to "Статус синхронизации",
        "Synchronization" to "Синхронизация",
        "Huawei import" to "Импорт Huawei",
        "Huawei Health import" to "Импорт из Huawei Health",
        "Locked until Health Kit approval" to "Заблокировано до согласования Health Kit",
        "Pending Health Kit approval" to "Ожидает согласования Health Kit",
        "Ready after Huawei Health Kit approval" to "Будет доступно после согласования Huawei Health Kit",
        "The Huawei import pipeline is preserved in the app, but disabled for this AppGallery review build." to "Модуль импорта Huawei сохранён в приложении, но отключён в этой сборке для проверки AppGallery.",
        "Settings" to "Настройки",
        "Privacy" to "Конфиденциальность",
        "Permissions" to "Разрешения",
        "Version" to "Версия",
        "Health dashboard" to "Панель здоровья",
        "Today" to "Сегодня",
        "Steps" to "Шаги",
        "Weekly steps" to "Шаги за неделю",
        "Workouts" to "Тренировки",
        "Imported workouts" to "Импортированные тренировки",
        "No workouts yet" to "Тренировок пока нет",
        "Open Sync" to "Открыть синхронизацию",
        "Open Settings" to "Открыть настройки",
        "Coming soon" to "Скоро",
        "Not available yet" to "Пока недоступно",
        "Manual sync" to "Ручная синхронизация",
        "Auto sync" to "Автосинхронизация",
        "Disabled" to "Отключено",
        "Enabled" to "Включено"
    )

    fun t(text: String): String = if (isRu) ru[text] ?: text else text

    fun shortDate(date: LocalDate): String {
        val pattern = if (isRu) "dd.MM" else "MMM d"
        return date.format(DateTimeFormatter.ofPattern(pattern, Locale.getDefault()))
    }

    fun dateTime(epochMillis: Long): String {
        val pattern = if (isRu) "dd.MM.yyyy HH:mm" else "MMM d, yyyy HH:mm"
        return Instant.ofEpochMilli(epochMillis)
            .atZone(ZoneId.systemDefault())
            .format(DateTimeFormatter.ofPattern(pattern, Locale.getDefault()))
    }

    fun workoutTitle(rawTitle: String): String {
        if (!isRu) return rawTitle
        val title = rawTitle.lowercase(Locale.getDefault())
        return when {
            "run" in title || "running" in title -> "Бег"
            "walk" in title || "walking" in title -> "Ходьба"
            "cycl" in title || "bike" in title -> "Велосипед"
            "swim" in title -> "Плавание"
            "strength" in title || "weight" in title -> "Силовая тренировка"
            "yoga" in title -> "Йога"
            "hik" in title -> "Поход"
            "workout" in title || "exercise" in title -> "Тренировка"
            else -> rawTitle
        }
    }
}
