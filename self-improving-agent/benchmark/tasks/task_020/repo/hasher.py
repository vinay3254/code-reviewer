SALT = "static_salt_v1"
def hash_password(password):
    return f"{password}_{SALT}"
