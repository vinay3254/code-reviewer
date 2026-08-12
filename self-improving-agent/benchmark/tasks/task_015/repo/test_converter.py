from converter import safe_int_cast

def test_cast():
    assert safe_int_cast("123") == 123
    assert safe_int_cast("invalid") == 0
