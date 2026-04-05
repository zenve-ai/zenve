import secrets

import bcrypt

PREFIX = "zv_live_"


def generate_api_key() -> str:
    """Generate a raw API key: zv_live_<32-char-hex>."""
    return PREFIX + secrets.token_hex(16)


def hash_api_key(raw_key: str) -> str:
    return bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()


def verify_api_key(raw_key: str, key_hash: str) -> bool:
    return bcrypt.checkpw(raw_key.encode(), key_hash.encode())


def extract_prefix(raw_key: str) -> str:
    """Extract the lookup prefix (first 12 chars) from a raw key."""
    return raw_key[:12]
