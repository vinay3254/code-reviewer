from router import get_status_code

def test_router():
    assert get_status_code("/home") == 200
    assert get_status_code("/unknown") == 404
