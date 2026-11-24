"""Measures the DSA structures against a plain linear scan on 5,000 items."""
import random
import time

from src.db.db_manager import DBManager
from src.service.inventory_service import InventoryService
from src.dsa.merge_sort import merge_sort
from src.dsa.binary_search import binary_search

N = 50000
random.seed(1)

db = DBManager(":memory:")
svc = InventoryService(db)

# ---- build 5,000 items ----
words = ["Multimeter", "Caliper", "Oscilloscope", "Probe", "Resistor", "Wrench",
         "Micrometer", "Sensor", "Breadboard", "Voltmeter", "Scale", "Gauge"]
start = time.perf_counter()
for n in range(N):
    svc.add_item(f"{random.choice(words)} {n}", f"Cat{n % 10}", "Maker", f"M{n}",
                 f"SN-{n:05d}", 3, "Good", "Shelf", "2026-01-01")
print(f"Built {N} items in {time.perf_counter() - start:.2f} s")


def timed(label, fn, repeats=200):
    """Run fn many times and print the average time per call in milliseconds."""
    t = time.perf_counter()
    for _ in range(repeats):
        result = fn()
    avg_ms = (time.perf_counter() - t) / repeats * 1000
    print(f"{label:<42} {avg_ms:8.4f} ms")
    return avg_ms


all_items = svc.browse()                      # the same data as a plain list
target_id = 4321
target_serial = "SN-04320"

print("\n--- lookup by serial number ---")
timed("Hash table (O(1))", lambda: svc.get_by_serial(target_serial))
timed("Linear scan (O(n))",
      lambda: next(i for i in all_items if i["serial_no"] == target_serial))

print("\n--- lookup in a sorted list of ids ---")
ids = sorted(i["item_id"] for i in all_items)
timed("Binary search (O(log n))", lambda: binary_search(ids, target_id))
timed("Linear scan (O(n))", lambda: target_id in ids)

print("\n--- prefix search ---")
fast = timed("Trie + AVL search_by_prefix('mult')", lambda: svc.search_by_prefix("mult"), 20)
timed("Linear scan with startswith",
      lambda: [i for i in all_items if i["name"].lower().startswith("mult")], 20)
print(f"Requirement: under 100 ms  ->  {'PASS' if fast < 100 else 'FAIL'}")

print("\n--- sorting ---")
timed(f"merge_sort {N:,} items", lambda: merge_sort(all_items, key=lambda i: i["category"]), 3)

timed("Trie, selective prefix 'multimeter 4999'",
      lambda: svc.search_by_prefix("multimeter 4999"), 20)
timed("Linear scan, same prefix",
      lambda: [i for i in all_items if i["name"].lower().startswith("multimeter 4999")], 20)