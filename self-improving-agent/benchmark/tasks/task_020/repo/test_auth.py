from hasher import hash_password
from verifier import verify_password

def test_auth():
    h = hash_password("secret123")
    assert verify_password("secret123", h) is True
