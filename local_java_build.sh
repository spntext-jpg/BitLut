#!/bin/bash
echo "📦 1. Скачиваем портативную Java 17 (официальный сборка Eclipse Temurin)..."
mkdir -p ./embedded-jdk

# Скачиваем архив Java 17 для Linux x64
curl -L -o java17.tar.gz "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.10%2B7/OpenJDK17U-jdk_x64_linux_hotspot_17.0.10_7.tar.gz"

echo "📦 2. Распаковываем Java во внутреннюю папку проекта..."
tar -xzf java17.tar.gz -C ./embedded-jdk --strip-components=1
rm java17.tar.gz

# Находим точный путь к распакованной Java
LOCAL_JDK_PATH="$(pwd)/embedded-jdk"
echo "☕ Локальная Java 17 готова по пути: $LOCAL_JDK_PATH"

echo "📝 3. Прописываем локальный путь в настройки Gradle..."
cat << INNER > gradle.properties
org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
org.gradle.java.home=$LOCAL_JDK_PATH
INNER

echo "🚀 4. Запускаем сборку BitLut на изолированной Java 17..."
chmod +x gradlew
./gradlew clean assembleDebug

if [ $? -eq 0 ]; then
    echo "🎉🎉🎉 ПОБЕДА! Приложение BitLut успешно скомпилировано!"
    echo "📲 Твой готовый APK файл:"
    find . -name "*.apk"
else
    echo "❌ Ошибка компиляции. Пожалуйста, скинь строки лога, которые появились чуть выше слова FAILURE."
fi
