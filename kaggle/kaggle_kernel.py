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

import base64
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

PROMPTS_B64 = "__PROMPTS_B64_PLACEHOLDER__"
GENERATE_MUSIC_B64 = "__GENERATE_MUSIC_B64_PLACEHOLDER__"

WORK_DIR = Path("/kaggle/working")
REPO_DIR = WORK_DIR / "ACE-Step-1.5"
AUDIO_DIR = WORK_DIR / "audio_out"


def sh(cmd: str):
    print(f"$ {cmd}")
    subprocess.run(cmd, shell=True, check=True)


def main():
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    prompts_path = WORK_DIR / "prompts_batch.json"
    if not PROMPTS_B64.startswith("__"):
        prompts_json = base64.b64decode(PROMPTS_B64.encode("ascii")).decode("utf-8")
    else:
        prompts_json = Path("output/prompts_batch.json").read_text() if Path("output/prompts_batch.json").exists() else "[]"
    prompts_path.write_text(prompts_json)

    if not REPO_DIR.exists():
        sh(f"git clone --depth 1 https://github.com/ace-step/ACE-Step-1.5.git {REPO_DIR}")
        req_file = REPO_DIR / "requirements.txt"
        if req_file.exists():
            clean_lines = [
                line for line in req_file.read_text().splitlines()
                if not any(pkg in line.lower() for pkg in ["flash-attn", "torch==", "torchvision", "torchaudio"])
            ]
            req_file.write_text("\n".join(clean_lines))
        sh(f"pip install -q -r {REPO_DIR}/requirements.txt")

    # Detect legacy P100 (sm_60) and reinstall ABI-matched torch 2.4.
    # We MUST run generate_music in a subprocess after this because the
    # current Python process already has torch 2.6's C++ symbols loaded
    # in memory — importing torchaudio 2.4 in-process causes an ABI
    # mismatch (undefined symbol _ZNK5torch8autograd4Node4nameEv).
    _needs_subprocess = False
    try:
        import torch
        if torch.cuda.is_available() and torch.cuda.get_device_capability()[0] < 7:
            cap = torch.cuda.get_device_capability()
            print(f"Legacy GPU detected (compute capability {cap}). Installing ABI-matched PyTorch 2.4 for sm_60...")
            sh("pip install -q --force-reinstall torch==2.4.0+cu121 torchvision==0.19.0+cu121 torchaudio==2.4.0+cu121 --index-url https://download.pytorch.org/whl/cu121")
            # Kaggle's pre-installed diffusers 0.34+ uses @_custom_op with PEP 604
            # union annotations (float | None) that torch 2.4's infer_schema rejects.
            # Pin to 0.31.0 which has AutoencoderOobleck but predates attention_dispatch.py.
            sh("pip install -q 'diffusers==0.31.0'")
            _needs_subprocess = True
    except Exception as e:
        print(f"GPU check notice: {e}")

    # Phase 4: Checkpoint caching from private Kaggle Dataset under /kaggle/input
    checkpoints_dest = REPO_DIR / "checkpoints"
    checkpoints_dest.mkdir(parents=True, exist_ok=True)
    input_dir = Path("/kaggle/input")
    if input_dir.exists():
        for ds_dir in input_dir.iterdir():
            if ds_dir.is_dir() and ("acestep" in ds_dir.name.lower() or "checkpoint" in ds_dir.name.lower()):
                print(f"Found local checkpoint dataset: {ds_dir}")
                for item in ds_dir.iterdir():
                    target = checkpoints_dest / item.name
                    if not target.exists():
                        try:
                            target.symlink_to(item)
                            print(f"  Symlinked {item.name} -> {target}")
                        except Exception as e:
                            import shutil
                            if item.is_dir():
                                shutil.copytree(item, target)
                            else:
                                shutil.copy2(item, target)
                            print(f"  Copied {item.name} -> {target} ({e})")

    # Write generate_music.py to working directory
    gm_path = WORK_DIR / "generate_music.py"
    if not GENERATE_MUSIC_B64.startswith("__"):
        gm_path.write_bytes(base64.b64decode(GENERATE_MUSIC_B64.encode("ascii")))
    elif Path("generate_music.py").exists():
        gm_path.write_text(Path("generate_music.py").read_text())

    if _needs_subprocess:
        # Fresh Python process loads the correct torch 2.4 .so from disk
        print("Running generate_music.py in subprocess (fresh torch ABI)...")
        subprocess.run(
            [sys.executable, "-c",
             f"import sys; sys.path.insert(0, '{WORK_DIR}'); sys.path.insert(0, '{REPO_DIR}'); "
             f"import generate_music as gm; gm.run('{prompts_path}', '{AUDIO_DIR}', '{REPO_DIR}')"],
            check=True,
        )
    else:
        sys.path.insert(0, str(WORK_DIR))
        import generate_music as gm
        gm.run(str(prompts_path), str(AUDIO_DIR), str(REPO_DIR))

    zip_path = WORK_DIR / "phonk_audio_batch.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in AUDIO_DIR.rglob("*"):
            zf.write(f, f.relative_to(WORK_DIR))
    print(f"Done. Output zip at {zip_path}")


if __name__ == "__main__":
    main()

