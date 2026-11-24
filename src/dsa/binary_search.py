# Binary search on a SORTED list
from typing import Any, Sequence


def binary_search(items: Sequence[Any], target: Any) -> int:
    ## Return the index of target in the sorted sequence, or -1 if absent
    low = 0
    high = len(items) - 1
    
    while low <= high:
        mid = (low + high) // 2
        if items[mid] == target:
            return mid
        if items[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1