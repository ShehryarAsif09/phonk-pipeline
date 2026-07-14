# Phonk Batch Pipeline

Zero-cost, mostly-automated pipeline that turns prompts into a
distributor-ready batch of phonk tracks: audio, cover art, and metadata.
You review and upload, the rest runs itself.

## What it actually does, stage by stage

| Stage | Script | Compute needed | Cost |
|---|---|---|---|
| 1. Prompts | `prompts/prompt_generator.py` | CPU | $0 |
| 2. Cover art | `cover/cover_art.py` | CPU | $0 |
| 3. Metadata | `metadata/metadata_builder.py` | CPU | $0 |
| 4. Audio | `generate/generate_music.py` | GPU | $0, with a catch (below) |
| 5. Package | `package.py` | CPU | $0 |

Stages 1, 2, 3, and 5 ran successfully in testing and produce real
output, you can check `output/` for a sample 10-track batch with
covers and metadata already generated. Stage 4 is the one honest
exception in this whole plan, and it deserves a straight explanation
instead of a workaround dressed up as a solution.

## Why stage 4 is the hard part

The model doing the actual generation is **ACE-Step-1.5**
(`github.com/ace-step/ACE-Step-1.5`), and it's the right choice for
your use case specifically because it's **MIT licensed end to end**,
weights included. That means you can put its output on Spotify and
keep 100% of the royalties with no legal gray area. Compare that to
the two other names that come up in every "free AI music" article:

| Model | License | Can you monetize the output? |
|---|---|---|
| ACE-Step-1.5 | MIT | Yes, no restriction |
| Meta MusicGen | CC-BY-NC-4.0 | No, non-commercial only |
| Stable Audio Open | Stability AI Community License | Only below a revenue threshold, and capped at 47 seconds output |

So ACE-Step-1.5 is correct on legal grounds. The catch: I pulled the
actual source code to verify this rather than go off memory, and it
confirms the model is built around a real GPU (CUDA, AMD ROCm, Apple
MPS, or Intel XPU). There's no CPU fallback path in the codebase. That
means it will not run at usable speed, or may not run at all, on:

- GitHub Actions' free runners (CPU only, no GPU option on free tier)
- Oracle Cloud's Always Free tier (Ampere ARM CPU, no free GPU shape exists)
- Cloudflare Workers (no Python/PyTorch runtime, hard 30-second CPU execution cap, no GPU)

This isn't a workaround-able limitation, every credible open-source
music model right now needs a GPU. If a tutorial tells you otherwise,
it's either using a paid GPU rental, or it's not actually testing at
real quality.

## The zero-cost way through it: Kaggle

Kaggle's free tier gives every account **30 GPU-hours/week** on a T4
or P100, for $0, and exposes an API (`kaggle kernels push` /
`kaggle kernels output`) that a script can drive. That's the one
legitimate free GPU in this entire stack, so the architecture is:

```
GitHub Actions (free, CPU, scheduled)
  |
  |-- generates prompts, covers, metadata directly (stages 1-3)
  |-- pushes a Kaggle kernel with that day's prompts (stage 4 trigger)
  |
Kaggle kernel (free, GPU, 30 hrs/week cap)
  |
  |-- clones ACE-Step-1.5, generates the .wav files
  |-- hands them back via the Kaggle API
  |
GitHub Actions (resumes)
  |
  |-- packages everything into one zip (stage 5)
  |-- publishes it to your repo's Releases page
```

Everything is already wired up in `.github/workflows/generate-phonks.yml`
and `kaggle/kaggle_kernel.py`. You need to do two things once:

1. Create a free Kaggle account, go to Settings, create an API token,
   this gives you a username and key.
2. In your GitHub repo, go to Settings, Secrets and variables, Actions,
   and add `KAGGLE_USERNAME` and `KAGGLE_KEY` with those values.

After that, the workflow runs on its own schedule (default: daily at
02:00 UTC, edit the cron line to change it) and you'll find a zip on
your Releases page each morning.

**Being straight about the tradeoff**: 30 GPU-hours/week is a real cap,
and Kaggle's free tier is meant for individual notebook use, not
guaranteed uptime for a commercial pipeline. Treat this as your
bootstrap phase, not your permanent infrastructure. Once tracks start
earning, move stage 4 to a rented GPU (RTX 3060-class spot instances
run roughly $0.15 to $0.30/day). That's a real cost, but it's small,
and it buys you reliability instead of a shared free quota.

## Why not just run it on your Oracle box?

Your MailBurn stack is already running on the Oracle Always Free
Ampere instance, and Oracle halved the free ARM allocation in June
2026 to 2 OCPU/12GB total for the tenancy. That's already committed to
Haraka, Dovecot, PostgreSQL, and Redis. Stacking a GPU-hungry ML
workload on top of a production email server sharing that allocation
is asking for resource contention on both sides, and Oracle's free
tier has no GPU shape regardless, so it wouldn't solve stage 4 even
if you dedicated the whole box to it.

Where Oracle and Cloudflare *do* fit here:

- **Cloudflare R2** (10GB free storage, no egress fees) is a good
  place to host the finished zips/audio files long-term if GitHub
  Releases ever feels cramped.
- **Cloudflare Workers** is fine for a thin API layer (serving
  metadata, a status endpoint, a webhook), just not for the generation
  itself.
- **Your Oracle box** stays dedicated to MailBurn. Don't put this
  pipeline there.

## Running it yourself, locally or in the sandbox

```bash
# CPU-only stages, works anywhere, no GPU needed:
python pipeline.py --count 20 --skip-audio

# Full pipeline, needs a GPU machine with ACE-Step-1.5 cloned nearby:
git clone https://github.com/ace-step/ACE-Step-1.5.git
pip install -r ACE-Step-1.5/requirements.txt
python pipeline.py --count 20 --acestep-repo ./ACE-Step-1.5
```

Output lands in `output/`, one folder per track (audio, cover,
per-track metadata.json), plus a dated zip ready to hand to your
distributor (FreshTunes or RouteNote Free, per the earlier cost
comparison, both $0 upfront).

## What's actually proven vs. what needs a GPU to test

Proven in this sandbox: prompt generation, cover art, metadata,
packaging, all ran end to end and produced the sample batch in
`output/`. Not runnable here: stage 4, because this sandbox has
neither a GPU nor network access to huggingface.co. That code is
written directly against ACE-Step-1.5's own real API (verified by
reading their source, not guessed), but you'll want to run one small
test batch (2 to 3 tracks) on Kaggle before trusting the full daily
cron, same as you'd sanity-check any new pipeline.

## Next honest milestone

Once this is producing a real catalog, the actual bottleneck moves to
where it always was: distribution, not generation. The pipeline gets
you volume at $0. Getting real listeners still needs the TikTok/Reels
promotion loop from the earlier plan.
