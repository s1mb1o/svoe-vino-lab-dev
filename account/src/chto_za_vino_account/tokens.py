"""Random secrets and their stored forms.

The service stores only hashes of bearer secrets. Six-digit email codes are short, so the
service stores an HMAC with a server key instead of a plain hash.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets


def new_token(size: int = 32) -> str:
    return secrets.token_urlsafe(size)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_email_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def code_mac(key: bytes, challenge_id: str, code: str) -> str:
    message = f"{challenge_id}:{code}".encode()
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def equal(left: str, right: str) -> bool:
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def pkce_pair() -> tuple[str, str]:
    """Return a PKCE code verifier and its S256 code challenge."""
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge
