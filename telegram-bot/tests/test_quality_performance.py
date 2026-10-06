"""Check exact quality values and event-loop progress during CPU work."""

import asyncio
import io
import random
import threading

import httpx
import pytest
from PIL import Image

from chto_za_vino_bot import quality


def reference_blur(image):
    gray = image.convert("L")
    if max(gray.size) > 1024:
        gray.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
    width, height = gray.size
    if width < 3 or height < 3:
        return 0.0
    pixels = gray.load()
    values = []
    step = 2 if width * height > 500_000 else 1
    for y in range(1, height - 1, step):
        for x in range(1, width - 1, step):
            values.append(
                4 * pixels[x, y]
                - pixels[x - 1, y]
                - pixels[x + 1, y]
                - pixels[x, y - 1]
                - pixels[x, y + 1]
            )
    mean = sum(values) / len(values)
    return max(0.0, sum(value * value for value in values) / len(values) - mean * mean)


@pytest.mark.parametrize(
    "size", [(1, 1), (2, 7), (3, 3), (13, 12), (1000, 500), (1000, 501), (999, 501), (1027, 1031)]
)
@pytest.mark.parametrize("mode", ["L", "RGB", "RGBA"])
def test_blur_matches_signed_pixel_reference(size, mode):
    randomizer = random.Random(71)
    bands = len(mode)
    image = Image.frombytes(mode, size, randomizer.randbytes(size[0] * size[1] * bands))
    assert quality.laplacian_variance(image) == reference_blur(image)


@pytest.mark.parametrize("size", [(0, 0), (11, 13), (511, 512), (517, 509), (700, 1700)])
def test_glare_matches_channel_reference(size):
    randomizer = random.Random(19)
    data = bytes(randomizer.choice((0, 252, 253, 254, 255)) for _ in range(size[0] * size[1] * 3))
    image = Image.frombytes("RGB", size, data)
    scaled = image.copy()
    if max(scaled.size) > 512:
        scaled.thumbnail((512, 512), Image.Resampling.LANCZOS)
    pixels = list(scaled.get_flattened_data())
    count = sum(min(pixel) >= 253 and max(pixel) - min(pixel) <= 4 for pixel in pixels)
    expected = count / len(pixels) if pixels else 0.0
    assert quality.glare_ratio(image) == expected


@pytest.mark.parametrize("value", [0, 127, 253, 255])
def test_uniform_image_has_zero_blur(value):
    assert quality.laplacian_variance(Image.new("L", (31, 32), value)) == 0.0


async def test_quality_cpu_work_does_not_block_event_loop(monkeypatch):
    output = io.BytesIO()
    Image.new("RGB", (10, 12), "white").save(output, "JPEG")
    entered = asyncio.Event()
    release = threading.Event()
    loop = asyncio.get_running_loop()
    worker_ids = []

    def parse(value, size, *, require_masks):
        worker_ids.append(threading.get_ident())
        loop.call_soon_threadsafe(entered.set)
        assert release.wait(5)
        return ()

    monkeypatch.setattr(quality, "parse_sam3_response", parse)
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={}))
    thresholds = quality.QualityThresholds(80, 0.2, 0.1, 0.015)
    async with httpx.AsyncClient(transport=transport) as client:
        job = asyncio.create_task(
            quality.QualityInspector("http://fixture.invalid", client, thresholds).inspect(
                output.getvalue()
            )
        )
        try:
            await asyncio.wait_for(entered.wait(), 5)
            assert worker_ids == [worker_ids[0]]
            assert worker_ids[0] != threading.get_ident()
            assert not job.done()
        finally:
            release.set()
            result = await job
    assert "bottle_missing" in result.issues


async def test_invalid_quality_image_fails_before_http():
    requests = []
    transport = httpx.MockTransport(lambda request: requests.append(request))
    async with httpx.AsyncClient(transport=transport) as client:
        inspector = quality.QualityInspector(
            "http://fixture.invalid", client, quality.QualityThresholds(80, 0.2, 0.1, 0.015)
        )
        with pytest.raises(quality.QualityUnavailable, match="quality image is invalid"):
            await inspector.inspect(b"invalid")
    assert requests == []
