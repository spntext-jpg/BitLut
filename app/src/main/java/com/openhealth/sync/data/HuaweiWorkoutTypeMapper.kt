package com.openhealth.sync.data

import androidx.health.connect.client.records.ExerciseSessionRecord
import java.util.Locale

/**
 * Single source of truth for Huawei ActivityRecord -> Health Connect workout types.
 *
 * Huawei numeric IDs follow the current Health Kit activity table. IDs 161
 * (marathon) and 162 (pickleball) were added by Huawei after the older table.
 * Activity-like sensor states that are not workouts are rejected instead of
 * being exported as EXERCISE_TYPE_OTHER_WORKOUT.
 */
internal object HuaweiWorkoutTypeMapper {
    // BITLUT_WORKOUT_HARDENING_V3
    private val activityNames: Map<Int, String> = mapOf(
        1 to "aerobics",
        2 to "archery",
        3 to "badminton",
        4 to "baseball",
        5 to "basketball",
        6 to "biathlon",
        7 to "boxing",
        8 to "calisthenics",
        9 to "circuit training",
        10 to "cricket",
        11 to "crossfit",
        12 to "curling",
        13 to "cycling",
        14 to "dancing",
        15 to "diving",
        16 to "elevator",
        17 to "elliptical",
        18 to "ergometer",
        19 to "escalator",
        20 to "fencing",
        21 to "american football",
        22 to "australian football",
        23 to "football",
        24 to "flying disc",
        25 to "gardening",
        26 to "golf",
        27 to "gymnastics",
        28 to "handball",
        29 to "hiit",
        30 to "hiking",
        31 to "hockey",
        32 to "horse riding",
        33 to "housework",
        34 to "ice skating",
        35 to "in vehicle",
        36 to "interval training",
        37 to "jumping rope",
        38 to "kayaking",
        39 to "kettlebell training",
        40 to "kickboxing",
        41 to "kitesurfing",
        42 to "martial arts",
        43 to "mixed martial arts",
        44 to "meditation",
        45 to "on foot",
        46 to "other",
        47 to "p90x",
        48 to "paragliding",
        49 to "pilates",
        50 to "polo",
        51 to "racquetball",
        52 to "rock climbing",
        53 to "rowing",
        54 to "rowing machine",
        55 to "rugby",
        56 to "running",
        57 to "indoor running",
        58 to "sailing",
        59 to "scuba diving",
        60 to "scooter riding",
        61 to "skateboarding",
        62 to "skating",
        63 to "skiing",
        64 to "sledding",
        65 to "sleep",
        70 to "snowboarding",
        71 to "snowmobile",
        72 to "snowshoeing",
        73 to "softball",
        74 to "squash",
        75 to "stair climbing",
        76 to "stair climbing machine",
        77 to "standup paddleboarding",
        78 to "still",
        79 to "strength training",
        80 to "surfing",
        81 to "swimming",
        82 to "open water swimming",
        83 to "pool swimming",
        84 to "table tennis",
        85 to "team sports",
        86 to "tennis",
        87 to "tilting",
        88 to "volleyball",
        89 to "wakeboarding",
        90 to "walking",
        91 to "water polo",
        92 to "weightlifting",
        93 to "wheelchair",
        94 to "windsurfing",
        95 to "yoga",
        96 to "zumba",
        97 to "indoor cycling",
        98 to "darts",
        99 to "billiards",
        100 to "shuttlecock",
        101 to "bowling",
        102 to "group calisthenics",
        103 to "tug of war",
        104 to "beach soccer",
        105 to "beach volleyball",
        106 to "gateball",
        107 to "sepaktakraw",
        108 to "dodge ball",
        109 to "treadmill",
        110 to "spinning",
        111 to "stroll machine",
        112 to "cross fit",
        113 to "functional training",
        114 to "physical training",
        115 to "belly dance",
        116 to "jazz",
        117 to "latin dance",
        118 to "ballet",
        119 to "core training",
        120 to "horizontal bar",
        121 to "parallel bars",
        122 to "hip hop",
        123 to "square dance",
        124 to "hula hoop",
        125 to "bmx",
        126 to "orienteering",
        127 to "indoor walking",
        128 to "indoor running",
        129 to "mountain climbing",
        130 to "trail running",
        131 to "roller skating",
        132 to "hunting",
        133 to "fly a kite",
        134 to "swing",
        135 to "obstacle race",
        136 to "bungee jumping",
        137 to "parkour",
        138 to "parachute",
        139 to "racing car",
        140 to "triathlon",
        141 to "ice hockey",
        142 to "cross country skiing",
        143 to "sled",
        144 to "fishing",
        145 to "drifting",
        146 to "dragon boat",
        147 to "motorboat",
        148 to "standup paddleboarding",
        149 to "free sparring",
        150 to "karate",
        151 to "body combat",
        152 to "kendo",
        153 to "tai chi",
        161 to "marathon",
        162 to "pickleball"
    )

    private val nonWorkoutTypes = setOf(
        "elevator",
        "escalator",
        "in vehicle",
        "sleep",
        "still",
        "tilting"
    )

    fun canonicalName(rawType: String?): String {
        val normalized = rawType.orEmpty()
            .trim()
            .lowercase(Locale.ROOT)

        normalized.toIntOrNull()?.let { numeric ->
            return activityNames[numeric] ?: "workout"
        }

        val spaced = normalized
            .replace('_', ' ')
            .replace('.', ' ')
            .replace(Regex("\\s+"), " ")
            .takeIf { it.isNotBlank() && it != "unknown" }
            ?: return "workout"

        return when (spaced) {
            "football american" -> "american football"
            "football australian" -> "australian football"
            "football soccer" -> "football"
            "running machine", "running indoor" -> "indoor running"
            "cycling indoor" -> "indoor cycling"
            "walking indoor" -> "indoor walking"
            "swimming open water" -> "open water swimming"
            "swimming pool" -> "pool swimming"
            else -> spaced
        }
    }

    /** Returns null only for Huawei states that are not actual workouts. */
    fun healthConnectType(canonicalType: String): Int? {
        val type = canonicalName(canonicalType)
        if (type in nonWorkoutTypes) return null

        val constantName = when {
            type == "american football" -> "EXERCISE_TYPE_FOOTBALL_AMERICAN"
            type == "australian football" -> "EXERCISE_TYPE_FOOTBALL_AUSTRALIAN"
            type == "football" || type == "beach soccer" -> "EXERCISE_TYPE_SOCCER"

            type == "indoor running" || type == "treadmill" -> "EXERCISE_TYPE_RUNNING_TREADMILL"
            type == "running" || type == "trail running" || type == "marathon" -> "EXERCISE_TYPE_RUNNING"
            type == "walking" || type == "indoor walking" || type == "on foot" -> "EXERCISE_TYPE_WALKING"
            type == "hiking" || type == "orienteering" || type == "mountain climbing" -> "EXERCISE_TYPE_HIKING"

            type == "indoor cycling" || type == "spinning" -> "EXERCISE_TYPE_BIKING_STATIONARY"
            type == "cycling" || type == "bmx" -> "EXERCISE_TYPE_BIKING"
            type == "rowing machine" -> "EXERCISE_TYPE_ROWING_MACHINE"
            type == "rowing" -> "EXERCISE_TYPE_ROWING"
            type == "kayaking" || type == "dragon boat" || type == "standup paddleboarding" -> "EXERCISE_TYPE_PADDLING"
            type == "elliptical" || type == "ergometer" || type == "stroll machine" -> "EXERCISE_TYPE_ELLIPTICAL"

            type == "open water swimming" -> "EXERCISE_TYPE_SWIMMING_OPEN_WATER"
            type == "swimming" || type == "pool swimming" -> "EXERCISE_TYPE_SWIMMING_POOL"
            type == "scuba diving" || type == "diving" -> "EXERCISE_TYPE_SCUBA_DIVING"
            type == "sailing" -> "EXERCISE_TYPE_SAILING"
            type == "surfing" || type == "kitesurfing" -> "EXERCISE_TYPE_SURFING"

            type == "cross country skiing" || type == "skiing" || type == "biathlon" -> "EXERCISE_TYPE_SKIING"
            type == "snowboarding" -> "EXERCISE_TYPE_SNOWBOARDING"
            type == "snowshoeing" -> "EXERCISE_TYPE_SNOWSHOEING"
            type == "ice skating" -> "EXERCISE_TYPE_ICE_SKATING"
            type == "skating" || type == "roller skating" || type == "skateboarding" -> "EXERCISE_TYPE_SKATING"
            type == "ice hockey" -> "EXERCISE_TYPE_ICE_HOCKEY"

            type == "stair climbing" -> "EXERCISE_TYPE_STAIR_CLIMBING"
            type == "stair climbing machine" -> "EXERCISE_TYPE_STAIR_CLIMBING_MACHINE"
            type == "rock climbing" -> "EXERCISE_TYPE_ROCK_CLIMBING"

            type == "strength training" || type == "kettlebell training" ||
                type == "functional training" || type == "physical training" || type == "tug of war" ->
                "EXERCISE_TYPE_STRENGTH_TRAINING"
            type == "weightlifting" -> "EXERCISE_TYPE_WEIGHTLIFTING"
            type == "calisthenics" || type == "group calisthenics" || type == "core training" ||
                type == "horizontal bar" || type == "parallel bars" || type == "hula hoop" ->
                "EXERCISE_TYPE_CALISTHENICS"
            type == "hiit" || type == "interval training" || type == "circuit training" ||
                type == "crossfit" || type == "cross fit" || type == "p90x" ||
                type == "jumping rope" || type == "obstacle race" || type == "parkour" ->
                "EXERCISE_TYPE_HIGH_INTENSITY_INTERVAL_TRAINING"

            type == "boxing" || type == "kickboxing" || type == "body combat" -> "EXERCISE_TYPE_BOXING"
            type == "martial arts" || type == "mixed martial arts" || type == "free sparring" ||
                type == "karate" || type == "kendo" || type == "tai chi" -> "EXERCISE_TYPE_MARTIAL_ARTS"
            type == "yoga" -> "EXERCISE_TYPE_YOGA"
            type == "pilates" -> "EXERCISE_TYPE_PILATES"
            type == "aerobics" -> "EXERCISE_TYPE_EXERCISE_CLASS"
            type == "dancing" || type == "zumba" || type == "belly dance" || type == "jazz" ||
                type == "latin dance" || type == "ballet" || type == "hip hop" || type == "square dance" ->
                "EXERCISE_TYPE_DANCING"
            type == "gymnastics" -> "EXERCISE_TYPE_GYMNASTICS"

            type == "badminton" -> "EXERCISE_TYPE_BADMINTON"
            type == "baseball" -> "EXERCISE_TYPE_BASEBALL"
            type == "softball" -> "EXERCISE_TYPE_SOFTBALL"
            type == "basketball" -> "EXERCISE_TYPE_BASKETBALL"
            type == "cricket" -> "EXERCISE_TYPE_CRICKET"
            type == "fencing" -> "EXERCISE_TYPE_FENCING"
            type == "flying disc" -> "EXERCISE_TYPE_FRISBEE_DISC"
            type == "golf" -> "EXERCISE_TYPE_GOLF"
            type == "handball" -> "EXERCISE_TYPE_HANDBALL"
            type == "paragliding" -> "EXERCISE_TYPE_PARAGLIDING"
            type == "racquetball" -> "EXERCISE_TYPE_RACQUETBALL"
            type == "rugby" -> "EXERCISE_TYPE_RUGBY"
            type == "squash" -> "EXERCISE_TYPE_SQUASH"
            type == "table tennis" -> "EXERCISE_TYPE_TABLE_TENNIS"
            type == "tennis" -> "EXERCISE_TYPE_TENNIS"
            type == "volleyball" || type == "beach volleyball" -> "EXERCISE_TYPE_VOLLEYBALL"
            type == "water polo" -> "EXERCISE_TYPE_WATER_POLO"
            type == "wheelchair" -> "EXERCISE_TYPE_WHEELCHAIR"

            else -> "EXERCISE_TYPE_OTHER_WORKOUT"
        }

        return exerciseTypeConstant(constantName)
    }

    private fun exerciseTypeConstant(name: String): Int = try {
        ExerciseSessionRecord::class.java.getField(name).getInt(null)
    } catch (_: Exception) {
        ExerciseSessionRecord.EXERCISE_TYPE_OTHER_WORKOUT
    }
}
