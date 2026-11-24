from src.dsa.wait_queue import WaitQueue

q = WaitQueue()
assert q.is_empty()                       # new queue is empty

q.enqueue("A")
q.enqueue("B")
q.enqueue("C")
assert not q.is_empty()
assert len(q) == 3
assert q.front() == "A"                   # front doesn't remove
assert len(q) == 3

assert q.dequeue() == "A"                 # first in, first out
assert q.dequeue() == "B"
assert q.dequeue() == "C"
assert q.is_empty()

try:                                      # error case
    q.dequeue()
    assert False, "should have raised IndexError"
except IndexError:
    pass

q.enqueue("X")                            # reuse after emptying (tests the tail reset)
assert q.dequeue() == "X"

print("wait_queue tests passed")