#!/bin/bash
set -e # Останавливать выполнение при любой ошибке

echo "=== [1/5] Инъекция Java 17 в конфигурацию сборщика ==="
# Находим валидный путь к JDK 17 в системе Codespaces
if [ -d "/usr/lib/jvm/java-17-openjdk-amd64" ]; then
    JDK_PATH="/usr/lib/jvm/java-17-openjdk-amd64"
elif [ -d "/usr/lib/jvm/java-1.17.0-openjdk-amd64" ]; then
    JDK_PATH="/usr/lib/jvm/java-1.17.0-openjdk-amd64"
else
    JDK_PATH=$(readlink -f /usr/bin/javac | sed "s:/bin/javac::")
fi

echo "Локализован JDK 17: $JDK_PATH"

# Проверяем или создаем gradle.properties и жестко фиксируем Java Home
touch gradle.properties
sed -i '/org.gradle.java.home/d' gradle.properties
echo "org.gradle.java.home=$JDK_PATH" >> gradle.properties
echo "Конфигурация org.gradle.java.home успешно добавлена в gradle.properties."

echo "=== [2/5] Нормализация индекса и фиксация Git-состояния ==="
# Возвращаем файлы в индекс после предыдущего rm --cached
git add .

# Проверяем наличие изменений перед коммитом
if ! git diff-index --quiet HEAD --; then
    echo "Фиксируем локальные исправления архитектуры..."
    git commit -m "Refactor: enforce architecture contracts and correct AppLogger paths"
else
    echo "Рабочая директория чиста, коммит не требуется."
fi

echo "=== [3/5] Синхронизация истории (Rebase) ==="
git fetch origin
git rebase origin/main --autostash

echo "=== [4/5] Очистка кэшей и верификационная сборка ==="
./gradlew clean --no-daemon
./gradlew assembleDebug

echo "=== [5/5] Пуш верифицированного кода на удаленный сервер ==="
git push origin main

echo "🎉 [SUCCESS] Окружение стабилизировано. Сборка прошла успешно. Код отправлен в репозиторий!"
