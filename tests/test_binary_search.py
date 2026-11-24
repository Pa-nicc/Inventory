from src.dsa.binary_search import binary_search

data = [5, 14, 17, 29, 38, 42, 63, 71, 88, 96]
assert binary_search(data, 63) == 6       # middle-ish
assert binary_search(data, 5) == 0        # first
assert binary_search(data, 96) == 9       # last
assert binary_search(data, 40) == -1      # not present
assert binary_search(data, 1) == -1       # smaller than all
assert binary_search(data, 100) == -1     # larger than all
assert binary_search([], 3) == -1         # empty list
assert binary_search([7], 7) == 0         # single element

print("binary_search tests passed")