#!/usr/bin/env python3
"""
Phase 4 walkthrough: build a toy CA chain, sign a PDF with PAdES, verify it,
then run all five break-it experiments and watch which field catches each
one. Read this output top to bottom — the AES/QES distinction is made
concrete in the last experiment, not just described.

Run: .venv/bin/python examples/qes_demo.py
"""

from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qes import tamper
from qes.ca import build_ca_world
from qes.pades import build_dummy_timestamper, build_signer, make_blank_pdf, sign_pdf_qes
from qes.verify_pades import config_from_ca_world, verify_pades

SEP = "\n" + "=" * 78 + "\n"
NOW = datetime.datetime(2026, 6, 1, tzinfo=datetime.timezone.utc)


def section(title: str) -> None:
    print(SEP + title + SEP)


def main() -> None:
    section("STEP 1 — build the CA chain")
    world = build_ca_world()
    print(f"root:      {world.root_cert.subject.rfc4514_string()}")
    print(f"QTSP:      {world.qtsp_cert.subject.rfc4514_string()}  (issued by root)")
    print(f"signer:    {world.qualified_leaf_cert.subject.rfc4514_string()}  (issued by QTSP)")
    print(f"TSA:       {world.tsa_cert.subject.rfc4514_string()}  (issued by QTSP)")
    print()
    print("The qualified leaf carries the ETSI EN 319 412-5 qcStatements extension")
    print("(OID 1.3.6.1.5.5.7.1.3, qc_compliance) — a real standard, not a lab convention.")
    print("The advanced leaf is otherwise byte-for-byte identical, minus that one extension.")

    section("STEP 2 — sign a PDF (PAdES baseline-B, qualified certificate)")
    signer = build_signer(world.qualified_leaf_cert, world.signer_key, [world.qtsp_cert, world.root_cert])
    timestamper = build_dummy_timestamper(world.tsa_cert, world.tsa_rsa_key, [world.qtsp_cert, world.root_cert], fixed_dt=NOW)
    blank_pdf = make_blank_pdf()
    signed_pdf = sign_pdf_qes(blank_pdf, signer=signer, timestamper=timestamper)
    print(f"blank PDF:  {len(blank_pdf)} bytes")
    print(f"signed PDF: {len(signed_pdf)} bytes (PAdES signature + embedded chain + timestamp)")

    section("STEP 3 — verify: happy path")
    config = config_from_ca_world(world)
    result = verify_pades(signed_pdf, config, now=NOW)
    print(json.dumps(result, indent=2))

    section("STEP 4 — five break-it experiments")
    for generator in tamper.ALL_EXPERIMENTS:
        experiment_world = build_ca_world()
        experiment_config = config_from_ca_world(experiment_world)
        variant = generator(experiment_world)
        experiment_result = verify_pades(variant.pdf_bytes, experiment_config, now=NOW)

        print(f"\n--- {variant.species} ---")
        print(f"defect: {variant.description}")
        print(f"  {variant.expected_field} = {experiment_result[variant.expected_field]}")
        other_fields = {k: v for k, v in experiment_result.items() if k not in (variant.expected_field, "detail")}
        print(f"  everything else: {other_fields}")
        if experiment_result["detail"]:
            print(f"  detail: {experiment_result['detail']}")

    section("the AES/QES distinction")
    print(
        "Four of the five experiments above are rejections — a check flips to false\n"
        "and the signature is untrustworthy. The fifth, advanced_not_qualified_cert_as_qes,\n"
        "is not: signature_valid, chain_trusted, document_unmodified, and timestamp_valid\n"
        "all stay true. Only is_qualified flips. Everything cryptographic about that\n"
        "signature is exactly as sound as the qualified one — the only difference is one\n"
        "X.509 extension the QTSP chose to attach or withhold, a legal/procedural fact,\n"
        "not a mathematical one. That's the whole AES-vs-QES ladder, made concrete in code."
    )


if __name__ == "__main__":
    main()
