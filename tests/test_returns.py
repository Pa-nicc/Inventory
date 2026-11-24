from datetime import date, timedelta
from src.db.db_manager import DBManager
from src.service.inventory_service import InventoryService


def days(n):
    """A date n days from today, as YYYY-MM-DD (so the test works on any day)."""
    return (date.today() + timedelta(days=n)).isoformat()


def must_fail(fn, *args):
    """Pass if fn(*args) raises ValueError, otherwise fail the test."""
    try:
        fn(*args)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


db = DBManager(":memory:")
svc = InventoryService(db)
a = svc.add_item("Multimeter", "Meters", "Fluke", "117", "SN-001", 2, "Good", "A1", "2026-01-15")
b = svc.add_item("Caliper", "Measuring", "Mitutoyo", "500", "SN-002", 1, "Good", "B1", "2026-02-01")

# ---- basic borrow and return ----
l1 = svc.borrow(a, "2024-001", "Ana", "Student", "Lab", days(7))
assert svc.get_by_id(a)["available"] == 1
assert len(svc.get_active_loans()) == 1
svc.return_item(l1, "Good")
assert svc.get_by_id(a)["available"] == 2
assert svc.get_active_loans() == []
assert db.get_loan(l1)["return_condition"] == "Good"
must_fail(svc.return_item, l1, "Good")               # already returned

l2 = svc.borrow(a, "2024-002", "Ben", "Student", "Lab", days(7))
must_fail(svc.return_item, l2, "Broken")             # invalid condition
assert len(svc.get_active_loans()) == 1              # still active
svc.return_item(l2, "Damaged")
assert svc.get_by_id(a)["available"] == 2
assert db.get_loan(l2)["return_condition"] == "Damaged"
must_fail(svc.return_item, 999, "Good")              # no such loan

# ---- waitlist, promotion, undo ----
lb = svc.borrow(b, "2024-001", "Ana", "Student", "Lab", days(7))
assert svc.get_by_id(b)["available"] == 0
assert svc.request_item(b, "2024-002", "Ben", "Student", "Project", days(5))[0] == "waitlist"
assert svc.request_item(b, "2024-003", "Cy", "Faculty", "Demo", days(5))[0] == "waitlist"
must_fail(svc.request_item, b, "2024-002", "Ben", "Student", "Project", days(5))   # duplicate
assert svc.waitlist_size(b) == 2
assert svc.next_in_line(b)["borrower_name"] == "Ben"   # first come, first served

info = svc.return_item(lb, "Good")                   # Ben is promoted
assert info["promoted_loan_id"] is not None
assert svc.get_by_id(b)["available"] == 0            # unit went straight to Ben
assert svc.waitlist_size(b) == 1
assert svc.next_in_line(b)["borrower_name"] == "Cy"
assert [l["borrower_name"] for l in svc.get_active_loans()] == ["Ben"]
assert svc.loans.get(info["promoted_loan_id"])["due_date"] == days(7)

svc.undo_last_return()                               # Ana has it again, Ben is first again
assert svc.get_by_id(b)["available"] == 0
assert svc.waitlist_size(b) == 2
assert svc.next_in_line(b)["borrower_name"] == "Ben"
assert [l["borrower_name"] for l in svc.get_active_loans()] == ["Ana"]
assert db.get_loan(lb)["returned_on"] is None

# ---- a lost item: quantity drops, nobody is promoted ----
info = svc.return_item(lb, "Lost")
assert info["promoted_loan_id"] is None
assert svc.get_by_id(b)["quantity"] == 0
assert svc.waitlist_size(b) == 2
assert svc.get_active_loans() == []
svc.undo_last_return()
assert svc.get_by_id(b)["quantity"] == 1
assert [l["borrower_name"] for l in svc.get_active_loans()] == ["Ana"]

# ---- request_item lends directly when stock is available ----
kind, _ = svc.request_item(a, "2024-009", "Dee", "Student", "Lab", days(3))
assert kind == "loan"

# ---- overdue list, most overdue first ----
d = svc.add_item("Oscilloscope", "Meters", "Rigol", "DS1", "SN-003", 3, "Good", "C1", "2026-03-01")
e = svc.add_item("Vernier", "Measuring", "X", "V1", "SN-004", 1, "Good", "B2", "2026-03-02")
svc.borrow(d, "2024-010", "Eli", "Student", "Lab", days(-3))
old = svc.borrow(d, "2024-011", "Fay", "Student", "Lab", days(-10))
svc.borrow(d, "2024-012", "Gus", "Faculty", "Lab", days(5))       # not overdue
svc.borrow(e, "2024-013", "Hal", "Student", "Lab", days(-1))
assert [o["days_overdue"] for o in svc.overdue_loans()] == [10, 3, 1]
assert svc.overdue_loans()[0]["borrower_name"] == "Fay"
svc.return_item(db.get_loan(old)["loan_id"], "Good")
assert [o["days_overdue"] for o in svc.overdue_loans()] == [3, 1]

# ---- input validation ----
must_fail(svc.borrow, a, "2024-020", "Ivy", "Student", "Lab", "12/01/2026")   # bad date
must_fail(svc.borrow, a, "2024-020", "Ivy", "Visitor", "Lab", days(5))        # bad role
must_fail(svc.borrow, a, "2024-020", "  ", "Student", "Lab", days(5))         # blank name
must_fail(svc.request_item, 999, "2024-020", "Ivy", "Student", "Lab", days(5))

# ---- persistence: a new service rebuilds loans, waitlist and overdue from SQLite ----
svc2 = InventoryService(db)
assert sorted(l["loan_id"] for l in svc2.get_active_loans()) == \
       sorted(l["loan_id"] for l in svc.get_active_loans())
assert svc2.waitlist_size(b) == 2
assert svc2.next_in_line(b)["borrower_name"] == "Ben"
assert [o["days_overdue"] for o in svc2.overdue_loans()] == [3, 1]

# ---- undo edge cases (fresh service each) ----
fresh = InventoryService(DBManager(":memory:"))
must_fail(fresh.undo_last_return)                    # nothing to undo

s = InventoryService(DBManager(":memory:"))
c = s.add_item("Probe", "Meters", "X", "Y", "SN-9", 1, "Good", "A1", "2026-01-01")
lc = s.borrow(c, "2024-001", "Ana", "Student", "Lab", days(7))
s.return_item(lc, "Good")
s.borrow(c, "2024-002", "Ben", "Student", "Lab", days(7))   # the unit is lent out again
must_fail(s.undo_last_return)                        # so the return cannot be undone
assert s.db.get_loan(lc)["returned_on"] is not None  # and nothing was changed

print("returns tests passed")