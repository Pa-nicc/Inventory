from src.db.db_manager import DBManager

db = DBManager(":memory:")                       # temporary database, vanishes after
assert db.get_all_items() == []

a = db.add_item("Multimeter", "Meters", "Fluke", "117", "SN-001", 2,
                "Good", "Shelf A1", "2026-01-15")
b = db.add_item("Caliper", "Measuring", "Mitutoyo", "500", "SN-002", 1,
                "Good", "Shelf B2", "2026-02-01")
assert a != b
assert len(db.get_all_items()) == 2
item = db.get_item(a)
assert item["name"] == "Multimeter"
assert item["quantity"] == 2 and item["available"] == 2
assert db.get_item(999) is None

# duplicate serial number is rejected
try:
    db.add_item("Other", "Meters", "X", "Y", "SN-001", 1, "Good", "A1", "2026-03-01")
    assert False, "duplicate serial should raise"
except ValueError:
    pass

# bad input is rejected
try:
    db.add_item("", "Meters", "X", "Y", "SN-003", 1, "Good", "A1", "2026-03-01")
    assert False, "empty name should raise"
except ValueError:
    pass

# borrowing lowers availability and creates a loan
loan = db.create_loan(b, "2024-001", "Ana", "Student", "Lab 3", "2026-12-01")
assert db.get_item(b)["available"] == 0
assert len(db.get_active_loans()) == 1

# no units left, so the next borrow is rejected
try:
    db.create_loan(b, "2024-002", "Ben", "Student", "Lab 3", "2026-12-02")
    assert False, "should raise when none available"
except ValueError:
    pass
assert db.get_item(b)["available"] == 0          # unchanged

# delete
assert db.delete_item(a) is True
assert db.delete_item(a) is False
assert len(db.get_all_items()) == 1

db.close()
print("db tests passed")