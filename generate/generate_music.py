"""
Music generation via ACE-Step-1.5 (github.com/ace-step/ACE-Step-1.5, MIT license).

WHY THIS MODEL SPECIFICALLY:
ACE-Step-1.5 is MIT licensed end to end (weights, training code, inference
scripts), which means you can put the output on Spotify and monetize it
with no legal ambiguity. This matters because the two most-hyped
alternatives don't clear that bar:
  - Meta's MusicGen weights are CC-BY-NC-4.0: non-commercial only. Using
    it for a monetized Spotify catalog violates the license.
  - Stable Audio Open uses the Stability AI Community License, which
    only permits commercial use below a revenue threshold, and it caps
    output at 47 seconds, so it's built for SFX/texture, not full tracks.
ACE-Step-1.5 has none of those strings attached.

THE CATCH, STATED PLAINLY:
This model is built around a GPU (CUDA, ROCm, Apple MPS, or Intel XPU).
It is not architected for a CPU-only fallback. That means it will NOT
run at a usable speed, or may not run at all, on:
  - GitHub Actions' free runners (CPU only)
  - Oracle Cloud's Always Free tier (Ampere ARM CPU, no free GPU shape)
  - Cloudflare Workers (no Python runtime, no GPU, hard execution limits)
This is not a bug in this script, it's the actual hardware requirement
of every credible open-source music model right now. See README.md in
the project root for the zero-cost way around this (Kaggle's free GPU
quota, orchestrated by GitHub Actions).

USAGE (on a machine or Kaggle kernel that has a GPU and can reach
huggingface.co to download checkpoints):
    python generate_music.py --prompts output/prompts_batch.json --out-dir output/audio

Reference: this wrapper mirrors ace-step/ACE-Step-1.5's own
run_generate_test.py smoke test, adapted to loop over a prompt batch.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Clear proxy vars that can break model downloads, same as upstream cli.py does.
for _proxy_var in ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"]:
    os.environ.pop(_proxy_var, None)


def run(prompts_path: str, out_dir: str, acestep_repo_root: str, config_path: str = "acestep-v15-turbo"):
    # ACE-Step-1.5 must be installed / cloned alongside this script; we add
    # its repo root to sys.path so `import acestep...` resolves, matching
    # how the upstream cli.py and run_generate_test.py are structured.
    sys.path.insert(0, acestep_repo_root)

    from loguru import logger
    from acestep.handler import AceStepHandler
    from acestep.llm_inference import LLMHandler
    from acestep.inference import GenerationParams, GenerationConfig, generate_music

    Path(out_dir).mkdir(parents=True, exist_ok=True)
    checkpoint_dir = os.path.join(acestep_repo_root, "checkpoints")

    logger.info("Initializing DiT handler (turbo config)...")
    t0 = time.time()
    dit_handler = AceStepHandler()
    status_msg, ok = dit_handler.initialize_service(
        project_root=acestep_repo_root,
        config_path=config_path,     # "acestep-v15-turbo" trades a little quality for speed, worth it for batch runs
        device="auto",                 # auto-detects CUDA / MPS / XPU
        offload_to_cpu=False,
    )
    if not ok:
        logger.error(f"DiT init failed: {status_msg}")
        sys.exit(1)
    logger.info(f"DiT loaded in {time.time() - t0:.1f}s")

    logger.info("Checking and ensuring 5Hz LM (0.6B) model is downloaded...")
    lm_dir = Path(checkpoint_dir) / "acestep-5Hz-lm-0.6B"
    if not lm_dir.exists():
        logger.info(f"LM directory not found at {lm_dir}. Downloading from HuggingFace Hub...")
        try:
            from acestep.model_downloader import download_5hz_lm
            download_5hz_lm("0.6B", str(checkpoint_dir))
        except Exception as e:
            logger.warning(f"acestep download_5hz_lm fallback triggered ({e}), using huggingface_hub snapshot_download...")
            from huggingface_hub import snapshot_download
            snapshot_download(
                repo_id="ACE-Step/Ace-Step1.5",
                allow_patterns=["*acestep-5Hz-lm-0.6B*"],
                local_dir=str(Path(checkpoint_dir).parent),
            )

    logger.info("Initializing LLM handler (0.6B)...")
    t0 = time.time()
    llm_handler = LLMHandler()
    status_msg, ok = llm_handler.initialize(
        checkpoint_dir=checkpoint_dir,
        lm_model_path="acestep-5Hz-lm-0.6B",  # smallest LM tier; fine for Tier 3+ GPUs (6GB+ VRAM)
        backend="pt",                            # portable fallback; use "vllm" if you have an NVIDIA GPU with 8GB+ VRAM
        device="auto",
        offload_to_cpu=False,
        dtype=None,
    )
    if not ok:
        logger.error(f"LLM init failed: {status_msg}")
        sys.exit(1)
    logger.info(f"LLM loaded in {time.time() - t0:.1f}s")

    batch = json.loads(Path(prompts_path).read_text())
    results = []

    for i, entry in enumerate(batch):
        logger.info(f"[{i+1}/{len(batch)}] Generating {entry['slug']}...")
        params = GenerationParams(
            task_type="text2music",
            thinking=True,
            caption=entry["caption"],
            lyrics=entry.get("lyrics", ""),
            bpm=entry.get("bpm"),
            keyscale=entry.get("keyscale", ""),
            timesignature=entry.get("timesignature", "4"),
            vocal_language=entry.get("language", "en"),
            duration=entry.get("duration", 60),
            inference_steps=8,      # turbo config default; raise to ~30-50 for slightly better fidelity at the cost of time
            guidance_scale=1.0,
            seed=-1,
        )
        config = GenerationConfig(batch_size=1, audio_format="wav")

        t0 = time.time()
        result = generate_music(dit_handler, llm_handler, params=params, config=config, save_dir=out_dir)
        elapsed = time.time() - t0

        if result.success:
            for audio in result.audios:
                src = Path(audio["path"])
                dest = Path(out_dir) / f"{entry['slug']}.wav"
                if src != dest:
                    src.rename(dest)
                logger.info(f"  -> {dest} ({elapsed:.1f}s)")
                results.append({"slug": entry["slug"], "path": str(dest), "seconds": round(elapsed, 1)})
        else:
            logger.error(f"  FAILED ({elapsed:.1f}s): {result.status_message}")
            results.append({"slug": entry["slug"], "path": None, "error": result.status_message})

    summary_path = Path(out_dir) / "_generation_summary.json"
    summary_path.write_text(json.dumps(results, indent=2))
    logger.info(f"Done. {sum(1 for r in results if r.get('path'))}/{len(batch)} tracks generated. Summary: {summary_path}")


def main():
    ap = argparse.ArgumentParser(description="Generate phonk audio via ACE-Step-1.5 (requires GPU).")
    ap.add_argument("--prompts", type=str, required=True, help="Path to prompts_batch.json")
    ap.add_argument("--out-dir", type=str, default="output/audio")
    ap.add_argument(
        "--acestep-repo",
        type=str,
        default="./ACE-Step-1.5",
        help="Path to a cloned ace-step/ACE-Step-1.5 repo (git clone https://github.com/ace-step/ACE-Step-1.5.git)",
    )
    ap.add_argument("--config", type=str, default="acestep-v15-turbo")
    args = ap.parse_args()
    run(args.prompts, args.out_dir, args.acestep_repo, args.config)


if __name__ == "__main__":
    main()
