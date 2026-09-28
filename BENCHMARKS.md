# Бенчмарки

Дата snapshot: 2026-09-27.

## Набор данных

- 2 228 query rows.
- 1 644 positive rows.
- 584 negative constraints.
- 1 851 уникальный image digest.
- Все 53 разрешённых профиля получили итоговый статус.
- 48 профилей дали валидный результат без query errors.
- Один профиль завершился с ошибками. Четыре профиля были недоступны из-за лимита памяти.

Negative row запрещает конкретное вино. Он не задаёт правильный ответ.

## Основные результаты

| Pipeline | Статус | R@1 | R@5 | Forbidden Top-1 | Bulk p50 / p95 |
| --- | --- | ---: | ---: | ---: | ---: |
| `siglip2-p512-as-is` | Текущий standalone matcher | 74,15% | 92,94% | 111 / 584 | 150 / 235 ms |
| `barcode-rerank-siglip2-512-crop` | Лучший R@1 в workbench | **84,67%** | 97,02% | 90 / 584 | 186 / 552 ms |
| `barcode-siglip2-p1024-crop` | Лучший R@5 в workbench | 83,33% | **97,99%** | 98 / 584 | 171 / 397 ms |

Bulk latency измерена с caches и четырьмя workers. Она не равна cold-start latency
публичного HTTP запроса.

## Проверка standalone matcher

- Bundle содержит 2 094 вина и 4 642 vectors размерности 1 152.
- Model input matcher совпал с workbench в 400 из 400 проверок.
- Top-1 matcher совпал с workbench в 100 из 100 проверок.
- Official harness получил 3 из 3 ответов за 334–455 ms после загрузки модели.
- Bundle версии 2 сохранил Top-1 старого bundle в 300 из 300 vector checks.

Эти проверки подтверждают перенос pipeline в standalone service. Они не заменяют
полный accuracy benchmark.

## Ограничения

- Это внутренний test set, а не официальный hidden set.
- 67 групп одинаковых bytes имеют несовместимые positive labels.
- Условный optimistic ceiling при текущей разметке равен 1 576 / 1 644, или 95,86%.
- Лучший workbench pipeline пока не является текущим standalone matcher.
- Результаты разных indexes имеют различное catalogue coverage.

Полный отчёт: [final profile comparison](workbench/docs/reports/2026-09-27_all-profile-rerun/final-profile-comparison.md).
Аудит разметки: [annotation audit](workbench/docs/reports/2026-09-27_all-profile-rerun/annotation-audit.md).
