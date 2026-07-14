"""
Metadata builder.

Turns each prompt entry into the fields a distributor (FreshTunes,
RouteNote) and social captions actually need: title, artist/brand,
description, tags, mood. Pure string templating, zero cost, zero
external calls.
"""

import argparse
import json
from pathlib import Path

# One "artist brand" per sub-genre, matching the earlier multi-brand strategy
# so streams spread across catalogs instead of one account carrying everything.
ARTIST_BRANDS = {
    "gym_phonk": "IronPhonk",
    "drift_phonk": "NightDrive",
    "rage_phonk": "Beast Mode",
    "sigma_phonk": "Alpha Frequency",
    "dark_phonk": "DarkPulse",
}

HASHTAGS_BY_SUBGENRE = {
    "gym_phonk": ["#phonk", "#gymphonk", "#workoutmusic", "#gymmotivation"],
    "drift_phonk": ["#phonk", "#driftphonk", "#nightdrive", "#carmusic"],
    "rage_phonk": ["#phonk", "#ragephonk", "#hardphonk"],
    "sigma_phonk": ["#phonk", "#sigmaphonk", "#sigmamusic"],
    "dark_phonk": ["#phonk", "#darkphonk", "#horrorphonk"],
}


def build_metadata(entry: dict, track_number: int) -> dict:
    subgenre = entry["subgenre"]
    brand = ARTIST_BRANDS.get(subgenre, "Unknown Artist")
    title = f"{entry['mood'].capitalize()} {subgenre.replace('_', ' ').title()} #{track_number}"
    description = (
        f"{title}. {entry['bpm']} BPM, {entry['keyscale']}. "
        f"Built for {('workouts' if subgenre == 'gym_phonk' else 'night drives' if subgenre == 'drift_phonk' else 'focus and edits')}. "
        f"Instrumental phonk, no vocals."
    )
    tags = HASHTAGS_BY_SUBGENRE.get(subgenre, ["#phonk"])

    return {
        "slug": entry["slug"],
        "track_number": track_number,
        "artist": brand,
        "title": title,
        "description": description,
        "genre": "Phonk",
        "subgenre": subgenre,
        "mood": entry["mood"],
        "bpm": entry["bpm"],
        "key": entry["keyscale"],
        "tags": tags,
        "explicit": False,
        "language": "Instrumental",
        "cover_file": f"{entry['slug']}.png",
        "audio_file": f"{entry['slug']}.wav",
    }


def main():
    ap = argparse.ArgumentParser(description="Build distributor + social metadata for each track.")
    ap.add_argument("--prompts", type=str, required=True)
    ap.add_argument("--out", type=str, default="output/metadata.json")
    args = ap.parse_args()

    batch = json.loads(Path(args.prompts).read_text())
    metadata = [build_metadata(entry, i + 1) for i, entry in enumerate(batch)]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False))
    print(f"Wrote metadata for {len(metadata)} tracks to {out_path}")


if __name__ == "__main__":
    main()
