# Сервис матчера для проверки

Этот подпроект предоставляет HTTP API матчера для официальной проверки распознавания
винных этикеток. Сервис поддерживает два backend: `siglip2` и `mock`. Конфигурация по
умолчанию `matcher/config.yaml` выбирает pipeline `siglip2-p512-as-is`.

Матчер не зависит от workbench. Он не импортирует код workbench и не читает
`lab.sqlite3`. Данные каталога приходят только через embedding bundle.

## Что делает сервис

Сервис принимает одну фотографию и возвращает slug вина:

~~~json
{"slug":"massandra-muskatel-belyy-belye-sorta-vinograda-beloe-sladkoe-16"}
~~~

Тестовый mock pipeline узнаёт три тестовых изображения по SHA-256. Для любого другого
изображения он возвращает пустой slug:

~~~json
{"slug":""}
~~~

## Требования

- Python 3.11 или новее.
- Пакеты из matcher/requirements.txt. Файл фиксирует точную версию каждого прямого
  пакета, включая pydantic.

Используйте Python-окружение проекта и установите зависимости:

~~~bash
~/.venvs/svoe-vino-lab/bin/pip install -r matcher/requirements.txt
~~~

Команды нужно выполнять из корня svoe-vino-lab.

## Конфигурация

По умолчанию сервис читает файл matcher/config.yaml. Этот файл выбирает pipeline
`siglip2-p512-as-is`. Переменная SVOE_VINO_MATCHER_CONFIG может указать другой файл.
Формат использует ту же структуру pipeline, что и svoe-vino-lab/workbench/config.yaml:

~~~yaml
matcher:
  pipeline: <pipeline-name>
  output_dir: "{env:SVOE_VINO_MATCHER_OUTPUT_DIR}"

pipeline:
  - name: <pipeline-name>
    backend: mock
    answers:
      <image-sha256>: <slug>
    unknown_slug: ""
~~~

Значение matcher.pipeline должно совпадать с name одной записи в списке pipeline. Поля
name и backend используют ту же структуру, что и svoe-vino-lab/workbench/config.yaml.

Чтобы включить Bearer-авторизацию, укажите имя переменной окружения с секретом:

~~~yaml
matcher:
  token: "{env:SVOE_VINO_MATCHER_TOKEN}"
~~~

Поле matcher.token содержит только точную ссылку `"{env:NAME}"` на переменную
окружения. Секретный токен не хранится в YAML.

Backend mock вычисляет SHA-256 загруженного изображения. Затем он ищет этот SHA-256 в
answers. Поле unknown_slug задаёт ответ для неизвестного изображения.

### Backend siglip2

Backend siglip2 вычисляет один вектор SigLIP2 для фотографии и ищет ближайшее вино в
embedding bundle:

~~~yaml
pipeline:
  - name: siglip2-p512-as-is
    backend: siglip2
    bundle: matcher/data/gx10-siglip2-so400m-patch16-naflex-p512
    endpoint: "{env:SIGLIP2_ENDPOINT}"
~~~

- Поле bundle задаёт каталог bundle. Относительный путь вычисляется от рабочего каталога
  процесса.
- Поле endpoint содержит корневой URL OpenAI-совместимого шлюза или точную ссылку
  `"{env:NAME}"`. Пример значения: `http://192.168.86.14:18081`. Сервис отправляет
  `POST <endpoint>/v1/embeddings`.
- Имя модели и `extra_body` backend берёт из `manifest.json` bundle. Для этого bundle это
  `siglip2-so400m-patch16-naflex` и `max_num_patches: 512`.

Backend выполняет шаги lab pipeline `siglip2-p512-as-is`:

1. Применяет EXIF-ориентацию.
2. Кладёт прозрачные пиксели на белый фон.
3. Уменьшает длинную сторону до 1024 пикселей с сохранением пропорций. Меньшее
   изображение не увеличивается.
4. Отправляет PNG в endpoint и нормализует вектор.
5. Сравнивает вектор с векторами view `full` в bundle. Векторы view `label` не
   участвуют.
6. Возвращает slug вина с лучшим косинусом. При равенстве побеждает меньший slug.

Backend не выполняет сегментацию и не обращается к SAM3. Сервис загружает bundle при
запуске. Он проверяет формат, версию, SHA-256 файлов `vectors.npy` и `candidates.jsonl`
и форму матрицы. Ошибка endpoint во время запроса даёт HTTP 500.

### Embedding bundle

Bundle не хранится в git. Каталог `matcher/data/` указан в `matcher/.gitignore`.
Соберите bundle в workbench и проверьте его:

~~~bash
cd workbench
python3 scripts/build_matcher_bundle.py \
    --embedding gx10-siglip2-so400m-patch16-naflex-p512 \
    --out ../matcher/data/gx10-siglip2-so400m-patch16-naflex-p512
python3 scripts/validate_matcher_bundle.py \
    ../matcher/data/gx10-siglip2-so400m-patch16-naflex-p512
~~~

Скрипт сборки по умолчанию не копирует изображения. Матчеру изображения не нужны.
Bundle этого embedding без изображений занимает около 23 МБ.

Поле matcher.output_dir задаёт каталог изображений и журналов запросов. Оно принимает
обычный непустой путь или точную строку `"{env:NAME}"`. Во втором случае сервис читает
путь из переменной окружения NAME при запуске. Относительный путь вычисляется от
рабочего каталога процесса. Если поле отсутствует, сервис для обратной совместимости
читает SVOE_VINO_MATCHER_OUTPUT_DIR напрямую.

## Переменные окружения

- SVOE_VINO_MATCHER_PORT — обязательный порт для команд запуска и проверки.
- SVOE_VINO_MATCHER_CONFIG — необязательный путь к файлу конфигурации. Без этой
  переменной сервис читает matcher/config.yaml.
- SIGLIP2_ENDPOINT — корневой URL шлюза SigLIP2 для matcher/config.yaml, например
  `http://192.168.86.14:18081`. Значение не содержит `/v1`.
- SVOE_VINO_MATCHER_OUTPUT_DIR — каталог для изображений и журналов запросов в тестовой
  конфигурации. Поле matcher.output_dir ссылается на эту переменную. Сервис создаёт
  каталог, если он отсутствует.
- SVOE_VINO_MATCHER_MAX_IMAGE_BYTES — необязательный положительный целочисленный лимит
  размера одного изображения в байтах. Значение по умолчанию равно 20971520 байтам
  (20 МиБ).
- SVOE_VINO_MATCHER_TOKEN — секретный Bearer-токен. Сервис читает его, только если
  выбранная конфигурация содержит
  `matcher.token: "{env:SVOE_VINO_MATCHER_TOKEN}"`.
- SVOE_VINO_MATCHER_MAX_IMAGE_PIXELS — максимальное число пикселей. Значение по
  умолчанию равно 40000000.
- SVOE_VINO_MATCHER_UPLOAD_TIMEOUT_SECONDS — максимальное время загрузки полного HTTP
  body. Значение по умолчанию равно 30 секундам.
- SVOE_VINO_MATCHER_MAX_INFLIGHT_REQUESTS — максимальное число одновременно
  обрабатываемых запросов к predict. Значение по умолчанию равно 8.
- SVOE_VINO_MATCHER_MAX_QUEUED_REQUESTS — максимальное число запросов в очереди.
  Значение по умолчанию равно 16.
- SVOE_VINO_MATCHER_QUEUE_TIMEOUT_SECONDS — максимальное время ожидания в очереди.
  Значение по умолчанию равно 0.25 секунды.

## Запуск

Выберите свободный локальный порт и сохраните его номер в переменной окружения
SVOE_VINO_MATCHER_PORT. Этот подпроект не резервирует постоянный порт.

~~~bash
if [ -z "${SVOE_VINO_MATCHER_PORT:-}" ]; then printf 'Свободный порт: '; read -r SVOE_VINO_MATCHER_PORT; fi; export SVOE_VINO_MATCHER_PORT
export SVOE_VINO_MATCHER_CONFIG=matcher/tests/config.yaml
export SVOE_VINO_MATCHER_OUTPUT_DIR=work/matcher-requests
export SVOE_VINO_MATCHER_MAX_IMAGE_BYTES=20971520

~/.venvs/svoe-vino-lab/bin/python -m uvicorn matcher.app:app \
  --host 127.0.0.1 --port "$SVOE_VINO_MATCHER_PORT"
~~~

Эта команда запускает API с тестовым mock pipeline. Сервис читает конфигурацию только
при запуске. После изменения выбранного файла конфигурации перезапустите процесс.

Чтобы запустить pipeline siglip2 из matcher/config.yaml, соберите bundle и задайте
адрес шлюза:

~~~bash
unset SVOE_VINO_MATCHER_CONFIG
export SIGLIP2_ENDPOINT=http://192.168.86.14:18081
export SVOE_VINO_MATCHER_OUTPUT_DIR=work/matcher-requests

~/.venvs/svoe-vino-lab/bin/python -m uvicorn matcher.app:app \
  --host 127.0.0.1 --port "$SVOE_VINO_MATCHER_PORT"
~~~

Первый запрос после простоя модели загружает модель в шлюзе. Такой запрос занимает
несколько секунд и может приблизиться к лимиту official harness в 10 секунд. Следующие
запросы занимают меньше секунды.

Чтобы включить авторизацию, выберите config.token.yaml и задайте секрет:

~~~bash
export SVOE_VINO_MATCHER_CONFIG=matcher/tests/config.token.yaml
export SVOE_VINO_MATCHER_TOKEN='<secret-token>'
~~~

Если `matcher.token` указан, сервис не запустится без непустой переменной с этим
именем.

## Docker

Файл matcher/Dockerfile собирает образ сервиса. Контекст сборки — каталог matcher.
Соберите образ из закоммиченной ревизии в корне svoe-vino-lab:

~~~bash
REV=$(git rev-parse HEAD)
git archive "$REV:matcher" | docker build --build-arg REVISION="$REV" \
  -t "svoe-vino-lab-matcher:$REV" -
~~~

Label `org.opencontainers.image.revision` образа содержит хеш коммита. Контейнер
слушает порт 8080. Процесс работает от uid 1000. Образ задаёт две переменные:

- SVOE_VINO_MATCHER_CONFIG=/config/config.yaml;
- SVOE_VINO_MATCHER_OUTPUT_DIR=/data/requests.

Смонтируйте файл конфигурации только для чтения и каталог данных для записи. Каталог
данных должен принадлежать uid 1000.

~~~bash
docker run --rm -p 127.0.0.1:8080:8080 \
  -v "$PWD/config.yaml:/config/config.yaml:ro" \
  -v "$PWD/data:/data" \
  -e SAM3_ENDPOINT='<url>' \
  "svoe-vino-lab-matcher:$REV"
~~~

Переменные адресов сервисов моделей необязательны: SIGLIP2_ENDPOINT,
GROUNDING_DINO_ENDPOINT, SAM3_ENDPOINT, VLM_ENDPOINT, VLM_MODEL, QR_SCANNER_ENDPOINT.
Образ не задаёт ни одну из них. Pipeline siglip2 читает только ту переменную, на которую
ссылается его поле endpoint. Mock pipeline не читает ни одну из них. Внутри контейнера
адрес 127.0.0.1 указывает на сам контейнер. Для сервиса на хосте укажите LAN-адрес
хоста.

Образ не содержит bundle. Рабочий каталог контейнера — `/app`, поэтому путь
`matcher/data/<bundle>` из конфигурации означает `/app/matcher/data/<bundle>`.
Смонтируйте bundle только для чтения, например
`-v "$PWD/matcher/data/<bundle>:/app/matcher/data/<bundle>:ro"`. Скрипт сборки создаёт
каталог bundle с правами 0700. Каталог должен быть доступен для чтения uid 1000.

Развёртывание prod и dev на gx10 через Docker Compose описано в
`drink-atlas-workspace/deploy/gx10/matcher-prod.md`. Этот каталог не входит в
git-репозиторий svoe-vino-lab.

## API

Endpoint POST /v1/eval/predict принимает multipart/form-data. Изображение должно
находиться в поле image.

Пример запроса:

~~~bash
curl --form 'image=@matcher/tests/data/02eef911.webp' \
  "http://127.0.0.1:$SVOE_VINO_MATCHER_PORT/v1/eval/predict"
~~~

Для конфигурации с авторизацией добавьте заголовок:

~~~bash
curl --header "Authorization: Bearer $SVOE_VINO_MATCHER_TOKEN" \
  --form 'image=@matcher/tests/data/02eef911.webp' \
  "http://127.0.0.1:$SVOE_VINO_MATCHER_PORT/v1/eval/predict"
~~~

Ответ:

~~~json
{"slug":"massandra-muskatel-belyy-belye-sorta-vinograda-beloe-sladkoe-16"}
~~~

Сервис принимает только JPEG, PNG и WEBP. Он возвращает HTTP 400 для пустого файла.
Он возвращает HTTP 401 при неверном токене. Он возвращает HTTP 408 при таймауте
загрузки. Он возвращает HTTP 413 при превышении размера body, размера изображения или
числа пикселей. Он возвращает HTTP 415 для другого формата. Он возвращает HTTP 422 для
повреждённого изображения или отсутствующего поля image. Он возвращает HTTP 503, если
очередь заполнена или запрос ждал в ней слишком долго.

Лимит полного HTTP body равен `SVOE_VINO_MATCHER_MAX_IMAGE_BYTES` плюс 64 КиБ для
multipart-обрамления. Этот лимит действует и для chunked upload без Content-Length.

## Проверка готовности

Endpoint GET /healthz показывает готовность процесса и выбранный pipeline:

~~~bash
curl "http://127.0.0.1:$SVOE_VINO_MATCHER_PORT/healthz"
~~~

Ответ:

~~~json
{"status":"ok","pipeline":"official-eval-mock"}
~~~

Путь `/healthz` используется как распространённый адрес инфраструктурной readiness
probe. Он всегда публичный. Страницы документации и `/openapi.json` также публичны.
Авторизация защищает только POST /v1/eval/predict.

## Журнал запросов

Сервис сохраняет каждый принятый файл в каталоге SVOE_VINO_MATCHER_OUTPUT_DIR. Один
запрос создаёт отдельный каталог:

~~~text
<output-dir>/<YYYY-MM-DD>/<request-id>/image.<extension>
<output-dir>/<YYYY-MM-DD>/<request-id>/request.json
~~~

Файл request.json содержит:

- время начала и завершения обработки в UTC;
- длительность обработки в миллисекундах;
- IP-адрес непосредственного клиента;
- метод, путь, query string, версию HTTP и заголовки запроса;
- исходное имя, Content-Type, размер, SHA-256 и путь сохранённого изображения;
- HTTP status и найденный slug.

Значения заголовков authorization, cookie, proxy-authorization, x-api-key и
x-auth-token заменяются на `<redacted>`. Имена этих заголовков сохраняются. Если сервис
работает за reverse proxy, поле client_ip содержит адрес proxy. Исходный адрес клиента
остаётся в переданном заголовке, например x-forwarded-for.

Сервис также пишет одну строку `matcher_request` в журнал Uvicorn после обработки.
Строка содержит request id, IP, SHA-256, размер, длительность, HTTP status, slug и пути
сохранённых файлов. Каталог содержит изображения и данные запросов. Ограничьте доступ к
нему и задайте правила хранения.

Запрос, отклонённый до проверки изображения, создаёт строку `matcher_rejected`. Она
содержит IP, HTTP status, причину, заявленный Content-Length и длительность. Сервис не
сохраняет опасный, незавершённый или неавторизованный body на диск.

## OpenAPI

Контракт API находится в файле `matcher/openapi.yaml`. Запущенный сервис также
публикует автоматически сформированную документацию:

- Swagger UI: `http://127.0.0.1:$SVOE_VINO_MATCHER_PORT/docs`;
- ReDoc: `http://127.0.0.1:$SVOE_VINO_MATCHER_PORT/redoc`;
- OpenAPI JSON: `http://127.0.0.1:$SVOE_VINO_MATCHER_PORT/openapi.json`.

OpenAPI описывает GET /healthz, обязательное multipart-поле image, опциональную схему
BearerAuth, успешный ответ со строкой slug и ошибки HTTP 400, 401, 408, 413, 415, 422 и
503.

## Тестирование

Инструкции для автоматических тестов, ручного official harness и GitLab CI находятся в
файле [TESTING.md](TESTING.md).
