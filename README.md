# BitLut

Открытый локальный Android-мост между **HUAWEI Health** и **Android Health Connect**.

```text
HUAWEI Health -> BitLut -> Health Connect -> совместимые приложения
```

Без аккаунта BitLut, backend, рекламы и серверного хранения health data.

## Что синхронизируется

Текущий scope — только активность и тренировки: шаги, дистанция, этажи/набор высоты, калории при наличии данных и workout sessions. Типы тренировок HUAWEI нормализуются через единый `HuaweiWorkoutTypeMapper`; состояния, которые не являются тренировками, фильтруются.

Дистанция тренировки берётся из activity-scoped данных HUAWEI, когда они доступны. BitLut не восстанавливает workout distance из грубых дневных Health Connect aggregates.

## Workout records

Exercise sessions записываются в Health Connect как `ACTIVELY_RECORDED` с Huawei device metadata, детерминированным `clientRecordId` и стабильным `clientRecordVersion` для неизменённой тренировки. Session и связанные total calories записываются одним bundle.

Единственное одобренное производное значение — документированный fallback для total workout calories, когда HUAWEI не отдаёт калории конкретной реальной тренировки. Этот exception нельзя расширять на дистанцию, шаги, высоту или другие метрики.

## Dashboard

Workout cards зависят от типа тренировки: walking/running используют pace, cycling — average speed, hiking — elevation, swimming — pace/100 m, strength — duration/calories. Отсутствующие метрики не заменяются выдуманными нулями.

## Corporate wellness compatibility

Корпоративное приложение пока игнорирует BitLut-origin workouts, хотя записи корректно присутствуют в Health Connect. Ведущая гипотеза — allowlist/trust policy источников на стороне reader app: Health Connect правильно указывает writer package `com.openhealth.sync`, а BitLut не может подменить `DataOrigin` Huawei.

## Интерфейс

Сохраняется August palette: Navy, Lime, Tangerine, Purple, Inter Variable и системные light/dark themes. Текущая UI-направленность — спокойная и content-first: плоские outlined cards, restrained hero depth, pill controls, удобные touch targets и минимальная анимация.

Settings намеренно минимален: data source, единая группа connection/sync actions, Health Connect settings deep link и steps goal. Workout-filter UI удалён, но `WorkoutFilterPrefs` по-прежнему применяется в sync path.

## Проверка перед commit

Обязательны обе проверки:

```bash
./gradlew :app:assembleDebug :app:lintDebug \
  --no-daemon \
  --max-workers=1 \
  --no-watch-fs \
  --console=plain \
  -Dorg.gradle.jvmargs="-Xmx1024m -XX:MaxMetaspaceSize=384m -Dfile.encoding=UTF-8" \
  -Pkotlin.compiler.execution.strategy=in-process
```

Перед изменениями прочитайте `CLAUDE.md`, `CONTEXT.md`, `SESSION_HANDOFF.md` и `design.md`.
