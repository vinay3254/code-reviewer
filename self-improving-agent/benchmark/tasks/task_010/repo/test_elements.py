from elements import first_element

def test_first_element():
    assert first_element([10, 20]) == 10
    assert first_element("") is None
