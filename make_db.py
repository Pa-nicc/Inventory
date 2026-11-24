from src.db.db_manager import DBManager, get_data_dir

db = DBManager()          # no argument, so it uses the real location
db.add_item("Multimeter", "Meters", "Fluke", "117", "SN-001", 2,
            "Good", "Shelf A1", "2026-01-15")
db.close()
print("Database is in:", get_data_dir())