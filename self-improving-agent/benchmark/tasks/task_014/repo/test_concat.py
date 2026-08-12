from concat import concat_list_items

def test_concat():
    assert concat_list_items(["a", 1, "b", 2]) == "a1b2"
