package com.openhealth.sync.data

import android.content.Context
import org.json.JSONObject
import java.text.Normalizer
import java.util.Locale

/** Public reference composition per 100 grams of the explicitly named preparation. */
data class CatalogFood(
    val id: String,
    val nameEn: String,
    val nameRu: String,
    val sourceDescription: String,
    val fdcId: Int,
    val kcalPer100g: Double,
    val proteinPer100g: Double,
    val fatPer100g: Double,
    val carbsPer100g: Double
) {
    fun name(locale: Locale): String = if (locale.language == "ru") nameRu else nameEn
    fun portion(grams: Double): FoodPortion {
        require(grams.isFinite() && grams > 0 && grams <= 5000)
        val factor = grams / 100.0
        return FoodPortion(kcalPer100g * factor, proteinPer100g * factor, fatPer100g * factor, carbsPer100g * factor)
    }
    internal val searchKey: String by lazy { normalizeFoodSearch("$nameEn $nameRu $sourceDescription") }
}

data class FoodPortion(val kcal: Double, val protein: Double, val fat: Double, val carbs: Double)

internal fun normalizeFoodSearch(text: String): String = Normalizer.normalize(text, Normalizer.Form.NFD)
    .replace(Regex("\\p{M}+"), "").lowercase(Locale.ROOT).replace('ё', 'е').trim()

/** No network calls, account, API keys or health permissions. Call load on Dispatchers.IO. */
object FoodCatalog {
    fun load(context: Context): List<CatalogFood> = context.assets.open("foods_v1.json")
        .bufferedReader().use { parse(it.readText()) }

    internal fun parse(raw: String): List<CatalogFood> {
        val root = JSONObject(raw)
        require(root.getInt("schemaVersion") == 1)
        val array = root.getJSONArray("foods")
        require(array.length() == 200) { "The catalog must contain exactly 200 foods" }
        val foods = (0 until array.length()).map { index ->
            val item = array.getJSONObject(index)
            CatalogFood(
                id = item.getString("id"), nameEn = item.getString("nameEn"), nameRu = item.getString("nameRu"),
                sourceDescription = item.getString("sourceDescription"), fdcId = item.getInt("fdcId"),
                kcalPer100g = item.getDouble("kcalPer100g"), proteinPer100g = item.getDouble("proteinPer100g"),
                fatPer100g = item.getDouble("fatPer100g"), carbsPer100g = item.getDouble("carbsPer100g")
            ).also { food ->
                require(food.nameEn.isNotBlank() && food.nameRu.isNotBlank())
                require(listOf(food.kcalPer100g, food.proteinPer100g, food.fatPer100g, food.carbsPer100g)
                    .all { it.isFinite() && it >= 0 })
                require(food.kcalPer100g <= 1000 && food.proteinPer100g + food.fatPer100g + food.carbsPer100g <= 105)
            }
        }
        require(foods.map { it.id }.distinct().size == 200)
        return foods
    }

    fun search(foods: List<CatalogFood>, query: String, locale: Locale): List<CatalogFood> {
        val tokens = normalizeFoodSearch(query).split(Regex("\\s+")).filter { it.isNotBlank() }
        return foods.filter { food -> tokens.all { it in food.searchKey } }
            .sortedBy { it.name(locale) }
    }
}
