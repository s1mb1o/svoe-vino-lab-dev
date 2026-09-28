import io

import pytest
from PIL import Image, ImageDraw

from chto_za_vino_bot.pipeline_artifacts import (
    base_artifacts,
    censored_artifact,
    persist_artifacts,
    quality_artifacts,
)
from chto_za_vino_bot.quality import QualityResult, Segment
from chto_za_vino_bot.storage import ArtifactStore


def encoded_image(mode="RGB", size=(200, 300), color="white", format="JPEG") -> bytes:
    image = Image.new(mode, size, color)
    output = io.BytesIO()
    image.save(output, format=format)
    return output.getvalue()


def mask(size, box) -> bytes:
    image = Image.new("1", size)
    ImageDraw.Draw(image).rectangle(box, fill=1)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_pipeline_artifacts_include_masks_overlay_crops_and_cutouts(tmp_path):
    source = encoded_image()
    bottle = Segment(
        "wine bottle",
        0.95,
        (30, 10, 170, 290),
        mask((200, 300), (30, 10, 170, 290)),
        39_000,
    )
    label = Segment(
        "label",
        0.9,
        (55, 115, 145, 195),
        mask((200, 300), (55, 115, 145, 195)),
        7_200,
    )
    quality = QualityResult(
        acceptable=True,
        issues=(),
        blur_variance=120,
        glare_ratio=0.01,
        bottle_area_ratio=0.65,
        label_area_ratio=0.12,
        segments=(bottle, label),
        selected_bottle=bottle,
        selected_label=label,
    )

    generated = base_artifacts(source, source) + quality_artifacts(source, quality)
    keys = {item.artifact_key for item in generated}

    assert {
        "matcher_input",
        "moderation_input",
        "sam3_overlay",
        "sam3_mask_01",
        "sam3_mask_02",
        "selected_bottle_box_crop",
        "selected_bottle_masked_cutout",
        "selected_label_box_crop",
        "selected_label_masked_cutout",
    } <= keys
    assert next(item for item in generated if item.artifact_key == "matcher_input").body == source
    rows = persist_artifacts(
        ArtifactStore(tmp_path),
        request_id="request-1",
        received_at=1000,
        artifacts=generated,
    )
    assert len(rows) == len(generated)
    assert all((tmp_path / item.relative_path).is_file() for item in rows)


def test_artifact_store_rejects_paths_outside_artifact_root(tmp_path):
    store = ArtifactStore(tmp_path)

    with pytest.raises(ValueError):
        store.resolve("../private.jpg")
    with pytest.raises(ValueError):
        store.resolve("accepted/private.jpg")


def test_censored_artifact_is_irreversibly_reduced_and_blurred():
    source = Image.new("RGB", (1200, 800), "white")
    draw = ImageDraw.Draw(source)
    for x in range(0, 1200, 4):
        draw.rectangle((x, 0, x + 1, 799), fill="black")
    output = io.BytesIO()
    source.save(output, format="JPEG")

    artifact = censored_artifact(output.getvalue())

    assert artifact.artifact_key == "censored_preview"
    assert artifact.exposure == "censored"
    assert max(artifact.width, artifact.height) == 768
    assert artifact.metadata == {
        "sample_max": 24,
        "output_max": 768,
        "blur_radius": 18,
    }
    with Image.open(io.BytesIO(artifact.body)) as preview:
        assert preview.format == "JPEG"
        extrema = preview.convert("L").getextrema()
    assert extrema[1] - extrema[0] < 32
