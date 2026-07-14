"""
Packages a finished batch into a single zip:

  phonk_batch_2026-07-11/
    <slug>/
      <slug>.wav        (if audio was generated)
      <slug>.png
      metadata.json      (this track's entry only, for per-track distributor upload)
    metadata_all.json     (full batch, for your own records / Spotify for Artists bulk notes)

One folder per track keeps each upload self-contained, which matters
once you're doing this daily: you drag one folder into your
distributor, not hunt across three separate directories for matching
files.
"""

import argparse
import json
import shutil
import zipfile
from datetime import date
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description="Package a batch into a release-ready zip.")
    ap.add_argument("--covers", type=str, required=True)
    ap.add_argument("--metadata", type=str, required=True)
    ap.add_argument("--audio", type=str, default="", help="Audio dir; leave empty if audio wasn't generated yet.")
    ap.add_argument("--out-dir", type=str, default="output")
    args = ap.parse_args()

    metadata = json.loads(Path(args.metadata).read_text())
    batch_name = f"phonk_batch_{date.today().isoformat()}"
    staging = Path(args.out_dir) / batch_name
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    covers_dir = Path(args.covers)
    audio_dir = Path(args.audio) if args.audio else None

    packaged = 0
    for track in metadata:
        slug = track["slug"]
        track_dir = staging / slug
        track_dir.mkdir(parents=True, exist_ok=True)

        cover_src = covers_dir / track["cover_file"]
        if cover_src.exists():
            shutil.copy(cover_src, track_dir / track["cover_file"])

        if audio_dir:
            audio_src = audio_dir / track["audio_file"]
            if audio_src.exists():
                shutil.copy(audio_src, track_dir / track["audio_file"])

        (track_dir / "metadata.json").write_text(json.dumps(track, indent=2, ensure_ascii=False))
        packaged += 1

    (staging / "metadata_all.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False))

    zip_path = Path(args.out_dir) / f"{batch_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in staging.rglob("*"):
            zf.write(file, file.relative_to(staging.parent))

    print(f"Packaged {packaged} tracks -> {zip_path}")
    if audio_dir is None or not any(audio_dir.glob("*.wav")):
        print("NOTE: no audio files found. This zip has covers + metadata only. "
              "Run generate/generate_music.py on a GPU machine to fill in the .wav files.")


if __name__ == "__main__":
    main()
