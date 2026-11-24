## Stack - (used for undo of the last return)
from typing import Any


class Stack:
    def __init__(self) -> None:
        self._items: list[Any] = []

    def push(self, value: Any) -> None:
        ## Put value on top. O(1)
        self._items.append(value)

    def pop(self) -> Any:
        ## Remove and return the top value. O(1).
        if not self._items:
            raise IndexError("empty stack - pop")

        top_item = self._items[-1]
        del self._items[-1]

        return top_item 

    def peek(self) -> Any:
        ## Return the top value without removing it. O(1).
        if not self._items:
            raise IndexError("empty stack - peek")
        return self._items[-1]

    def is_empty(self) -> bool:
        ## Returns True if list is empty, False if not
        return len(self._items) == 0

    def __len__(self) -> int:
        ## Returns length of the list
        return len(self._items)