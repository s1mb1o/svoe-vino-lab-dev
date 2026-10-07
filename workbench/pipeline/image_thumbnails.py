"""Cache bounded previews of image-store files. Never change the source image."""
import hashlib
import io
import os
import tempfile
import threading
import time
from pathlib import Path

from PIL import Image, ImageOps

SIDE = 768
VERSION = 'webp-768-q82-v1'
MAX_CACHE_BYTES = 256 * 1024 * 1024
_LOCKS = tuple(threading.Lock() for _ in range(64))
_BUILD_SLOTS = threading.BoundedSemaphore(1)
_TRIM_LOCK = threading.Lock()
_LAST_TRIM = {}


def _trim(directory):
    """Bound disk use. Run at most once a minute, after a new preview is written."""
    with _TRIM_LOCK:
        now = time.monotonic()
        if now - _LAST_TRIM.get(directory, -60) < 60:
            return
        _LAST_TRIM[directory] = now
        files = []
        for path in directory.glob('*.webp'):
            try:
                stat = path.stat()
                files.append((stat.st_mtime_ns, stat.st_size, path))
            except OSError:
                pass
        total = sum(size for _, size, _ in files)
        for _, size, path in sorted(files):
            if total <= MAX_CACHE_BYTES:
                break
            try:
                path.unlink()
                total -= size
            except OSError:
                pass


def get(path, directory):
    """Return a WebP with at most SIDE pixels per edge, cached by source metadata.

    Callers resolve the trusted image-store route. An absent or invalid source raises
    OSError. Cache failures raise OSError so the route can send the original image.
    """
    path, directory = Path(path), Path(directory)
    stat = path.stat()
    key = hashlib.sha256(f'{VERSION}:{path.resolve()}:{stat.st_size}:'
                         f'{stat.st_mtime_ns}:{stat.st_ctime_ns}'.encode()).hexdigest()
    cached = directory / (key + '.webp')
    with _LOCKS[int(key[:8], 16) % len(_LOCKS)]:
        try:
            return cached.read_bytes()
        except FileNotFoundError:
            pass
        # Bound cold decodes when browser lazy-loading starts many large photos.
        with _BUILD_SLOTS:
            with Image.open(path) as image:
                # JPEG draft reduction avoids decoding the full capture where supported.
                image.thumbnail((SIDE, SIDE), Image.Resampling.LANCZOS)
                image = ImageOps.exif_transpose(image)
                if image.mode not in ('RGB', 'RGBA'):
                    image = image.convert('RGBA' if 'A' in image.getbands() or 'transparency' in image.info else 'RGB')
                out = io.BytesIO()
                image.save(out, format='WEBP', quality=82, method=1,
                           icc_profile=image.info.get('icc_profile', b''))
                data = out.getvalue()
        directory.mkdir(parents=True, exist_ok=True)
        temp = None
        try:
            with tempfile.NamedTemporaryFile(dir=directory, suffix='.tmp', delete=False) as fh:
                temp = fh.name
                fh.write(data)
            os.replace(temp, cached)
        finally:
            if temp and os.path.exists(temp):
                os.unlink(temp)
        _trim(directory)
        return data
