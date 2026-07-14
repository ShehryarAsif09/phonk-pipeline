"""
Runs INSIDE a Kaggle kernel (free T4/P100 GPU, 30 GPU-hours/week quota).

Why Kaggle and not GitHub Actions or Oracle directly: ACE-Step-1.5 needs
a real GPU (see generate/generate_music.py for the full explanation).
GitHub Actions runners and Oracle's Always Free tier are CPU only.
Kaggle's free tier is the one place that hands out real GPU-hours for
$0, and it exposes an API (`kaggle kernels push` / `... output`) that a
GitHub Actions workflow can drive on a schedule. That's the whole trick.

This file is a TEMPLATE. The `PROMPTS_JSON` block below gets replaced
by the GitHub Actions workflow (see ../.github/workflows/generate-phonks.yml)
with that day's actual prompt batch before the kernel is pushed to
Kaggle. Don't hand-edit PROMPTS_JSON here directly, edit
prompts/prompt_generator.py instead.

Kaggle usage caveat: the free GPU quota (30 hrs/week) is meant for
individual notebook use, not guaranteed uptime for a commercial
pipeline. Treat this as the bootstrap phase. Once the catalog is
producing real revenue, move generation to a paid GPU rental (RTX
3060-class instances run about $0.15-0.30/day on spot providers) so
you're not depending on a free tier for something you're monetizing.
"""

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

PROMPTS_JSON = """__PROMPTS_JSON_PLACEHOLDER__"""

WORK_DIR = Path("/kaggle/working")
REPO_DIR = WORK_DIR / "ACE-Step-1.5"
AUDIO_DIR = WORK_DIR / "audio_out"


def sh(cmd: str):
    print(f"$ {cmd}")
    subprocess.run(cmd, shell=True, check=True)


def main():
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    prompts_path = WORK_DIR / "prompts_batch.json"
    prompts_path.write_text(PROMPTS_JSON)

    if not REPO_DIR.exists():
        sh(f"git clone --depth 1 https://github.com/ace-step/ACE-Step-1.5.git {REPO_DIR}")
        sh(f"pip install -q -r {REPO_DIR}/requirements.txt")

    # generate_music.py is bundled into this same directory at push time by the
    # GitHub Actions workflow (kaggle kernels push uploads every file sitting
    # next to kernel-metadata.json), so this import just works on Kaggle.
    sys.path.insert(0, str(Path(__file__).parent))
    import generate_music as gm
    gm.run(str(prompts_path), str(AUDIO_DIR), str(REPO_DIR))

    zip_path = WORK_DIR / "phonk_audio_batch.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in AUDIO_DIR.rglob("*"):
            zf.write(f, f.relative_to(WORK_DIR))
    print(f"Done. Output zip at {zip_path}")


if __name__ == "__main__":
    main()
