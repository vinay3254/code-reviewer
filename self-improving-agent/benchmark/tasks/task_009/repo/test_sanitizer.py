from sanitizer import sanitize_string

def test_sanitize():
    assert sanitize_string(" Hello ") == "hello"
    assert sanitize_string(None) == ""
