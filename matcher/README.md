# Сервис матчера для проверки

Этот подпроект предоставляет HTTP API матчера для официальной проверки распознавания
винных этикеток. Сервис поддерживает два backend: `siglip2` и `mock`. Конфигурация по
умолчанию `matcher/config.yaml` выбирает pipeline `siglip2-p512-as-is`.

У сервиса три endpoint распознавания:

- POST /v1/eval/predict возвращает один slug. Это контракт хакатона.
- POST /v1/match возвращает до `k` кандидатов с карточками вин. Этот endpoint нужен
  telegram-bot и другим клиентам. Он работает с bundle версии 2 или с каталогом
  лаборатории.
- POST /v1/group/match сегментирует бутылки на фотографии стеллажа. Он возвращает
  координаты, маску и лучшее совпадение с карточкой для каждой бутылки. Он работает
  с bundle версии 2 или с каталогом лаборатории и с настроенным `SAM3_ENDPOINT`.

Матчер не зависит от workbench. Он не импортирует код workbench и не читает
`lab.sqlite3`. Данные каталога приходят через embedding bundle или через копию каталога
лаборатории: матчер читает из её базы только два фиксированных view.

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
- Пакеты из matcher/requirements.txt. Файл фиксирует версии прямых зависимостей.
- Файл matcher/requirements.lock фиксирует полный граф для Python 3.11 на Linux.
  Файл содержит SHA-256 каждого допустимого дистрибутива.

Используйте Python-окружение проекта и установите зависимости:

~~~bash
~/.venvs/svoe-vino-lab/bin/pip install -r matcher/requirements.txt
~~~

Docker и `matcher/tests/run_ci.sh` устанавливают `requirements.lock` в режиме
`--require-hashes`. Обновите lock-файл после изменения прямых зависимостей:

~~~bash
uv pip compile matcher/requirements.txt \
  --python-version 3.11 \
  --python-platform x86_64-unknown-linux-gnu \
  --generate-hashes \
  --output-file matcher/requirements.lock
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

Необязательное поле bundle у mock pipeline задаёт bundle с карточками вин для
POST /v1/match и POST /v1/group/match. Для известного изображения mock ставит его slug на первое место со
score 1.0. Остальные места получают случайные вина bundle со случайным score в
диапазоне [0, 1). Для неизвестного изображения все места получают случайные вина. Slug
без карточки mock пропускает. Эти score ничего не значат. Без поля bundle
POST /v1/match и POST /v1/group/match возвращают HTTP 503.

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

By default, the backend does not segment single images. The optional
`hand_selection: true` step selects one package with SAM3 before embedding.
`POST /v1/group/match` always segments bottles with SAM3. It ignores hand selection.

Сервис загружает bundle при
запуске. Он проверяет формат, версию, SHA-256 файлов `vectors.npy` и `candidates.jsonl`
и форму матрицы. Для bundle версии 2 он также проверяет SHA-256 файла `wines.jsonl` и
читает карточки вин. Ошибка SigLIP2 даёт HTTP 502. Таймаут SigLIP2 даёт HTTP 504.

Для POST /v1/match backend ранжирует все вина по тому же косинусу. Первое место всегда
совпадает с ответом POST /v1/eval/predict. Вино без карточки backend пропускает, и его
место занимает следующее вино.

### Optional hand-aware selection

Set `hand_selection: true` in the selected `pipeline` entry. The default is `false`.
Set `SAM3_ENDPOINT` to the SAM3 base URL. Restart the matcher after a configuration
change. This option applies only to the `siglip2` backend.

Both `POST /v1/match` and `POST /v1/eval/predict` request package and hand detections.
The selector combines hand-box overlap with package size, position, sharpness, and
other scene signals. Without a hand, it uses scene ranking. It crops the selected
package and replaces the background outside its mask with white. Without a usable
package, it keeps the original image. Hand overlap is a heuristic, not proof of a grip.

The group endpoint ignores this option even when it is enabled. Its SAM3 prompt stays
`wine bottle`. Every retained bottle crop goes directly to batch embedding. It does
not detect hands or select one main bottle.

Missing SAM3 configuration gives HTTP 503. Invalid SAM3 data gives HTTP 502. A SAM3
timeout gives HTTP 504. These failures do not silently use the original photo.
Read [hand-selection.md](docs/hand-selection.md) for the configuration and behavior.

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

Скрипт сборки пишет bundle версии 2. В этой версии `wines.jsonl` содержит карточки вин:
название, производителя, категорию, регион, цвет, сорта винограда, `page_url`,
`image_url` и `qr_urls`. Матчер принимает bundle версии 1 и версии 2. Bundle версии 1
не содержит карточек, поэтому POST /v1/match и POST /v1/group/match возвращают для
него HTTP 503. Формат
описан в `workbench/docs/testing/matcher-bundle.md`.

Bundle версии 3 (план 82 workbench) содержит повёрнутые строки записи embeddings с ключом
`rotation_step`: одна строка вектора на каждый угол изображения. Вино получает лучший
косинус своих строк, то есть максимум по поворотам. Матчер принимает версию 3 и читает
угол каждой строки из `items.jsonl` в поле `Bundle.angles`. Ответ API не меняется. Копия
каталога лаборатории с такой записью даёт те же строки и углы.

### Каталог лаборатории

Вместо bundle pipeline может читать копию каталога лаборатории
(`workbench/docs/plans/75_data-layout.md`). Поля catalog и embedding заменяют поле
bundle:

~~~yaml
pipeline:
  - name: siglip2-p512-as-is
    backend: siglip2
    catalog: workbench/data/catalog
    embedding: gx10-siglip2-so400m-patch16-naflex-p512
    endpoint: "{env:SIGLIP2_ENDPOINT}"
~~~

- Поле catalog задаёт каталог с `catalog.sqlite3` и `embeddings/<embedding>/`.
  Относительный путь вычисляется от рабочего каталога процесса.
- Из базы матчер читает только view `matcher_wine` и `matcher_wine_image`. Базовые
  таблицы лаборатории он не читает.
- Матчер читает `embeddings/<embedding>/index.json` и файл векторов, который назван в
  индексе. Имя модели и `extra_body` он берёт из поля `config` индекса.
- Карточки вин матчер строит по правилам сборщика bundle версии 2. На одних и тех же
  данных POST /v1/eval/predict и POST /v1/match дают те же ответы, что и с bundle.
- Pipeline указывает либо bundle, либо catalog вместе с embedding.

Матчер использует каждый элемент индекса. Согласованную копию с актуальными элементами
делает скрипт workbench:

~~~bash
cd workbench
python3 scripts/copy_catalog.py --out <новый каталог> \
    --embedding gx10-siglip2-so400m-patch16-naflex-p512 --no-images
rsync -a --delete <новый каталог>/ <host>:<путь>/
~~~

Скрипт отказывает, если идёт сборка embedding или если индекс содержит неактуальный
элемент. Базу он копирует через SQLite backup API, поэтому работающая лаборатория не
мешает копии. Без `--no-images` копия содержит также `images/` и `cuts/`.

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
- SAM3_ENDPOINT — корневой URL SAM3. POST /v1/group/match отправляет запрос в
  `<SAM3_ENDPOINT>/segment`. Канонический адрес GX10 равен
  `http://192.168.86.14:18081/upstream/sam3`.
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
  умолчанию равно 40000000. The value MUST NOT exceed 89478485, the Pillow limit. A
  larger value stops the service at start.
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
Dockerfile фиксирует `python:3.11-slim` по OCI digest. Он устанавливает полный граф
Python-зависимостей из `matcher/requirements.lock` в режиме `--require-hashes`.
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
ссылается его поле endpoint. POST /v1/group/match дополнительно читает
`SAM3_ENDPOINT` при любом выбранном pipeline. Одиночные запросы mock pipeline не читают
адреса моделей. Внутри контейнера адрес 127.0.0.1 указывает на сам контейнер. Для
сервиса на хосте укажите LAN-адрес хоста.

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

The admission check reads the image header and does not decode the pixels. A damaged
JPEG, MPO, or WEBP can pass it. The decoding then fails, and the service returns HTTP 422.
The request archive keeps such an image and its `request.json` record.

Лимит полного HTTP body равен `SVOE_VINO_MATCHER_MAX_IMAGE_BYTES` плюс 64 КиБ для
multipart-обрамления. Этот лимит действует и для chunked upload без Content-Length.

### POST /v1/match

Endpoint POST /v1/match принимает то же поле image. Необязательный query-параметр `k`
задаёт максимальное число кандидатов: от 1 до 20, по умолчанию 20. Pipeline всегда
берётся из конфигурации. Запрос не выбирает pipeline.

~~~bash
curl --form 'image=@matcher/tests/data/02eef911.webp' \
  "http://127.0.0.1:$SVOE_VINO_MATCHER_PORT/v1/match?k=4"
~~~

Ответ:

~~~json
{
  "pipeline": "siglip2-p512-as-is",
  "latency_ms": 812.5,
  "candidates": [
    {
      "rank": 1,
      "slug": "massandra-muskatel-belyy-belye-sorta-vinograda-beloe-sladkoe-16",
      "score": 0.83,
      "wine": {
        "name": "...",
        "page_url": "https://vino-svoe.ru/wines/massandra-muskatel-belyy-belye-sorta-vinograda-beloe-sladkoe-16",
        "producer": "...",
        "category": "...",
        "region": "...",
        "color": "...",
        "grapes": "...",
        "sugar": "Сладкое",
        "image_url": "https://api.vino-svoe.ru/v1/img/str-api/1920/1920/resize/uploads/...",
        "qr_urls": []
      }
    }
  ]
}
~~~

- `rank` начинается с 1. `score` не растёт от места к месту. Slug не повторяются.
- `candidates` содержит от 0 до `k` элементов. Пустой список значит, что совпадения нет.
- `wine.name` и `wine.page_url` всегда строки. Остальные поля карточки, кроме
  `qr_urls`, могут быть null.
- `sugar` матчер определяет по slug и названию по тем же правилам, что telegram-bot.
- `latency_ms` содержит время обработки запроса.

Ограничения размера, формат, авторизация и очередь такие же, как у POST
/v1/eval/predict. Значение `k` вне диапазона даёт HTTP 422. Pipeline без карточек даёт
HTTP 503.

### POST /v1/group/match

Endpoint POST /v1/group/match принимает фотографию стеллажа в поле `image`. Сервис
нормализует фотографию, вызывает `${SAM3_ENDPOINT}/segment` и распознаёт каждый
возвращённый crop. SigLIP2 отправляет все crop в одном embedding-запросе.

~~~bash
curl --form 'image=@shelf.jpg' \
  "http://127.0.0.1:$SVOE_VINO_MATCHER_PORT/v1/group/match?k=5"
~~~

Необязательный параметр `k` задаёт число кандидатов для каждой бутылки: от 1 до 20,
по умолчанию 1.

Ответ содержит нормализованную фотографию для точного совмещения масок:

~~~json
{
  "pipeline": "siglip2-p512-as-is",
  "latency_ms": 3482.1,
  "image": {
    "width": 1280,
    "height": 853,
    "preview": "data:image/jpeg;base64,..."
  },
  "detected_count": 2,
  "truncated": false,
  "bottles": [
    {
      "id": "b1",
      "segmentation_score": 0.91,
      "box": [0.12, 0.08, 0.21, 0.84],
      "mask": "data:image/png;base64,...",
      "match": {
        "rank": 1,
        "slug": "wine-slug",
        "score": 0.83,
        "wine": {
          "name": "...",
          "page_url": "https://vino-svoe.ru/wines/wine-slug",
          "producer": "...",
          "category": "...",
          "region": "...",
          "color": "...",
          "grapes": "...",
          "sugar": "Сухое",
          "image_url": "...",
          "qr_urls": []
        }
      },
      "candidates": [
        {"rank": 1, "slug": "wine-slug", "score": 0.83, "wine": {"...": "..."}},
        {"rank": 2, "slug": "other-wine", "score": 0.79, "wine": {"...": "..."}}
      ]
    }
  ]
}
~~~

- `box` содержит нормализованные координаты `[left, top, right, bottom]`.
- `mask` содержит прозрачный PNG, обрезанный по `box`.
- `match` равен null, если каталог не дал совпадение.
- `candidates` содержит до `k` кандидатов, лучший первым. Первый кандидат равен
  `match`. Список пуст, если `match` равен null.
- `detected_count` содержит число валидных детекций до удаления дублей и лимитов.
- `truncated` равен true, если лимит 100 бутылок или 6 МиБ визуальных данных исключил
  валидную бутылку.

SAM3 получает `text=wine bottle`, `threshold=0.4`, `mask_threshold=0.5` и
`return_masks=true`. Сервис применяет EXIF-ориентацию и ограничивает изображение
размером 1600 × 1600. Общий бюджет SAM3 равен 300 секундам. Сервис возвращает HTTP 502
при ошибке SAM3, HTTP 503 без `SAM3_ENDPOINT` и HTTP 504 при таймауте.

Полный контракт и лимиты находятся в [docs/group-match.md](docs/group-match.md).

## Проверка состояния

Endpoint GET /healthz показывает, что процесс работает. Этот endpoint не проверяет
model endpoint:

~~~bash
curl "http://127.0.0.1:$SVOE_VINO_MATCHER_PORT/healthz"
~~~

Ответ:

~~~json
{"status":"ok","pipeline":"official-eval-mock"}
~~~

Endpoint GET /readyz проверяет зависимости выбранного pipeline:

~~~bash
curl "http://127.0.0.1:$SVOE_VINO_MATCHER_PORT/readyz"
~~~

Mock pipeline не имеет model dependency. Для него `/readyz` сразу возвращает HTTP 200.
SigLIP2 pipeline отправляет небольшое изображение в настроенный embedding endpoint.
При `hand_selection: true` он сначала проверяет `SAM3_ENDPOINT`. Если обязательная
зависимость недоступна, `/readyz` возвращает HTTP 503. `/healthz` при этом возвращает
HTTP 200, пока процесс работает.

Docker `HEALTHCHECK` вызывает `/readyz`. Поэтому контейнер не получает состояние
`healthy`, если обязательная зависимость выбранного pipeline недоступна. Оба endpoint
всегда публичны. Страницы документации и `/openapi.json` также публичны. Авторизация
защищает POST /v1/eval/predict, POST /v1/match и POST /v1/group/match.

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
- HTTP status и найденный slug; для POST /v1/match — список slug кандидатов; для
  POST /v1/group/match — число детекций и slug каждой бутылки.

Значения заголовков authorization, cookie, proxy-authorization, x-api-key и
x-auth-token заменяются на `<redacted>`. Имена этих заголовков сохраняются. Если сервис
работает за reverse proxy, поле client_ip содержит адрес proxy. Исходный адрес клиента
остаётся в переданном заголовке, например x-forwarded-for.

Сервис также пишет одну строку `matcher_request` в журнал Uvicorn после обработки.
Строка содержит request id, IP, SHA-256, размер, длительность, HTTP status, slug и пути
сохранённых файлов. Для POST /v1/match строка также содержит slug кандидатов. Сервис
сохраняет исходную фотографию группового запроса. Он не сохраняет маски и crop.
Каталог содержит изображения и данные запросов. Ограничьте доступ к
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

OpenAPI описывает GET /healthz, GET /readyz, обязательное multipart-поле image и
опциональную схему BearerAuth. Он описывает успешные ответы и ошибки HTTP 400, 401,
408, 413, 415, 422, 502, 503 и 504.
Для POST /v1/match OpenAPI также описывает параметр `k` и схемы `MatchResult`,
`MatchCandidate` и `WineCard`. Для POST /v1/group/match OpenAPI описывает схемы
`GroupMatchResult`, `GroupImage` и `GroupBottle`.

## Тестирование

Инструкции для автоматических тестов, ручного official harness и GitLab CI находятся в
файле [TESTING.md](TESTING.md).

## Known issues

[docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md) lists the known defects that are not fixed yet.
