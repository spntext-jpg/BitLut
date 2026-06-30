#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(".")
errors = []
app_build = (ROOT / "app/build.gradle.kts").read_text(encoding="utf-8") if (ROOT / "app/build.gradle.kts").exists() else ""
manifest = (ROOT / "app/src/main/AndroidManifest.xml").read_text(encoding="utf-8") if (ROOT / "app/src/main/AndroidManifest.xml").exists() else ""
main = (ROOT / "app/src/main/java/com/openhealth/sync/MainActivity.kt").read_text(encoding="utf-8") if (ROOT / "app/src/main/java/com/openhealth/sync/MainActivity.kt").exists() else ""
orchestrator = (ROOT / "app/src/main/java/com/openhealth/sync/domain/SyncOrchestrator.kt").read_text(encoding="utf-8") if (ROOT / "app/src/main/java/com/openhealth/sync/domain/SyncOrchestrator.kt").exists() else ""
google = (ROOT / "app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt").read_text(encoding="utf-8") if (ROOT / "app/src/main/java/com/openhealth/sync/data/GoogleHealthManager.kt").exists() else ""
huawei = (ROOT / "app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt").read_text(encoding="utf-8") if (ROOT / "app/src/main/java/com/openhealth/sync/data/HuaweiHealthManager.kt").exists() else ""
policy = (ROOT / "app/src/main/java/com/openhealth/sync/config/HealthPermissionPolicy.kt").read_text(encoding="utf-8") if (ROOT / "app/src/main/java/com/openhealth/sync/config/HealthPermissionPolicy.kt").exists() else ""
ui_shell = (ROOT / "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt").read_text(encoding="utf-8") if (ROOT / "app/src/main/java/com/openhealth/sync/ui/screens/FinalBitLutShell.kt").exists() else ""
glass_nav = (ROOT / "app/src/main/java/com/openhealth/sync/ui/components/GlassNavigation.kt").read_text(encoding="utf-8") if (ROOT / "app/src/main/java/com/openhealth/sync/ui/components/GlassNavigation.kt").exists() else ""
glass_cards = (ROOT / "app/src/main/java/com/openhealth/sync/ui/components/GlassCards.kt").read_text(encoding="utf-8") if (ROOT / "app/src/main/java/com/openhealth/sync/ui/components/GlassCards.kt").exists() else ""
metric_charts = (ROOT / "app/src/main/java/com/openhealth/sync/ui/components/MetricCharts.kt").read_text(encoding="utf-8") if (ROOT / "app/src/main/java/com/openhealth/sync/ui/components/MetricCharts.kt").exists() else ""
release_doc = (ROOT / "docs/release-1.9.9.md").read_text(encoding="utf-8") if (ROOT / "docs/release-1.9.9.md").exists() else ""
readme = (ROOT / "README.md").read_text(encoding="utf-8") if (ROOT / "README.md").exists() else ""
context = (ROOT / "CONTEXT.md").read_text(encoding="utf-8") if (ROOT / "CONTEXT.md").exists() else ""
workflow_files = list((ROOT / ".github/workflows").glob("*.yml")) + list((ROOT / ".github/workflows").glob("*.yaml")) if (ROOT / ".github/workflows").exists() else []
workflow_text = "\n".join([p.read_text(encoding="utf-8") for p in workflow_files])
all_health_sources = "\n".join([manifest, google, huawei, policy])
all_ui_sources = "\n".join([ui_shell, glass_nav, glass_cards, metric_charts])
errors.append("Gradle app version fields should exist, but are workflow-owned") if not ("versionName" in app_build or "versionCode" in app_build) else None
errors.append("GitHub Actions workflows must exist for release builds") if not workflow_text.strip() else None
errors.append("Workflow should contain Gradle release/build step") if not ("gradlew" in workflow_text or "assembleRelease" in workflow_text or "bundleRelease" in workflow_text) else None
errors.append("SyncOrchestrator must exist") if "class SyncOrchestrator" not in orchestrator else None
errors.append("MainActivity must create/use SyncOrchestrator") if "SyncOrchestrator(" not in main else None
errors.append("MainActivity must not directly orchestrate WorkManager") if "WorkManager.getInstance" in main else None
errors.append("MainActivity must not directly enqueue sync") if "BackgroundSyncScheduler.enqueueImmediateSync" in main else None
errors.append("MainActivity must not directly schedule periodic sync") if "BackgroundSyncScheduler.schedulePeriodic" in main else None
errors.append("MainActivity must use lifecycle-aware state collection") if "collectAsStateWithLifecycle" not in main else None
errors.append("GlassNavigation.kt must define Glass20BottomNavigation") if "internal fun Glass20BottomNavigation(" not in glass_nav else None
errors.append("GlassNavigation.kt must define Glass20NavButton") if "private fun Glass20NavButton(" not in glass_nav else None
errors.append("GlassCards.kt must define SoftCard") if "internal fun SoftCard(" not in glass_cards else None
errors.append("MetricCharts.kt must define MetricBarChartCard") if "internal fun MetricBarChartCard(" not in metric_charts else None
errors.append("MetricCharts must be compile-safe after MetricBar removal") if "bars: List<Any?>" not in metric_charts else None
errors.append("Metric bars must keep minimum visible height") if "defaultMinSize(minHeight = 6.dp)" not in metric_charts else None
errors.append("Metric bar drawing area must be bounded") if ".height(84.dp)" not in metric_charts else None
errors.append("Metric chart row must reserve stable vertical space") if ".height(132.dp)" not in metric_charts else None
errors.append("Material NavigationBarItem must not remain") if "NavigationBarItem(" in all_ui_sources else None
errors.append("Material NavigationBar must not remain") if "NavigationBar(" in all_ui_sources else None
[errors.append(f"Forbidden non-activity health scope remains: {x}") for x in ["SleepSessionRecord","HeartRateRecord","OxygenSaturationRecord","HeartRateVariabilityRmssdRecord","RestingHeartRateRecord","RespiratoryRateRecord","BodyTemperatureRecord","BloodPressureRecord","READ_SLEEP","WRITE_SLEEP","READ_HEART_RATE","WRITE_HEART_RATE","READ_OXYGEN_SATURATION","WRITE_OXYGEN_SATURATION","READ_HEART_RATE_VARIABILITY","WRITE_HEART_RATE_VARIABILITY","READ_RESTING_HEART_RATE","WRITE_RESTING_HEART_RATE","READ_RESPIRATORY_RATE","WRITE_RESPIRATORY_RATE"] if x in all_health_sources]
[errors.append(f"Required activity Health Connect record missing: {x}") for x in ["StepsRecord","DistanceRecord","FloorsClimbedRecord","ElevationGainedRecord","ActiveCaloriesBurnedRecord","ExerciseSessionRecord"] if x not in all_health_sources]
errors.append("Release doc missing 1.9.9 heading") if "# BitLut 1.9.9 Release Readiness" not in release_doc else None
errors.append("Release doc must state version is workflow-owned") if "intentionally does not modify `versionName` or `versionCode`" not in release_doc else None
errors.append("README missing v1.9.9 release-readiness note") if "## v1.9.9 release-readiness sprint" not in readme else None
errors.append("CONTEXT missing v1.9.9 release-readiness note") if "## v1.9.9 release-readiness sprint" not in context else None
print("BitLut 1.9.9 release-readiness verification failed:") if errors else print("BitLut 1.9.9 release-readiness verification passed.")
[print(" -", e) for e in errors]
sys.exit(1 if errors else 0)
