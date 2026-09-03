#!/usr/bin/env python3
"""
patch_scaling_roadmap_2026_09_03_v1.py

Adds docs/SCALING_ROADMAP.md (new file) -- the durable reference for
lifting BitLut's Huawei Health Kit 100-user test-phase cap, researched
against Huawei's current (2026) developer documentation. Updates
sync.md, docs/HEALTH_DATA_PERMISSION_MATRIX.md, docs/BACKLOG.md,
CONTEXT.md, CLAUDE.md, SESSION_HANDOFF.md, and CHANGELOG.md to point to
it and to correct one factual error found during research.

Findings this patch documents:

1. The 100-user cap and the Huawei data-scope tier are separate gates.
   Lifting the cap is Huawei's "Applying for Verification" step --
   reachable on the existing individual developer account, no new scopes,
   ~15 working day review, no cost beyond developer time.

2. HEALTHKIT_CALORIES_READ has never been requested by BitLut. Its
   scope array (HuaweiHealthManager.kt) is Step/Distance/Activity/
   ActivityRecord/HistoryWeek only. Calories are a distinct OAuth scope,
   not a field bundled into those five. Huawei's own documentation
   places calories (and separately, height/weight) in the unrestricted,
   quickly-approved Basic tier -- reachable without an Enterprise
   account, distinct from the manually-reviewed tier (heart rate, blood
   pressure, blood glucose, SpO2) and the individual-developer-closed
   Advanced tier (sleep, stress).

3. Correction: sync.md section 4.11 and
   docs/HEALTH_DATA_PERMISSION_MATRIX.md previously described Huawei
   activeCalories/ActiveCaloriesBurnedRecord as permanently blocked,
   conflating it with the genuinely permanent Advanced-tier ceiling.
   sync.md section 3.2 itself already correctly lists active calories as
   part of the individual-developer-reachable activity tier -- the 50005
   error is fully explained by the scope never having been requested.
   Both documents corrected here. No source code is touched by this
   correction: WorkoutCalorieEstimator remains in place and in use, and
   both existing call sites already prefer real Huawei data over the
   estimate via a plain ?: fallback, so requesting the real scope later
   needs no code restructuring.

No Kotlin/XML/Gradle source is touched by this patch; documentation only.

Mandatory workflow already completed before this script was written:
hand-edited a mirror -> real diff (diff -u against the baseline tree,
which itself reflects patch_doc_sync_2026_09_02_v1.py already applied)
-> this script generated from that diff -> tested on a clean extraction
with a fake gradlew -> byte-diffed against the mirror -> re-run for
idempotency.
"""
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
BACKUP_DIR = REPO_ROOT / ".bitlut_patch_backup"

SYNC_FILE = REPO_ROOT / "sync.md"
PERMISSION_MATRIX_FILE = REPO_ROOT / "docs" / "HEALTH_DATA_PERMISSION_MATRIX.md"
BACKLOG_FILE = REPO_ROOT / "docs" / "BACKLOG.md"
CONTEXT_FILE = REPO_ROOT / "CONTEXT.md"
CLAUDE_FILE = REPO_ROOT / "CLAUDE.md"
HANDOFF_FILE = REPO_ROOT / "SESSION_HANDOFF.md"
CHANGELOG_FILE = REPO_ROOT / "CHANGELOG.md"
ROADMAP_FILE = REPO_ROOT / "docs" / "SCALING_ROADMAP.md"

ROADMAP_CONTENT = '# BitLut Scaling Roadmap\n\nUpdated: 2026-09-03\n\nGoal: remove the Huawei Health Kit 100-user test-phase cap. Secondary,\nlower-priority goal: add any Basic-tier Huawei scope that is genuinely\nreachable without becoming a Huawei Enterprise developer.\n\nThis document is the durable reference for that effort, the way `sync.md`\nis for the sync pipeline. Sources are Huawei\'s own current documentation,\nchecked August/September 2026; each claim below is linked to where it came\nfrom so it can be re-verified if Huawei\'s policy changes.\n\n## 1. The two constraints are separate problems\n\nIt\'s easy to conflate "more users" with "more data," because both are\ngated by the same Huawei Health Kit console. They are not the same gate,\nhave different requirements, and (per current docs) resolving one has no\neffect on the other.\n\n| | 100-user cap | Data scope tier |\n|---|---|---|\n| What it limits | How many real users can authorize the app | Which Huawei data categories the app can request at all |\n| Current status | Active — BitLut is still in the test phase | Basic tier only: steps, distance, floors, elevation, activity/workout records |\n| Fix | Submit Huawei\'s "Applying for Verification" request | Structural: Advanced tier (sleep, heart rate, SpO2, stress, blood pressure, blood glucose) is closed to individual developers, full stop |\n| Requires Enterprise? | No | Yes, for Advanced. No, for any *additional Basic-tier* scope BitLut hasn\'t requested yet (see section 3) |\n| Cost | Free; developer time only | Free to request; Advanced is unreachable at any price without incorporating a company with ≥CNY 5,000,000 paid-up capital |\n\n## 2. Lifting the 100-user cap — the actual goal, and it\'s reachable now\n\nHuawei\'s own Health Service Kit integration-process documentation\ndescribes a distinct "Applying for Verification" step, separate from the\noriginal Health Kit scope application:\n\n> "After the development and testing of your app or plugin are completed,\n> you can perform this step to remove the limit on the number of trial\n> users and put your app or plugin into large-scale commercial use...\n> Video and required document checklists need to be submitted for the\n> review, which usually takes 15 working days."\n\nSource: [Health Service Kit — Access Process](https://developer.huawei.com/consumer/en/doc/hmscore-guides/access-process-0000001624467736) (Huawei Developers, last updated 2026-05-13).\n\nKey facts about this step:\n\n- **No enterprise account needed.** Nothing in the Verification requirements\n  is gated on developer type; an individual developer account can submit it.\n- **No new scopes needed.** This lifts the *user-count* limit on the scopes\n  BitLut already holds. It does not grant access to any new data category.\n- **Cost is developer time, not money.** Preparing the video proof and\n  checklists is the only real cost.\n- **Turnaround is ~15 working days** per Huawei\'s own stated review time.\n\n### What Huawei\'s checklist is understood to expect\n\n(Cross-referenced against `docs/HUAWEI_PRODUCTION_REVIEW_PACKAGE.md`,\nwhich already documents BitLut\'s production-readiness checklist for\nAppGallery review — the same evidence largely overlaps.)\n\n- A working, published AppGallery release.\n- A real-device video demonstrating the full data flow: Huawei Health ->\n  BitLut -> Health Connect -> a third-party reader actually displaying the\n  synced data (BitLut has a concrete, confirmed example of this now: the\n  corporate wellness app import, `sync.md` section 4.6).\n- Confirmation that the app does not fabricate health data outside its one\n  documented, narrow exception (the MET-formula calorie estimate,\n  `sync.md` section 4.11 / `docs/HEALTH_DATA_PERMISSION_MATRIX.md`).\n- Good developer account standing (no adverse credit records — already a\n  stated individual-developer qualification requirement independent of\n  this step).\n\n### Action items\n\n1. Re-read `docs/HUAWEI_PRODUCTION_REVIEW_PACKAGE.md`, "Qualifications\n   Requirements for Developers," and "FAQs About Applications Being\n   Rejected" on Huawei Developers before submitting — Huawei\'s own docs\n   call these out as required pre-reads for this step.\n2. Record the real-device demo video: Huawei Health authorization -> a\n   fresh sync -> the resulting workout/steps/distance appearing correctly\n   in Health Connect -> a third-party app (e.g. the corporate wellness app,\n   or any Health-Connect-reading app) importing it.\n3. Submit the Verification request through the Huawei Developers console\n   under the Health Service Kit section.\n4. Track the review (~15 working days). No code changes are required for\n   this step by itself.\n\n## 3. Scope expansion without Enterprise — one concrete, low-risk candidate found\n\nThe individual-developer scope ceiling (`sync.md` section 3.2) correctly\nstates the reachable tier is: **steps, distance, floors, elevation, active\ncalories, and exercise/workout records.** BitLut\'s current scope request\n(`HuaweiHealthManager.kt`) is only five of those:\n\n```\nHEALTHKIT_STEP_READ\nHEALTHKIT_DISTANCE_READ\nHEALTHKIT_ACTIVITY_READ\nHEALTHKIT_ACTIVITY_RECORD_READ\nHEALTHKIT_HISTORYDATA_OPEN_WEEK\n```\n\n**`HEALTHKIT_CALORIES_READ` (`https://www.huawei.com/healthkit/calories.read`)\nhas never been requested.** Calories are a distinct OAuth scope from\nactivity/steps/distance, not a field bundled into the scopes above.\n`sync.md` section 4.11 previously described `activeCalories` as "not\nexpected to ever be approved," treating it as if it were part of the same\npermanently-closed Advanced tier as sleep/heart rate — this was a\nmisreading of the observed 50005 error, corrected in this update (see\nsection 4). Huawei\'s own documentation and multiple independent developer\nwrite-ups consistently place calories (and separately, height/weight) in\nthe same unrestricted, quickly-approved bucket as steps/distance/activity\n-- distinct from the manually-reviewed bucket (heart rate, blood pressure,\nblood glucose, SpO2) and the individual-developer-closed Advanced bucket\n(sleep, stress):\n\n> "In the demo, the height and weight data are applied for, which are\n> unrestricted data and will be quickly approved after your application is\n> submitted. If you want to apply for restricted data scopes such as heart\n> rate, blood pressure, blood glucose, and blood oxygen saturation, your\n> application will be manually reviewed."\n\nSource: [Turn Your App into a Handy Health Assistant](https://dev.to/hmosdevelopers/turn-your-app-into-a-handy-health-assistant-3d23) (Huawei HMS Core developer community); consistent with [Qualifications Requirements for Developers](https://developer.huawei.com/consumer/en/doc/atomic-guides-V5/health-application-qualifications-as-V5) (Huawei Developers).\n\n### What this would fix\n\nReal per-workout active-calorie data, currently unavailable, causing\n`WorkoutCalorieEstimator`\'s MET-formula estimate to be the only calorie\nfigure BitLut can write (`sync.md` section 4.11). Both call sites\n(`GoogleHealthManager.kt`, `FinalBitLutShell.kt`) already prefer real\nHuawei data over the estimate wherever it\'s present, via a plain `?:`\nfallback — so adding this scope requires **no code restructuring**, only\nadding the scope to the request array and requesting it through the\nHuawei console alongside the existing five.\n\n### What is NOT recommended\n\n- **`HEALTHKIT_HEIGHTWEIGHT_READ`** — also Basic-tier and quickly\n  approved, but BitLut has no feature that uses height/weight (no BMI or\n  body-composition display). Adding an unused scope has no product benefit\n  and adds an unnecessary permission surface. Not recommended unless a\n  future feature actually needs it.\n- **Any restricted-but-technically-Basic scope requiring manual review**\n  (none identified beyond calories/height-weight in the Basic tier) — no\n  evidence found of another such scope relevant to BitLut\'s feature set.\n- **Anything in the Advanced tier** — sleep, heart rate, SpO2, stress,\n  blood pressure, blood glucose remain structurally closed to individual\n  developers regardless of app quality or review history. This is not a\n  bar that can be cleared by asking again; see section 4.\n\n### Unresolved / to verify before submitting\n\n- **Console mechanics**: whether adding a new scope requires resubmitting\n  the whole Health Kit application (all 6 scopes as a single new\n  application/review) or can be added incrementally to the existing\n  approved application without disturbing the 5 already-granted scopes.\n  Not confirmed in Huawei\'s docs found so far; treat as unverified and\n  check the Huawei Developers console directly, or ask Huawei support,\n  before submitting.\n- Whether adding a scope resets or otherwise interacts with the AppGallery\n  Verification request in section 2 — if both are being pursued in the\n  same window, doing the scope-add first (and letting Huawei approve it)\n  before submitting Verification is the more conservative order, so the\n  Verification video/checklist reflects the final, complete scope set.\n\n## 4. Correction made to project docs in this pass\n\n`sync.md` section 4.11 and `docs/HEALTH_DATA_PERMISSION_MATRIX.md`\npreviously stated or implied that Huawei\'s `activeCalories`/\n`ActiveCaloriesBurnedRecord` data was permanently blocked for this\nindividual-developer account, in the same category as the Advanced-tier\nceiling (sleep/heart rate/SpO2/stress). This was incorrect: `sync.md`\nsection 3.2 itself already correctly lists "active calories" as part of\nthe individual-developer-reachable activity tier. The 50005 error\nobserved for `activeCalories` reads (section 3.3) is explained simply by\nthe scope never having been requested (section 3 above) — not by a\nplatform-level ceiling. Both documents corrected in this update; the MET\nestimate remains in place and in use until/unless the real scope is\nrequested and approved.\n\n## 5. What does NOT change\n\n- **Advanced-tier categories remain permanently out of reach** without\n  incorporating an enterprise entity with ≥CNY 5,000,000 paid-up capital —\n  this is unchanged, and not something this roadmap recommends pursuing\n  given BitLut\'s scope and business model. Huawei does support converting\n  an existing individual account to enterprise later if this ever becomes\n  relevant, so nothing done in sections 2-3 forecloses that option.\n- **Historical sync window (7 days)** and **no-fabricated-data** rules are\n  unaffected by anything in this roadmap and remain in force.\n- **No advanced-category code paths** — this standing project rule is\n  correct and stays in force; this roadmap does not change it.\n\n## Sources\n\n- [Health Service Kit — Access Process](https://developer.huawei.com/consumer/en/doc/hmscore-guides/access-process-0000001624467736) — Verification step, 15-workday review, large-scale commercial use. Last updated 2026-05-13.\n- [Qualifications Requirements for Developers](https://developer.huawei.com/consumer/en/doc/atomic-guides-V5/health-application-qualifications-as-V5) — individual vs. enterprise requirements; Advanced tier closed to individual developers. Last updated 2024-11-21 (content re-confirmed current as of this search).\n- [Turn Your App into a Handy Health Assistant](https://dev.to/hmosdevelopers/turn-your-app-into-a-handy-health-assistant-3d23) — height/weight and (by the same pattern) calories as unrestricted, quickly-approved Basic data vs. manually-reviewed restricted data.\n- `HEALTHKIT_CALORIES_READ` scope identifier (`https://www.huawei.com/healthkit/calories.read`) — Huawei Health Kit `Scopes` class, cross-referenced via the `huawei_health` Flutter plugin\'s published API docs (same underlying native scope constants).\n'


def die(message: str) -> None:
    print(f"FATAL: {message}", file=sys.stderr)
    sys.exit(1)


def backup(path: Path) -> None:
    if not path.exists():
        die(f"Cannot back up missing file: {path}")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    rel = path.relative_to(REPO_ROOT)
    dest = BACKUP_DIR / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        shutil.copy2(path, dest)


def apply_edit(path: Path, old: str, new: str, expected_old_count: int, expected_new_count: int, description: str) -> None:
    """Genuine replacement. Idempotent via exact old_str occurrence count."""
    text = path.read_text(encoding="utf-8")
    old_count = text.count(old)
    new_count = text.count(new)

    if old_count == 0 and new_count >= expected_new_count:
        print(f"  [skip] {description} (already applied)")
        return

    if old_count != expected_old_count:
        die(
            f"{description}: expected {expected_old_count} occurrence(s) of anchor "
            f"in {path.name}, found {old_count}. Aborting -- source has diverged."
        )

    backup(path)
    text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")
    print(f"  [applied] {description}")


def apply_insertion(path: Path, anchor: str, new_with_anchor: str, unique_marker: str, description: str) -> None:
    """Pure insertion: anchor text itself is unchanged and still present after
    the edit, so idempotency cannot key on the anchor's occurrence count (it
    would still be found, as a substring of new_with_anchor, on every re-run).
    Keys instead on unique_marker, a string that only exists after this
    insertion has been applied.
    """
    text = path.read_text(encoding="utf-8")

    if unique_marker in text:
        print(f"  [skip] {description} (already applied)")
        return

    anchor_count = text.count(anchor)
    if anchor_count != 1:
        die(
            f"{description}: expected exactly 1 occurrence of anchor in {path.name}, "
            f"found {anchor_count}. Aborting -- source has diverged."
        )

    backup(path)
    text = text.replace(anchor, new_with_anchor)
    path.write_text(text, encoding="utf-8")
    print(f"  [applied] {description}")


def create_new_file(path: Path, content: str, description: str) -> None:
    """Idempotent creation of a brand-new file. Skips if the file already
    exists with this exact content; aborts if it exists with different
    content (source has diverged from what this script expects)."""
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing == content:
            print(f"  [skip] {description} (already applied)")
            return
        die(
            f"{description}: {path.name} already exists with different content. "
            "Aborting -- source has diverged."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  [applied] {description}")


def run_compile_gate() -> None:
    gradlew = REPO_ROOT / "gradlew"
    if not gradlew.exists():
        die("gradlew not found; cannot run compile gate")

    cmd = [
        str(gradlew),
        ":app:compileDebugKotlin",
        "--no-daemon",
        "--max-workers=1",
        "--no-watch-fs",
        "--console=plain",
        "-Dorg.gradle.jvmargs=-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8",
        "-Pkotlin.compiler.execution.strategy=in-process",
    ]
    print("Running compile gate: " + " ".join(cmd))
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    if result.returncode != 0:
        die("Compile gate failed. No commit/push performed. See Gradle output above.")


def git_commit_and_push() -> None:
    subprocess.run(["git", "add", "-A"], cwd=REPO_ROOT, check=True)
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    )
    if not status.stdout.strip():
        print("Nothing to commit (already applied and clean).")
        return

    subprocess.run(
        [
            "git",
            "commit",
            "-m",
            "Docs: add scaling roadmap (100-user cap, calorie scope gap), "
            "correct activeCalories permanence claim",
        ],
        cwd=REPO_ROOT,
        check=True,
    )
    subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=REPO_ROOT, check=True)


def main() -> None:
    print("=== 1/7: docs/SCALING_ROADMAP.md (new file) ===")
    create_new_file(
        ROADMAP_FILE,
        ROADMAP_CONTENT,
        description="docs/SCALING_ROADMAP.md: create scaling roadmap doc",
    )

    print("=== 2/7: sync.md section 4.11 -- correct activeCalories permanence claim ===")
    apply_edit(
        SYNC_FILE,
        old=(
            "Real per-workout active-calorie data from Huawei is gated behind the\n"
            "`activeCalories` scope, which returns 50005 for this individual-developer\n"
            "account (and is not expected to ever be approved — see 3.2's ceiling). To\n"
            "give third-party readers *something* non-zero to import for a workout's\n"
            "total calories, `WorkoutCalorieEstimator.estimateTotalCaloriesKcal(exerciseType,\n"
        ),
        new=(
            "Real per-workout active-calorie data from Huawei requires the\n"
            "`HEALTHKIT_CALORIES_READ` scope, which BitLut has never requested (its\n"
            "current scope array is Step/Distance/Activity/ActivityRecord/HistoryWeek\n"
            "only — see `docs/SCALING_ROADMAP.md` section 3). This is why\n"
            "`activeCalories` reads return 50005: an unrequested scope, not a denied\n"
            "one. It is **not** part of the permanently-closed Advanced tier (3.2\n"
            "correctly lists active calories as part of the individual-developer-\n"
            "reachable activity tier) and is understood, per Huawei's own developer\n"
            "documentation, to be unrestricted, quickly-approved Basic-tier data — see\n"
            "`docs/SCALING_ROADMAP.md` for the request plan. Until that scope is\n"
            "requested and approved, to give third-party readers *something* non-zero\n"
            "to import for a workout's total calories,\n"
            "`WorkoutCalorieEstimator.estimateTotalCaloriesKcal(exerciseType,\n"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="sync.md: correct activeCalories permanence claim in 4.11",
    )

    print("=== 3/7: docs/HEALTH_DATA_PERMISSION_MATRIX.md -- two corrections ===")
    apply_edit(
        PERMISSION_MATRIX_FILE,
        old=(
            "- Huawei Health Kit application scope is approved; individual metric availability may still vary and must be handled independently.\n"
        ),
        new=(
            "- Huawei Health Kit application scope is approved for 5 of 6 reachable\n"
            "  Basic-tier categories; individual metric availability may still vary and\n"
            "  must be handled independently. `HEALTHKIT_CALORIES_READ` is the one\n"
            "  reachable-but-unrequested scope -- see `docs/SCALING_ROADMAP.md`.\n"
            "- The app is currently limited to 100 trial users under Huawei's Health\n"
            "  Kit test phase; lifting this is tracked in `docs/SCALING_ROADMAP.md`.\n"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="docs/HEALTH_DATA_PERMISSION_MATRIX.md: add scope-gap + 100-user-cap notes",
    )
    apply_edit(
        PERMISSION_MATRIX_FILE,
        old=(
            "- `TotalCaloriesBurnedRecord` is used specifically because it is a distinct\n"
            "  Health Connect data type from `ActiveCaloriesBurnedRecord` (Huawei's\n"
            "  permanently-blocked, sensor-measured category) -- this avoids conflating\n"
            "  an estimate with the exact record type users and other apps already\n"
            "  expect to mean \"measured by a real sensor.\"\n"
        ),
        new=(
            "- `TotalCaloriesBurnedRecord` is used specifically because it is a distinct\n"
            "  Health Connect data type from `ActiveCaloriesBurnedRecord` (Huawei's\n"
            "  active-calorie category, currently returning 50005 because BitLut has\n"
            "  never requested the `HEALTHKIT_CALORIES_READ` scope for it -- see\n"
            "  `docs/SCALING_ROADMAP.md` -- not because it is permanently blocked) --\n"
            "  this avoids conflating\n"
            "  an estimate with the exact record type users and other apps already\n"
            "  expect to mean \"measured by a real sensor.\"\n"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="docs/HEALTH_DATA_PERMISSION_MATRIX.md: correct permanently-blocked claim",
    )

    print("=== 4/7: docs/BACKLOG.md -- add scaling items as highest priority ===")
    apply_edit(
        BACKLOG_FILE,
        old=(
            "# BitLut Backlog\n"
            "\n"
            "Updated: 2026-09-02\n"
            "\n"
            "## Highest priority\n"
            "\n"
            "- Add focused unit tests for `HuaweiWorkoutTypeMapper` and workout metric selection.\n"
        ),
        new=(
            "# BitLut Backlog\n"
            "\n"
            "Updated: 2026-09-03\n"
            "\n"
            "## Highest priority\n"
            "\n"
            "- **Scaling: submit Huawei Health Kit Verification** to lift the 100-user test-phase cap -- the top current goal. See `docs/SCALING_ROADMAP.md` section 2 for the concrete action items (~15 working day review, no code changes required).\n"
            "- **Scaling: request `HEALTHKIT_CALORIES_READ`** scope for real per-workout active-calorie data -- Basic-tier, individual-developer-reachable, no Enterprise account needed. See `docs/SCALING_ROADMAP.md` section 3.\n"
            "- Add focused unit tests for `HuaweiWorkoutTypeMapper` and workout metric selection.\n"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="docs/BACKLOG.md: bump date, add scaling items",
    )

    print("=== 5/7: CONTEXT.md, CLAUDE.md, SESSION_HANDOFF.md -- pointers + dates ===")
    apply_edit(
        CONTEXT_FILE,
        old=(
            "Updated: 2026-09-02\n"
        ),
        new=(
            "Updated: 2026-09-03\n"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="CONTEXT.md: bump Updated date",
    )
    apply_edit(
        CONTEXT_FILE,
        old=(
            "`sync.md` is the durable technical reference for the full sync pipeline (why it's built the way it is); this file stays the short current-state summary.\n"
        ),
        new=(
            "`sync.md` is the durable technical reference for the full sync pipeline (why it's built the way it is); this file stays the short current-state summary. `docs/SCALING_ROADMAP.md` is the durable reference for lifting the 100-user Huawei test-phase cap and any reachable scope expansion -- this is the current top-priority goal.\n"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="CONTEXT.md: add SCALING_ROADMAP.md pointer",
    )
    apply_insertion(
        CLAUDE_FILE,
        anchor=(
            "Real-data rule: never fabricate missing metrics. The only approved exception is the existing workout total-calorie estimate used when Huawei supplies no workout calories; keep that exception isolated to `TotalCaloriesBurnedRecord`.\n"
        ),
        new_with_anchor=(
            "Real-data rule: never fabricate missing metrics. The only approved exception is the existing workout total-calorie estimate used when Huawei supplies no workout calories; keep that exception isolated to `TotalCaloriesBurnedRecord`.\n"
            "\n"
            "Current top-priority goal: lift the Huawei Health Kit 100-user test-phase cap, and add `HEALTHKIT_CALORIES_READ` if it can be done without an Enterprise account. See `docs/SCALING_ROADMAP.md` for the plan; do not add any Advanced-tier scope (sleep/heart rate/SpO2/stress) regardless -- that remains permanently closed to individual developers.\n"
        ),
        unique_marker="Current top-priority goal: lift the Huawei Health Kit 100-user test-phase cap",
        description="CLAUDE.md: add scaling top-priority-goal pointer",
    )
    apply_edit(
        HANDOFF_FILE,
        old=(
            "Current handoff date: 2026-09-02.\n"
        ),
        new=(
            "Current handoff date: 2026-09-03.\n"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="SESSION_HANDOFF.md: bump handoff date",
    )
    apply_insertion(
        HANDOFF_FILE,
        anchor=(
            "Scope is activity/workout data only. No account/backend. Do not fabricate missing metrics. The only documented exception is the existing workout total-calorie estimate used when Huawei provides no workout calories; do not extend that exception to distance, steps, elevation, heart data, sleep, etc.\n"
        ),
        new_with_anchor=(
            "Scope is activity/workout data only. No account/backend. Do not fabricate missing metrics. The only documented exception is the existing workout total-calorie estimate used when Huawei provides no workout calories; do not extend that exception to distance, steps, elevation, heart data, sleep, etc.\n"
            "\n"
            "## Current top-priority goal: scaling\n"
            "\n"
            "`docs/SCALING_ROADMAP.md` is the durable reference. Two separate tracks:\n"
            "\n"
            "1. **Lift the Huawei Health Kit 100-user test-phase cap** via Huawei's \"Applying for Verification\" step -- individual account, no new scopes, ~15 working day review. This is the actual current goal; start here.\n"
            "2. **Request `HEALTHKIT_CALORIES_READ`** -- a Basic-tier, individual-developer-reachable scope BitLut has never requested (its scope array is Step/Distance/Activity/ActivityRecord/HistoryWeek only). This would let real Huawei active-calorie data replace the `WorkoutCalorieEstimator` MET fallback wherever Huawei provides it; both call sites already prefer real data via `?:`, so no code restructuring is needed, only the scope addition + console request.\n"
            "\n"
            "Do not pursue Advanced-tier scopes (sleep/heart rate/SpO2/stress) — permanently closed to individual developers regardless of app quality or review history; the only path is incorporating an enterprise entity with ≥CNY 5,000,000 paid-up capital, which is out of scope for this project.\n"
        ),
        unique_marker="## Current top-priority goal: scaling",
        description="SESSION_HANDOFF.md: add scaling top-priority-goal section",
    )

    print("=== 6/7: CHANGELOG.md entry ===")
    apply_edit(
        CHANGELOG_FILE,
        old=(
            "# Changelog\n"
            "\n"
            "## 2026-09-02 -- documentation sync pass, repo root cleanup\n"
        ),
        new=(
            "# Changelog\n"
            "\n"
            "## 2026-09-03 -- scaling roadmap: 100-user cap, calorie scope gap\n"
            "\n"
            "- **New `docs/SCALING_ROADMAP.md`**, the durable reference for lifting the\n"
            "  Huawei Health Kit 100-user test-phase cap (the current top-priority\n"
            "  goal) and for the one Basic-tier scope BitLut hasn't requested yet.\n"
            "  Researched against Huawei's current (2026) developer documentation;\n"
            "  sources linked in the doc itself.\n"
            "- **Key finding: the 100-user cap and the data-scope tier are separate\n"
            "  gates.** Lifting the cap is Huawei's \"Applying for Verification\" step --\n"
            "  individual account, no new scopes, no cost beyond developer time, ~15\n"
            "  working day review. It does not require Enterprise status.\n"
            "- **Key finding: `HEALTHKIT_CALORIES_READ` has never been requested.**\n"
            "  BitLut's scope array (`HuaweiHealthManager.kt`) is Step/Distance/\n"
            "  Activity/ActivityRecord/HistoryWeek only. Calories are a separate OAuth\n"
            "  scope, not a field bundled into those five. Huawei's own documentation\n"
            "  places calories (and separately, height/weight) in the unrestricted,\n"
            "  quickly-approved Basic-tier bucket -- distinct from the manually-reviewed\n"
            "  bucket (heart rate, blood pressure, blood glucose, SpO2) and the\n"
            "  individual-developer-closed Advanced bucket (sleep, stress). This is\n"
            "  reachable without an Enterprise account.\n"
            "- **Correction: `sync.md` section 4.11 and\n"
            "  `docs/HEALTH_DATA_PERMISSION_MATRIX.md` previously described Huawei\n"
            "  `activeCalories`/`ActiveCaloriesBurnedRecord` as permanently blocked**,\n"
            "  conflating it with the genuinely permanent Advanced-tier ceiling\n"
            "  (sleep/heart rate/SpO2/stress). `sync.md` section 3.2 itself already\n"
            "  correctly listed active calories as part of the individual-developer-\n"
            "  reachable activity tier -- the 50005 error is fully explained by the\n"
            "  scope never having been requested, not by a platform-level block. Both\n"
            "  documents corrected; the MET-formula estimate (`WorkoutCalorieEstimator`)\n"
            "  remains in place and in use until/unless the real scope is requested and\n"
            "  approved. No code changed -- both existing call sites already prefer\n"
            "  real Huawei data over the estimate via a plain `?:` fallback, so adding\n"
            "  the scope later needs no restructuring.\n"
            "- `docs/BACKLOG.md`, `CONTEXT.md`, `CLAUDE.md`, and `SESSION_HANDOFF.md`\n"
            "  updated with pointers to `docs/SCALING_ROADMAP.md` and the two action\n"
            "  items (Verification submission, calorie-scope request) as current\n"
            "  highest priority.\n"
            "- Explicitly not recommended: `HEALTHKIT_HEIGHTWEIGHT_READ` (also\n"
            "  Basic-tier/quickly-approved, but BitLut has no feature that would use\n"
            "  it) and anything in the Advanced tier (still permanently closed to\n"
            "  individual developers; the only path is incorporating an enterprise\n"
            "  entity with >= CNY 5,000,000 paid-up capital, out of scope for this\n"
            "  project).\n"
            "\n"
            "## 2026-09-02 -- documentation sync pass, repo root cleanup\n"
        ),
        expected_old_count=1,
        expected_new_count=1,
        description="CHANGELOG.md: add 2026-09-03 scaling roadmap entry",
    )

    print("=== 7/7: Running compile gate (no source touched; expected no-op) ===")
    run_compile_gate()

    print("=== Compile gate passed. Committing and pushing. ===")
    git_commit_and_push()

    print("Done.")


if __name__ == "__main__":
    main()
