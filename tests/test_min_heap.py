from src.dsa.min_heap import MinHeap

h = MinHeap()
assert h.is_empty()
assert len(h) == 0

# insert and extract come out in sorted order
for x in [5, 3, 8, 1, 9, 2]:
    h.insert(x)
assert len(h) == 6
assert h.peek_min() == 1                  # peek doesn't remove
assert len(h) == 6
out = []
while not h.is_empty():
    out.append(h.extract_min())
assert out == [1, 2, 3, 5, 8, 9]

# duplicates
h.insert(4); h.insert(4); h.insert(1)
assert h.extract_min() == 1
assert h.extract_min() == 4
assert h.extract_min() == 4
assert h.is_empty()

# single element
h.insert(7)
assert h.extract_min() == 7
assert h.is_empty()

# heapify
h.heapify([9, 4, 7, 1])
assert h.peek_min() == 1
assert [h.extract_min() for _ in range(4)] == [1, 4, 7, 9]

# tuples work too: earliest due date first (this is the overdue use case)
h.insert(("2026-11-20", "Oscilloscope"))
h.insert(("2026-11-05", "Multimeter"))
h.insert(("2026-11-12", "Caliper"))
assert h.extract_min() == ("2026-11-05", "Multimeter")
assert h.extract_min() == ("2026-11-12", "Caliper")

# errors on empty
h2 = MinHeap()
try:
    h2.extract_min()
    assert False, "extract_min on empty heap should raise"
except IndexError:
    pass
try:
    h2.peek_min()
    assert False, "peek_min on empty heap should raise"
except IndexError:
    pass

print("min_heap tests passed")