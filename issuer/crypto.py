"""
Crypto primitives for the hand-rolled SD-JWT VC issuer.

Deliberately no JWT/JOSE/SSI library. This module is the entire trust
boundary between "bytes on the wire" and "a claim the issuer stands behind" —
every later verifier check (ATLAS_EUDI.md §9, steps 2, 5, 6) bottoms out in
one of these functions. Everything here is ES256 (ECDSA / P-256 / SHA-256),
the curve+hash pair the ARF names for wallet interop.
"""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature,
    encode_dss_signature,
)

CURVE = ec.SECP256R1()  # P-256, the curve behind the "ES256" JWS alg
COORDINATE_BYTES = 32  # P-256 field element width


# --------------------------------------------------------------------------
# base64url — JWS/JWT use base64url *without* padding throughout.
# --------------------------------------------------------------------------

def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def json_dumps_canonical(obj: dict) -> bytes:
    """Compact, key-order-preserving JSON — matches what we sign, byte for byte."""
    return json.dumps(obj, separators=(",", ":")).encode("utf-8")


# --------------------------------------------------------------------------
# Hashing — used both for JWS-unrelated digests (disclosure hashes) and as
# the "sha-256" alg named in the SD-JWT `_sd_alg` claim.
# --------------------------------------------------------------------------

def sha256_b64url(data: bytes) -> str:
    return b64url_encode(hashlib.sha256(data).digest())


# --------------------------------------------------------------------------
# EC keys
# --------------------------------------------------------------------------

@dataclass
class KeyPair:
    private_key: ec.EllipticCurvePrivateKey
    public_key: ec.EllipticCurvePublicKey

    @classmethod
    def generate(cls) -> "KeyPair":
        priv = ec.generate_private_key(CURVE)
        return cls(private_key=priv, public_key=priv.public_key())

    @classmethod
    def from_seed(cls, seed: int) -> "KeyPair":
        """Deterministic keypair for reproducible runs (lab-only; never do this in production).

        P-256 private scalars must be in [1, n-1]. We derive a scalar from the
        seed via SHA-256 and reduce it modulo the curve order so any seed is valid.
        """
        order = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
        digest = hashlib.sha256(f"eidas-lab-seed:{seed}".encode()).digest()
        scalar = (int.from_bytes(digest, "big") % (order - 1)) + 1
        priv = ec.derive_private_key(scalar, CURVE)
        return cls(private_key=priv, public_key=priv.public_key())

    def public_jwk(self) -> dict:
        """RFC 7517 EC JWK — this is what goes in the `cnf` claim for holder binding."""
        numbers = self.public_key.public_numbers()
        x = numbers.x.to_bytes(COORDINATE_BYTES, "big")
        y = numbers.y.to_bytes(COORDINATE_BYTES, "big")
        return {
            "kty": "EC",
            "crv": "P-256",
            "x": b64url_encode(x),
            "y": b64url_encode(y),
        }


def jwk_to_public_key(jwk: dict) -> ec.EllipticCurvePublicKey:
    if jwk.get("kty") != "EC" or jwk.get("crv") != "P-256":
        raise ValueError(f"unsupported JWK kty/crv: {jwk.get('kty')}/{jwk.get('crv')}")
    x = int.from_bytes(b64url_decode(jwk["x"]), "big")
    y = int.from_bytes(b64url_decode(jwk["y"]), "big")
    numbers = ec.EllipticCurvePublicNumbers(x, y, CURVE)
    return numbers.public_key()


# --------------------------------------------------------------------------
# ES256 sign/verify over raw JWS Signing Input.
#
# `cryptography`'s ECDSA sign/verify produces/consumes DER-encoded (r, s).
# JWS (RFC 7518 §3.4) instead wants the *fixed-width concatenation* R || S,
# each zero-padded to the coordinate size (32 bytes for P-256, so a 64-byte
# signature). We convert both directions by hand here — this is exactly the
# kind of "assemble the JWT ourselves" step the phase is testing.
# --------------------------------------------------------------------------

def es256_sign(private_key: ec.EllipticCurvePrivateKey, signing_input: bytes) -> bytes:
    der_sig = private_key.sign(signing_input, ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der_sig)
    return r.to_bytes(COORDINATE_BYTES, "big") + s.to_bytes(COORDINATE_BYTES, "big")


def es256_verify(public_key: ec.EllipticCurvePublicKey, signing_input: bytes, signature: bytes) -> bool:
    if len(signature) != 2 * COORDINATE_BYTES:
        return False
    r = int.from_bytes(signature[:COORDINATE_BYTES], "big")
    s = int.from_bytes(signature[COORDINATE_BYTES:], "big")
    der_sig = encode_dss_signature(r, s)
    try:
        public_key.verify(der_sig, signing_input, ec.ECDSA(hashes.SHA256()))
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------
# Hand-rolled JWT compact serialization: base64url(header) . base64url(payload) . base64url(sig)
# --------------------------------------------------------------------------

def encode_jwt(header: dict, payload: dict, private_key: ec.EllipticCurvePrivateKey) -> str:
    header_b64 = b64url_encode(json_dumps_canonical(header))
    payload_b64 = b64url_encode(json_dumps_canonical(payload))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = es256_sign(private_key, signing_input)
    sig_b64 = b64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_jwt_parts(jwt: str) -> tuple[dict, dict, bytes, bytes]:
    """Split a compact JWT into (header, payload, signature_bytes, signing_input) without verifying."""
    parts = jwt.split(".")
    if len(parts) != 3:
        raise ValueError(f"malformed JWT: expected 3 dot-separated parts, got {len(parts)}")
    header_b64, payload_b64, sig_b64 = parts
    header = json.loads(b64url_decode(header_b64))
    payload = json.loads(b64url_decode(payload_b64))
    signature = b64url_decode(sig_b64)
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    return header, payload, signature, signing_input


def verify_jwt(jwt: str, public_key: ec.EllipticCurvePublicKey) -> tuple[bool, dict, dict]:
    """Returns (signature_valid, header, payload). Parse errors propagate — format check is separate."""
    header, payload, signature, signing_input = decode_jwt_parts(jwt)
    valid = es256_verify(public_key, signing_input, signature)
    return valid, header, payload
