package com.openhealth.sync.ui

import android.content.Context
import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.openhealth.sync.data.GoogleHealthManager
import com.openhealth.sync.data.import.HuaweiExportParser
import com.openhealth.sync.data.import.HuaweiExportSummary
import com.openhealth.sync.util.AppLogger
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
    private val googleManager: GoogleHealthManager,
    private val context: Context
) : ViewModel() {

    private val parser = HuaweiExportParser(context)

    private val _state = MutableStateFlow<ImportState>(ImportState.Idle)
    val state: StateFlow<ImportState> = _state.asStateFlow()

    fun parseFile(uri: Uri) {
        _state.update { ImportState.Parsing }

        viewModelScope.launch {
            try {
                val summary = withContext(Dispatchers.IO) { parser.parse(uri) }

                if (summary.stepCount == 0 &&
                    summary.distanceCount == 0 &&
                    summary.calorieCount == 0 &&
                    summary.activityCount == 0
                ) {
                    _state.update {
                        ImportState.Error(
                            "В файле не найдено данных для импорта.\n\n" +
                            "Убедитесь что вы выбрали правильный ZIP-архив из Huawei Health. " +
                            "Найденные файлы: ${summary.filesFound.joinToString()}\n" +
                            "Пропущенные файлы: ${summary.filesSkipped.size}"
                        )
                    }
                } else {
                    _state.update { ImportState.Preview(summary) }
                }
            } catch (e: Exception) {
                AppLogger.e(TAG, "Failed to parse export file", e)
                _state.update {
                    ImportState.Error(
                        "Не удалось прочитать файл.\n\n${e.message ?: "Неизвестная ошибка"}"
                    )
                }
            }
        }
    }

    fun confirmImport(summary: HuaweiExportSummary) {
        _state.update { ImportState.Writing }

        viewModelScope.launch {
            try {
                val ok = withContext(Dispatchers.IO) {
                    googleManager.writeSnapshot(summary.snapshot)
                }

                if (ok) {
                    _state.update {
                        ImportState.Success(
                            stepsWritten = summary.stepCount,
                            distancesWritten = summary.distanceCount,
                            caloriesWritten = summary.calorieCount,
                            activitiesWritten = summary.activityCount
                        )
                    }
                    AppLogger.i(TAG, "Import complete: steps=${summary.stepCount} distances=${summary.distanceCount} calories=${summary.calorieCount} activities=${summary.activityCount}")
                } else {
                    _state.update {
                        ImportState.Error(
                            "Не удалось записать данные в Google Health Connect.\n\n" +
                            "Проверьте что разрешения Google Health выданы и попробуйте снова."
                        )
                    }
                }
            } catch (e: Exception) {
                AppLogger.e(TAG, "Failed to write import data", e)
                _state.update {
                    ImportState.Error("Ошибка записи данных: ${e.message ?: "Неизвестная ошибка"}")
                }
            }
        }
    }

    fun reset() {
        _state.update { ImportState.Idle }
    }

    companion object {
        fun provideFactory(
            googleManager: GoogleHealthManager,
            context: Context
        ): ViewModelProvider.Factory = object : ViewModelProvider.Factory {
            @Suppress("UNCHECKED_CAST")
            override fun <T : ViewModel> create(modelClass: Class<T>): T =
                ImportViewModel(googleManager, context) as T
        }
    }
}
