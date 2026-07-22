"""
Phonk Pipeline Orchestrator (Aura / Dark Gym Phonk Edition).

Pipeline Order:
  1. prompts/prompt_generator.py       -> output/prompts_batch.json         (4 Aura Phonk prompts, 120s duration)
  2. cover/cover_art.py                -> output/covers/*.png               (AI Cover Art + 3 Reel Backgrounds per track)
                                       -> output/reels_bg/*.png
  3. metadata/metadata_builder.py    -> output/metadata.json              (Track metadata)
  4. generate/generate_music.py        -> output/audio/*.wav                (ACE-Step-1.5 2-minute WAV generation)
  5. package.py                        -> output/phonk_batch_<date>.zip     (Packages 4 Reels per track + metadata)
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent


def run_step(cmd: list[str], label: str):
    print(f"\n=== {label} ===")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        print(f"Step failed: {label}")
        sys.exit(result.returncode)


def main():
    ap = argparse.ArgumentParser(description="Run the Aura Phonk pipeline.")
    ap.add_argument("--count", type=int, default=4, help="Number of tracks to generate (default 4).")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--skip-audio", action="store_true", help="Skip GPU music generation.")
    ap.add_argument("--acestep-repo", type=str, default="./ACE-Step-1.5")
    args = ap.parse_args()

    prompts_path = ROOT / "output" / "prompts_batch.json"
    covers_dir = ROOT / "output" / "covers"
    reels_bg_dir = ROOT / "output" / "reels_bg"
    metadata_path = ROOT / "output" / "metadata.json"
    audio_dir = ROOT / "output" / "audio"

    run_step(
        [sys.executable, "prompts/prompt_generator.py", "--count", str(args.count),
         "--out", str(prompts_path)] + (["--seed", str(args.seed)] if args.seed is not None else []),
        "1/5 Generating LLM + RAG Aura Phonk Prompts (4 tracks, 120s)",
    )
    run_step(
        [sys.executable, "cover/cover_art.py", "--prompts", str(prompts_path),
         "--out-dir", str(covers_dir), "--reels-dir", str(reels_bg_dir)],
        "2/5 Generating AI Cover Arts & Motivational Reel Backgrounds",
    )
    run_step(
        [sys.executable, "metadata/metadata_builder.py", "--prompts", str(prompts_path), "--out", str(metadata_path)],
        "3/5 Building Track Metadata",
    )

    if not args.skip_audio:
        run_step(
            [sys.executable, "generate/generate_music.py", "--prompts", str(prompts_path),
             "--out-dir", str(audio_dir), "--acestep-repo", args.acestep_repo],
            "4/5 Generating 2-Minute Audio via ACE-Step-1.5 (GPU Required)",
        )
    else:
        print("\n=== 4/5 Skipped audio generation (--skip-audio) ===")

    run_step(
        [sys.executable, "package.py", "--covers", str(covers_dir), "--reels-dir", str(reels_bg_dir),
         "--metadata", str(metadata_path), "--audio", str(audio_dir) if not args.skip_audio else "",
         "--out-dir", str(ROOT / "output")],
        "5/5 Packaging Release Zip (4 Reels per track)",
    )


if __name__ == "__main__":
    main()
