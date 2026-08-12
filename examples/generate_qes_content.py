#!/usr/bin/env python3
"""
Phase 8d: generates `portal/content/qes_walkthrough.json`, the precomputed
data Try It's QES section renders as a recorded run (real CA chain, real
PAdES signature — no browser can drive PAdES signing interactively, so this
is labelled a recording rather than faked as live). Built from the exact
same functions `examples/qes_demo.py` already walks through interactively
(`qes.ca`, `qes.pades`, `qes.verify_pades`, `qes.tamper`) — a frozen
snapshot of an already-tested code path, not new crypto, so Phase 8 stays
honestly "no new verifier logic."

Run: .venv/bin/python examples/generate_qes_content.py
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

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "portal" / "content" / "qes_walkthrough.json"
NOW = datetime.datetime(2026, 6, 1, tzinfo=datetime.timezone.utc)


def build_walkthrough() -> dict:
    world = build_ca_world()
    chain = {
        "root": world.root_cert.subject.rfc4514_string(),
        "qtsp": world.qtsp_cert.subject.rfc4514_string(),
        "signer": world.qualified_leaf_cert.subject.rfc4514_string(),
        "tsa": world.tsa_cert.subject.rfc4514_string(),
    }

    signer = build_signer(world.qualified_leaf_cert, world.signer_key, [world.qtsp_cert, world.root_cert])
    timestamper = build_dummy_timestamper(world.tsa_cert, world.tsa_rsa_key, [world.qtsp_cert, world.root_cert], fixed_dt=NOW)
    blank_pdf = make_blank_pdf()
    signed_pdf = sign_pdf_qes(blank_pdf, signer=signer, timestamper=timestamper)

    config = config_from_ca_world(world)
    happy_result = verify_pades(signed_pdf, config, now=NOW)

    experiments = []
    for generator in tamper.ALL_EXPERIMENTS:
        experiment_world = build_ca_world()
        experiment_config = config_from_ca_world(experiment_world)
        variant = generator(experiment_world)
        experiment_result = verify_pades(variant.pdf_bytes, experiment_config, now=NOW)
        experiments.append(
            {
                "species": variant.species,
                "description": variant.description,
                "expected_field": variant.expected_field,
                "result": experiment_result,
            }
        )

    return {
        "chain": chain,
        "blank_pdf_bytes": len(blank_pdf),
        "signed_pdf_bytes": len(signed_pdf),
        "happy_result": happy_result,
        "experiments": experiments,
    }


def main() -> None:
    walkthrough = build_walkthrough()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(walkthrough, indent=2) + "\n")
    print(f"wrote QES recorded run ({len(walkthrough['experiments'])} experiments) to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
