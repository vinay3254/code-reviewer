from json_loader import read_json_file

def test_read_json():
    assert read_json_file("non_existent_file.json") == {}
