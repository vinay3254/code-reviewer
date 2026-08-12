from stats import average_score

def test_average():
    assert average_score([10, 20]) == 15.0
    assert average_score([]) == 0.0
