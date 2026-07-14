"""
Pipeline orchestrator.

Runs, in order:
  1. prompt_generator.py   -> output/prompts_batch.json         (CPU, free, instant)
  2. cover/cover_art.py     -> output/covers/*.png               (CPU, free, seconds)
  3. metadata/metadata_builder.py -> output/metadata.json        (CPU, free, instant)
  4. generate/generate_music.py -> output/audio/*.wav            (GPU required, see README)
  5. package.py             -> output/phonk_batch_<date>.zip     (CPU, free)

Steps 1-3 and 5 run anywhere, including this sandbox, GitHub Actions,
or your laptop. Step 4 is the one that needs a GPU (see README.md for
why, and the Kaggle-based zero-cost workaround).

Run with --skip-audio to execute everything except the GPU step, e.g.
to test the rest of the pipeline on a machine without a GPU.
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
    ap = argparse.ArgumentParser(description="Run the full phonk pipeline.")
    ap.add_argument("--count", type=int, default=20, help="Number of tracks to generate.")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--skip-audio", action="store_true", help="Skip the GPU-dependent music generation step.")
    ap.add_argument("--acestep-repo", type=str, default="./ACE-Step-1.5")
    args = ap.parse_args()

    prompts_path = ROOT / "output" / "prompts_batch.json"
    covers_dir = ROOT / "output" / "covers"
    metadata_path = ROOT / "output" / "metadata.json"
    audio_dir = ROOT / "output" / "audio"

    run_step(
        [sys.executable, "prompts/prompt_generator.py", "--count", str(args.count),
         "--out", str(prompts_path)] + (["--seed", str(args.seed)] if args.seed is not None else []),
        "1/5 Generating prompts",
    )
    run_step(
        [sys.executable, "cover/cover_art.py", "--prompts", str(prompts_path), "--out-dir", str(covers_dir)],
        "2/5 Generating cover art",
    )
    run_step(
        [sys.executable, "metadata/metadata_builder.py", "--prompts", str(prompts_path), "--out", str(metadata_path)],
        "3/5 Building metadata",
    )

    if not args.skip_audio:
        run_step(
            [sys.executable, "generate/generate_music.py", "--prompts", str(prompts_path),
             "--out-dir", str(audio_dir), "--acestep-repo", args.acestep_repo],
            "4/5 Generating audio (GPU required)",
        )
    else:
        print("\n=== 4/5 Skipped audio generation (--skip-audio) ===")

    run_step(
        [sys.executable, "package.py", "--covers", str(covers_dir), "--metadata", str(metadata_path),
         "--audio", str(audio_dir) if not args.skip_audio else "", "--out-dir", str(ROOT / "output")],
        "5/5 Packaging release zip",
    )


if __name__ == "__main__":
    main()
