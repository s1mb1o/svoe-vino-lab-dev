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
ошибку теста. Набор содержит 37 тестов.

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
runner с labels `self-hosted`, `Linux`, `X64` и `svoe-vino-lab`. Docker runner этому
job не нужен.

Workflow проверяет наличие bash, curl, jq, awk и утилиты SHA-256. Он устанавливает
Python 3.11 и зависимости из `matcher/requirements.txt`. Затем он запускает все тесты,
которые обнаруживает `unittest`. Job завершается с ошибкой, если тест не был запущен или
был пропущен.

## GitLab CI

Job `matcher-tests` находится в корневом файле `.gitlab-ci.yml`. GitLab использует
образ `python:3.11-slim`. Job устанавливает curl и jq, устанавливает зависимости из
`matcher/requirements.txt`, запускает `pip check` и выполняет полный набор из 37 тестов.

Pipeline должен завершить job `matcher-tests` со статусом passed. В логе должна быть
строка `Ran 37 tests` и итог `OK`.
