"""
DCQL-lite query + authorization-request objects.

Real OpenID4VP v1.0 uses DCQL (Digital Credentials Query Language, ATLAS_EUDI.md
§5) — a JSON structure that can name multiple credential formats, multiple
credential sets, claim value constraints, and more. This is the "-lite" cut:
one credential query, a flat list of required claim names, and a required
trust tier/LoA. Enough to make check 7 (registration_purpose) and the LoA
half of check 8 (policy) meaningful, without building a DCQL parser.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DcqlLiteQuery:
    """What the verifier says it wants."""

    vct: str  # credential type, e.g. issuer.pid.VCT
    required_claims: tuple[str, ...]
    required_tier: str | None = None  # "PID" | "QEAA" | "PuB-EAA" | "EAA" | None (any)
    required_loa: str | None = None  # "high" | "substantial" | "low" | None (any)


@dataclass(frozen=True)
class AuthorizationRequest:
    """OpenID4VP-lite authorization request: what a verifier hands the wallet."""

    verifier_id: str  # the `aud` the wallet's KB-JWT must bind to
    nonce: str
    query: DcqlLiteQuery
