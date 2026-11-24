# Trie - prefix tree (used for search-box autocomplete)
from typing import Any


class _TrieNode:
    def __init__(self, char: str = "") -> None:
        self.char = char
        self.children: list[_TrieNode] = []
        self.word: str | None = None      # original word if a word ends here


class Trie:
    """Case-insensitive prefix tree for strings."""

    def __init__(self) -> None:
        self._root = _TrieNode()
        self._size = 0

    @staticmethod
    def _check(word: Any) -> str:
        if not isinstance(word, str):
            raise TypeError("word must be a string")
        if word == "":
            raise ValueError("word must not be empty")
        return word.lower()

    @staticmethod
    def _find_child(node: _TrieNode, ch: str) -> "_TrieNode | None":
        for child in node.children:
            if child.char == ch:
                return child
        return None

    def insert(self, word: str) -> bool:
        """Add word. Returns False if it was already present. O(L * k)."""
        key = self._check(word)
        node = self._root
        for ch in key:
            child = self._find_child(node, ch)
            if child is None:
                child = _TrieNode(ch)
                node.children.append(child)
            node = child
        if node.word is not None:
            return False
        node.word = word
        self._size += 1
        return True

    def contains(self, word: str) -> bool:
        """True if the exact word is stored. O(L * k)."""
        node = self._walk(self._check(word))
        return node is not None and node.word is not None

    def search_prefix(self, prefix: str = "") -> list[str]:
        """Return all stored words starting with prefix (empty prefix = all)."""
        if not isinstance(prefix, str):
            raise TypeError("prefix must be a string")
        node = self._walk(prefix.lower())
        results: list[str] = []
        if node is not None:
            self._collect(node, results)
        return results

    def remove(self, word: str) -> bool:
        """Remove word and prune unused nodes. Returns True if removed. O(L * k)."""
        key = self._check(word)
        if not self.contains(word):
            return False
        self._remove(self._root, key, 0)
        self._size -= 1
        return True

    def _walk(self, key: str) -> "_TrieNode | None":
        """Follow key from the root; None if the path doesn't exist."""
        node = self._root
        for ch in key:
            child = self._find_child(node, ch)
            if child is None:
                return None
            node = child
        return node

    def _collect(self, node: _TrieNode, results: list[str]) -> None:
        """Depth-first: add every word at or below node."""
        if node.word is not None:
            results.append(node.word)
        for child in node.children:
            self._collect(child, results)

    def _remove(self, node: _TrieNode, key: str, depth: int) -> bool:
        """Unmark the word; return True if this node can be deleted by its parent."""
        if depth == len(key):
            node.word = None
        else:
            child = self._find_child(node, key[depth])
            if child is not None and self._remove(child, key, depth + 1):
                node.children.remove(child)
        return node.word is None and len(node.children) == 0

    def __len__(self) -> int:
        return self._size