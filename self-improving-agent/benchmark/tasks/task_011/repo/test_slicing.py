from slicing import get_subslice

def test_slicing():
    assert get_subslice([0, 1, 2, 3, 4], 1, 3) == [1, 2]
