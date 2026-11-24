## WaitQueue - queue built on linked nodes
from typing import Any

class _Node:
    def __init__(self, value: Any) -> None:
        self.value = value
        self.next: "_Node | None" = None


class WaitQueue:
    ## Queue using a linked list with root and tail pointers

    def __init__(self) -> None:
        self._root: _Node | None = None   # front of the line
        self._tail: _Node | None = None   # back of the line
        self._size = 0

    def enqueue(self, value: Any) -> None:
        ## Add item at the back of queue
        node = _Node(value)
        if self._tail is None:            # queue was empty
            self._root = node
        else:
            self._tail.next = node
        self._tail = node
        self._size += 1

    def dequeue(self) -> Any:
        ## Remove and return the front item from queue
        if self._root is None:
            raise IndexError("dequeue from empty queue")
        node = self._root
        self._root = node.next
        if self._root is None:            # queue is now empty
            self._tail = None
        self._size -= 1
        return node.value

    def front(self) -> Any:
        ## Return the front item without removing it 
        if self._root is None:
            raise IndexError("front queue empty")
        return self._root.value

    def is_empty(self) -> bool:
        ## Check if queue empty
        return self._root is None

    def __len__(self) -> int:
        ## Return queue size or length
        return self._size