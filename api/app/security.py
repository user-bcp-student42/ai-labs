from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import time
from typing import Any

SECRET_ENV_VAR = "WORKSHOP_JWT_SECRET"
EXPECTED_ISSUER = "ai-labs-auth"
EXPECTED_AUDIENCE = "ai-labs-api"
BEARER_PREFIX = "Bearer "
SIGNING_ALGORITHM = "HS256"
JWT_SEGMENT_COUNT = 3


class InvalidTokenError(Exception):
    pass


def identity_from_authorization(authorization: str) -> dict[str, str]:
    claims = verify_token(read_bearer_token(authorization))
    return {"username": claims["sub"], "role": claims["role"]}


def read_bearer_token(authorization: str) -> str:
    if not authorization.startswith(BEARER_PREFIX):
        raise InvalidTokenError("missing bearer scheme")
    return authorization[len(BEARER_PREFIX):]


def verify_token(token: str) -> dict[str, Any]:
    segments = token.split(".")
    if len(segments) != JWT_SEGMENT_COUNT:
        raise InvalidTokenError("malformed token")
    header_segment, payload_segment, signature_segment = segments
    secret = load_secret()
    try:
        header = decode_json_segment(header_segment)
        claims = decode_json_segment(payload_segment)
        verify_signature(header_segment, payload_segment, signature_segment, secret)
    except (ValueError, TypeError, binascii.Error) as error:
        raise InvalidTokenError("malformed token") from error
    verify_header(header)
    verify_claims(claims)
    return claims


def load_secret() -> str:
    secret = os.environ.get(SECRET_ENV_VAR, "")
    if not secret:
        raise InvalidTokenError("signing secret not configured")
    return secret


def decode_json_segment(segment: str) -> dict[str, Any]:
    payload = json.loads(decode_base64url(segment))
    if not isinstance(payload, dict):
        raise InvalidTokenError("segment is not an object")
    return payload


def decode_base64url(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def verify_signature(header_segment: str, payload_segment: str, signature_segment: str, secret: str) -> None:
    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    expected = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, decode_base64url(signature_segment)):
        raise InvalidTokenError("signature mismatch")


def verify_header(header: dict[str, Any]) -> None:
    if header.get("alg") != SIGNING_ALGORITHM:
        raise InvalidTokenError("unsupported algorithm")


def verify_claims(claims: dict[str, Any]) -> None:
    if not isinstance(claims.get("sub"), str) or not isinstance(claims.get("role"), str):
        raise InvalidTokenError("missing identity claims")
    verify_expiration(claims)
    if claims.get("iss") != EXPECTED_ISSUER or claims.get("aud") != EXPECTED_AUDIENCE:
        raise InvalidTokenError("issuer or audience mismatch")


def verify_expiration(claims: dict[str, Any]) -> None:
    try:
        expires_at = int(claims.get("exp", 0))
    except (TypeError, ValueError) as error:
        raise InvalidTokenError("invalid expiration") from error
    if expires_at < int(time.time()):
        raise InvalidTokenError("token expired")
