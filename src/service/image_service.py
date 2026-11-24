"""ImageService: validates, copies and thumbnails item photos.
Only the filename goes in the database, never the image itself."""
import random
import shutil
import string
from pathlib import Path

from PIL import Image

from src.db.db_manager import get_data_dir

MAX_BYTES = 2 * 1024 * 1024
ALLOWED = (".jpg", ".jpeg", ".png")
THUMB_SIZE = (96, 96)


class ImageService:
    def __init__(self, base_dir: str | Path | None = None) -> None:
        base = Path(base_dir) if base_dir else get_data_dir()
        self.images = base / "images"
        self.thumbs = base / "thumbnails"
        self.images.mkdir(parents=True, exist_ok=True)
        self.thumbs.mkdir(parents=True, exist_ok=True)

    def save_image(self, source: str | Path, item_id: int) -> str:
        """Validate, copy as {item_id}_{random8}.{ext}, make a thumbnail.
        Returns the new filename. Raises ValueError for bad files."""
        src = Path(source)
        if not src.is_file():
            raise ValueError("image file not found")
        ext = src.suffix.lower()
        if ext not in ALLOWED:
            raise ValueError("image must be a JPG or PNG file")
        if src.stat().st_size > MAX_BYTES:
            raise ValueError("image must be 2 MB or smaller")
        try:
            with Image.open(src) as im:
                im.verify()                          # checks the file is a real image
        except Exception:
            raise ValueError("file is not a valid image")
        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        name = f"{item_id}_{suffix}{ext}"
        shutil.copy2(src, self.images / name)
        with Image.open(src) as im:                  # reopen: verify() uses the file up
            im.thumbnail(THUMB_SIZE)
            im.save(self.thumbs / name)
        return name

    def delete_image(self, filename: str) -> None:
        """Remove the image and its thumbnail if they exist."""
        for folder in (self.images, self.thumbs):
            path = folder / Path(filename).name
            if path.is_file():
                path.unlink()

    def image_path(self, filename: str) -> Path:
        return self.images / filename

    def thumb_path(self, filename: str) -> Path:
        return self.thumbs / filename