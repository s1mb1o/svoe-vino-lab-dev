# Аудит готовности `svoe-vino-lab` к хакатону

Дата: 2026-09-26.

Репозиторий: `svoe-vino-lab`.

Снимок кода: commit `b71d5c9` и незакоммиченные изменения рабочего дерева.

Цель: оценить изолированный репозиторий глазами технического эксперта, жюри и LLM.

## Краткий вывод

Проект имеет сильную инженерную основу.
Проект имеет слабую хакатонную витрину.

Внутри проекта есть 846 тестов, строгая схема SQLite, OpenAPI, smoke-тесты, журнал
исследований, воспроизводимые run-артефакты и подробный benchmark.
Это существенно выше среднего уровня прототипа.

Первая страница репозитория не показывает эту ценность.
README начинает рассказ с неверного имени `svoe-vino-testset`.
README описывает старые каталоги, которые отсутствуют в корне.
README смешивает активную лабораторию и legacy-инструмент.
README имеет 2 413 строк.
В репозитории нет скриншота, видео, лицензии, CI и публичного quick start.

Изолированный репозиторий не даёт судье очевидный путь
`фото → распознавание → карточка вина → измеренный результат`.
Он показывает внутреннюю лабораторию и зависит от соседних репозиториев, локальной БД,
локальной модели и частных адресов.

Предварительная оценка инженерного качества: **8,0 из 10**.

Предварительная готовность к подаче: **54 из 100**.

После выполнения P0 проект может получить приблизительно **85 из 100** по запасной
матрице этого аудита.
Это не прогноз результата хакатона.
Официальная оценочная матрица отсутствует в изолированном репозитории.

## Ограничения аудита

1. Рабочее дерево активно меняют несколько сессий.
2. На момент проверки было 41 изменённый tracked-файл и 16 untracked-файлов.
3. Ветка `main` была на 7 commits впереди `origin/main`.
4. `origin` указывает на частный GitLab, а не на GitHub.
5. Идёт отдельный полный benchmark 45 pipelines.
6. Этот аудит не включает незавершённый результат этого benchmark.
7. В репозитории есть ссылка на `docs/task-10-specification.pdf`.
8. Указанный PDF отсутствует в репозитории.
9. Поэтому точные правила хакатона и точные веса критериев не проверены.
10. Оценка 54 из 100 использует запасную матрицу.

## Что это за проект

`svoe-vino-lab` является лабораторией для разработки и проверки поиска вина по фото.

Активная система выполняет следующие задачи:

1. Она хранит каталог и разметку в SQLite.
2. Она хранит изображения по SHA-256.
3. Она готовит package и label views через SAM3.
4. Она строит embedding indexes для нескольких моделей.
5. Она строит clusters похожих карточек.
6. Она строит VLM rules для сложных clusters.
7. Она запускает pipelines на тестовых наборах.
8. Она считает R@1, R@5, R@10, MRR, F1, SLA и ошибки near-duplicates.
9. Она показывает данные, эксперименты и ошибки в Web UI.

Проект также содержит legacy-поколение в `scripts/`.
Legacy-поколение строит тестовый набор и имеет отдельный review server.

Репозиторий не является законченным пользовательским приложением.
Репозиторий не содержит самостоятельный публичный search-by-photo service.
Эта роль находится в других компонентах рабочего пространства или во внешних APIs.

Для хакатона нужно выбрать один вариант:

1. Подать объединённый продукт с одним входом для судьи.
2. Чётко представить `svoe-vino-lab` как техническую лабораторию решения.
3. Добавить в этот репозиторий минимальный демонстрационный inference path.

Первый или третий вариант лучше для изолированной оценки.

## Проверенные сильные стороны

### Код и тесты

1. `python3 -m unittest discover -s tests` выполнил 846 тестов.
2. Все 846 тестов прошли.
3. Пять тестов были пропущены.
4. Прогон занял 137,261 секунды.
5. `python3 -m compileall -q pipeline scripts tests` завершился успешно.
6. Активный код `pipeline/` имеет 17 383 строки Python.
7. Тесты имеют 14 917 строк Python.
8. Соотношение тестового и активного кода высокое.
9. API проверяет ошибочные методы, пути, типы и конфликтующие операции.
10. Записи файлов используют content addressing и атомарную замену.
11. Run-артефакты сохраняют запросы, ответы, метрики и часть provenance.

### Данные и эксперименты

1. `PRAGMA integrity_check` вернул `ok`.
2. `PRAGMA foreign_key_check` не нашёл ошибку.
3. Схема имеет version 21.
4. База содержит 2 103 вина.
5. Таблица `image` содержит 9 551 строку.
6. Тестовые наборы содержат 4 323 фото.
7. Репозиторий хранит отдельный benchmark report.
8. Report описывает метод, denominators, ограничения и defects данных.
9. Report не скрывает плохие результаты.
10. Report сравнивает несколько model families и preprocessing variants.

### Документация

1. В репозитории есть README, ChangeLog, ResearchLog и SMOKE_TESTS.
2. В репозитории есть 45 implementation plans на момент снимка.
3. В репозитории есть decision record для SQLite architecture.
4. В репозитории есть OpenAPI на 3 355 строк.
5. В репозитории есть API guide на 635 строк.
6. В tracked Markdown есть 118 локальных ссылок.
7. Проверка не нашла битую локальную Markdown-ссылку.
8. `AGENTS.md` и `CLAUDE.md` задают строгие правила совместной работы.
9. Проект фиксирует owner decisions и технические исследования.

### Интерфейс

1. Страницы Dataset, Embeddings, Clusters, Testset, Runs и Health используют общий UI.
2. Dataset показывает 2 103 записи и инструменты ручной проверки.
3. Runs показывает подробные результаты каждого запроса.
4. Health показывает базу, watcher, jobs, models и endpoints.
5. Интерфейс поддерживает светлую и тёмную системную тему.

## Главные проблемы

### 1. Репозиторий не объясняет продукт на первом экране

Severity: P0.

Evidence:

- Заголовок README: `svoe-vino-testset`.
- Имя репозитория: `svoe-vino-lab`.
- Первый абзац говорит только про test data.
- README не начинает рассказ с задачи, пользователя и результата.
- В README нет hero image, screenshot, GIF или demo link.
- В README нет headline benchmark.
- В README нет команды для судьи.

Impact:

LLM может классифицировать проект как набор данных или внутреннюю утилиту.
Человек может не найти основную ценность до конца проверки.

Change:

Сделать новый короткий README на русском языке.
Перенести текущую подробную справку в `docs/reference/`.
Поставить в первые 40 строк:

1. название;
2. одно предложение про результат;
3. задачу хакатона;
4. core user journey;
5. один screenshot или GIF;
6. честную headline metric;
7. demo link или одну команду;
8. ссылку на architecture и полные результаты.

Acceptance:

Новый человек объясняет проект после 60 секунд чтения.

### 2. Нет самостоятельного demo path

Severity: P0.

Evidence:

- `config.yaml` содержит абсолютный путь `/Volumes/T7_2TB/...`.
- Конфигурация содержит адреса `192.168.86.14`.
- Команды используют соседние репозитории.
- `data/`, `runs/` и фото игнорируются Git.
- Зависимости и model artifacts не скачиваются одной командой.
- Изолированный clone не может повторить demo.

Impact:

Судья не может проверить completion.
LLM отметит проект как environment-dependent.

Change:

Добавить один режим для судьи.
Рекомендуемый вариант:

1. `demo/` содержит 3–10 разрешённых sample photos.
2. `demo/` содержит маленький precomputed catalogue index или download manifest.
3. `config.demo.yaml` использует только relative paths.
4. `./demo.sh` или `make demo` запускает один понятный сценарий.
5. Сценарий показывает input, top candidates, выбранное вино, latency и explanation.
6. Режим не использует соседний repository.
7. Режим ясно отмечает precomputed parts.

Публичный deployment может заменить локальный режим.
Сырая лаборатория не должна быть доступна в интернет без защиты.

Acceptance:

Судья запускает demo на чистой машине за 10 минут или открывает public URL.

### 3. Нет короткого demo video и визуальных доказательств

Severity: P0.

Evidence:

- Git не содержит ни одного PNG, JPEG, GIF, WebP, SVG или video artifact.
- README не содержит media.
- UI существует только на localhost.

Impact:

Судья не видит работающий продукт без установки.
Первичный LLM не может оценить UX.

Change:

Сделать video длительностью 90–120 секунд.
Показать реальное фото.
Показать preprocessing, top candidates и итог.
Показать один сложный near-duplicate case.
Показать Runs evidence и Health в конце.
Добавить 3 screenshots и один result chart в README.

Acceptance:

Видео показывает работающий сценарий.
Видео не является набором slides.

### 4. Результат пока не достигает заявленного целевого уровня

Severity: P0 для algorithm score.

Evidence из `docs/reports/2026-09-26_embedding-benchmark.md`:

- Лучший `R@1` на `my`: 79,8% для 1 625 positive photos.
- Лучший `R@5` на `my`: 95,1%.
- Для 34 positive photos отсутствует catalogue image.
- Для пяти photos есть byte-equal leakage в чужие catalogue cards.
- На `official-real-photos` общий `R@1`: 69,5%.
- На subset с catalogue image `R@1`: 93,2% для 44 photos.
- Текущий vino-svoe.ru baseline имеет общий `R@1`: 57,6%.
- Новый pipeline улучшает общий R@1 на 11,9 percentage points.
- Но у нового pipeline false match at 1 равен 7 из 21 negative photos.
- У baseline это 4 из 21.
- Task document, который описывает target 90–100%, отсутствует в repository.

Impact:

Документация не может заменить недостающий algorithm result.
Headline `93,2%` без denominator будет вводить судью в заблуждение.

Change:

1. Добавить отсутствующие catalogue images.
2. Исправить две contaminated cards.
3. Добавить blocking leakage check.
4. Завершить benchmark 45 pipelines.
5. Выбрать final pipeline по официальной score function.
6. Добавить reject or abstain rule для no-match и low-margin cases.
7. Проверить fusion, barcode и cluster-rule rerank.
8. Выполнить serial no-cache final run.
9. Показать R@1, F1@1, F1@5, SLA, near-duplicate confusion и false matches.
10. Показать полный denominator.

Acceptance:

Final report соответствует официальной матрице.
Final report использует clean data snapshot.
Final report не использует скрытый subset как headline.

### 5. Нет clean release snapshot на GitHub

Severity: P0.

Evidence:

- Remote указывает на private GitLab.
- Ветка на 7 commits впереди remote.
- Рабочее дерево имеет 57 изменённых или untracked paths.
- Несколько sessions имеют completed but uncommitted work.
- В GitHub-specific `.github/` нет файлов.

Impact:

Публичная версия может не содержать результаты текущей работы.
Жюри не сможет связать submission с проверенным snapshot.

Change:

1. Остановить feature work перед release.
2. Завершить или удалить временные owner-approved changes.
3. Запустить verification gate.
4. Сделать clean commit.
5. Создать public GitHub repository.
6. Создать tag `hackathon-submission`.
7. Указать tag в submission.
8. Проверить repository view в incognito mode.

Acceptance:

`git status --short` пуст.
GitHub Actions зелёный.
Public tag содержит README, demo, license и final report.

### 6. Автоматическая проверка не является частью репозитория

Severity: P0.

Evidence:

- CI отсутствует.
- `pyproject.toml` отсутствует.
- Python version не зафиксирована.
- `requirements-local.txt` использует lower bounds.
- Lock file отсутствует.
- Ruff находит 39 errors во всём Python-коде.
- Ruff находит 4 errors в активном `pipeline/`.
- Два active findings имеют code `F821`.
- Ruff formatter хочет изменить 132 файла.
- Tests создают много `ResourceWarning` для files, HTTP errors и SQLite connections.

Impact:

Судья видит passed tests только как утверждение автора.
Dependency resolver может собрать другое окружение.

Change:

1. Зафиксировать supported Python version.
2. Добавить `pyproject.toml` с Ruff config.
3. Исправить 4 active Ruff findings.
4. Исправить значимые `ResourceWarning`.
5. Добавить lock file или exact judge requirements.
6. Добавить одну команду `make verify` или `scripts/verify.sh`.
7. Добавить GitHub Actions для compile, lint и unit tests.
8. Не запускать массовое форматирование перед deadline без отдельного review.

Acceptance:

Одна локальная команда и CI выполняют одинаковые checks.

### 7. Нет license и submission metadata

Severity: P0 для eligibility, если организатор требует public source.

Evidence:

- `LICENSE` отсутствует.
- OpenAPI содержит `LicenseRef-not-stated`.
- Team section отсутствует.
- Hackathon section отсутствует.
- AI-tool disclosure отсутствует.
- Data and model license table отсутствует.

Impact:

Организатор может не понять право на использование кода и данных.
Некоторые платформы требуют public repository и MIT License.
Точные правила этого хакатона не проверены.

Change:

Владелец должен выбрать лицензию.
Добавить team, hackathon, challenge, build period, credits, AI tools, model licenses и
data rights.
Не выбирать лицензию автоматически.

Acceptance:

Каждый обязательный submission field имеет один canonical answer.

## Качество кода

### Что сделано хорошо

1. Active pipeline разделён на domain modules.
2. SQLite migrations имеют последовательные номера.
3. Foreign keys проверяются перед commit migration.
4. Path traversal checks есть в run file access.
5. API возвращает точные error statuses.
6. Long model calls обычно выполняются вне write transaction.
7. Caches используют stable request fields.
8. Benchmark сохраняет raw rows и aggregate metrics.
9. UI предоставляет operational visibility.

### Что нужно исправить

1. `pipeline/derive.py` не читает canonical environment variable `SAM3_ENDPOINT`.
2. `config.yaml` содержит host-specific absolute path.
3. `pipeline/gdino.py` и `pipeline/run_steps.py` содержат hard-coded gateway address.
4. `pipeline/lab_server.py` разрешает `--host` без authentication и CSRF protection.
5. Public bind лаборатории может открыть write и process-control routes.
6. Model and run provenance не содержит полный artifact digest.
7. Migration ledger не хранит checksum SQL files.
8. `pipeline/lab_server.py` имеет 1 373 строки.
9. `pipeline/pages/dataset.html` имеет 3 144 строки.
10. `pipeline/pages/testset.html` имеет 2 339 строк.
11. Legacy `scripts/review_server.py` имеет 9 801 строку.
12. README не отделяет active system от retired system.

Эти проблемы важны для дальнейшей разработки.
Большинство из них имеют меньший judging impact, чем README, demo и final metrics.

## Качество документации

### Depth score

Оценка глубины: **9 из 10**.

Проект фиксирует почти каждое решение, API, план, test case и benchmark.

### Entry-point score

Оценка входа: **3 из 10**.

README перегружен и содержит stale statements.

Проверенные contradictions:

1. README называет проект `svoe-vino-testset`.
2. README говорит про корневые `eval/` и `my/`.
3. Эти каталоги отсутствуют в корне.
4. README говорит, что `config.yaml` имеет два keys.
5. Файл имеет сотни строк и много sections.
6. README говорит, что lab server открывает database read-only.
7. Тот же README описывает многочисленные write operations.
8. README одновременно описывает active lab и retired catalogue clusters.
9. README содержит локальные addresses и private infrastructure details.

Рекомендация: сохранить подробную документацию, но убрать её с landing page.

## Симуляция первичной проверки LLM

### Первые 30 секунд

LLM видит имя `svoe-vino-testset`.
LLM читает, что это test data.
LLM не видит problem statement, demo image, final metric или license.

Вероятный вывод:

> Это внутренний набор данных и лабораторный инструмент. Репозиторий не показывает
> самостоятельный пользовательский продукт и не даёт быстрый запуск.

Риск отсева: высокий.

### Первые 2 минуты

LLM видит SQLite, many scripts, private paths и detailed implementation notes.
LLM не видит одно canonical architecture diagram.
LLM не понимает, какой component является submission.

Вероятный вывод:

> Техническая работа значительная. Completion и reproducibility не доказаны для
> внешнего судьи.

Риск отсева: средне-высокий.

### Первые 10 минут

LLM находит 846 tests, OpenAPI и benchmark report.
LLM видит честные limitations и сильную experiment discipline.
Оценка технического качества резко растёт.

Вероятный вывод:

> Это сильная R&D-система. Она плохо упакована как хакатонная работа.

Основной риск состоит в том, что массовый screening не даст проекту эти 10 минут.

## Запасная оценочная матрица

Эта матрица не является official rubric.

| Area | Max | Now | После P0 | Причина текущей оценки |
|---|---:|---:|---:|---|
| Eligibility and task fit | 15 | 4 | 12 | Нет rules, license, team и public snapshot. |
| Problem, user, and value | 15 | 7 | 14 | Ценность скрыта глубоко в документации. |
| Working result and demo | 20 | 9 | 17 | Live lab работает, но нет public product demo. |
| Technical merit | 15 | 14 | 14 | Сильная data, model и evaluation system. |
| Evidence and evaluation | 15 | 12 | 13 | Сильный report, но data defects и metric gap остаются. |
| Reproducibility and completion | 10 | 3 | 7 | Private infrastructure и нет CI/lock/demo bundle. |
| UX and visual communication | 5 | 3 | 4 | Lab UI хорош, end-user journey не показан. |
| Repository trust | 5 | 2 | 4 | Нет CI/license, но tests и internal docs сильные. |
| **Total** | **100** | **54** | **85** | Potential зависит от final metric и actual rules. |

## Pareto-план

### P0. Первые 80% прироста оценки

| # | Доработка | Impact | Effort | Acceptance |
|---:|---|---|---|---|
| 1 | Новый русский README и перенос legacy reference. | Очень высокий | 4–6 ч | Ценность понятна за 60 секунд. |
| 2 | Видео 90–120 секунд, screenshots и result chart. | Очень высокий | 3–5 ч | Полный сценарий виден без установки. |
| 3 | Standalone demo или public deployment. | Очень высокий | 0,5–2 дня | Чистый clone даёт результат за 10 минут. |
| 4 | Clean GitHub release tag. | Очень высокий | 2–4 ч | Public tag, clean tree, все artifacts на месте. |
| 5 | Final benchmark на clean data. | Очень высокий | 0,5–2 дня | Официальные metrics, denominator, baseline и SLA. |
| 6 | CI, pinned judge environment и fix active Ruff errors. | Высокий | 4–8 ч | Одна verify command и зелёный CI. |
| 7 | License, team, credits, AI and data disclosure. | Высокий | 1–3 ч | Все eligibility fields заполнены. |
| 8 | Одно architecture diagram и rubric mapping. | Высокий | 2–4 ч | Судья видит components и task coverage на одном экране. |

### P1. Следующий прирост

1. Добавить `config.example.yaml` с relative paths.
2. Использовать `SAM3_ENDPOINT` во всех SAM3 clients.
3. Убрать hard-coded gateway hosts.
4. Добавить model and data provenance digests.
5. Добавить backup and restore verification.
6. Отделить active docs от legacy docs.
7. Исправить `ResourceWarning`.
8. Добавить authentication перед public deployment.
9. Добавить mobile screenshot и accessibility check.

### P2. После подачи

1. Разделить большие HTML и server modules.
2. Завершить удаление legacy write paths.
3. Добавить migration checksums.
4. Выполнить отдельный format-only commit.
5. Добавить CONTRIBUTING, CODE_OF_CONDUCT и issue templates.
6. Добавить coverage reporting после стабилизации CI.

## Рекомендуемая структура нового README

1. `# Своё Вино Lab — поиск вина по фотографии`.
2. Одна строка с результатом и target user.
3. Demo GIF или video thumbnail.
4. `Попробовать` с public URL или `make demo`.
5. `Результаты` с baseline chart.
6. `Как это работает` с diagram.
7. `Почему это сложно` с near-duplicates.
8. `Запуск для жюри`.
9. `Проверка` с `make verify`.
10. `Ограничения`.
11. `Команда и вклад`.
12. `Лицензии и AI tools`.
13. Links на полную technical documentation.

## Рекомендуемый сценарий видео

1. 0–10 секунд: проблема и результат.
2. 10–35 секунд: фото бутылки и top result.
3. 35–60 секунд: сложный near-duplicate case.
4. 60–80 секунд: pipeline diagram и key technical decision.
5. 80–100 секунд: benchmark against baseline.
6. 100–115 секунд: reproducibility, tests и Health.
7. 115–120 секунд: repository and team.

## Интернет-рекомендации

GitHub указывает, что README обычно является первым файлом для посетителя.
GitHub рекомендует описать назначение, пользу, запуск, поддержку и maintainers.
GitHub также рекомендует держать в README только информацию для начала работы.
Длинную справку нужно вынести из landing page.

Источник:
[GitHub: About READMEs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes).

GitHub community profile проверяет README, LICENSE, CONTRIBUTING и CODE_OF_CONDUCT.
Security policy также является частью repository trust.

Источник:
[GitHub: community profiles](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/about-community-profiles-for-public-repositories).

Devpost обычно ожидает image gallery, public demo video и code repository URL.
Некоторые forms требуют public repository и MIT License.
Нужно проверить exact rules этого хакатона.

Источник:
[Devpost: submission steps](https://help.devpost.com/article/126-know-your-submission-steps).

MLH рекомендует короткое видео, которое показывает demo, а не презентацию.
MLH оценивает technology, design, completion и learning в своей общей матрице.
Этот хакатон может использовать другую матрицу.

Источники:
[MLH standard rules](https://github.com/MLH/mlh-policies/blob/main/standard-hackathon-rules.md),
[MLH judging plan](https://github.com/MLH/mlh-hackathon-organizer-guide/blob/master/general-information/judging-and-submissions/judging-plan.md).

Devpost советует показать, что проект делает, как он решает задачу и как работает.
Devpost советует вынести ключевую информацию в начало короткого видео.

Источник:
[Devpost: demo video tips](https://info.devpost.com/blog/6-tips-for-making-a-hackathon-demo-video).

## Команды проверки

```text
git status --short --branch
git log --oneline --decorate -12
git ls-files
python3 -m unittest discover -s tests
python3 -m compileall -q pipeline scripts tests
ruff check pipeline scripts tests --statistics
ruff check pipeline
ruff format --check pipeline scripts tests
git diff --check
sqlite3 -readonly data/lab.sqlite3 'PRAGMA integrity_check;'
sqlite3 -readonly data/lab.sqlite3 'PRAGMA foreign_key_check;'
```

## Итог

Главная проблема проекта не состоит в недостатке кода.
Главная проблема состоит в том, что сильный код не виден на входе.

Нельзя начинать улучшение с большого refactoring.
Нужно сначала сделать понятный submission artifact, working demo и честный final result.
После этого CI, license и clean release закрепят доверие.
