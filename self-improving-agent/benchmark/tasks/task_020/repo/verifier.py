from hasher import hash_password

EXPECTED_SALT = "static_salt_v2"

def verify_password(password, hashed):
    return hashed == f"{password}_{EXPECTED_SALT}"
