from counter_obj import Counter

def test_counter_obj():
    c1 = Counter()
    assert c1.increment() == 1
    c2 = Counter()
    assert c2.increment() == 1
