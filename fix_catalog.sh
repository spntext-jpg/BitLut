#!/bash/bin
echo "🔍 1. Проверяем наличие каталога версий..."
if [ -f "gradle/libs.versions.toml" ]; then
    echo "✅ Файл gradle/libs.versions.toml на месте. Проблема в кэше."
else
    echo "⚠️ Файла gradle/libs.versions.toml нет в корневом каталоге gradle/."
    echo "Попробуем найти его по всему проекту:"
    find . -name "libs.versions.toml"
fi

echo "📝 2. Переписываем корневой build.gradle.kts на классический синтаксис (без libs)..."
# Бэкапим старый файл на всякий случай
cp build.gradle.kts build.gradle.kts.bak

# Создаем чистый корневой build.gradle.kts, где плагины прописаны напрямую с версиями,
# подходящими под твой Gradle 8.2 и Java 17
cat << 'INNER' > build.gradle.kts
plugins {
    id("com.android.application") version "8.2.2" apply false
    id("com.android.library") version "8.2.2" apply false
    id("org.jetbrains.kotlin.android") version "1.8.22" apply false
}
INNER

echo "🚀 3. Пробуем собрать проект заново..."
./gradlew clean assembleDebug

if [ $? -eq 0 ]; then
    echo "🎉🎉🎉 ПОБЕДА! Сборка успешно завершена!"
    find . -name "*.apk"
else
    echo "❌ Всё ещё ругается. Скинь, пожалуйста, новые строчки ошибки (особенно если они будут внутри папки app/)."
fi
