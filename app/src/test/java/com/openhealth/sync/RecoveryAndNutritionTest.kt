package com.openhealth.sync

import com.openhealth.sync.config.*
import com.openhealth.sync.data.FoodCatalog
import com.openhealth.sync.util.ProviderFailurePolicy
import com.openhealth.sync.util.StableRecordVersion
import org.junit.Assert.*
import org.junit.Test
import java.io.File
import java.io.IOException
import java.util.Locale

class RecoveryAndNutritionTest {
    private fun foods() = FoodCatalog.parse(File("src/main/assets/foods_v1.json").readText())

    @Test fun catalogHasTwoHundredDistinctFoodsWithSourceIds() {
        val foods = foods()
        assertEquals(200, foods.size)
        assertEquals(200, foods.map { it.fdcId }.distinct().size)
        assertTrue(foods.all { it.nameEn.isNotBlank() && it.nameRu.isNotBlank() && it.sourceDescription.isNotBlank() })
    }

    @Test fun gramScalingUsesSourceValuesWithoutPrematureRounding() {
        val banana = foods().single { it.fdcId == 173944 }
        val portion = banana.portion(125.5)
        assertEquals(89.0 * 1.255, portion.kcal, 0.00001)
        assertEquals(banana.proteinPer100g * 1.255, portion.protein, 0.00001)
        assertEquals(banana.fatPer100g * 1.255, portion.fat, 0.00001)
        assertEquals(banana.carbsPer100g * 1.255, portion.carbs, 0.00001)
    }

    @Test fun bilingualSearchUsesAllTokensAndNormalizesYo() {
        assertTrue(FoodCatalog.search(foods(), "куриная грудка", Locale("ru")).any { it.nameEn == "Chicken breast, roasted" })
        assertTrue(FoodCatalog.search(foods(), "ЗЕЛЕНЫЙ ГОРОШЕК", Locale("ru")).isNotEmpty())
        assertTrue(FoodCatalog.search(foods(), "rice cooked", Locale.ENGLISH).isNotEmpty())
        assertTrue(FoodCatalog.search(foods(), "no-such-food-123456", Locale.ENGLISH).isEmpty())
    }

    @Test fun zeroCalorieFoodsCanBeLogged() {
        val water = foods().single { it.nameEn == "Water, tap" }.portion(250.0)
        assertEquals(0.0, water.kcal, 0.0)
        NutritionJournalPrefs.validate(FoodEntry(1, 20000, MealType.SNACK, "Water", 0.0, grams = 250.0, protein = 0.0, fat = 0.0, carbs = 0.0))
    }

    @Test fun legacyCalorieEntriesKeepTheirDateIdAndUnknownMacros() {
        val legacy = """[{"id":123,"day":20000,"meal":"lunch","name":"Lunch","kcal":540}]"""
        val entry = NutritionJournalPrefs.decode(legacy).single()
        assertEquals(123L, entry.id)
        assertEquals(20000L, entry.epochDay)
        assertEquals(540.0, entry.kcal, 0.0)
        assertNull(entry.grams)
        assertFalse(entry.hasMacros)
        assertEquals(entry, NutritionJournalPrefs.decode(NutritionJournalPrefs.encode(listOf(entry))).single())
    }

    @Test fun totalsExposeIncompleteMacrosAndSeparateDays() {
        val known = FoodEntry(1, 1, MealType.LUNCH, "Food", 100.25, 100.0, 5.5, 2.0, 15.0)
        val unknown = FoodEntry(2, 1, MealType.DINNER, "Legacy", 200.25)
        val otherDay = known.copy(id = 3, epochDay = 2, kcal = 700.0)
        val totals = NutritionTotals.of(listOf(known, unknown, otherDay).filter { it.epochDay == 1L })
        assertEquals(300.5, totals.kcal, 0.0)
        assertEquals(5.5, totals.protein, 0.0)
        assertEquals(1, totals.unknownMacros)
    }

    @Test fun corruptJournalIsRejectedInsteadOfSilentlyCleared() {
        assertThrows(Exception::class.java) { NutritionJournalPrefs.decode("broken") }
        assertThrows(Exception::class.java) { NutritionJournalPrefs.decode("""[{"id":1,"day":2,"kcal":-1}]""") }
    }

    @Test fun invalidWeightAndNonFiniteValuesAreRejected() {
        val food = foods().first()
        for (grams in listOf(-1.0, 0.0, Double.NaN, Double.POSITIVE_INFINITY, 5001.0)) {
            assertThrows(IllegalArgumentException::class.java) { food.portion(grams) }
        }
        assertThrows(IllegalArgumentException::class.java) {
            NutritionJournalPrefs.validate(FoodEntry(1, 1, MealType.SNACK, "invalid", 1.0, 5.0, 10.0, 0.0, 0.0))
        }
    }

    @Test fun stableVersionsDoNotChurnButCorrectionsAlwaysIncrease() {
        val first = StableRecordVersion.resolve(null, "123", 1000)
        assertEquals(first, StableRecordVersion.resolve(first, "123", 9000))
        val corrected = StableRecordVersion.resolve(first, "124", 500)
        assertEquals("1001|124", corrected)
        assertEquals("1002|123", StableRecordVersion.resolve(corrected, "123", 200))
    }

    @Test fun providerQuotaAndTransportFailuresAbortTheWholeCycle() {
        assertTrue(ProviderFailurePolicy.shouldDefer(IOException("disk unavailable")))
        assertTrue(ProviderFailurePolicy.shouldDefer(RuntimeException("outer", IllegalStateException("Rate limit exceeded"))))
        assertTrue(ProviderFailurePolicy.shouldDefer(RuntimeException("quota exhausted")))
        assertFalse(ProviderFailurePolicy.shouldDefer(IllegalArgumentException("Invalid interval")))
        assertFalse(ProviderFailurePolicy.shouldDefer(SecurityException("Permission missing")))
    }
}
