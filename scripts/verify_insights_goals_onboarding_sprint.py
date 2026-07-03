#!/usr/bin/env python3
"""
Verifies the v1.9.12 sprint (insights/streak/notifications + configurable
goals/onboarding), strictly within the already-approved Huawei activity-only
scope (steps, distance, calories, floors, workouts). No sleep/heart-rate/
stress/SpO2 field is read, written, or referenced anywhere in this sprint.

Sprint 4 -- insights & assistant:
1. AchievementsStore: personal records (steps/distance) + goal streak.
2. WeekComparison: week-over-week % change for steps/distance/calories.
3. EveningReminderWorker + NotificationHelper: once-daily goal-progress
   notification, activity-only content.
4. POST_NOTIFICATIONS permission + runtime request wiring.

Sprint 7 -- polish:
5. GoalPrefs: configurable steps/distance/active-minutes/calories goals.
6. Settings goal steppers wired to DashboardViewModel.
7. PermissionsOnboardingScreen: one-time rationale before the system
   Health Connect permission dialog.
"""
from pathlib import Path
import sys

errors = []


def read(path):
    p = Path(path)
    if not p.exists():
        errors.append(f"Missing {path}")
        return ""
    return p.read_text(encoding="utf-8")


def require(condition, message):
    if not condition:
        errors.append(message)


achievements = read("app/src/main/java/com/openhealth/sync/data/AchievementsStore.kt")
contracts = read("app/src/main/java/com/openhealth/sync/data/HealthDataContracts.kt")
google = read("app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt")
sync_worker = read("app/src/main/java/com/openhealth/sync/data/worker/SyncWorker.kt")
evening_worker = read("app/src/main/java/com/openhealth/sync/data/worker/EveningReminderWorker.kt")
scheduler = read("app/src/main/java/com/openhealth/sync/data/worker/BackgroundSyncScheduler.kt")
notif_helper = read("app/src/main/java/com/openhealth/sync/notifications/NotificationHelper.kt")
goal_prefs = read("app/src/main/java/com/openhealth/sync/config/GoalPrefs.kt")
onboarding_prefs = read("app/src/main/java/com/openhealth/sync/config/OnboardingPrefs.kt")
app_container = read("app/src/main/java/com/openhealth/sync/di/AppContainer.kt")
dashboard_vm = read("app/src/main/java/com/openhealth/sync/ui/DashboardViewModel.kt")
main_activity = read("app/src/main/java/com/openhealth/sync/MainActivity.kt")
shell = read("app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt")
manifest = read("app/src/main/AndroidManifest.xml")
strings_en = read("app/src/main/res/values/strings.xml")
strings_ru = read("app/src/main/res/values-ru/strings.xml")
ic_notification = read("app/src/main/res/drawable/ic_notification.xml")

# ---------------------------------------------------------------------------
# Activity-only boundary: the single most important invariant in this sprint.
# ---------------------------------------------------------------------------
forbidden_tokens = ["sleepHours =", "heartRateBpm =", "stressScore =", "spo2Percent ="]
for label, src in [
    ("AchievementsStore.kt", achievements),
    ("EveningReminderWorker.kt", evening_worker),
    ("NotificationHelper.kt", notif_helper),
]:
    for token in forbidden_tokens:
        require(token not in src, f"{label} must stay activity-only; found forbidden field write: {token}")

goal_prefs_declarations = "\n".join(
    line for line in goal_prefs.splitlines() if "fun " in line or "const val" in line or "val " in line
)
require(
    "sleep" not in goal_prefs_declarations.lower() and "heart" not in goal_prefs_declarations.lower() and "stress" not in goal_prefs_declarations.lower(),
    "GoalPrefs must only define activity-only goals (steps/distance/active minutes/calories)"
)

# ---------------------------------------------------------------------------
# 1. AchievementsStore
# ---------------------------------------------------------------------------
require("class AchievementsStore" in achievements, "AchievementsStore must exist")
require("fun bestStepsDay()" in achievements, "bestStepsDay() must exist")
require("fun bestDistanceMetersDay()" in achievements, "bestDistanceMetersDay() must exist")
require("fun recordDailyTotals(" in achievements, "recordDailyTotals() must exist")
require("fun updateStreak(" in achievements, "updateStreak() must exist")
require("data class StreakState" in achievements, "StreakState must exist")

# ---------------------------------------------------------------------------
# 2. WeekComparison
# ---------------------------------------------------------------------------
require("data class WeekComparison" in contracts, "WeekComparison must be defined in HealthDataContracts.kt")
require("suspend fun readWeekOverWeekComparison(): WeekComparison?" in contracts, "readWeekOverWeekComparison must be part of the interface")
require("override suspend fun readWeekOverWeekComparison(" in google, "GoogleHealthManager must implement readWeekOverWeekComparison")
require(
    "StepsRecord.COUNT_TOTAL" in google and "DistanceRecord.DISTANCE_TOTAL" in google and "ActiveCaloriesBurnedRecord.ACTIVE_CALORIES_TOTAL" in google,
    "Week comparison must aggregate only steps/distance/active calories (activity-only)"
)

# ---------------------------------------------------------------------------
# 3. Notifications
# ---------------------------------------------------------------------------
require("class EveningReminderWorker" in evening_worker, "EveningReminderWorker must exist")
require("object NotificationHelper" in notif_helper, "NotificationHelper must exist")
require("fun ensureChannel(" in notif_helper, "NotificationHelper must create a notification channel")
require("hasPermission(context)" in notif_helper, "NotificationHelper must check POST_NOTIFICATIONS before posting")
require("scheduleEveningReminder" in scheduler, "BackgroundSyncScheduler must schedule the evening reminder")
require("ExistingPeriodicWorkPolicy.KEEP" in scheduler, "Evening reminder must use KEEP (not UPDATE) to avoid re-shifting its scheduled time on every app launch")
require(len(ic_notification) > 0, "ic_notification.xml drawable must exist")
require("android:fillColor" in ic_notification, "ic_notification.xml must be a flat vector icon suitable for the status bar")

# ---------------------------------------------------------------------------
# 4. POST_NOTIFICATIONS permission
# ---------------------------------------------------------------------------
require("android.permission.POST_NOTIFICATIONS" in manifest, "AndroidManifest.xml must declare POST_NOTIFICATIONS")
require("notificationPermissionLauncher" in main_activity, "MainActivity must request POST_NOTIFICATIONS at runtime")
require("requestNotificationPermissionIfNeeded" in main_activity, "MainActivity must have a runtime notification permission request path")

# ---------------------------------------------------------------------------
# 5. GoalPrefs
# ---------------------------------------------------------------------------
require("class GoalPrefs" in goal_prefs, "GoalPrefs must exist")
require("fun stepsGoal()" in goal_prefs and "fun setStepsGoal(" in goal_prefs, "Steps goal get/set must exist")
require("fun distanceGoalMeters()" in goal_prefs and "fun setDistanceGoalMeters(" in goal_prefs, "Distance goal get/set must exist")
require("fun activeMinutesGoal()" in goal_prefs and "fun setActiveMinutesGoal(" in goal_prefs, "Active minutes goal get/set must exist")
require("fun caloriesGoalKcal()" in goal_prefs and "fun setCaloriesGoalKcal(" in goal_prefs, "Calories goal get/set must exist")
require("val goalPrefs: GoalPrefs by lazy" in app_container, "AppContainer must host a shared GoalPrefs instance")

# ---------------------------------------------------------------------------
# 6. Settings goal steppers wired end-to-end
# ---------------------------------------------------------------------------
require("fun setStepsGoal(value: Long)" in dashboard_vm, "DashboardViewModel must expose setStepsGoal")
require("GoalStepperRow" in shell, "FinalBitLutShell must render the goal stepper rows")
require("onStepsGoalChanged" in main_activity, "MainActivity must wire onStepsGoalChanged through to DashboardViewModel")
require("dashboardViewModel.setStepsGoal(value)" in main_activity, "MainActivity must call DashboardViewModel.setStepsGoal")
require("GoalPrefs.STEPS_GOAL_RANGE" in shell, "Goal steppers must clamp to GoalPrefs' defined ranges")

# ---------------------------------------------------------------------------
# 7. Onboarding
# ---------------------------------------------------------------------------
require("class OnboardingPrefs" in onboarding_prefs, "OnboardingPrefs must exist")
require("fun hasSeenPermissionsRationale()" in onboarding_prefs, "hasSeenPermissionsRationale() must exist")
require("PermissionsOnboardingScreen" in shell, "PermissionsOnboardingScreen composable must exist")
require("wrappedOnRequestGoogle" in shell, "FinalBitLutShell must wrap onRequestGoogle to show onboarding first")
require("onboardingPrefs.markPermissionsRationaleSeen()" in main_activity, "MainActivity must persist that onboarding was seen")

# ---------------------------------------------------------------------------
# Insights UI rendered on Summary (per explicit product decision: a card
# block under the core metrics, not a separate tab)
# ---------------------------------------------------------------------------
require("WeeklyComparisonCard" in shell, "WeeklyComparisonCard must exist")
require("PersonalRecordsCard" in shell, "PersonalRecordsCard must exist")
require("StreakCard" in shell, "StreakCard must exist")
require("state.weekComparison" in shell, "SummaryScreen must render the week comparison when available")

# ---------------------------------------------------------------------------
# String resource parity between locales (except intentional EN one/other vs
# RU one/few/many plural forms for the streak string)
# ---------------------------------------------------------------------------
import re

def extract_keys(src):
    return set(re.findall(r'<string name="([a-z0-9_]+)"', src))

en_keys = extract_keys(strings_en)
ru_keys = extract_keys(strings_ru)
en_only_expected = {"insights_streak_days_one", "insights_streak_days_other"}
ru_only_expected = {"insights_streak_days_ru_one", "insights_streak_days_ru_few", "insights_streak_days_ru_many"}

unexpected_en_only = (en_keys - ru_keys) - en_only_expected
unexpected_ru_only = (ru_keys - en_keys) - ru_only_expected

require(len(unexpected_en_only) == 0, f"Strings missing from Russian locale: {sorted(unexpected_en_only)}")
require(len(unexpected_ru_only) == 0, f"Strings missing from English locale: {sorted(unexpected_ru_only)}")
require("insights_streak_days_ru_one" in ru_keys, "Russian streak string must use proper one/few/many plural forms")

if errors:
    print("Sprint 4 + 7 verification failed:")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("Sprint 4 + 7 (insights, notifications, goals, onboarding) verification passed.")
