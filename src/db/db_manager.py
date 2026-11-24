"""DBManager: the only module that talks to SQLite. Every change is committed
immediately (write-through), so a forced close cannot corrupt the data."""
import os
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def get_data_dir() -> Path:
    """Return %LOCALAPPDATA%\\EngInventory, creating it if needed."""
    base = os.environ.get("LOCALAPPDATA", str(Path.home()))
    path = Path(base) / "EngInventory"
    path.mkdir(parents=True, exist_ok=True)
    return path


class DBManager:
    def __init__(self, db_path: str | None = None) -> None:
        """Open (or create) the database. Use ':memory:' for tests."""
        if db_path is None:
            db_path = str(get_data_dir() / "inventory.db")
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row          # rows act like dicts
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

    def close(self) -> None:
        self.conn.close()

    # ---------- items ----------

    def add_item(self, name: str, category: str, manufacturer: str, model: str,
                 serial_no: str, quantity: int, item_condition: str,
                 location: str, date_acquired: str,
                 image_file: str | None = None) -> int:
        """Insert an item and return its new item_id."""
        for label, text in [("name", name), ("category", category),
                            ("serial_no", serial_no)]:
            if not text.strip():
                raise ValueError(f"{label} is required")
        if quantity < 0:
            raise ValueError("quantity cannot be negative")
        try:
            with self.conn:                           # commits, or rolls back on error
                cur = self.conn.execute(
                    """INSERT INTO items (name, category, manufacturer, model,
                           serial_no, quantity, available, item_condition,
                           location, date_acquired, image_file)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (name, category, manufacturer, model, serial_no, quantity,
                     quantity, item_condition, location, date_acquired, image_file))
            return cur.lastrowid
        except sqlite3.IntegrityError:
            raise ValueError(f"serial number '{serial_no}' already exists")

    def get_item(self, item_id: int) -> sqlite3.Row | None:
        cur = self.conn.execute("SELECT * FROM items WHERE item_id = ?", (item_id,))
        return cur.fetchone()

    def get_all_items(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM items").fetchall()

    def delete_item(self, item_id: int) -> bool:
        with self.conn:
            cur = self.conn.execute("DELETE FROM items WHERE item_id = ?", (item_id,))
        return cur.rowcount > 0

    # ---------- loans ----------

    def create_loan(self, item_id: int, borrower_id: str, borrower_name: str,
                    role: str, purpose: str, due_date: str) -> int:
        """Lend one unit: availability goes down by 1 and a loan row is added.
        Raises ValueError if the item is missing or has none available."""
        item = self.get_item(item_id)
        if item is None:
            raise ValueError("item does not exist")
        if item["available"] <= 0:
            raise ValueError("no units available")
        with self.conn:                               # both changes succeed or neither
            self.conn.execute(
                "UPDATE items SET available = available - 1 WHERE item_id = ?",
                (item_id,))
            cur = self.conn.execute(
                """INSERT INTO loans (item_id, borrower_id, borrower_name, role,
                       purpose, borrowed_on, due_date)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (item_id, borrower_id, borrower_name, role, purpose,
                 date.today().isoformat(), due_date))
        return cur.lastrowid

    def get_active_loans(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM loans WHERE returned_on IS NULL").fetchall()

    # ---------- loans: lookup, return, undo ----------

    def get_loan(self, loan_id: int) -> sqlite3.Row | None:
        cur = self.conn.execute("SELECT * FROM loans WHERE loan_id = ?", (loan_id,))
        return cur.fetchone()

    def process_return(self, loan_id: int, condition: str,
                       promote_days: int = 7) -> dict[str, Any]:
        """Return a loan, restore stock, and promote the first person waiting.
        Everything happens in ONE transaction. Returns a record that
        undo_return() can use to reverse it exactly."""
        if condition not in ("Good", "Damaged", "Lost"):
            raise ValueError("condition must be Good, Damaged or Lost")
        loan = self.get_loan(loan_id)
        if loan is None:
            raise ValueError("loan does not exist")
        if loan["returned_on"] is not None:
            raise ValueError("loan was already returned")

        item_id = loan["item_id"]
        today = date.today()
        promoted_loan_id = None
        promoted_wait = None
        with self.conn:
            self.conn.execute(
                "UPDATE loans SET returned_on = ?, return_condition = ? WHERE loan_id = ?",
                (today.isoformat(), condition, loan_id))
            if condition == "Lost":
                self.conn.execute(
                    "UPDATE items SET quantity = quantity - 1 WHERE item_id = ?", (item_id,))
            else:
                self.conn.execute(
                    "UPDATE items SET available = available + 1 WHERE item_id = ?", (item_id,))
                nxt = self.conn.execute(
                    "SELECT * FROM waitlist WHERE item_id = ? ORDER BY wait_id LIMIT 1",
                    (item_id,)).fetchone()
                if nxt is not None:
                    self.conn.execute("DELETE FROM waitlist WHERE wait_id = ?", (nxt["wait_id"],))
                    self.conn.execute(
                        "UPDATE items SET available = available - 1 WHERE item_id = ?", (item_id,))
                    due = (today + timedelta(days=promote_days)).isoformat()
                    cur = self.conn.execute(
                        """INSERT INTO loans (item_id, borrower_id, borrower_name, role,
                               purpose, borrowed_on, due_date)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (item_id, nxt["borrower_id"], nxt["borrower_name"], nxt["role"],
                         "Promoted from waitlist", today.isoformat(), due))
                    promoted_loan_id = cur.lastrowid
                    promoted_wait = dict(nxt)
        return {"loan_id": loan_id, "item_id": item_id, "condition": condition,
                "promoted_loan_id": promoted_loan_id, "promoted_wait": promoted_wait}

    def undo_return(self, info: dict[str, Any]) -> None:
        """Reverse a process_return() in one transaction. Raises
        sqlite3.IntegrityError if the stock can no longer be taken back."""
        item_id = info["item_id"]
        with self.conn:
            if info["promoted_loan_id"] is not None:
                self.conn.execute("DELETE FROM loans WHERE loan_id = ?",
                                  (info["promoted_loan_id"],))
                self.conn.execute(
                    "UPDATE items SET available = available + 1 WHERE item_id = ?", (item_id,))
                w = info["promoted_wait"]
                self.conn.execute(
                    """INSERT INTO waitlist (wait_id, item_id, borrower_id, borrower_name,
                           role, requested_on) VALUES (?, ?, ?, ?, ?, ?)""",
                    (w["wait_id"], w["item_id"], w["borrower_id"], w["borrower_name"],
                     w["role"], w["requested_on"]))
            if info["condition"] == "Lost":
                self.conn.execute(
                    "UPDATE items SET quantity = quantity + 1 WHERE item_id = ?", (item_id,))
            else:
                self.conn.execute(
                    "UPDATE items SET available = available - 1 WHERE item_id = ?", (item_id,))
            self.conn.execute(
                "UPDATE loans SET returned_on = NULL, return_condition = NULL WHERE loan_id = ?",
                (info["loan_id"],))

    # ---------- waitlist ----------

    def add_waitlist(self, item_id: int, borrower_id: str, borrower_name: str,
                     role: str) -> sqlite3.Row:
        """Add a person to an item's waitlist and return the new row."""
        with self.conn:
            cur = self.conn.execute(
                """INSERT INTO waitlist (item_id, borrower_id, borrower_name, role, requested_on)
                   VALUES (?, ?, ?, ?, ?)""",
                (item_id, borrower_id, borrower_name, role, date.today().isoformat()))
        return self.conn.execute("SELECT * FROM waitlist WHERE wait_id = ?",
                                 (cur.lastrowid,)).fetchone()

    def get_waitlist(self, item_id: int) -> list[sqlite3.Row]:
        """One item's waitlist, first in line first."""
        return self.conn.execute(
            "SELECT * FROM waitlist WHERE item_id = ? ORDER BY wait_id", (item_id,)).fetchall()

    def get_all_waitlist(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM waitlist ORDER BY wait_id").fetchall()

        # ---------- users and images ----------

    def add_user(self, username: str, password_hash: str, salt: str,
                 role: str, full_name: str) -> int:
        try:
            with self.conn:
                cur = self.conn.execute(
                    """INSERT INTO users (username, password_hash, salt, role, full_name)
                       VALUES (?, ?, ?, ?, ?)""",
                    (username, password_hash, salt, role, full_name))
            return cur.lastrowid
        except sqlite3.IntegrityError:
            raise ValueError(f"username '{username}' already exists")

    def get_user(self, username: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)).fetchone()

    def count_users(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    def set_image(self, item_id: int, filename: str | None) -> bool:
        with self.conn:
            cur = self.conn.execute(
                "UPDATE items SET image_file = ? WHERE item_id = ?", (filename, item_id))
        return cur.rowcount > 0