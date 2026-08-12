from user import format_user_name

def test_format_user_name():
    assert format_user_name("John", "Doe", "Robert") == "John Robert Doe"
    assert format_user_name("Jane", "Smith") == "Jane Smith"
