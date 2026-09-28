# «Своё Вино»: поиск вина по фотографии

Проект распознаёт вино по фотографии бутылки или этикетки. Пользователь получает
карточку вина и ссылку на каталог [vino-svoe.ru](https://vino-svoe.ru/).

Решение создано для задачи #10 от РСХБ.Цифра "Сканер российских вин с описанием на платформе Свое Вино". Репозиторий содержит:
- Web UI, 
- Telegram-бота, 
- HTTP matcher, 
- локальные model service, 
- сервис для обработки датасетов и проведения экспериментов.

## Что умеет система

- Принимает JPEG, PNG и WebP через Web UI, Telegram и HTTP API.
- Возвращает один slug через `POST /v1/eval/predict`.
- Возвращает до 20 кандидатов через `POST /v1/match`.
- Использует SigLIP2 и embedding index из 2 094 вин.
- Проверяет фотографии Telegram через ShieldGemma 2 до записи на диск.
- Использует SAM3 для поиска бутылки и этикетки.
- Показывает варианты, если уверенность результата недостаточна.
- Предлагает продукты к вину по данным выбранного магазина «Глобус».
- Сохраняет воспроизводимые benchmark runs и технический trace.

## Результаты

Текущий standalone matcher использует профиль `siglip2-p512-as-is`.
На внутреннем наборе он получил **74,15% R@1** и **92,94% R@5**.

!!!TODO указать что представляет собой набор.

Лучший исследовательский pipeline получил **84,67% R@1** и **97,02% R@5**.
Он использует barcode, SAM3 crop и cluster re-rank. Эти этапы пока не входят в
standalone matcher. Методика и ограничения описаны в [BENCHMARKS.md](BENCHMARKS.md).

## Быстрый запуск интерфейса

```bash
cd webui
npm ci
npm run dev
```

Откройте [http://127.0.0.1:8153](http://127.0.0.1:8153).
По умолчанию Web UI явно работает в mock mode. Для реального распознавания нужен
matcher и model endpoint. Полная инструкция находится в [SETUP.md](SETUP.md).

## Компоненты

| Каталог | Назначение |
| --- | --- |
| `webui/` | Nuxt Web UI, evaluator route и рекомендации еды. |
| `telegram-bot/` | Бот [@ChtoZaVinoBot](https://t.me/ChtoZaVinoBot), moderation и очередь. |
| `matcher/` | FastAPI matcher с Top-1 и ranked API. |
| `bootstrap/` | Локальные endpoints SigLIP2, SAM3, ShieldGemma 2 и QR scanner. |
| `matcher-inspector/` | Read-only просмотр запросов и embedding bundles. |
| `workbench/` | Данные, индексы, эксперименты, benchmarks и сборка bundles. |

## Документация

- [Архитектура](ARCHITECTURE.md)
- [Benchmarks](BENCHMARKS.md)
- [Установка и запуск](SETUP.md)
- [Matcher API](matcher/README.md)
- [Telegram-бот](telegram-bot/README.md)
- [Web UI](webui/README.md)
- [Развертывание локальных моделей](docs/bootstrap/README.md)
- [Эндпоинты моделей на Apple Silicon](docs/bootstrap/apple-silicon.md)
- [Эндпоинты моделей на Selectel RTX 4090](docs/bootstrap/selectel-rtx4090.md)

## Ограничения

- Model weights и embedding bundle не хранятся в Git.
- Реальный запуск требует SigLIP2 endpoint и bundle.
- Shelf mode в Web UI выключен по умолчанию.
- Лаборатория и inspector не имеют публичной аутентификации. Их нельзя публиковать в WAN.
- Benchmark является внутренней инженерной оценкой. Это не официальный score хакатона.
