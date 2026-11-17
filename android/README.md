# Android-приложение «Наш атлас» (TWA)

Приложение — это сам сайт nash-atlas.ru в оболочке Android (Trusted Web Activity): без адресной строки, с иконкой на экране. Никакого отдельного кода: обновляете сайт, и приложение обновляется вместе с ним. Новый файл для магазина нужен, только когда меняются иконка, название или настройки в `twa-manifest.json`.

Пакет: `ru.nashatlas.app`. Приложение открывает боевой сайт nash-atlas.ru, не бету.

> Конфиг и порядок ниже подготовлены без сборки: в среде, где я работал, нет Android SDK и доступа к Maven. Первая сборка у вас может потребовать мелких правок.

## 1. Что нужно на компьютере
- Node.js 18+ и JDK 17 (`java -version`).
- `npm i -g @bubblewrap/cli`. При первом запуске Bubblewrap предложит скачать Android SDK, соглашайтесь.

## 2. Ключ подписи
Один раз, в папке `android/`:

```bash
keytool -genkeypair -v -keystore atlas-release.keystore -alias atlas -keyalg RSA -keysize 2048 -validity 10000
```

- Файл `atlas-release.keystore` и пароль храните вне репозитория и сделайте копию в двух местах: потерянный ключ нельзя восстановить. `.gitignore` не пускает `*.keystore` в git.
- Если включена «Подпись приложения Google Play» (по умолчанию для новых приложений), отпечаток для `assetlinks.json` берётся из Play Console: «Целостность приложения» → «Подпись приложения» → SHA-256 ключа подписи приложения (не ключа загрузки).

## 3. Сборка
```bash
cd android
bubblewrap update      # собирает Android-проект из twa-manifest.json
bubblewrap build       # app-release-bundle.aab (для Google Play) и app-release-signed.apk (для проверки на телефоне)
```
Если `update` не стартует без проекта, один раз выполните `bubblewrap init --manifest=https://nash-atlas.ru/manifest.webmanifest`, затем замените созданный `twa-manifest.json` нашим.

Перед каждой новой загрузкой в магазин увеличивайте `appVersionCode` (и при желании `appVersion`) в `twa-manifest.json`.

## 4. Связь приложения с сайтом (assetlinks.json)
Без неё приложение откроется с адресной строкой Chrome.
1. Впишите SHA-256 отпечаток в `android/fingerprint.txt` (строка вида `AA:BB:...`, можно несколько: ключ загрузки и ключ Google).
2. Сборка сайта (`scripts/build_web.py`) создаст `/.well-known/assetlinks.json`.
3. После публикации в `main` проверьте https://nash-atlas.ru/.well-known/assetlinks.json в браузере. Если файла нет, значит GitHub Pages не отдал папку с точкой, это надо исправить в `pages.yml`.

## 5. Проверка на телефоне
Установите `app-release-signed.apk` (разрешив установку из файла). Приложение должно открыться без адресной строки. Если она есть, значит `assetlinks.json` не связан с ключом.

## 6. Карточка в Google Play
Иконка 512×512 (`web-src/icon-512.png`), скриншоты телефона, описание, ссылка на политику https://nash-atlas.ru/privacy.html, форма «Безопасность данных», удаление аккаунта. Минимальный целевой уровень API (`targetSdkVersion`) Google повышает каждый год, перед загрузкой сверьте его в консоли.
