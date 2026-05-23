#!/bin/bash
echo "🛠️ 1. Исправляем настройки Java..."

# Удаляем неверный путь из gradle.properties, оставляем только базовые аргументы
cat << 'INNER' > gradle.properties
org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
INNER

# Используем встроенный в Codespaces менеджер sdkman, чтобы активировать Java 17 для этого терминала
export SDKMAN_DIR="$HOME/.sdkman"
if [ -s "$SDKMAN_DIR/bin/sdkman-init.sh" ]; then
    source "$SDKMAN_DIR/bin/sdkman-init.sh"
    echo "☕ Переключаемся на Java 17..."
    sdk use java 17.0.10-ms < /dev/null || sdk use java 17.0.9-tem < /dev/null || echo "Используем системную Java..."
fi

echo "🔄 2. Синхронизируем Git, чтобы убрать конфликты..."
git pull origin main --rebase

echo "📦 3. Запуск чистой сборки BitLut..."
chmod +x gradlew
./gradlew clean assembleDebug

if [ $? -eq 0 ]; then
    echo "🎉🎉🎉 УРА! Сборка успешно завершена!"
    echo "📲 Твой готовый файл приложения BitLut находится здесь:"
    find . -name "*.apk"
else
    echo "❌ Сборка не удалась. Давай посмотрим, на какую строчку кода ругается сам компилятор."
fi
