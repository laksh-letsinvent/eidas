"""
Corpus builder: ~50 labelled presentations across the thirteen scoreable
defect species (twelve from Phase 3, plus Phase 3.5's
`cross_device_origin_phish`), seeded and reproducible (BUILD_PROMPT_PHASE3.md
acceptance criterion 1).

`genuine` gets a meaningful share (8 items, varying which registered claims
are revealed) rather than a token one or two — the harness needs enough
genuine traffic to make a false-reject rate (BPCER) mean anything, not just
a sanity check that at least one accept exists. Every defect species gets
four repeats with different holder keys/salts/nonces (via `index`), so a
transient index-specific fluke can't masquerade as a species-level result.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from eval.species import ALL_SPECIES, GENERATORS, CorpusItem, World, build_world

# A fixed epoch, not wall-clock — every corpus item's `issued_at`/`expires_at`
# and the harness's `now` at verification time are pinned to this, so the
# corpus (and every score derived from it) is identical on every run,
# indefinitely, not just "reproducible today."
DEFAULT_NOW = 1_785_600_000  # 2026-08-02T00:00:00Z, arbitrary fixed point
DEFAULT_SEED = 3

GENUINE_COUNT = 8
DEFECT_REPEATS = 4

GENUINE_REVEAL_VARIANTS: tuple[tuple[str, ...], ...] = (
    ("age_over_18",),
    ("age_over_18", "nationality"),
    ("age_over_18", "given_name"),
    ("nationality", "given_name"),
    ("age_over_18", "nationality", "given_name"),
)


@dataclass(frozen=True)
class Corpus:
    seed: int
    now: int
    items: list[CorpusItem] = field(default_factory=list)


def build_corpus(seed: int = DEFAULT_SEED, now: int = DEFAULT_NOW, world: World | None = None) -> Corpus:
    """Every item's generator receives `index = seed * 10_000 + running_counter`
    — changing `seed` shifts every holder key, salt, and nonce in the corpus
    to a disjoint deterministic range, so two different seeds never
    accidentally collide on the same material."""
    world = world or build_world()
    base = seed * 10_000
    items: list[CorpusItem] = []
    counter = 0

    for i in range(GENUINE_COUNT):
        reveal = GENUINE_REVEAL_VARIANTS[i % len(GENUINE_REVEAL_VARIANTS)]
        items.append(GENERATORS["genuine"](world, index=base + counter, now=now, reveal=reveal))
        counter += 1

    for species in ALL_SPECIES:
        if species == "genuine":
            continue
        for _ in range(DEFECT_REPEATS):
            items.append(GENERATORS[species](world, index=base + counter, now=now))
            counter += 1

    return Corpus(seed=seed, now=now, items=items)
