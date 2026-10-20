# Проверка сканера винных этикеток

## Требования

- Запустите свой сервис распознавания.
- Убедитесь, что установлены `bash`, `curl`, `jq` и `awk`.
- Контрольные изображения должны находиться в папке `queries/` и быть перечислены в `queries.tsv`.

Сервис должен принимать изображение в multipart-поле `image` и возвращать Top-1 `slug`:

```json
{"slug":"kokur-suhoe-2025"}
```

Также поддерживается ответ текущего API в виде массива: `[{"slug":"..."}]`.

## Запуск

```bash
chmod +x participant_test.sh

./participant_test.sh \
  --images-dir ./queries \
  --manifest ./queries.tsv \
  --endpoint 'http://127.0.0.1:8080/v1/eval/predict' \
  --output ./predictions.jsonl
```

Если `predictions.jsonl` уже существует, удалите или переименуйте его перед повторным запуском.

## Принцип работы

Скрипт обрабатывает фотографии по порядку из `queries.tsv`. Каждое изображение отправляется отдельно. Скрипт ждёт полный ответ сервиса, записывает результат и только после этого отправляет следующее изображение. Параллельных запросов и повторных попыток нет.

Результат сохраняется в `predictions.jsonl`, по одной JSON-строке на фотографию:

```json
{"query_id":"q-000001","image_path":"019c68d0.jpg","image_sha256":"8d9c821e...","predicted_slug":"kokur-suhoe-2025","latency_ms":842}
```

Если сервис не вернул корректный `slug`, значение `predicted_slug` будет `null`. После завершения передайте `predictions.jsonl` организатору. Правильные ответы и итоговый `confidence` находятся и рассчитываются только у организатора.

---

## Запуск с matcher svoe-vino-lab

Этот раздел добавлен в svoe-vino-lab. Текст выше — оригинальный README организаторов
без изменений. Файлы `participant_test.sh`, `queries.tsv` и `queries/` совпадают с
поставкой организаторов 2026-09-17. Строка `README.md` в `checksums.sha256` относится к
оригинальному README, поэтому после этого дополнения её проверка не проходит. Остальные
строки проходят:

```bash
shasum -a 256 -c checksums.sha256
```

Проверка использует тот же порядок, что и выше. Изменён только порт: matcher
svoe-vino-lab слушает порт `8158` вместо `8080`.

### 1. Запустите matcher

Matcher требует:

1. Python-окружение с пакетами `matcher/requirements.txt`. Подготовка описана в
   [SETUP.md](../SETUP.md) и [matcher/README.md](../matcher/README.md).
2. The committed embedding bundle `matcher/data/gx10-siglip2-so400m-patch16-naflex-p512`.
   `workbench/scripts/build_matcher_bundle.py` creates this bundle.
3. An OpenAI-compatible SigLIP2 endpoint. Set its root URL without `/v1` in the selected YAML.
   Read [bootstrap/README.md](../bootstrap/README.md) for the local model services.

Выполните команды из корня svoe-vino-lab:

```bash
export SVOE_VINO_MATCHER_CONFIG=matcher/config.local.example.yaml
python -m uvicorn matcher.app:app --host 127.0.0.1 --port 8158
```

The [local YAML example](../matcher/config.local.example.yaml) selects `siglip2-p512-as-is`.
It sets the gateway to `http://127.0.0.1:18090` and the request archive to `work/matcher-requests`.
For another installation, make a private YAML copy and change `pipeline[].endpoint` and
`matcher.output_dir`. Set `SVOE_VINO_MATCHER_CONFIG` to that copy.
`SIGLIP2_ENDPOINT` and `SVOE_VINO_MATCHER_OUTPUT_DIR` do not override YAML.

Проверьте matcher во втором терминале из корня svoe-vino-lab:

```bash
curl -F image=@eval/queries/02eef911.webp \
  http://127.0.0.1:8158/v1/eval/predict
```

Ответ содержит один `slug`, например `{"slug":"..."}`.

### 2. Запустите проверку

Выполните команды из каталога `eval/`:

```bash
chmod +x participant_test.sh

./participant_test.sh \
  --images-dir ./queries \
  --manifest ./queries.tsv \
  --endpoint 'http://127.0.0.1:8158/v1/eval/predict' \
  --output ./predictions.jsonl
```

Скрипт записывает `predictions.jsonl` в `eval/`. Файл указан в `eval/.gitignore`. Перед
повторным запуском удалите или переименуйте его.

### Результат локального запуска 2026-09-29

- Matcher: pipeline `siglip2-p512-as-is`, SigLIP2 на шлюзе gx10.
- Скрипт вернул `slug` для 3 из 3 фотографий. `latency_ms`: 311–499.
- Правильные ответы есть только у организатора. Этот запуск проверяет порядок работы, а
  не точность.
