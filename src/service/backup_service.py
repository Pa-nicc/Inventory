"""Backup and restore: a zip holding inventory.db, images/ and thumbnails/."""
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from src.db.db_manager import DBManager, SCHEMA_PATH

FOLDERS = ("images", "thumbnails")


def create_backup(db: DBManager, base_dir: str | Path,
                  dest_zip: str | Path | None = None) -> Path:
    """Zip the database and image folders. Returns the zip's path."""
    base = Path(base_dir)
    if dest_zip is None:
        backups = base / "backups"
        backups.mkdir(parents=True, exist_ok=True)
        dest = backups / f"backup_{datetime.now():%Y%m%d_%H%M%S}.zip"
    else:
        dest = Path(dest_zip)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp_db = Path(tmp) / "inventory.db"
        copy = sqlite3.connect(tmp_db)
        try:
            db.conn.backup(copy)                     # consistent copy of the database
        finally:
            copy.close()
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(tmp_db, "inventory.db")
            for folder in FOLDERS:
                d = base / folder
                if d.is_dir():
                    for f in d.iterdir():
                        if f.is_file():
                            z.write(f, f"{folder}/{f.name}")
    return dest


def restore_backup(db: DBManager, base_dir: str | Path, zip_path: str | Path) -> None:
    """Replace the live data with a backup. Raises ValueError if the file is bad.
    After this, build a NEW InventoryService so the structures reload."""
    base = Path(base_dir)
    try:
        z = zipfile.ZipFile(zip_path)
    except (zipfile.BadZipFile, OSError):
        raise ValueError("not a valid backup file")
    with z:
        names = z.namelist()
        if "inventory.db" not in names:
            raise ValueError("backup does not contain inventory.db")
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            tmp_db = Path(tmp) / "inventory.db"
            tmp_db.write_bytes(z.read("inventory.db"))
            src = sqlite3.connect(tmp_db)
            try:
                found = src.execute("SELECT name FROM sqlite_master "
                                    "WHERE type='table' AND name='items'").fetchone()
                if found is None:
                    raise ValueError("backup database is not valid")
                src.backup(db.conn)                  # copy INTO the live database
            except sqlite3.DatabaseError:
                raise ValueError("backup database is not valid")
            finally:
                src.close()
        db.conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))   # older backups
        for folder in FOLDERS:
            d = base / folder
            d.mkdir(parents=True, exist_ok=True)
            for f in d.iterdir():
                if f.is_file():
                    f.unlink()
        for name in names:
            parts = name.split("/")
            if len(parts) == 2 and parts[0] in FOLDERS and parts[1] and ".." not in parts[1]:
                (base / parts[0] / parts[1]).write_bytes(z.read(name))