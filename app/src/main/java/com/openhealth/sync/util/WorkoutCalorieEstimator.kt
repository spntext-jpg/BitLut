package com.openhealth.sync.util

import androidx.health.connect.client.records.ExerciseSessionRecord

/**
 * MET-formula calorie ESTIMATE for a workout -- not measured data.
 *
 * Extracted (sprint 2026-08-26) from GoogleHealthManager so the exact same
 * formula and MET table back both:
 * - the TotalCaloriesBurnedRecord GoogleHealthManager writes to Health
 *   Connect so third-party readers have something to import (see
 *   GoogleHealthManager.writeActivitySessionsBatch), and
 * - the workout card's own calorie display when Huawei's real
 *   activeCaloriesKcal is unavailable (see workoutMetricDisplays in
 *   FinalBitLutShell.kt).
 *
 * Keeping one shared implementation means a future correction to the MET
 * table or the formula only has to be made once, and the two call sites can
 * never silently drift apart.
 *
 * This is NOT measured data: Huawei's real per-workout calorie figure is
 * gated behind the activeCalories scope that returns error 50005 for this
 * individual-developer account, and nothing about that is expected to
 * change. The formula itself -- kcal = MET * 3.5 * weightKg * minutes / 200
 * -- and the MET values below are drawn from the Compendium of Physical
 * Activities (Ainsworth et al.), the standard reference most fitness
 * calorie calculators cite. Reference body weight is fixed at 70 kg, the
 * conventional default used across MET calculators when no real weight is
 * available -- BitLut has no access to the user's actual weight, and adding
 * that would be a new data category, which this feature is explicitly
 * scoped to avoid.
 *
 * MET values are the "general/moderate" variant for each activity where the
 * Compendium lists multiple intensity bands, since Huawei's activity
 * records carry no intensity signal to pick a different one.
 *
 * See docs/HEALTH_DATA_PERMISSION_MATRIX.md's "Documented exception:
 * estimated workout calories" section for the full rationale and the
 * explicit exception this makes to that document's "never synthesize fake
 * health data" rule.
 */
object WorkoutCalorieEstimator {

    private const val REFERENCE_WEIGHT_KG = 70.0

    /**
     * Estimated total calories burned for a workout of the given exercise
     * type and duration. Returns null for a zero-or-negative duration, so
     * callers can fall back to a "no data" display or skip writing a record
     * for a malformed session.
     */
    fun estimateTotalCaloriesKcal(exerciseType: Int, startTimeMs: Long, endTimeMs: Long): Double? {
        val minutes = (endTimeMs - startTimeMs) / 60_000.0
        if (minutes <= 0.0) return null

        val met = metValueFor(exerciseType)
        return met * 3.5 * REFERENCE_WEIGHT_KG * minutes / 200.0
    }

    /** General/moderate MET value per Health Connect exercise type, from the
     *  Compendium of Physical Activities. See [estimateTotalCaloriesKcal]. */
    private fun metValueFor(exerciseType: Int): Double = when (exerciseType) {
        ExerciseSessionRecord.EXERCISE_TYPE_RUNNING,
        ExerciseSessionRecord.EXERCISE_TYPE_RUNNING_TREADMILL -> 8.0
        ExerciseSessionRecord.EXERCISE_TYPE_BIKING,
        ExerciseSessionRecord.EXERCISE_TYPE_BIKING_STATIONARY -> 7.5
        ExerciseSessionRecord.EXERCISE_TYPE_SWIMMING_POOL,
        ExerciseSessionRecord.EXERCISE_TYPE_SWIMMING_OPEN_WATER -> 6.0
        ExerciseSessionRecord.EXERCISE_TYPE_HIKING -> 6.0
        ExerciseSessionRecord.EXERCISE_TYPE_ROWING,
        ExerciseSessionRecord.EXERCISE_TYPE_ROWING_MACHINE -> 7.0
        ExerciseSessionRecord.EXERCISE_TYPE_ELLIPTICAL -> 5.0
        ExerciseSessionRecord.EXERCISE_TYPE_STRENGTH_TRAINING,
        ExerciseSessionRecord.EXERCISE_TYPE_WEIGHTLIFTING -> 3.5
        ExerciseSessionRecord.EXERCISE_TYPE_YOGA -> 2.5
        ExerciseSessionRecord.EXERCISE_TYPE_WALKING -> 3.5
        ExerciseSessionRecord.EXERCISE_TYPE_SKIING -> 7.0
        ExerciseSessionRecord.EXERCISE_TYPE_SNOWBOARDING -> 5.3
        ExerciseSessionRecord.EXERCISE_TYPE_SKATING -> 7.0
        ExerciseSessionRecord.EXERCISE_TYPE_TENNIS -> 7.3
        ExerciseSessionRecord.EXERCISE_TYPE_TABLE_TENNIS -> 4.0
        ExerciseSessionRecord.EXERCISE_TYPE_BASKETBALL -> 6.5
        ExerciseSessionRecord.EXERCISE_TYPE_VOLLEYBALL -> 4.0
        ExerciseSessionRecord.EXERCISE_TYPE_BADMINTON -> 5.5
        ExerciseSessionRecord.EXERCISE_TYPE_BASEBALL -> 5.0
        ExerciseSessionRecord.EXERCISE_TYPE_BOXING -> 7.0
        ExerciseSessionRecord.EXERCISE_TYPE_DANCING -> 4.5
        ExerciseSessionRecord.EXERCISE_TYPE_HIGH_INTENSITY_INTERVAL_TRAINING -> 8.0
        ExerciseSessionRecord.EXERCISE_TYPE_PILATES -> 3.0
        ExerciseSessionRecord.EXERCISE_TYPE_GOLF -> 4.8
        ExerciseSessionRecord.EXERCISE_TYPE_SOCCER -> 7.0
        ExerciseSessionRecord.EXERCISE_TYPE_FOOTBALL_AMERICAN,
        ExerciseSessionRecord.EXERCISE_TYPE_FOOTBALL_AUSTRALIAN -> 8.0
        else -> 4.0 // EXERCISE_TYPE_OTHER_WORKOUT and anything unmapped: conservative moderate-activity default.
    }
}
