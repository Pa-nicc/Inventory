# HashTable - separate chaining, resizes at load factor 0.75
from typing import Any, Iterator

_MAX_LOAD = 0.75

class _Entry:
    def __init__(self, key: Any, value: Any) -> None:
        self.key = key
        self.value = value
        self.next: "_Entry | None" = None


class HashTable:
    """Hash table for int and str keys, using chaining for collisions"""

    def __init__(self, capacity: int = 8) -> None:
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        self._buckets: list[_Entry | None] = [None] * capacity
        self._size = 0

    @staticmethod
    def _hash(key: Any) -> int:
        """Turn a key into a non-negative integer"""
        if isinstance(key, int):
            return abs(key)
        if isinstance(key, str):
            h = 0
            for ch in key:
                h = (h * 31 + ord(ch)) % (2 ** 32)
            return h
        raise TypeError("key must be int or str")

    def _index(self, key: Any) -> int:
        """Turns hash to key and use as index in hash table"""
        return self._hash(key) % len(self._buckets)

    def insert(self, key: Any, value: Any) -> None:
        """Add key -> value, or update the value if key exists."""
        i = self._index(key)
        current = self._buckets[i]
        while current is not None:
            if current.key == key:
                current.value = value        # key exists: update
                return
            current = current.next
        entry = _Entry(key, value)           # new key: add at head of chain
        entry.next = self._buckets[i]
        self._buckets[i] = entry
        self._size += 1
        if self._size / len(self._buckets) > _MAX_LOAD:
            self._resize()

    def get(self, key: Any) -> Any:
        """Return the value for key. Raises KeyError if missing"""
        current = self._buckets[self._index(key)]
        while current is not None:
            if current.key == key:
                return current.value
            current = current.next
        raise KeyError(key)

    def contains(self, key: Any) -> bool:
        current = self._buckets[self._index(key)]
        while current is not None:
            if current.key == key:
                return True
            current = current.next
        return False

    def delete(self, key: Any) -> bool:
        """Remove key. Returns True if it was present"""
        i = self._index(key)
        prev = None
        current = self._buckets[i]
        while current is not None:
            if current.key == key:
                if prev is None:             # removing the head of the chain
                    self._buckets[i] = current.next
                else:
                    prev.next = current.next
                self._size -= 1
                return True
            prev = current
            current = current.next
        return False

    def keys(self) -> Iterator[Any]:
        """Yield every key (in no particular order)"""
        for head in self._buckets:
            current = head
            while current is not None:
                yield current.key
                current = current.next

    def _resize(self) -> None:
        """Double the array and re-insert every entry"""
        old = self._buckets
        self._buckets = [None] * (len(old) * 2)
        for head in old:
            current = head
            while current is not None:
                nxt = current.next           # save, because we relink the node
                i = self._index(current.key)
                current.next = self._buckets[i]
                self._buckets[i] = current
                current = nxt

    def __len__(self) -> int:
        return self._size