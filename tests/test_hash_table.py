from src.dsa.hash_table import HashTable

h = HashTable()
assert len(h) == 0
assert not h.contains(1)

# basic insert / get / contains
h.insert(1, "Multimeter")
h.insert("SN-204", "Oscilloscope")
assert h.get(1) == "Multimeter"
assert h.get("SN-204") == "Oscilloscope"
assert h.contains(1) and h.contains("SN-204")
assert len(h) == 2

# update an existing key (no duplicate)
h.insert(1, "Digital Multimeter")
assert h.get(1) == "Digital Multimeter"
assert len(h) == 2

# collisions: 1, 9, 17 all land in slot 1 when capacity is 8
h2 = HashTable(capacity=8)
h2.insert(1, "a")
h2.insert(9, "b")
h2.insert(17, "c")
assert h2.get(1) == "a" and h2.get(9) == "b" and h2.get(17) == "c"

# delete from a chain: head, middle, tail
assert h2.delete(17) is True              # head of chain (inserted last)
assert not h2.contains(17)
assert h2.get(1) == "a" and h2.get(9) == "b"
assert h2.delete(1) is True               # tail of chain
assert h2.get(9) == "b"
assert h2.delete(9) is True
assert len(h2) == 0
assert h2.delete(9) is False              # already gone

# resizing keeps everything findable
big = HashTable(capacity=2)
for n in range(1000):
    big.insert(n, n * 2)
assert len(big) == 1000
assert all(big.get(n) == n * 2 for n in range(1000))
assert sorted(big.keys()) == list(range(1000))

# many string keys
s = HashTable()
for n in range(200):
    s.insert(f"SN-{n}", n)
assert s.get("SN-150") == 150
assert not s.contains("SN-999")

# errors
try:
    h.get("missing")
    assert False, "get on a missing key should raise KeyError"
except KeyError:
    pass
try:
    h.insert(3.5, "bad")
    assert False, "float key should raise TypeError"
except TypeError:
    pass

print("hash_table tests passed")