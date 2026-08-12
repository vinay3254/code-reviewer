from accumulator import add_item

def test_add_item():
    res1 = add_item("a")
    res2 = add_item("b")
    assert res1 == ["a"]
    assert res2 == ["b"]
