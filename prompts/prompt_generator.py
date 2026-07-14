"""
Phonk prompt generator.

Why template-based instead of an LLM call:
- Zero cost, zero API key, zero rate limit, zero network dependency.
- Phonk sub-genres are formulaic (BPM range + a handful of signature
  instruments + a mood word), so a combinatorial template covers the
  space just as well as an LLM would, without a moving part that can
  fail or cost money.
- If you later want more variety, drop in a free-tier Groq call here
  (you already use Groq elsewhere) but that's an upgrade, not a
  requirement to get this running.

Output: a list of dicts matching the shape ACE-Step-1.5 expects
(caption, bpm, keyscale, timesignature, duration, language), plus a
`subgenre` and `slug` field the rest of the pipeline uses for
filenames and metadata.
"""

import argparse
import json
import random
from pathlib import Path

# Each sub-genre = its own "artist brand" bucket per the earlier strategy.
SUBGENRES = {
    "gym_phonk": {
        "bpm": (150, 165),
        "keys": ["C minor", "D minor", "F minor", "G minor"],
        "instruments": [
            "distorted 808 bass", "aggressive cowbell", "Memphis vocal chops",
            "punchy trap hats", "sub-bass drop", "gritty vinyl crackle",
        ],
        "moods": ["aggressive", "high-energy", "menacing", "relentless"],
    },
    "drift_phonk": {
        "bpm": (140, 155),
        "keys": ["A minor", "E minor", "B minor"],
        "instruments": [
            "screechy tape-saturated synth", "cowbell", "car engine texture",
            "deep rolling 808", "chopped soul vocal sample", "night-drive pad",
        ],
        "moods": ["moody", "nocturnal", "cinematic", "hypnotic"],
    },
    "rage_phonk": {
        "bpm": (155, 170),
        "keys": ["C# minor", "F# minor", "G minor"],
        "instruments": [
            "distorted rage lead", "screaming 808 glide", "hard-hitting kick",
            "industrial noise stab", "reverse cymbal riser", "detuned bell",
        ],
        "moods": ["chaotic", "explosive", "dark", "unhinged"],
    },
    "sigma_phonk": {
        "bpm": (130, 145),
        "keys": ["D minor", "A minor", "E minor"],
        "instruments": [
            "slowed vocal chop", "minimalist 808", "cowbell hits",
            "wide reverb tail", "cold synth pad", "sparse hi-hat pattern",
        ],
        "moods": ["cold", "confident", "brooding", "stylish"],
    },
    "dark_phonk": {
        "bpm": (135, 150),
        "keys": ["F minor", "C minor", "B minor"],
        "instruments": [
            "horror-tinged pad", "muffled 808", "eerie choir stab",
            "cowbell", "distorted bass growl", "tape hiss",
        ],
        "moods": ["ominous", "haunting", "heavy", "tense"],
    },
}

TIMESIGNATURE = "4"
LANGUAGE = "en"  # phonk is instrumental-first; kept for schema completeness


def _slugify(subgenre: str, index: int) -> str:
    return f"{subgenre}_{index:04d}"


def generate_prompt(subgenre: str, index: int, rng: random.Random) -> dict:
    cfg = SUBGENRES[subgenre]
    bpm = rng.randint(*cfg["bpm"])
    key = rng.choice(cfg["keys"])
    mood = rng.choice(cfg["moods"])
    instruments = rng.sample(cfg["instruments"], k=min(3, len(cfg["instruments"])))
    caption = (
        f"A {mood} {subgenre.replace('_', ' ')} track at {bpm} BPM in {key}, "
        f"built around {', '.join(instruments[:-1])} and {instruments[-1]}. "
        f"Instrumental, no lyrics, built for a workout or night drive edit."
    )
    return {
        "subgenre": subgenre,
        "slug": _slugify(subgenre, index),
        "caption": caption,
        "lyrics": "",  # instrumental
        "bpm": bpm,
        "keyscale": key,
        "timesignature": TIMESIGNATURE,
        "duration": 60,  # seconds; short-form for Shorts/Reels-first distribution
        "language": LANGUAGE,
        "mood": mood,
        "instruments": instruments,
    }


def generate_batch(count: int, seed: int | None = None) -> list[dict]:
    rng = random.Random(seed)
    subgenre_names = list(SUBGENRES.keys())
    batch = []
    for i in range(count):
        subgenre = subgenre_names[i % len(subgenre_names)]
        batch.append(generate_prompt(subgenre, i, rng))
    return batch


def main():
    ap = argparse.ArgumentParser(description="Generate phonk prompts (zero-cost, template based).")
    ap.add_argument("--count", type=int, default=20, help="How many prompts to generate.")
    ap.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility.")
    ap.add_argument("--out", type=str, default="prompts_batch.json", help="Output JSON file.")
    args = ap.parse_args()

    batch = generate_batch(args.count, args.seed)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(batch, indent=2, ensure_ascii=False))
    print(f"Wrote {len(batch)} prompts to {out_path}")


if __name__ == "__main__":
    main()
