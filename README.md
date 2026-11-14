# Наш атлас

Карта путешествий: наши места из Google Карт, правила въезда по паспортам, безопасность по странам.

## Как устроено

- `site/index.html` — исходник приложения (вся логика и стили).
- `site/data/` — данные: границы, города, правила въезда, безопасность, списки мест.
- `scripts/` — сборка данных и самого сайта.
- `web-src/` — иконки и service worker для версии-сайта.

## Сборка

```bash
cd build && npm i d3 topojson-client jszip @fontsource/unbounded @fontsource/manrope && cd ..
python3 scripts/build_web.py          # сайт в папку web/
python3 scripts/build_standalone.py   # один HTML-файл в out/
```

Папку `web/` можно выложить на любой статический хостинг. Сайт работает без интернета для того, что уже открывали (service worker включается на https).

## Источники данных

Natural Earth, OpenStreetMap / OpenTopoMap, Passport Index (MIT), OurAirports (public domain), Wikimedia Commons (обложки паспортов, свободные лицензии), ACLED, МИДы стран.

## Аккаунты (Supabase)

1. Создать проект на supabase.com (регион Frankfurt).
2. SQL Editor → вставить `supabase/schema.sql` → Run.
3. Authentication → URL Configuration: Site URL и Redirect URLs — адрес сайта, например `https://ИМЯ.github.io/nash-atlas/`.
4. Authentication → Emails → шаблон «Magic Link»: добавить код `{{ .Token }}`, чтобы в письме была и ссылка, и код.
5. Project Settings → API: адрес проекта и anon (publishable) ключ вписать в `web-src/config.js`. Этот ключ публичный: доступ ограничивают правила в базе.

## Публикация (GitHub Pages)

Settings → Pages → Source: GitHub Actions. Каждый push в `main` пересобирает и публикует сайт (`.github/workflows/pages.yml`).
