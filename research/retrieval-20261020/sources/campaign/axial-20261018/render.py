"""Render the installed axial recipe from frozen package and label cuts."""
import hashlib
from pathlib import Path
import tempfile
from PIL import Image, ImageOps
from rotate_bottle import BottleRotator

ANGLES = [0] + [a for a in range(-30, 31, 5) if a]


def pixels(image):
    return hashlib.sha256(str(image.size).encode() + image.tobytes()).hexdigest()


def opened(path):
    with Image.open(path) as image:
        return ImageOps.exif_transpose(image).copy()


def finish(image):
    if image.mode == 'RGBA':
        image = Image.alpha_composite(Image.new('RGBA', image.size, 'white'), image).convert('RGB')
    else:
        image = image.convert('RGB')
    if max(image.size) > 1024:
        scale = 1024 / max(image.size)
        image = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))), Image.Resampling.LANCZOS)
    return image


def render(record):
    zero = opened(record['zero']['path']).convert('RGB')
    try:
        package, label = record['package'], record['label']
        if not package or not label:
            raise ValueError('no package mask' if not package else 'no label mask')
        cut = opened(package['path'])
        box = package['box']
        if cut.size != (box[2] - box[0], box[3] - box[1]):
            raise ValueError('package mask dimensions differ from its source box')
        assert pixels(finish(cut)) == pixels(zero), record['source_sha256']
        label_image = opened(label['path'])
        lb = label['box']
        if label_image.size != (lb[2] - lb[0], lb[3] - lb[1]):
            raise ValueError('label mask dimensions differ from its source box')
        mask = Image.new('L', cut.size, 0)
        alpha = label_image.getchannel('A') if label_image.mode == 'RGBA' else Image.new('L', label_image.size, 255)
        mask.paste(alpha, (lb[0] - box[0], lb[1] - box[1]))
        if mask.getbbox() is None:
            raise ValueError('label mask has no pixel inside the package cut')
        top, bottom = max(0, lb[1] - box[1]), min(cut.height, lb[3] - box[1])
        with tempfile.TemporaryDirectory(prefix='axial-frozen-') as directory:
            mask.save(Path(directory) / 'mask.png')
            calibration = {'version': 1, 'reference_size': list(cut.size), 'layers': [
                {'name': 'label', 'mask': 'mask.png', 'distance': 300,
                 'camera_y': (top + bottom) / 2, 'fill': 'vertical', 'smooth_profile': True}]}
            fill = 'vertical'
            try:
                rotator = BottleRotator(cut, calibration, config_dir=Path(directory))
            except ValueError as exc:
                if 'reconstruct glass' not in str(exc):
                    raise
                calibration['layers'][0]['fill'] = fill = 'inpaint'
                rotator = BottleRotator(cut, calibration, config_dir=Path(directory))
            images = [zero] + [finish(rotator.render(angle)) for angle in ANGLES[1:]]
        return images, {'status': 'rendered', 'fill': fill, 'axial_angles': ANGLES}
    except (OSError, ValueError, ImportError) as exc:
        return [zero], {'status': 'skipped', 'reason': str(exc), 'axial_angles': [0]}
