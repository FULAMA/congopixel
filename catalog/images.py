from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from PIL import Image, ImageOps

Image.MAX_IMAGE_PIXELS = 60_000_000

MAIN_SIDE, MAIN_QUALITY = 1200, 82
THUMB_SIDE, THUMB_QUALITY = 480, 78


def _encode(file, max_side, quality):
    file.seek(0)
    with Image.open(file) as img:
        img = ImageOps.exif_transpose(img)
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA" if img.mode in ("P", "LA") else "RGB")
        img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        buffer = BytesIO()
        img.save(buffer, format="WEBP", quality=quality, method=6)
    return ContentFile(buffer.getvalue())


def optimize(instance):
    """Remplace l'image par une version WebP réduite et crée la miniature.

    Retourne l'ancien nom de fichier si l'image était déjà enregistrée, sinon None.
    """
    source = instance.image
    stem = Path(source.name).stem[:60] or "photo"
    main = _encode(source, MAIN_SIDE, MAIN_QUALITY)
    thumb = _encode(source, THUMB_SIDE, THUMB_QUALITY)
    old_name = None
    if source._committed:
        old_name = source.name
        source.close()
    instance.image.save(f"{stem}.webp", main, save=False)
    instance.thumb.save(f"{stem}.webp", thumb, save=False)
    return old_name