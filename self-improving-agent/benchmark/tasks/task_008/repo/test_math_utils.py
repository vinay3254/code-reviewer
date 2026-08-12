from math_utils import find_max

def test_find_max():
    assert find_max([1, 5, 3]) == 5
    assert find_max([]) is None
