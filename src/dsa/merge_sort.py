# Merge sort - stable, returns a new sorted list
from typing import Any, Callable, Sequence

def merge_sort(items: Sequence[Any], key: Callable[[Any], Any] = lambda x: x) -> list[Any]:
    ## Stable merge sort by key(item)
    if len(items) <= 1:
        return list(items)

    mid = len(items) // 2
    L = merge_sort(items[:mid], key)
    R = merge_sort(items[mid:], key)

    result: list[Any] = []
    i, j = 0, 0
    while i < len(L) and j < len(R):
        if key(L[i]) <= key(R[j]):        # <= keeps equal items in original order
            result.append(L[i])
            i += 1
        else:
            result.append(R[j])
            j += 1
    result.extend(L[i:])
    result.extend(R[j:])
    return result