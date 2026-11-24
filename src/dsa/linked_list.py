# LinkedList - singly linked list (used for active loans)
from typing import Any, Iterator


class Node:
    def __init__(self, value: Any) -> None:
        self.value = value
        self.next: "Node | None" = None


class LinkedList:
    def __init__(self) -> None:
        self.root: Node | None = None
        self._size = 0

    def add(self, value: Any) -> None:
        ## Add value at the root
        node = Node(value)
        node.next = self.root
        self.root = node
        self._size += 1

    def remove(self, value: Any) -> bool:
        ## Remove the first node equal to value. Returns True if removed
        prev_node = None
        current_node = self.root
        while current_node is not None:
            if current_node.value == value:
                if prev_node is None:            # removing the root
                    self.root = current_node.next
                else:
                    prev_node.next = current_node.next
                self._size -= 1
                return True
            else:
                prev_node = current_node
                current_node = current_node.next
        return False

    def find(self, value: Any) -> bool:
        ## Returns a bool if the item is found or not
        for v in self:
            if v == value:
                return True
        return False

    def traverse(self) -> list[Any]:
        ## Return all values from root to end as a Python list
        return list(self)

    def __iter__(self) -> Iterator[Any]:
        current = self.root
        while current is not None:
            yield current.value
            current = current.next

    def __len__(self) -> int:
        return self._size