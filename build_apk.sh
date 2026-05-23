#!/bin/bash
echo "📦 Запуск сборки приложения OpenHealthSync..."
./gradlew assembleDebug

if [ $? -eq 0 ]; then
    echo "🎉 Сборка успешно завершена!"
    echo "📲 Твой готовый установочный файл находится по пути:"
    echo "app/build/outputs/apk/debug/app-debug.apk"
else
    echo "❌ Ошибка компиляции. Проверь логи выше."
fi
