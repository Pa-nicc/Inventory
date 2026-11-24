import tempfile
import zipfile
from pathlib import Path

from PIL import Image

from src.db.db_manager import DBManager
from src.service.auth_service import AuthService
from src.service.backup_service import create_backup, restore_backup
from src.service.image_service import ImageService
from src.service.inventory_service import InventoryService


def must_fail(fn, *args):
    try:
        fn(*args)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


# ---------------- auth ----------------
db = DBManager(":memory:")
auth = AuthService(db)
auth.register("admin", "secret1", "Admin", "Admin User")
user = auth.login("admin", "secret1")
assert user["role"] == "Admin" and user["username"] == "admin"
assert "password_hash" not in user                       # the hash never leaves AuthService

row = db.get_user("admin")
assert row["password_hash"] != "secret1" and "secret1" not in row["password_hash"]
assert len(row["salt"]) == 32                            # 16 random bytes as hex

must_fail(auth.login, "admin", "wrong-password")
must_fail(auth.login, "nobody", "secret1")
must_fail(auth.register, "admin", "another1", "Student", "Dup")      # duplicate username
must_fail(auth.register, "bob", "123", "Student", "Bob")             # password too short
must_fail(auth.register, "bob", "secret1", "Visitor", "Bob")         # bad role
must_fail(auth.register, "  ", "secret1", "Student", "Bob")          # blank username

auth.register("u1", "samepass", "Student", "One")
auth.register("u2", "samepass", "Student", "Two")
assert db.get_user("u1")["password_hash"] != db.get_user("u2")["password_hash"]   # salts differ
db.close()

# ---------------- images and backup (real files in a temp folder) ----------------
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as t:
    tmp = Path(t)
    db2 = DBManager(str(tmp / "inventory.db"))
    images = ImageService(tmp)
    svc = InventoryService(db2, images)
    a = svc.add_item("Multimeter", "Meters", "Fluke", "117", "SN-001", 2, "Good", "A1", "2026-01-15")

    Image.new("RGB", (400, 300), "red").save(tmp / "photo.png")
    Image.new("RGB", (200, 200), "blue").save(tmp / "photo2.jpg")

    name = svc.set_item_image(a, tmp / "photo.png")
    assert name.startswith(f"{a}_") and name.endswith(".png")
    assert svc.get_by_id(a)["image_file"] == name
    assert db2.get_item(a)["image_file"] == name
    assert (tmp / "images" / name).exists()
    assert (tmp / "thumbnails" / name).exists()
    with Image.open(tmp / "thumbnails" / name) as th:
        assert max(th.size) <= 96                        # thumbnail was shrunk

    # replacing deletes the old files
    name2 = svc.set_item_image(a, tmp / "photo2.jpg")
    assert name2.endswith(".jpg") and name2 != name
    assert not (tmp / "images" / name).exists()
    assert not (tmp / "thumbnails" / name).exists()

    # bad images are rejected and change nothing
    (tmp / "notes.txt").write_text("hello")
    (tmp / "fake.png").write_bytes(b"this is not an image")
    (tmp / "big.png").write_bytes(b"0" * (3 * 1024 * 1024))
    must_fail(svc.set_item_image, a, tmp / "notes.txt")      # wrong type
    must_fail(svc.set_item_image, a, tmp / "fake.png")       # not a real image
    must_fail(svc.set_item_image, a, tmp / "big.png")        # over 2 MB
    must_fail(svc.set_item_image, a, tmp / "nope.png")       # missing file
    must_fail(svc.set_item_image, 999, tmp / "photo.png")    # no such item
    assert svc.get_by_id(a)["image_file"] == name2

    # backup contains the database and the image files
    zip_path = create_backup(db2, tmp)
    assert zip_path.exists()
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
    assert "inventory.db" in names
    assert f"images/{name2}" in names and f"thumbnails/{name2}" in names

    # deleting the item removes its image files too
    assert svc.delete_item(a) is True
    assert not (tmp / "images" / name2).exists()
    assert svc.get_by_id(a) is None

    # restore brings back both the data and the files
    restore_backup(db2, tmp, zip_path)
    svc2 = InventoryService(db2, images)
    assert svc2.get_by_id(a)["name"] == "Multimeter"
    assert (tmp / "images" / name2).exists()
    assert (tmp / "thumbnails" / name2).exists()

    # bad backup files are rejected
    (tmp / "bad.zip").write_text("not a zip")
    must_fail(restore_backup, db2, tmp, tmp / "bad.zip")
    with zipfile.ZipFile(tmp / "empty.zip", "w") as z:
        z.writestr("readme.txt", "no database here")
    must_fail(restore_backup, db2, tmp, tmp / "empty.zip")
    assert svc2.get_by_id(a) is not None                     # data untouched

    db2.close()

print("extras tests passed")