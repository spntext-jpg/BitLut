# BitLut Scaling Roadmap

Updated: 2026-09-03

Goal: remove the Huawei Health Kit 100-user test-phase cap. Secondary,
lower-priority goal: add any Basic-tier Huawei scope that is genuinely
reachable without becoming a Huawei Enterprise developer.

This document is the durable reference for that effort, the way `sync.md`
is for the sync pipeline. Sources are Huawei's own current documentation,
checked August/September 2026; each claim below is linked to where it came
from so it can be re-verified if Huawei's policy changes.

## 1. The two constraints are separate problems

It's easy to conflate "more users" with "more data," because both are
gated by the same Huawei Health Kit console. They are not the same gate,
have different requirements, and (per current docs) resolving one has no
effect on the other.

| | 100-user cap | Data scope tier |
|---|---|---|
| What it limits | How many real users can authorize the app | Which Huawei data categories the app can request at all |
| Current status | Active — BitLut is still in the test phase | Basic tier only: steps, distance, floors, elevation, activity/workout records |
| Fix | Submit Huawei's "Applying for Verification" request | Structural: Advanced tier (sleep, heart rate, SpO2, stress, blood pressure, blood glucose) is closed to individual developers, full stop |
| Requires Enterprise? | No | Yes, for Advanced. No, for any *additional Basic-tier* scope BitLut hasn't requested yet (see section 3) |
| Cost | Free; developer time only | Free to request; Advanced is unreachable at any price without incorporating a company with ≥CNY 5,000,000 paid-up capital |

## 2. Lifting the 100-user cap — the actual goal, and it's reachable now

Huawei's own Health Service Kit integration-process documentation
describes a distinct "Applying for Verification" step, separate from the
original Health Kit scope application:

> "After the development and testing of your app or plugin are completed,
> you can perform this step to remove the limit on the number of trial
> users and put your app or plugin into large-scale commercial use...
> Video and required document checklists need to be submitted for the
> review, which usually takes 15 working days."

Source: [Health Service Kit — Access Process](https://developer.huawei.com/consumer/en/doc/hmscore-guides/access-process-0000001624467736) (Huawei Developers, last updated 2026-05-13).

Key facts about this step:

- **No enterprise account needed.** Nothing in the Verification requirements
  is gated on developer type; an individual developer account can submit it.
- **No new scopes needed.** This lifts the *user-count* limit on the scopes
  BitLut already holds. It does not grant access to any new data category.
- **Cost is developer time, not money.** Preparing the video proof and
  checklists is the only real cost.
- **Turnaround is ~15 working days** per Huawei's own stated review time.

### What Huawei's checklist is understood to expect

(Cross-referenced against `docs/HUAWEI_PRODUCTION_REVIEW_PACKAGE.md`,
which already documents BitLut's production-readiness checklist for
AppGallery review — the same evidence largely overlaps.)

- A working, published AppGallery release.
- A real-device video demonstrating the full data flow: Huawei Health ->
  BitLut -> Health Connect -> a third-party reader actually displaying the
  synced data (BitLut has a concrete, confirmed example of this now: the
  corporate wellness app import, `sync.md` section 4.6).
- Confirmation that the app does not fabricate health data outside its one
  documented, narrow exception (the MET-formula calorie estimate,
  `sync.md` section 4.11 / `docs/HEALTH_DATA_PERMISSION_MATRIX.md`).
- Good developer account standing (no adverse credit records — already a
  stated individual-developer qualification requirement independent of
  this step).

### Action items

1. Re-read `docs/HUAWEI_PRODUCTION_REVIEW_PACKAGE.md`, "Qualifications
   Requirements for Developers," and "FAQs About Applications Being
   Rejected" on Huawei Developers before submitting — Huawei's own docs
   call these out as required pre-reads for this step.
2. Record the real-device demo video: Huawei Health authorization -> a
   fresh sync -> the resulting workout/steps/distance appearing correctly
   in Health Connect -> a third-party app (e.g. the corporate wellness app,
   or any Health-Connect-reading app) importing it.
3. Submit the Verification request through the Huawei Developers console
   under the Health Service Kit section.
4. Track the review (~15 working days). No code changes are required for
   this step by itself.

## 3. Scope expansion without Enterprise — one concrete, low-risk candidate found

The individual-developer scope ceiling (`sync.md` section 3.2) correctly
states the reachable tier is: **steps, distance, floors, elevation, active
calories, and exercise/workout records.** BitLut's current scope request
(`HuaweiHealthManager.kt`) is only five of those:

```
HEALTHKIT_STEP_READ
HEALTHKIT_DISTANCE_READ
HEALTHKIT_ACTIVITY_READ
HEALTHKIT_ACTIVITY_RECORD_READ
HEALTHKIT_HISTORYDATA_OPEN_WEEK
```

**`HEALTHKIT_CALORIES_READ` (`https://www.huawei.com/healthkit/calories.read`)
has never been requested.** Calories are a distinct OAuth scope from
activity/steps/distance, not a field bundled into the scopes above.
`sync.md` section 4.11 previously described `activeCalories` as "not
expected to ever be approved," treating it as if it were part of the same
permanently-closed Advanced tier as sleep/heart rate — this was a
misreading of the observed 50005 error, corrected in this update (see
section 4). Huawei's own documentation and multiple independent developer
write-ups consistently place calories (and separately, height/weight) in
the same unrestricted, quickly-approved bucket as steps/distance/activity
-- distinct from the manually-reviewed bucket (heart rate, blood pressure,
blood glucose, SpO2) and the individual-developer-closed Advanced bucket
(sleep, stress):

> "In the demo, the height and weight data are applied for, which are
> unrestricted data and will be quickly approved after your application is
> submitted. If you want to apply for restricted data scopes such as heart
> rate, blood pressure, blood glucose, and blood oxygen saturation, your
> application will be manually reviewed."

Source: [Turn Your App into a Handy Health Assistant](https://dev.to/hmosdevelopers/turn-your-app-into-a-handy-health-assistant-3d23) (Huawei HMS Core developer community); consistent with [Qualifications Requirements for Developers](https://developer.huawei.com/consumer/en/doc/atomic-guides-V5/health-application-qualifications-as-V5) (Huawei Developers).

### What this would fix

Real per-workout active-calorie data, currently unavailable, causing
`WorkoutCalorieEstimator`'s MET-formula estimate to be the only calorie
figure BitLut can write (`sync.md` section 4.11). Both call sites
(`GoogleHealthManager.kt`, `FinalBitLutShell.kt`) already prefer real
Huawei data over the estimate wherever it's present, via a plain `?:`
fallback — so adding this scope requires **no code restructuring**, only
adding the scope to the request array and requesting it through the
Huawei console alongside the existing five.

### What is NOT recommended

- **`HEALTHKIT_HEIGHTWEIGHT_READ`** — also Basic-tier and quickly
  approved, but BitLut has no feature that uses height/weight (no BMI or
  body-composition display). Adding an unused scope has no product benefit
  and adds an unnecessary permission surface. Not recommended unless a
  future feature actually needs it.
- **Any restricted-but-technically-Basic scope requiring manual review**
  (none identified beyond calories/height-weight in the Basic tier) — no
  evidence found of another such scope relevant to BitLut's feature set.
- **Anything in the Advanced tier** — sleep, heart rate, SpO2, stress,
  blood pressure, blood glucose remain structurally closed to individual
  developers regardless of app quality or review history. This is not a
  bar that can be cleared by asking again; see section 4.

### Unresolved / to verify before submitting

- **Console mechanics**: whether adding a new scope requires resubmitting
  the whole Health Kit application (all 6 scopes as a single new
  application/review) or can be added incrementally to the existing
  approved application without disturbing the 5 already-granted scopes.
  Not confirmed in Huawei's docs found so far; treat as unverified and
  check the Huawei Developers console directly, or ask Huawei support,
  before submitting.
- Whether adding a scope resets or otherwise interacts with the AppGallery
  Verification request in section 2 — if both are being pursued in the
  same window, doing the scope-add first (and letting Huawei approve it)
  before submitting Verification is the more conservative order, so the
  Verification video/checklist reflects the final, complete scope set.

## 4. Correction made to project docs in this pass

`sync.md` section 4.11 and `docs/HEALTH_DATA_PERMISSION_MATRIX.md`
previously stated or implied that Huawei's `activeCalories`/
`ActiveCaloriesBurnedRecord` data was permanently blocked for this
individual-developer account, in the same category as the Advanced-tier
ceiling (sleep/heart rate/SpO2/stress). This was incorrect: `sync.md`
section 3.2 itself already correctly lists "active calories" as part of
the individual-developer-reachable activity tier. The 50005 error
observed for `activeCalories` reads (section 3.3) is explained simply by
the scope never having been requested (section 3 above) — not by a
platform-level ceiling. Both documents corrected in this update; the MET
estimate remains in place and in use until/unless the real scope is
requested and approved.

## 5. What does NOT change

- **Advanced-tier categories remain permanently out of reach** without
  incorporating an enterprise entity with ≥CNY 5,000,000 paid-up capital —
  this is unchanged, and not something this roadmap recommends pursuing
  given BitLut's scope and business model. Huawei does support converting
  an existing individual account to enterprise later if this ever becomes
  relevant, so nothing done in sections 2-3 forecloses that option.
- **Historical sync window (7 days)** and **no-fabricated-data** rules are
  unaffected by anything in this roadmap and remain in force.
- **No advanced-category code paths** — this standing project rule is
  correct and stays in force; this roadmap does not change it.

## Sources

- [Health Service Kit — Access Process](https://developer.huawei.com/consumer/en/doc/hmscore-guides/access-process-0000001624467736) — Verification step, 15-workday review, large-scale commercial use. Last updated 2026-05-13.
- [Qualifications Requirements for Developers](https://developer.huawei.com/consumer/en/doc/atomic-guides-V5/health-application-qualifications-as-V5) — individual vs. enterprise requirements; Advanced tier closed to individual developers. Last updated 2024-11-21 (content re-confirmed current as of this search).
- [Turn Your App into a Handy Health Assistant](https://dev.to/hmosdevelopers/turn-your-app-into-a-handy-health-assistant-3d23) — height/weight and (by the same pattern) calories as unrestricted, quickly-approved Basic data vs. manually-reviewed restricted data.
- `HEALTHKIT_CALORIES_READ` scope identifier (`https://www.huawei.com/healthkit/calories.read`) — Huawei Health Kit `Scopes` class, cross-referenced via the `huawei_health` Flutter plugin's published API docs (same underlying native scope constants).
