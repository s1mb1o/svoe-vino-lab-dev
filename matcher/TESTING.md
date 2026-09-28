# Тестирование matcher

Этот документ описывает тестовые конфигурации, автоматические тесты и ручной запуск
official harness. Выполняйте команды из корня `svoe-vino-lab`.

## Требования

- Python 3.11 или новее.
- Пакеты из `matcher/requirements.txt`.
- bash, curl, jq и awk для `participant_test.sh`.

Установите зависимости в Python-окружение проекта:

~~~bash
~/.venvs/svoe-vino-lab/bin/pip install -r matcher/requirements.txt
~~~

## Тестовые конфигурации

Файл `matcher/tests/config.yaml` содержит mock pipeline для проверки API:

~~~yaml
matcher:
  pipeline: official-eval-mock
  output_dir: "{env:SVOE_VINO_MATCHER_OUTPUT_DIR}"

pipeline:
  - name: official-eval-mock
    backend: mock
    answers:
      <image-sha256>: <slug>
    unknown_slug: ""
~~~

Эта конфигурация не требует авторизации. Файл `matcher/tests/config.token.yaml`
проверяет тот же pipeline с Bearer-авторизацией:

~~~yaml
matcher:
  pipeline: official-eval-mock
  output_dir: "{env:SVOE_VINO_MATCHER_OUTPUT_DIR}"
  token: "{env:SVOE_VINO_MATCHER_TOKEN}"
~~~

Поле matcher.token содержит только точную ссылку `"{env:NAME}"` на переменную
окружения. Секретный токен не хранится в YAML. Комментарии в начале каждого файла
объясняют назначение конфигурации. Эти файлы предназначены только для тестов и
локального mock-запуска. Они не заменяют будущий рабочий файл `matcher/config.yaml`.

Тесты явно задают `SVOE_VINO_MATCHER_CONFIG=matcher/tests/config.yaml`. Они также
создают временный `SVOE_VINO_MATCHER_OUTPUT_DIR` и задают отдельный лимит файла.

## Автоматические тесты

Запустите полный набор тестов:

~~~bash
~/.venvs/svoe-vino-lab/bin/python -W error::ResourceWarning \
  -m unittest discover -s matcher/tests -v
~~~

Параметр `-W error::ResourceWarning` преобразует предупреждение о незакрытом ресурсе в
ошибку теста. Набор содержит 69 тестов.

### API и official harness

Интеграционный тест запускает FastAPI на временном свободном порту. Затем тест запускает
локальную копию `participant_test.sh` с локальными `queries.tsv` и изображениями.

Тесты проверяют следующие условия:

- `GET /healthz` возвращает состояние готовности и имя pipeline.
- Неизвестное изображение возвращает пустой slug.
- Пустой файл возвращает HTTP 400.
- Слишком большой файл возвращает HTTP 413.
- Отсутствующее поле image возвращает HTTP 422.
- Первая строка JSONL содержит пять документированных полей.
- JSONL содержит полный SHA-256, ожидаемый slug и неотрицательный `latency_ms`.
- Архив запроса содержит изображение, заголовки, IP, SHA-256, результат и длительность.
- Разобранный `matcher/openapi.yaml` полностью совпадает с живым `/openapi.json`.

### Конфигурация и авторизация

Unit tests отклоняют повреждённый YAML, неизвестный pipeline, дублированное имя
pipeline, неверный SHA-256 и неподдерживаемый backend. Они проверяют обычный output
directory, ссылку `"{env:NAME}"`, конфигурацию без output_dir, отсутствующую или пустую
переменную окружения и неверную ссылку. Для matcher.token они отдельно проверяют точную
ссылку, bare-имя, malformed-ссылки, отсутствующую и пустую переменную. Устаревший ключ
matcher.token_env также отклоняется.

Тесты авторизации проверяют публичный доступ к `/healthz` и OpenAPI. Они проверяют
отсутствующий токен, неверную схему, неверное значение и успешный Bearer-запрос.

### Устойчивость

Тесты устойчивости используют локальные сокеты. Они отправляют следующие данные:

- JPEG с объявленными размерами 65535 × 65535;
- повреждённое изображение;
- неподдерживаемый GIF;
- chunked body сверх лимита;
- медленную загрузку;
- запрос при заполненной очереди.

Отдельный тест создаёт sparse-файл размером 1 ГиБ. Тест проверяет ранний отказ по
Content-Length без передачи содержимого файла. После каждого сценария тест проверяет
`/healthz` и обработку обычного JPEG.

### Backend siglip2

Файл `matcher/tests/test_siglip2.py` не использует настоящий bundle и шлюз gx10. Тест
создаёт маленький bundle во временном каталоге в формате
`workbench/pipeline/matcher_bundle.py`. Локальный fake-сервер отвечает на
`POST /v1/embeddings` заданным вектором. Поэтому тесты работают в CI без сети.

Тесты проверяют следующие условия:

- Top-1 определяет лучший косинус view `full`. Вектор view `label` не участвует.
- Изображение двух вин отдаёт Top-1 меньшему slug.
- Запрос содержит имя модели и `max_num_patches` из bundle и один PNG data URI.
- PNG имеет белый фон вместо прозрачности и длинную сторону 1024 пикселя.
- Маленькое изображение не увеличивается. EXIF-ориентация применяется.
- HTTP 500, вектор другой размерности и нулевой вектор дают `Siglip2Error`.
- Неверные поля bundle и endpoint, отсутствующая переменная окружения, изменённый payload,
  другой формат bundle и bundle без view `full` дают `ConfigError`.
- `matcher/config.yaml` выбирает pipeline `siglip2-p512-as-is`.
- Official harness получает slug через uvicorn, pipeline siglip2 и fake-сервер.

### POST /v1/match

Файл `matcher/tests/test_match.py` создаёт маленький bundle версии 2 во временном
каталоге. Он использует fake-сервер из `test_siglip2.py`. Тесты проверяют следующие
условия:

- Первое вино `Bundle.ranked` совпадает с `Bundle.top1`.
- Ранжированные вина не повторяются и идут по убыванию score. При равенстве меньший slug
  идёт первым. Вино без вектора view `full` не участвует.
- Bundle версии 1 не содержит карточек. Bundle версии 2 отдаёт карточки с `sugar`.
- Изменённый `wines.jsonl` отклоняется.
- Правила `sugar` совпадают с правилами telegram-bot.
- Mock ставит slug известного изображения первым со score 1.0 и дополняет список
  случайными винами. Для неизвестного изображения mock отдаёт до `k` случайных вин.
  Slug без карточки пропускается.
- Backend siglip2 ранжирует view `full` и пропускает вино без карточки. Ответ
  POST /v1/eval/predict при этом не меняется.
- Через uvicorn POST /v1/match возвращает ранги, score, карточки, pipeline и
  `latency_ms`. `k=2` ограничивает список. `k=0`, `k=21` и `k=x` дают HTTP 422.
  Запрос без токена даёт HTTP 401. Пустой файл даёт HTTP 400. Журнал запроса содержит
  slug кандидатов.
- Pipeline без карточек даёт HTTP 503.

### Каталог лаборатории

Файл `matcher/tests/test_catalog.py` создаёт маленький каталог во временном
каталоге: `catalog.sqlite3` с двумя view в виде таблиц, `index.json` и файл векторов.
Тесты проверяют следующие условия:

- Каталог и bundle тех же данных дают одинаковые slug, векторы каждого view и ответы
  `top1` и `ranked`.
- Close-up роли `label` участвует только во view `label`.
- Карточка содержит `page_url`, `image_url` с URL-кодированием имени файла,
  нормализованные уникальные `qr_urls` и `sugar`. Вино без элемента индекса не
  получает карточку.
- Нет view или другие столбцы, неверное имя или отсутствие файла векторов, номер
  строки вне матрицы, ненормализованные векторы, другой тип или форма матрицы и
  неверное имя embedding дают `CatalogError`.
- Pipeline siglip2 и mock читают поля catalog и embedding. Оба поля bundle и catalog,
  catalog без embedding и embedding без catalog дают `ConfigError`.

Правила view проверяет `workbench/tests/test_matcher_views.py`. Скрипт копии
проверяет `workbench/tests/test_catalog_copy.py`.

### POST /v1/group/match

Файл `matcher/tests/test_group.py` проверяет групповой endpoint без настоящего SAM3.
Unit tests используют fake opener. Интеграционные тесты используют локальные fake SAM3
и uvicorn.

Тесты проверяют следующие условия:

- Сервис применяет EXIF-ориентацию и удаляет metadata.
- Сервис ограничивает box размерами изображения.
- Сервис обрезает прозрачную PNG-маску по box.
- Сервис удаляет дубли с IoU не меньше 0.9.
- Сервис сортирует бутылки по полке и слева направо.
- Лимит бутылок и лимит размера ответа устанавливают `truncated=true`.
- Пустой ответ SAM3 вызывает один повторный запрос.
- Неверный endpoint и неверные данные SAM3 дают явную ошибку.
- POST /v1/group/match возвращает preview, координаты, маски и карточки вин.
- Bearer-авторизация защищает групповой endpoint.
- SigLIP2 обрабатывает несколько crop в одном embedding-запросе.
- Статический OpenAPI совпадает с OpenAPI запущенного приложения.

### Живая проверка siglip2

Живая проверка использует настоящий bundle и шлюз gx10. Она не входит в CI. Запустите
matcher с `matcher/config.yaml` по инструкции из [README.md](README.md) и выполните
official harness из следующего раздела.

Ответ Top-1 каждого изображения должен быть slug из `wines.jsonl` bundle. Два из трёх
ожидаемых slug mock pipeline отсутствуют в каталоге bundle, поэтому живая проверка не
сравнивает ответы с `queries.tsv`. Результаты проверок записаны в
`workbench/ChangeLog.md`.

## Ручная проверка official harness

Копия официального тестового клиента находится в `matcher/tests/participant_test.sh`.
Манифест находится в `matcher/tests/queries.tsv`. Три изображения находятся в
`matcher/tests/data/`. Соседний репозиторий `svoe-wino-hackaton` не требуется.

Запустите matcher по инструкции из [README.md](README.md). Затем выполните:

~~~bash
bash matcher/tests/participant_test.sh \
  --images-dir matcher/tests/data \
  --manifest matcher/tests/queries.tsv \
  --endpoint "http://127.0.0.1:$SVOE_VINO_MATCHER_PORT/v1/eval/predict" \
  --output /tmp/svoe-vino-matcher-predictions.jsonl
~~~

Файл результата не должен существовать до запуска. Скрипт отправляет изображения по
одному. Он создаёт одну строку JSON для каждого запроса.

Пример строки результата:

~~~json
{"query_id":"q-000001","image_path":"019c68d0.jpg","image_sha256":"c975b31e...","predicted_slug":"tabia_pino_nuar","latency_ms":12}
~~~

Если matcher вернул пустой slug, поле predicted_slug равно null.

## GitHub Actions

Workflow `.github/workflows/matcher-tests.yml` запускается для изменений в `matcher/`,
для изменений самого workflow и вручную. Job `matcher-tests` использует self-hosted
runner с labels `self-hosted`, `Linux`, `X64` и `docker`.

Workflow повторяет pull образа `python:3.11-slim` до трёх раз. Он монтирует исходники в
одноразовый контейнер только для чтения. Контейнер устанавливает curl, jq и зависимости
из `matcher/requirements.txt` с помощью `matcher/tests/run_ci.sh`. Затем скрипт запускает
все тесты, которые обнаруживает `unittest`. Job завершается с ошибкой, если тест не был
запущен или был пропущен. В конце журнала должна быть строка
`matcher tests: discovered=69 run=69 skipped=0`.

## GitLab CI

Job `matcher-tests` находится в корневом файле `.gitlab-ci.yml`. GitLab использует
образ `python:3.11-slim`. Job устанавливает curl и jq, устанавливает зависимости из
`matcher/requirements.txt`, запускает `pip check` и выполняет полный набор из 69 тестов.

Pipeline должен завершить job `matcher-tests` со статусом passed. В логе должна быть
строка `Ran 69 tests` и итог `OK`.
