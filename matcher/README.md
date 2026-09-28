# Сервис матчера для проверки

Этот подпроект предоставляет HTTP API матчера для официальной проверки распознавания
винных этикеток. Сейчас сервис использует простой и полностью предсказуемый mock pipeline.

## Что делает сервис

Сервис принимает одну фотографию и возвращает slug вина:

~~~json
{"slug":"massandra-muskatel-belyy-belye-sorta-vinograda-beloe-sladkoe-16"}
~~~

Mock pipeline узнаёт три тестовых изображения по SHA-256. Для любого другого изображения
сервис возвращает пустой slug:

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

По умолчанию сервис ожидает рабочий файл по пути matcher/config.yaml. Этот файл будет
добавлен вместе с реальным pipeline. Переменная SVOE_VINO_MATCHER_CONFIG может указать
другой файл. Формат использует ту же структуру pipeline, что и
svoe-vino-lab/config.yaml:

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
name и backend используют ту же структуру, что и svoe-vino-lab/config.yaml.

Чтобы включить Bearer-авторизацию, укажите имя переменной окружения с секретом:

~~~yaml
matcher:
  token: "{env:SVOE_VINO_MATCHER_TOKEN}"
~~~

Поле matcher.token содержит только точную ссылку `"{env:NAME}"` на переменную
окружения. Секретный токен не хранится в YAML.

Backend mock вычисляет SHA-256 загруженного изображения. Затем он ищет этот SHA-256 в
answers. Поле unknown_slug задаёт ответ для неизвестного изображения.

Поле matcher.output_dir задаёт каталог изображений и журналов запросов. Оно принимает
обычный непустой путь или точную строку `"{env:NAME}"`. Во втором случае сервис читает
путь из переменной окружения NAME при запуске. Относительный путь вычисляется от
рабочего каталога процесса. Если поле отсутствует, сервис для обратной совместимости
читает SVOE_VINO_MATCHER_OUTPUT_DIR напрямую.

## Переменные окружения

- SVOE_VINO_MATCHER_PORT — обязательный порт для команд запуска и проверки.
- SVOE_VINO_MATCHER_CONFIG — необязательный путь к файлу конфигурации. Без этой
  переменной сервис читает matcher/config.yaml.
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

Чтобы включить авторизацию, выберите config.token.yaml и задайте секрет:

~~~bash
export SVOE_VINO_MATCHER_CONFIG=matcher/tests/config.token.yaml
export SVOE_VINO_MATCHER_TOKEN='<secret-token>'
~~~

Если `matcher.token` указан, сервис не запустится без непустой переменной с этим
именем.

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
