# TODO до подачи на хакатон

Цель: один чистый public snapshot, который человек и LLM понимают за 60 секунд.

## P0. Обязательно

- [ ] **Зафиксировать правила и форму подачи.**
  Добавить `docs/HACKATHON.md`: название, задача, критерии, веса, deadline, team limits,
  обязательные links, video limit, правила лицензии и AI tools. Приложить разрешённую
  копию спецификации или официальный URL.

- [ ] **Сделать новый русский README.**
  Первые 40 строк: проблема, пользователь, решение, один GIF, лучший честный результат,
  baseline, `Попробовать`, architecture link. Перенести текущие 2 413 строк в
  `docs/reference/`. Исправить имя `svoe-vino-testset`.

- [ ] **Дать судье работающий путь.**
  Сделать `make demo` или public URL. Чистый clone должен показать путь
  `фото → top candidates → выбранное вино → latency`. Не требовать sibling repositories,
  private IP или личный absolute path.

- [ ] **Записать demo video 90–120 секунд.**
  Показать реальный input, обычный case, near-duplicate case, итог, benchmark и Health.
  Это должно быть demo, а не набор slides. Добавить 3 screenshots и result chart.

- [ ] **Закрыть metric gap на clean data.**
  Добавить отсутствующие catalogue images. Исправить contaminated cards. Включить
  leakage gate. Завершить 45-pipeline benchmark. Выбрать final pipeline. Выполнить
  serial no-cache run. Показать общий denominator, R@1, F1@1, F1@5, SLA, near-duplicate
  confusion и false matches. Не использовать `93,2%` без пояснения `44 photos`.

- [ ] **Добавить единый verification gate.**
  Зафиксировать Python version. Добавить lock или exact judge requirements.
  Исправить 4 Ruff findings в active `pipeline/` и значимые `ResourceWarning`.
  Одна команда должна запускать compile, lint и 846 tests. GitHub Actions должна
  запускать ту же команду.

- [ ] **Добавить trust metadata.**
  Владелец выбирает LICENSE. Добавить team, hackathon, challenge, credits, AI-tool
  disclosure, data rights и model licenses. Заменить `LicenseRef-not-stated`.

- [ ] **Сделать clean release.**
  Завершить параллельные changes. Получить пустой `git status`. Создать public GitHub
  repository и tag `hackathon-submission`. Проверить links и media в incognito mode.

## P1. Если P0 завершён

- [ ] Добавить one-screen architecture diagram с data flow и внешними services.
- [ ] Добавить `config.example.yaml` с relative paths и `.env.example` без secrets.
- [ ] Использовать `SAM3_ENDPOINT` и убрать hard-coded gateway hosts.
- [ ] Не публиковать raw lab server. Добавить auth и CSRF перед remote access.
- [ ] Добавить model, config, data и source digests в final run provenance.
- [ ] Исправить stale и retired sections. Оставить короткий canonical documentation path.

## Definition of done

Новый судья открывает public tag, понимает ценность за 60 секунд, смотрит полный demo
за две минуты, запускает judge path за 10 минут и получает те же headline metrics.
