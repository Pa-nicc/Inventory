from src.dsa.merge_sort import merge_sort

assert merge_sort([]) == []
assert merge_sort([1]) == [1]
assert merge_sort([3, 1, 2]) == [1, 2, 3]
assert merge_sort([42, 17, 88, 5, 63, 29, 71, 14, 96, 38]) == \
    [5, 14, 17, 29, 38, 42, 63, 71, 88, 96]
assert merge_sort([2, 2, 1, 1]) == [1, 1, 2, 2]           # duplicates
assert merge_sort([5, 4, 3, 2, 1]) == [1, 2, 3, 4, 5]     # reverse order

# stability: equal keys keep their original order
pairs = [(2, "a"), (1, "x"), (2, "b"), (1, "y")]
assert merge_sort(pairs, key=lambda p: p[0]) == [(1, "x"), (1, "y"), (2, "a"), (2, "b")]

# the original list is not modified
orig = [3, 1, 2]
merge_sort(orig)
assert orig == [3, 1, 2]

print("merge_sort tests passed")