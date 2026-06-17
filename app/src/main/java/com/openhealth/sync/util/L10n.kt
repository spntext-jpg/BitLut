package com.openhealth.sync.util

import java.text.NumberFormat
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

/**
 * Lightweight localization bridge for the current Compose shell.
 *
 * Russian device locale receives a fully localized interface and CIS-style date/time.
 * Other locales keep the English fallback. New large screens can later move to
 * Android string resources one by one without changing the product behavior.
 */
object L10n {
    val isRu: Boolean
        get() = Locale.getDefault().language.equals("ru", ignoreCase = true)

    private val ru = mapOf(
        "BitLut" to "BitLut",
        "Health Sync OS" to "ОС синхронизации здоровья",
        "Dashboard" to "Главная",
        "Sync" to "Синхронизация",
        "Settings" to "Настройки",
        "Dashboard-first release" to "Релиз с фокусом на панель данных",
        "Health overview" to "Обзор здоровья",
        "Sync methods" to "Методы синхронизации",
        "Privacy and release" to "Приватность и релиз",
        "Synchronization" to "Синхронизация",
        "Connect sources and manage available import methods." to "Подключите источники данных и управляйте доступными способами импорта.",
        "Google Health Connect" to "Google Health Connect",
        "Connected" to "Подключено",
        "Not connected" to "Не подключено",
        "Read-only access is active. BitLut can show steps, weekly progress and workouts." to "Доступ только на чтение активен. BitLut показывает шаги, прогресс за неделю и тренировки.",
        "Read-only access is required to show steps, weekly progress and workouts." to "Нужен доступ только на чтение, чтобы показать шаги, прогресс за неделю и тренировки.",
        "Refresh dashboard" to "Обновить главную",
        "Connect Google Health" to "Подключить Google Health",
        "Huawei Health import" to "Импорт из Huawei Health",
        "Locked until Huawei Health Kit approval" to "Заблокировано до согласования Huawei Health Kit",
        "The import pipeline is preserved in the app. It will be enabled here after Huawei approves Health Kit access." to "Модуль импорта сохранён в приложении. Он будет включён здесь после согласования доступа Huawei Health Kit.",
        "Approval pending" to "Ожидает согласования",
        "Manual sync" to "Ручная синхронизация",
        "Auto sync" to "Автосинхронизация",
        "Disabled for review build" to "Отключено в сборке для проверки",
        "Background Huawei sync is intentionally off until approval." to "Фоновая синхронизация Huawei намеренно отключена до согласования.",
        "Data policy" to "Политика данных",
        "Minimum permissions" to "Минимум разрешений",
        "Dashboard uses read-only Google Health data. Write permissions are reserved for the future import stage." to "Главная использует данные Google Health только на чтение. Разрешения на запись зарезервированы для будущего этапа импорта.",
        "Release settings" to "Настройки релиза",
        "Current build" to "Текущая сборка",
        "Huawei feature flag" to "Флаг функции Huawei",
        "Keep disabled until Huawei Health Kit approval and real-device QA." to "Оставить отключённым до согласования Huawei Health Kit и проверки на реальном устройстве.",
        "Protected" to "Защищено",
        "Private by design" to "Приватность по умолчанию",
        "Health data stays on the device and is requested only when the user grants access." to "Данные здоровья остаются на устройстве и запрашиваются только после разрешения пользователя.",
        "Open" to "Открыть",
        "Status" to "Статус",
        "Runtime" to "Режим",
        "Prepared" to "Подготовлено",
        "Locked" to "Заблокировано",
        "Enabled" to "Включено",
        "Disabled" to "Отключено",
        "Stable" to "Стабильно",
        "Pending" to "В ожидании",
        "Today" to "Сегодня",
        "Steps" to "Шаги",
        "Weekly steps" to "Шаги за неделю",
        "Workouts" to "Тренировки",
        "Imported workouts" to "Импортированные тренировки",
        "No workouts yet" to "Тренировок пока нет",
        "Connect Google Health Connect" to "Подключить Google Health Connect",
        "Refresh data" to "Обновить данные"
    )

    fun t(text: String): String = if (isRu) ru[text] ?: text else text

    fun number(value: Long): String = NumberFormat.getIntegerInstance(Locale.getDefault()).format(value)

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
