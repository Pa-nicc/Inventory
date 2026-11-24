"""First-run bootstrap: data folder, logging, database, sample data."""
from src.app_logging import setup_logging
from src.db.db_manager import DBManager, get_data_dir
from src.service.auth_service import AuthService
from src.service.image_service import ImageService
from src.service.inventory_service import InventoryService


def seed_if_empty(db: DBManager, svc: InventoryService, auth: AuthService) -> None:
    """Add sample users and items on the very first run."""
    if db.count_users() == 0:
        auth.register("admin", "admin123", "Admin", "Administrator")
        auth.register("2024-001", "student123", "Student", "Sample Student")
        auth.register("fac-001", "faculty123", "Faculty", "Sample Faculty")
    if not db.get_all_items():
        samples = [
            ("Multimeter", "Meters", "Fluke", "117", "SN-1001", 3, "Good", "Shelf A1"),
            ("Oscilloscope", "Meters", "Rigol", "DS1054Z", "SN-1002", 2, "Good", "Shelf A2"),
            ("Vernier Caliper", "Measuring", "Mitutoyo", "500-196", "SN-1003", 5, "Good", "Shelf B1"),
            ("Soldering Station", "Tools", "Hakko", "FX-888D", "SN-1004", 1, "Good", "Shelf C1"),
        ]
        for name, cat, maker, model, serial, qty, cond, loc in samples:
            svc.add_item(name, cat, maker, model, serial, qty, cond, loc, "2026-01-15")


def bootstrap_app():
    """Returns (db, svc, auth, images, base_dir)."""
    base = get_data_dir()
    setup_logging()
    db = DBManager()
    images = ImageService(base)
    svc = InventoryService(db, images)
    auth = AuthService(db)
    seed_if_empty(db, svc, auth)
    return db, svc, auth, images, base