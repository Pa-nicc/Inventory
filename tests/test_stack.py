from src.dsa.stack import Stack

s = Stack()
assert s.is_empty()
s.push(5)
s.push(8)
s.push(2)
assert len(s) == 3
assert s.peek() == 2          # peek doesn't remove
assert len(s) == 3
assert s.pop() == 2           # last in, first out
assert s.pop() == 8
assert s.pop() == 5
assert s.is_empty()

try:
    s.pop()
    assert False, "pop on empty stack should raise"
except IndexError:
    pass

try:
    s.peek()
    assert False, "peek on empty stack should raise"
except IndexError:
    pass

print("stack tests passed")