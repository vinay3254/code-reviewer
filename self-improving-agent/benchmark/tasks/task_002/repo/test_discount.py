from discount import calculate_discount

def test_discount():
    assert calculate_discount(150) == 135.0
    assert calculate_discount(50) == 50.0
