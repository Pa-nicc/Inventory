"""InventoryService: connects SQLite (durable) with the in-memory DSA structures
(fast). Every change goes to the database first, then to the structures."""
import sqlite3
from datetime import date
from typing import Any

from src.db.db_manager import DBManager
from src.dsa.avl_tree import AVLTree
from src.dsa.hash_table import HashTable
from src.dsa.linked_list import LinkedList
from src.dsa.merge_sort import merge_sort
from src.dsa.min_heap import MinHeap
from src.dsa.stack import Stack
from src.dsa.trie import Trie
from src.dsa.wait_queue import WaitQueue
from src.service.image_service import ImageService

import logging
log = logging.getLogger("audit")

_BIG_ID = 10 ** 12          # larger than any real item_id, used for range queries


class InventoryService:
    def __init__(self, db: DBManager, images: ImageService | None = None) -> None:
        self.db = db
        self.images = images
        self.current_user = "system"        # the GUI sets this after login
        self.by_id = HashTable()            # item_id -> item (dict)
        self.by_serial = HashTable()        # serial_no -> item_id
        self.sorted_items = AVLTree()       # (name.lower(), item_id) -> item_id
        self.names = Trie()                 # item names for autocomplete
        self.loans = HashTable()            # loan_id -> active loan (dict)
        self.active_loans = LinkedList()    # loan_ids of active loans
        self.waitlists = HashTable()        # item_id -> WaitQueue
        self.undo_stack = Stack()           # return records, newest on top
        self.load()

    def load(self) -> None:
        """Rebuild every structure from SQLite."""
        for row in self.db.get_all_items():
            self._index(dict(row))
        for row in self.db.get_active_loans():
            self._track_loan(dict(row))
        for row in self.db.get_all_waitlist():
            self._queue_for(row["item_id"]).enqueue(dict(row))

    # ---------- internal helpers ----------

    def _index(self, item: dict[str, Any]) -> None:
        """Put one item into every item structure."""
        self.by_id.insert(item["item_id"], item)
        self.by_serial.insert(item["serial_no"], item["item_id"])
        self.sorted_items.insert((item["name"].lower(), item["item_id"]), item["item_id"])
        self.names.insert(item["name"])

    def _refresh(self, item_id: int) -> None:
        """Re-read one item from SQLite and update the hash table copy."""
        self.by_id.insert(item_id, dict(self.db.get_item(item_id)))

    def _track_loan(self, loan: dict[str, Any]) -> None:
        self.loans.insert(loan["loan_id"], loan)
        self.active_loans.add(loan["loan_id"])

    def _untrack_loan(self, loan_id: int) -> None:
        self.active_loans.remove(loan_id)
        self.loans.delete(loan_id)

    def _queue_for(self, item_id: int) -> WaitQueue:
        """The item's waitlist queue, created on first use."""
        if not self.waitlists.contains(item_id):
            self.waitlists.insert(item_id, WaitQueue())
        return self.waitlists.get(item_id)

    def _rebuild_queue(self, item_id: int) -> None:
        """Rebuild one item's queue from the database (used by undo). O(k)."""
        q = WaitQueue()
        for row in self.db.get_waitlist(item_id):
            q.enqueue(dict(row))
        self.waitlists.insert(item_id, q)

    @staticmethod
    def _check_date(text: str) -> None:
        try:
            date.fromisoformat(text)
        except (ValueError, TypeError):
            raise ValueError("date must look like YYYY-MM-DD")

    @staticmethod
    def _check_borrower(borrower_id: str, borrower_name: str, role: str) -> None:
        if not borrower_id.strip() or not borrower_name.strip():
            raise ValueError("borrower ID and name are required")
        if role not in ("Student", "Faculty"):
            raise ValueError("role must be Student or Faculty")

    # ---------- items ----------

    def add_item(self, name: str, category: str, manufacturer: str, model: str,
                 serial_no: str, quantity: int, item_condition: str,
                 location: str, date_acquired: str,
                 image_file: str | None = None) -> int:
        """Add an item. The database validates first, so a rejected item never
        reaches the structures. O(log n)."""
        item_id = self.db.add_item(name, category, manufacturer, model, serial_no,
                                   quantity, item_condition, location,
                                   date_acquired, image_file)
        self._index(dict(self.db.get_item(item_id)))
        log.info("ADD item_id=%s name=%s user=%s", item_id, name, self.current_user)
        return item_id

    def delete_item(self, item_id: int) -> bool:
        """Delete an item everywhere. Returns False if it doesn't exist."""
        item = self.get_by_id(item_id)
        if item is None:
            return False
        try:
            self.db.delete_item(item_id)
        except sqlite3.IntegrityError:
            raise ValueError("item has loan or waitlist records and cannot be deleted")
        self.by_id.delete(item_id)
        self.by_serial.delete(item["serial_no"])
        self.sorted_items.delete((item["name"].lower(), item_id))
        name = item["name"].lower()
        if not self.sorted_items.range_query((name, 0), (name, _BIG_ID)):
            self.names.remove(item["name"])
        if item["image_file"] and self.images:
            self.images.delete_image(item["image_file"])
        log.info("DELETE item_id=%s name=%s user=%s", item_id, item["name"], self.current_user)
        return True

    # ---------- lookups ----------

    def get_by_id(self, item_id: int) -> dict[str, Any] | None:
        """O(1) average."""
        return self.by_id.get(item_id) if self.by_id.contains(item_id) else None

    def get_by_serial(self, serial_no: str) -> dict[str, Any] | None:
        """O(1) average."""
        if not self.by_serial.contains(serial_no):
            return None
        return self.get_by_id(self.by_serial.get(serial_no))

    def browse(self) -> list[dict[str, Any]]:
        """All items sorted A-Z by name. O(n)."""
        return [self.by_id.get(item_id)
                for _, item_id in self.sorted_items.in_order_traversal()]

    def search_by_prefix(self, prefix: str) -> list[dict[str, Any]]:
        """Items whose name starts with prefix, sorted by name then id."""
        results: list[dict[str, Any]] = []
        for name in self.names.search_prefix(prefix):
            low, high = (name.lower(), 0), (name.lower(), _BIG_ID)
            for _, item_id in self.sorted_items.range_query(low, high):
                results.append(self.by_id.get(item_id))
        return merge_sort(results, key=lambda it: (it["name"].lower(), it["item_id"]))

    def filter_by_category(self, category: str) -> list[dict[str, Any]]:
        """Sorted items in one category. A scan, O(n); fine for a filter."""
        return [it for it in self.browse()
                if it["category"].lower() == category.lower()]

    # ---------- borrowing and waitlist ----------

    def borrow(self, item_id: int, borrower_id: str, borrower_name: str,
               role: str, purpose: str, due_date: str) -> int:
        """Lend one unit. Raises ValueError if none are available."""
        self._check_borrower(borrower_id, borrower_name, role)
        self._check_date(due_date)
        loan_id = self.db.create_loan(item_id, borrower_id, borrower_name,
                                      role, purpose, due_date)
        self._refresh(item_id)
        self._track_loan(dict(self.db.get_loan(loan_id)))
        log.info("BORROW loan_id=%s item_id=%s borrower=%s user=%s",
                 loan_id, item_id, borrower_id, self.current_user)
        return loan_id

    def request_item(self, item_id: int, borrower_id: str, borrower_name: str,
                     role: str, purpose: str, due_date: str) -> tuple[str, int]:
        """Borrow if a unit is available, otherwise join the waitlist.
        Returns ("loan", loan_id) or ("waitlist", wait_id). Enqueue is O(1)."""
        item = self.get_by_id(item_id)
        if item is None:
            raise ValueError("item does not exist")
        if item["available"] > 0:
            return ("loan", self.borrow(item_id, borrower_id, borrower_name,
                                        role, purpose, due_date))
        self._check_borrower(borrower_id, borrower_name, role)
        for row in self.db.get_waitlist(item_id):
            if row["borrower_id"] == borrower_id:
                raise ValueError("this borrower is already on the waitlist")
        row = self.db.add_waitlist(item_id, borrower_id, borrower_name, role)
        self._queue_for(item_id).enqueue(dict(row))
        log.info("WAITLIST wait_id=%s item_id=%s borrower=%s user=%s",
            row["wait_id"], item_id, borrower_id, self.current_user)
        return ("waitlist", row["wait_id"])

    def waitlist_size(self, item_id: int) -> int:
        return len(self._queue_for(item_id))

    def next_in_line(self, item_id: int) -> dict[str, Any] | None:
        """Who is first on the waitlist (the notification board). O(1)."""
        q = self._queue_for(item_id)
        return None if q.is_empty() else q.front()

    def get_active_loans(self) -> list[dict[str, Any]]:
        """All loans not yet returned. O(n)."""
        return [self.loans.get(loan_id) for loan_id in self.active_loans]

    # ---------- return and undo ----------

    def return_item(self, loan_id: int, condition: str) -> dict[str, Any]:
        """Return a loan (Good / Damaged / Lost), promote the next person on the
        waitlist, and push a record on the undo stack. Returns that record."""
        info = self.db.process_return(loan_id, condition)
        item_id = info["item_id"]
        self._refresh(item_id)
        self._untrack_loan(loan_id)
        if info["promoted_loan_id"] is not None:
            self._queue_for(item_id).dequeue()        # same person the DB promoted
            self._track_loan(dict(self.db.get_loan(info["promoted_loan_id"])))
        self.undo_stack.push(info)
        log.info("RETURN loan_id=%s item_id=%s condition=%s promoted_loan=%s user=%s",
                loan_id, item_id, condition, info["promoted_loan_id"], self.current_user)
        return info

    def undo_last_return(self) -> dict[str, Any]:
        """Reverse the most recent return. Raises ValueError if there is nothing
        to undo or the stock can no longer be taken back."""
        if self.undo_stack.is_empty():
            raise ValueError("nothing to undo")
        info = self.undo_stack.peek()                 # look first, pop only on success
        try:
            self.db.undo_return(info)
        except sqlite3.IntegrityError:
            raise ValueError("cannot undo: the returned unit was already lent out again")
        self.undo_stack.pop()
        item_id = info["item_id"]
        self._refresh(item_id)
        if info["promoted_loan_id"] is not None:
            self._untrack_loan(info["promoted_loan_id"])
            self._rebuild_queue(item_id)              # person is back in their old place
        self._track_loan(dict(self.db.get_loan(info["loan_id"])))
        return info

    # ---------- overdue ----------

    def overdue_loans(self, today: str | None = None) -> list[dict[str, Any]]:
        """Active loans past their due date, most overdue first.
        Heapify is O(n), each extract is O(log n)."""
        today = today or date.today().isoformat()
        heap = MinHeap()
        heap.heapify([(loan["due_date"], loan["loan_id"])
                      for loan in self.get_active_loans() if loan["due_date"] < today])
        out: list[dict[str, Any]] = []
        while not heap.is_empty():
            due, loan_id = heap.extract_min()
            loan = dict(self.loans.get(loan_id))
            loan["days_overdue"] = (date.fromisoformat(today) - date.fromisoformat(due)).days
            out.append(loan)
        return out

    def set_item_image(self, item_id: int, source_path) -> str:
        """Attach or replace an item's photo. Returns the stored filename."""
        item = self.get_by_id(item_id)
        if item is None:
            raise ValueError("item does not exist")
        if self.images is None:
            raise ValueError("image storage is not configured")
        new_name = self.images.save_image(source_path, item_id)   # validates first
        old_name = item["image_file"]
        self.db.set_image(item_id, new_name)
        self._refresh(item_id)
        if old_name:
            self.images.delete_image(old_name)                    # no orphan files
        log.info("IMAGE item_id=%s file=%s user=%s", item_id, new_name, self.current_user)
        return new_name