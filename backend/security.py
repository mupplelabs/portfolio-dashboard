import os
from cryptography.fernet import Fernet

# Define the path for the secret key file (in the volume-mounted data dir so it persists)
SECRET_KEY_FILE = os.path.join(os.path.dirname(__file__), "data", "secret.key")

def get_or_create_key() -> bytes:
    if os.path.exists(SECRET_KEY_FILE):
        with open(SECRET_KEY_FILE, "rb") as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        os.makedirs(os.path.dirname(SECRET_KEY_FILE), exist_ok=True)
        with open(SECRET_KEY_FILE, "wb") as f:
            f.write(key)
        return key

cipher_suite = Fernet(get_or_create_key())

def encrypt_api_key(api_key: str) -> str:
    if not api_key:
        return ""
    try:
        return cipher_suite.encrypt(api_key.encode('utf-8')).decode('utf-8')
    except Exception:
        return ""

def decrypt_api_key(encrypted_key: str) -> str:
    if not encrypted_key:
        return ""
    try:
        return cipher_suite.decrypt(encrypted_key.encode('utf-8')).decode('utf-8')
    except Exception:
        # Fallback for plain text keys if already stored before encryption was enabled
        return encrypted_key
