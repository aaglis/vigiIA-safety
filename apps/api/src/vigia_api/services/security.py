from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone


# TODO: production target is Argon2id. PBKDF2-HMAC is a stdlib-friendly fallback for this prototype.
PBKDF2_ITERATIONS = 210_000
PBKDF2_ALGORITHM = "pbkdf2_sha256"
ACCESS_TOKEN_ALGORITHM = "HS256"


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"{PBKDF2_ALGORITHM}${PBKDF2_ITERATIONS}${_b64url_encode(salt)}${_b64url_encode(derived)}"


def verify_password(password: str, password_hash: str) -> bool:
    algorithm, iterations, salt_b64, hash_b64 = password_hash.split("$", 3)
    if algorithm != PBKDF2_ALGORITHM:
        return False
    salt = _b64url_decode(salt_b64)
    expected = _b64url_decode(hash_b64)
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
    return hmac.compare_digest(actual, expected)


def generate_token(size: int = 32) -> str:
    return secrets.token_urlsafe(size)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8"), usedforsecurity=True).hexdigest()


def encode_jwt(claims: dict[str, object], secret: str, expires_in_seconds: int) -> str:
    header = {"alg": ACCESS_TOKEN_ALGORITHM, "typ": "JWT"}
    payload = dict(claims)
    payload["exp"] = int((datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)).timestamp())
    header_part = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_part = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_part}.{payload_part}".encode("ascii")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_part}.{payload_part}.{_b64url_encode(signature)}"


def decode_jwt(token: str, secret: str) -> dict[str, object]:
    header_part, payload_part, signature_part = token.split(".")
    signing_input = f"{header_part}.{payload_part}".encode("ascii")
    expected = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, _b64url_decode(signature_part)):
        raise ValueError("invalid token signature")
    payload = json.loads(_b64url_decode(payload_part))
    if int(payload["exp"]) < int(datetime.now(timezone.utc).timestamp()):
        raise ValueError("token expired")
    return payload
