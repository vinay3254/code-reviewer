from tax import calculate_tax

def test_tax():
    assert round(calculate_tax(100, 10, 0.1), 2) == 11.0
