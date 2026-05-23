#!/bin/bash
export SDKMAN_DIR="$HOME/.sdkman"
[[ -s "$SDKMAN_DIR/bin/sdkman-init.sh" ]] && source "$SDKMAN_DIR/bin/sdkman-init.sh"

# Ищем путь до Java 17 через sdkman
DETECTED_PATH=$(sdk home java 17.0.10-ms 2>/dev/null || sdk home java 17.0.9-tem 2>/dev/null)

if [ -z "$DETECTED_PATH" ]; then
    DETECTED_PATH=$(find $HOME/.sdkman/candidates/java/ -maxdepth 1 -name "*17*" | head -n 1)
fi

if [ -z "$DETECTED_PATH" ]; then
    echo "❌ Java 17 не найдена в системе через SDKMAN. Попробуем собрать на текущей."
    rm -f gradle.properties
else
    echo "☕ Найдена Java 17 по пути: $DETECTED_PATH"
    # Записываем точный путь в gradle.properties
    cat << INNER > gradle.properties
org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
org.gradle.java.home=$DETECTED_PATH
INNER
fi

echo "📦 Запуск сборки BitLut..."
chmod +x gradlew
./gradlew clean assembleDebug

if [ $? -eq 0 ]; then
    echo "🎉🎉🎉 ПОБЕДА! Приложение BitLut успешно скомпилировано!"
    echo "📲 Локация твоего готового APK файла:"
    find . -name "*.apk"
else
    echo "❌ Ошибка компиляции. Пожалуйста, скинь последние 15 строк лога."
fi
