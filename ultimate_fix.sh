#!/bin/bash
echo "🧹 1. Сбрасываем мусорные файлы для Git..."
# Прячем все временные изменения, чтобы дать Git сделать pull
git stash

echo "🔄 2. Синхронизируем репозиторий..."
git pull origin main --rebase
git stash pop 2>/dev/null # возвращаем файлы обратно, если нужно

echo "☕ 3. Привязываем точный и проверенный путь к Java 17..."
# В Codespaces от Microsoft Java 17 всегда предустановлена по этому пути:
JDK_17_PATH="/usr/lib/jvm/msopenjdk-17"

if [ -d "$JDK_17_PATH" ]; then
    echo "✅ Найдена Microsoft OpenJDK 17 по стандартному пути."
else
    # Если вдруг там другое имя, найдем любую 17-ю версию в системе:
    JDK_17_PATH=$(find /usr/lib/jvm -maxdepth 1 -name "*17*" | head -n 1)
    echo "✅ Найдена альтернативная Java 17: $JDK_17_PATH"
fi

# Жестко прописываем этот рабочий путь в настройки проекта
cat << INNER > gradle.properties
org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
org.gradle.java.home=$JDK_17_PATH
INNER

echo "📦 4. Запускаем компиляцию BitLut..."
chmod +x gradlew
./gradlew clean assembleDebug

if [ $? -eq 0 ]; then
    echo "🎉🎉🎉 УРА! Проект BitLut успешно собран!"
    echo "📲 Лови свой готовый APK файл:"
    find . -name "*.apk"
else
    echo "❌ Сборка опять споткнулась. Пожалуйста, скинь строчки лога, которые появятся чуть выше слова FAILURE."
fi
