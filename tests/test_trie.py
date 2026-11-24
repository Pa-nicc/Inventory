from src.dsa.trie import Trie

t = Trie()
assert len(t) == 0
assert t.search_prefix("a") == []              # empty trie
assert not t.contains("Caliper")

for w in ["Multimeter", "Multiplier", "Oscilloscope", "Caliper", "Cal"]:
    assert t.insert(w) is True
assert len(t) == 5

# exact lookup
assert t.contains("Caliper")
assert t.contains("cal")                       # case-insensitive
assert not t.contains("Cali")                  # a prefix is not a stored word

# prefix search
assert sorted(t.search_prefix("mult")) == ["Multimeter", "Multiplier"]
assert sorted(t.search_prefix("MULTI")) == ["Multimeter", "Multiplier"]
assert sorted(t.search_prefix("cal")) == ["Cal", "Caliper"]
assert t.search_prefix("Osc") == ["Oscilloscope"]
assert t.search_prefix("xyz") == []            # no match
assert len(t.search_prefix("")) == 5           # empty prefix returns everything

# duplicate insert
assert t.insert("caliper") is False            # same word, different case
assert len(t) == 5

# remove a word that is a prefix of another: the longer word must survive
assert t.remove("Cal") is True
assert not t.contains("Cal")
assert t.contains("Caliper")
assert t.search_prefix("cal") == ["Caliper"]

# remove the long word: its unused path is pruned
assert t.remove("Caliper") is True
assert t.search_prefix("cal") == []
assert len(t) == 3

# remove something missing
assert t.remove("Caliper") is False
assert t.remove("Mult") is False               # only a prefix, not a word
assert t.contains("Multimeter")                # untouched

# many words
big = Trie()
for n in range(2000):
    big.insert(f"item{n}")
assert len(big) == 2000
assert len(big.search_prefix("item19")) == 111  # item19, item190-199
assert len(big.search_prefix("item1999")) == 1

# errors
for bad, exc in [("", ValueError), (5, TypeError)]:
    try:
        t.insert(bad)
        assert False, "should have raised"
    except exc:
        pass

print("trie tests passed")