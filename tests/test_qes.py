"""
Tests against BUILD_PROMPT_PHASE4-6.md's Phase 4 acceptance criteria:

1. CA chain builds; a PDF signed with PAdES verifies (integrity + chain +
   timestamp).
2. Each of the five break-it experiments is detected with the correct
   failure reason (the correct field flips, and only that field).
3. `qes` result object is populated and schema-validates.
4. docs/AES_VS_QES.md exists and is readable (a light presence check —
   content quality isn't pytest's job).
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path

import jsonschema
import pytest

from qes import tamper
from qes.ca import build_ca_world
from qes.pades import build_dummy_timestamper, build_signer, make_blank_pdf, sign_pdf_qes
from qes.verify_pades import config_from_ca_world, verify_pades

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "contracts" / "verification_result.schema.json"
NOW = datetime.datetime(2026, 6, 1, tzinfo=datetime.timezone.utc)


@pytest.fixture
def world():
    return build_ca_world()


def _sign_happy_path(world) -> bytes:
    signer = build_signer(world.qualified_leaf_cert, world.signer_key, [world.qtsp_cert, world.root_cert])
    timestamper = build_dummy_timestamper(world.tsa_cert, world.tsa_rsa_key, [world.qtsp_cert, world.root_cert], fixed_dt=NOW)
    return sign_pdf_qes(make_blank_pdf(), signer=signer, timestamper=timestamper)


class TestChainConstruction:
    def test_qtsp_signed_by_root(self, world):
        world.root_key.public_key.verify(
            world.qtsp_cert.signature,
            world.qtsp_cert.tbs_certificate_bytes,
            __import__("cryptography.hazmat.primitives.asymmetric.ec", fromlist=["ECDSA"]).ECDSA(
                world.qtsp_cert.signature_hash_algorithm
            ),
        )  # raises InvalidSignature if not

    def test_leaf_signed_by_qtsp(self, world):
        world.qtsp_key.public_key.verify(
            world.qualified_leaf_cert.signature,
            world.qualified_leaf_cert.tbs_certificate_bytes,
            __import__("cryptography.hazmat.primitives.asymmetric.ec", fromlist=["ECDSA"]).ECDSA(
                world.qualified_leaf_cert.signature_hash_algorithm
            ),
        )

    def test_qualified_leaf_carries_qc_statements_extension(self, world):
        from qes.ca import QC_STATEMENTS_EXTENSION_OID

        oids = {e.oid.dotted_string for e in world.qualified_leaf_cert.extensions}
        assert QC_STATEMENTS_EXTENSION_OID.dotted_string in oids

    def test_advanced_leaf_has_no_qc_statements_extension(self, world):
        from qes.ca import QC_STATEMENTS_EXTENSION_OID

        oids = {e.oid.dotted_string for e in world.advanced_leaf_cert.extensions}
        assert QC_STATEMENTS_EXTENSION_OID.dotted_string not in oids

    def test_untrusted_root_has_a_distinct_name_from_the_real_root(self, world):
        """Regression: an earlier version of build_untrusted_root_and_leaf
        accidentally reused the real root's subject name, which confused
        X.509 path-building (a false-start InvalidSignature before falling
        back correctly) rather than cleanly failing to find a path."""
        assert world.untrusted_root_cert.subject != world.root_cert.subject


class TestHappyPath:
    def test_signature_verifies_and_is_qualified(self, world):
        config = config_from_ca_world(world)
        signed_pdf = _sign_happy_path(world)
        result = verify_pades(signed_pdf, config, now=NOW)
        assert result == {
            "signature_valid": True,
            "chain_trusted": True,
            "document_unmodified": True,
            "timestamp_valid": True,
            "is_qualified": True,
            "anchor_id": "eidas-lab-qtsp-root-1",
            "detail": None,
        }

    def test_signed_pdf_is_a_valid_pdf(self, world):
        from io import BytesIO

        from pyhanko.pdf_utils.reader import PdfFileReader

        signed_pdf = _sign_happy_path(world)
        reader = PdfFileReader(BytesIO(signed_pdf))
        assert len(reader.root["/Pages"]["/Kids"]) == 1

    def test_qes_result_schema_validates(self, world):
        config = config_from_ca_world(world)
        signed_pdf = _sign_happy_path(world)
        result = verify_pades(signed_pdf, config, now=NOW)

        schema = json.loads(SCHEMA_PATH.read_text())
        sample = {
            "schema_version": "wallet-1.0",
            "presentation_id": "qes-demo-1",
            "decision": "accept",
            "checks": [],
            "trust": {"tier": None, "anchor_id": None, "loa": None},
            "policy_version": "qes-v1",
            "qes": result,
            "timing": {"total_ms": 1.0},
        }
        jsonschema.validate(sample, schema)


class TestBreakItExperiments:
    @pytest.mark.parametrize("generator", tamper.ALL_EXPERIMENTS, ids=lambda fn: fn.__name__)
    def test_only_the_expected_field_flips(self, generator):
        world = build_ca_world()  # fresh world per experiment — some mutate revoked_serials
        config = config_from_ca_world(world)
        variant = generator(world)
        result = verify_pades(variant.pdf_bytes, config, now=NOW)

        assert result[variant.expected_field] in (False, None), (
            f"{variant.species}: expected {variant.expected_field!r} to fail, got {result}"
        )

        # every OTHER boolean field should still read as the happy-path value
        happy_path_flags = {
            "signature_valid": True,
            "chain_trusted": True,
            "document_unmodified": True,
            "timestamp_valid": True,
            "is_qualified": True,
        }
        for field, expected in happy_path_flags.items():
            if field == variant.expected_field:
                continue
            assert result[field] == expected, (
                f"{variant.species}: unrelated field {field!r} unexpectedly changed to {result[field]!r}"
            )

    def test_advanced_not_qualified_is_not_a_rejection(self):
        """The one experiment that isn't a rejection: everything about the
        signature verifies cleanly, only is_qualified flips."""
        world = build_ca_world()
        config = config_from_ca_world(world)
        variant = tamper.advanced_not_qualified_cert_as_qes(world)
        result = verify_pades(variant.pdf_bytes, config, now=NOW)
        assert result["signature_valid"] is True
        assert result["chain_trusted"] is True
        assert result["document_unmodified"] is True
        assert result["timestamp_valid"] is True
        assert result["is_qualified"] is False

    def test_qes_result_schema_validates_for_every_experiment(self):
        schema = json.loads(SCHEMA_PATH.read_text())
        for generator in tamper.ALL_EXPERIMENTS:
            world = build_ca_world()
            config = config_from_ca_world(world)
            variant = generator(world)
            result = verify_pades(variant.pdf_bytes, config, now=NOW)
            jsonschema.validate(result, schema["properties"]["qes"])


class TestDocs:
    def test_aes_vs_qes_doc_exists(self):
        doc_path = Path(__file__).resolve().parent.parent / "docs" / "AES_VS_QES.md"
        assert doc_path.exists()
        assert len(doc_path.read_text()) > 500
