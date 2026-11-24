# AVLTree - self-balancing binary search tree
from typing import Any


class _AVLNode:
    def __init__(self, key: Any, value: Any) -> None:
        self.key = key
        self.value = value
        self.left: "_AVLNode | None" = None
        self.right: "_AVLNode | None" = None
        self.height = 1


class AVLTree:
    """AVL tree mapping unique keys to values, kept sorted by key."""

    def __init__(self) -> None:
        self._root: _AVLNode | None = None
        self._size = 0
        self._flag = False        # set by _insert / _delete to report what happened

    # ---------- public operations ----------

    def insert(self, key: Any, value: Any = None) -> bool:
        """Add key -> value. If key exists, update value and return False. O(log n)."""
        if key is None:
            raise ValueError("key must not be None")
        self._flag = False
        self._root = self._insert(self._root, key, value)
        if self._flag:
            self._size += 1
        return self._flag

    def delete(self, key: Any) -> bool:
        """Remove key. Returns True if it was present. O(log n)."""
        self._flag = False
        self._root = self._delete(self._root, key)
        if self._flag:
            self._size -= 1
        return self._flag

    def search(self, key: Any) -> Any:
        """Return the value for key. Raises KeyError if missing. O(log n)."""
        node = self._root
        while node is not None:
            if key == node.key:
                return node.value
            node = node.left if key < node.key else node.right
        raise KeyError(key)

    def contains(self, key: Any) -> bool:
        """O(log n)."""
        try:
            self.search(key)
            return True
        except KeyError:
            return False

    def in_order_traversal(self) -> list[tuple[Any, Any]]:
        """Return all (key, value) pairs in sorted key order. O(n)."""
        out: list[tuple[Any, Any]] = []
        self._in_order(self._root, out)
        return out

    def range_query(self, low: Any, high: Any) -> list[tuple[Any, Any]]:
        """Return (key, value) pairs with low <= key <= high, sorted. O(log n + m)."""
        out: list[tuple[Any, Any]] = []
        self._range(self._root, low, high, out)
        return out

    def height(self) -> int:
        """Height of the whole tree (0 if empty). O(1)."""
        return self._h(self._root)

    def is_balanced(self) -> bool:
        """Check every node's stored height and balance factor. O(n). Used in tests."""
        return self._check(self._root) != -1

    def __len__(self) -> int:
        return self._size

    # ---------- height and rotations ----------

    @staticmethod
    def _h(node: "_AVLNode | None") -> int:
        return node.height if node is not None else 0

    def _update(self, node: _AVLNode) -> None:
        node.height = 1 + max(self._h(node.left), self._h(node.right))

    def _balance(self, node: _AVLNode) -> int:
        return self._h(node.left) - self._h(node.right)

    def _rotate_right(self, y: _AVLNode) -> _AVLNode:
        """      y            x
                / \\          / \\
               x   C   ->   A   y
              / \\              / \\
             A   B            B   C      Returns the new subtree root x."""
        x = y.left
        assert x is not None
        y.left = x.right
        x.right = y
        self._update(y)               # y is lower now, so update it first
        self._update(x)
        return x

    def _rotate_left(self, x: _AVLNode) -> _AVLNode:
        """Mirror image of _rotate_right. Returns the new subtree root y."""
        y = x.right
        assert y is not None
        x.right = y.left
        y.left = x
        self._update(x)
        self._update(y)
        return y

    def _rebalance(self, node: _AVLNode) -> _AVLNode:
        """Update node's height and fix it if it is out of balance."""
        self._update(node)
        b = self._balance(node)
        if b > 1:                                     # left-heavy
            if self._balance(node.left) < 0:          # Left-Right case
                node.left = self._rotate_left(node.left)
            return self._rotate_right(node)           # Left-Left case
        if b < -1:                                    # right-heavy
            if self._balance(node.right) > 0:         # Right-Left case
                node.right = self._rotate_right(node.right)
            return self._rotate_left(node)            # Right-Right case
        return node

    # ---------- recursive helpers ----------

    def _insert(self, node: "_AVLNode | None", key: Any, value: Any) -> _AVLNode:
        if node is None:
            self._flag = True
            return _AVLNode(key, value)
        if key < node.key:
            node.left = self._insert(node.left, key, value)
        elif key > node.key:
            node.right = self._insert(node.right, key, value)
        else:
            node.value = value                        # key exists: update only
            return node
        return self._rebalance(node)

    def _delete(self, node: "_AVLNode | None", key: Any) -> "_AVLNode | None":
        if node is None:
            return None                               # key not found
        if key < node.key:
            node.left = self._delete(node.left, key)
        elif key > node.key:
            node.right = self._delete(node.right, key)
        else:
            self._flag = True
            if node.left is None:                     # zero or one child (right)
                return node.right
            if node.right is None:                    # one child (left)
                return node.left
            successor = node.right                    # two children:
            while successor.left is not None:         # smallest key in right subtree
                successor = successor.left
            node.key, node.value = successor.key, successor.value
            node.right = self._delete(node.right, successor.key)
        return self._rebalance(node)

    def _in_order(self, node: "_AVLNode | None", out: list) -> None:
        if node is None:
            return
        self._in_order(node.left, out)
        out.append((node.key, node.value))
        self._in_order(node.right, out)

    def _range(self, node: "_AVLNode | None", low: Any, high: Any, out: list) -> None:
        if node is None:
            return
        if low < node.key:                            # left side may hold matches
            self._range(node.left, low, high, out)
        if low <= node.key <= high:
            out.append((node.key, node.value))
        if node.key < high:                           # right side may hold matches
            self._range(node.right, low, high, out)

    def _check(self, node: "_AVLNode | None") -> int:
        """Return the node's true height, or -1 if anything below is invalid."""
        if node is None:
            return 0
        lh, rh = self._check(node.left), self._check(node.right)
        if lh == -1 or rh == -1 or abs(lh - rh) > 1:
            return -1
        if node.height != 1 + max(lh, rh):
            return -1
        return node.height