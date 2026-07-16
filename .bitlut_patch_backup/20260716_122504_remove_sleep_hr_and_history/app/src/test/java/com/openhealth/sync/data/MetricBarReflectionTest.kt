package com.openhealth.sync.data

import java.time.LocalDate

fun main() {
    val bar = MetricBar(LocalDate.now(), LocalDate.now(), 42.0)
    val valueMethod = bar.javaClass.methods.firstOrNull { it.name == "getValue" && it.parameterCount == 0 }
    val dateMethod = bar.javaClass.methods.firstOrNull { it.name == "getStartDate" && it.parameterCount == 0 }
    println("valueMethod: $valueMethod")
    println("valueMethod invoke: ${valueMethod?.invoke(bar)}")
    println("dateMethod: $dateMethod")
    println("dateMethod invoke: ${dateMethod?.invoke(bar)}")
    println("all methods: ${bar.javaClass.methods.map { it.name }}")
}
