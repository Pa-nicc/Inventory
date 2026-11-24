from src.db.db_manager import DBManager
from src.service.inventory_service import InventoryService

db = DBManager(":memory:")
svc = InventoryService(db)

a = svc.add_item("Multimeter", "Meters", "Fluke", "117", "SN-001", 2, "Good", "A1", "2026-01-15")
b = svc.add_item("Multiplier", "Meters", "X", "M1", "SN-002", 1, "Good", "A2", "2026-01-16")
c = svc.add_item("Caliper", "Measuring", "Mitutoyo", "500", "SN-003", 1, "Good", "B1", "2026-02-01")
d = svc.add_item("Multimeter", "Meters", "Fluke", "87V", "SN-004", 1, "Good", "A1", "2026-03-01")

# browse is sorted by name, then id
assert [(i["name"], i["item_id"]) for i in svc.browse()] == \
    [("Caliper", c), ("Multimeter", a), ("Multimeter", d), ("Multiplier", b)]

# lookups
assert svc.get_by_id(a)["serial_no"] == "SN-001"
assert svc.get_by_serial("SN-002")["item_id"] == b
assert svc.get_by_id(999) is None
assert svc.get_by_serial("nope") is None

# prefix search (two items share the name Multimeter)
assert [i["item_id"] for i in svc.search_by_prefix("mult")] == [a, d, b]
assert [i["item_id"] for i in svc.search_by_prefix("CAL")] == [c]
assert svc.search_by_prefix("zzz") == []
assert len(svc.search_by_prefix("")) == 4

# category filter
assert len(svc.filter_by_category("meters")) == 3

# a rejected add must not touch the structures
try:
    svc.add_item("Dup", "Meters", "X", "Y", "SN-001", 1, "Good", "A1", "2026-04-01")
    assert False, "duplicate serial should raise"
except ValueError:
    pass
assert len(svc.browse()) == 4
assert svc.get_by_serial("SN-001")["name"] == "Multimeter"

# borrowing updates both the database and memory
svc.borrow(c, "2024-001", "Ana", "Student", "Lab 3", "2026-12-01")
assert svc.get_by_id(c)["available"] == 0
assert db.get_item(c)["available"] == 0
try:
    svc.borrow(c, "2024-002", "Ben", "Student", "Lab 3", "2026-12-02")
    assert False, "no units left"
except ValueError:
    pass

# persistence: a fresh service on the same database rebuilds the same state
svc2 = InventoryService(db)
assert [i["item_id"] for i in svc2.browse()] == [i["item_id"] for i in svc.browse()]
assert svc2.get_by_id(c)["available"] == 0

# delete: trie keeps "Multimeter" while another item still uses the name
assert svc.delete_item(d) is True
assert [i["item_id"] for i in svc.search_by_prefix("multim")] == [a]
assert svc.delete_item(a) is True
assert svc.search_by_prefix("multim") == []
assert svc.get_by_serial("SN-001") is None
assert svc.delete_item(a) is False
try:
    svc.delete_item(c)               # has a loan record
    assert False, "should refuse"
except ValueError:
    pass

print("service tests passed")