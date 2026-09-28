import io

from PIL import Image, ImageDraw

from chto_za_vino_bot.fingerprints import difference_hash, perceptual_hash


def picture(*, reverse: bool = False) -> bytes:
    image = Image.new("RGB", (64, 64), "white" if not reverse else "black")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 30, 63), fill="black" if not reverse else "white")
    output = io.BytesIO()
    image.save(output, format="JPEG")
    return output.getvalue()


def test_hashes_are_stable_and_content_sensitive():
    body = picture()

    assert perceptual_hash(body) == perceptual_hash(body)
    assert difference_hash(body) == difference_hash(body)
    assert len(perceptual_hash(body)) == 16
    assert len(difference_hash(body)) == 16
    assert perceptual_hash(body) != perceptual_hash(picture(reverse=True))
