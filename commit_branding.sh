#!/bin/bash
echo "🎨 Добавляем иконку и название приложения OpenHealth..."
mkdir -p app/src/main/res/values
mkdir -p app/src/main/res/drawable

git add icon.svg
git add app/src/main/res/values/strings.xml
git add app/src/main/res/drawable/vector_icon.xml
git add app/src/main/AndroidManifest.xml

git commit -m "style: add minimalist branding, SVG icon and app name OpenHealth"
git push origin main
echo "🚀 Брендинг успешно залит на GitHub!"
