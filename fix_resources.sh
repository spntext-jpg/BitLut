#!/bin/bash
set -e

echo "=== [1/3] Исправление ресурса иконки (Растеризация сложного SVG) ==="
# Удаляем сломанный вектор
rm -f app/src/main/res/drawable/ic_bitlut.xml

# Создаем временную среду Node для конвертации, чтобы не мусорить в Git
mkdir -p temp_icon_build
cd temp_icon_build
npm init -y > /dev/null
npm install sharp > /dev/null

# Конвертируем SVG в PNG (размер 512x512)
node -e "
const sharp = require('sharp');
sharp('../BitLut.svg')
  .resize(512, 512, { fit: 'contain' })
  .png()
  .toFile('../app/src/main/res/drawable/ic_bitlut_fg.png')
  .then(() => console.log('SVG успешно конвертирован в высококачественный PNG!'))
  .catch(err => { console.error('Ошибка конвертации:', err); process.exit(1); });
"
cd ..
rm -rf temp_icon_build # Убираем за собой

echo "=== [2/3] Исправление синтаксиса Adaptive Icon ==="
# Используем системный @android:color/white вместо #FFFFFF
cat << 'XML_EOF' > app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml
<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@android:color/white"/>
    <foreground android:drawable="@drawable/ic_bitlut_fg"/>
</adaptive-icon>
XML_EOF

cat << 'XML_EOF' > app/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml
<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@android:color/white"/>
    <foreground android:drawable="@drawable/ic_bitlut_fg"/>
</adaptive-icon>
XML_EOF

echo "=== [3/3] Запуск сборки и коммит ==="
