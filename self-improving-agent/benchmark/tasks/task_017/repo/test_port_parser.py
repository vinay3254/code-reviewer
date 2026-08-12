from port_parser import parse_port

def test_parse_port():
    assert parse_port({"port": "9000"}) == 9000
    assert parse_port({"port": "abc"}) == 8080
