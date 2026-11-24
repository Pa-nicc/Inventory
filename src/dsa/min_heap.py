# MinHeap - binary min-heap stored in a list (used for the overdue dashboard)
from typing import Any, Iterable


class MinHeap:
    """Min-heap: the smallest item (by <) is always at index 0."""

    def __init__(self) -> None:
        self._data: list[Any] = []

    def insert(self, value: Any) -> None:
        """Add value, then sift it up into place"""
        self._data.append(value)
        self._sift_up(len(self._data) - 1)

    def extract_min(self) -> Any:
        """Remove and return the smallest item"""
        if not self._data:
            raise IndexError("extract_min from empty heap")
        smallest = self._data[0]
        last = self._data.pop()           # remove the last item
        if self._data:                    # if anything is left, put last at the top
            self._data[0] = last
            self._sift_down(0)
        return smallest

    def peek_min(self) -> Any:
        """Return the smallest item without removing it"""
        if not self._data:
            raise IndexError("peek_min from empty heap")
        return self._data[0]

    def heapify(self, values: Iterable[Any]) -> None:
        """Replace the contents with values arranged as a heap"""
        self._data = list(values)
        for i in range(len(self._data) // 2 - 1, -1, -1):
            self._sift_down(i)

    def is_empty(self) -> bool:
        return len(self._data) == 0

    def __len__(self) -> int:
        return len(self._data)

    def _sift_up(self, i: int) -> None:
        """Move the item at i up while it is smaller than its parent"""
        while i > 0:
            parent = (i - 1) // 2
            if self._data[i] < self._data[parent]:
                self._data[i], self._data[parent] = self._data[parent], self._data[i]
                i = parent
            else:
                break

    def _sift_down(self, i: int) -> None:
        """Move the item at i down while a child is smaller than it"""
        n = len(self._data)
        while True:
            left = 2 * i + 1
            right = 2 * i + 2
            smallest = i
            if left < n and self._data[left] < self._data[smallest]:
                smallest = left
            if right < n and self._data[right] < self._data[smallest]:
                smallest = right
            if smallest == i:             # already smaller than both children
                break
            self._data[i], self._data[smallest] = self._data[smallest], self._data[i]
            i = smallest