package com.openhealth.sync.ui

import android.content.Context
import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.openhealth.sync.data.HealthConnectManager
import com.openhealth.sync.data.import.HuaweiExportParser
import com.openhealth.sync.data.import.HuaweiExportSummary
import com.openhealth.sync.util.AppLogger
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

private const val TAG = "ImportViewModel"

sealed class ImportState {
    object Idle : ImportState()
    object Parsing : ImportState()
    data class Preview(val summary: HuaweiExportSummary) : ImportState()
    object Writing : ImportState()
    data class Success(
        val stepsWritten: Int,
        val distancesWritten: Int,
        val caloriesWritten: Int,
        val activitiesWritten: Int
    ) : ImportState()
    data class Error(val message: String) : ImportState()
}

class ImportViewModel(
    private val googleManager: HealthConnectManager,
    context: Context
) : ViewModel() {
    private val parser = HuaweiExportParser(context.applicationContext)
    private val _state = MutableStateFlow<ImportState>(ImportState.Idle)
    val state: StateFlow<ImportState> = _state.asStateFlow()

    fun parseFile(uri: Uri) {
        _state.update { ImportState.Parsing }
        viewModelScope.launch {
            try {
                val summary = withContext(Dispatchers.IO) { parser.parse(uri) }
                val hasData = summary.stepCount > 0 || summary.distanceCount > 0 ||
                    summary.calorieCount > 0 || summary.activityCount > 0

                if (hasData) {
                    _state.update { ImportState.Preview(summary) }
                } else {
                    val detail = buildString {
                        if (summary.filesFound.isNotEmpty()) {
                            append("Recognized: ")
                            append(summary.filesFound.joinToString { it.substringAfterLast('/') })
                        }
                        if (summary.filesSkipped.isNotEmpty()) {
                            if (isNotEmpty()) append("; ")
                            append("Skipped JSON files: ${summary.filesSkipped.size}")
                        }
                    }
                    _state.update { ImportState.Error("import_error_no_data|$detail") }
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                AppLogger.e(TAG, "Failed to parse export file", e)
                _state.update { ImportState.Error("import_error_read_failed|${e.message.orEmpty()}") }
            }
        }
    }

    fun confirmImport(summary: HuaweiExportSummary) {
        _state.update { ImportState.Writing }
        viewModelScope.launch {
            try {
                val result = withContext(Dispatchers.IO) { googleManager.writeSnapshot(summary.snapshot) }
                if (result.anySucceeded) {
                    _state.update {
                        ImportState.Success(
                            stepsWritten = if ("steps" in result.succeededCategories) summary.stepCount else 0,
                            distancesWritten = if ("distance" in result.succeededCategories) summary.distanceCount else 0,
                            caloriesWritten = if ("activeCalories" in result.succeededCategories) summary.calorieCount else 0,
                            activitiesWritten = if ("activitySessions" in result.succeededCategories) summary.activityCount else 0
                        )
                    }
                    if (!result.allSucceeded) {
                        AppLogger.w(TAG, "Import partially written; failed categories: ${result.failedCategories.joinToString()}")
                    }
                    AppLogger.i(TAG, "Import complete; succeeded categories: ${result.succeededCategories.joinToString()}")
                } else {
                    _state.update { ImportState.Error("import_error_write_failed|${result.failedCategories.joinToString()}") }
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                AppLogger.e(TAG, "Failed to write import data", e)
                _state.update { ImportState.Error("import_error_write_failed|${e.message.orEmpty()}") }
            }
        }
    }

    fun reset() {
        _state.update { ImportState.Idle }
    }

    companion object {
        fun provideFactory(
            googleManager: HealthConnectManager,
            context: Context
        ): ViewModelProvider.Factory = object : ViewModelProvider.Factory {
            @Suppress("UNCHECKED_CAST")
            override fun <T : ViewModel> create(modelClass: Class<T>): T =
                ImportViewModel(googleManager, context) as T
        }
    }
}
