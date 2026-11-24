from src.dsa.linked_list import LinkedList

ll = LinkedList()
assert len(ll) == 0
assert ll.traverse() == []                # empty list
assert ll.remove("x") is False            # removing from empty

ll.add("A")
ll.add("B")
ll.add("C")                            # head is now C
assert ll.traverse() == ["C", "B", "A"]
assert len(ll) == 3
assert ll.find("B")
assert not ll.find("Z")

assert ll.remove("B") is True             # middle
assert ll.traverse() == ["C", "A"]
assert ll.remove("C") is True             # head
assert ll.traverse() == ["A"]
assert ll.remove("A") is True             # last remaining
assert ll.traverse() == []
assert ll.remove("A") is False            # already gone
assert len(ll) == 0

print("linked_list tests passed")