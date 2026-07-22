"""
Packages a finished batch into release-ready track folders with 4 Reels per track:

  phonk_batch_2026-07-22/
    <slug>/
      <slug>.wav                 (2-minute high-quality audio)
      cover_<slug>.png           (Primary AI Cover Art)
      reel_bg_1_<slug>.png       (Motivational Aesthetic 1)
      reel_bg_2_<slug>.png       (Motivational Aesthetic 2)
      reel_bg_3_<slug>.png       (Motivational Aesthetic 3)
      reel_1.mp4                  (Video Reel 1: Cover)
      reel_2.mp4                  (Video Reel 2: Motivational 1)
      reel_3.mp4                  (Video Reel 3: Motivational 2)
      reel_4.mp4                  (Video Reel 4: Motivational 3)
      metadata.json              (Track metadata)
    metadata_all.json
"""

import argparse
import json
import os
import shutil
import subprocess
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent


def get_ffmpeg_cmd() -> str:
    """Finds system ffmpeg or uses imageio_ffmpeg fallback binary."""
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return sys_ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def render_reel(image_path: Path, audio_path: Path, output_mp4: Path) -> bool:
    """Uses ffmpeg to render a 1080x1920 vertical video reel."""
    ffmpeg_exe = get_ffmpeg_cmd()
    cmd = [
        ffmpeg_exe, "-y", "-loop", "1", "-i", str(image_path), "-i", str(audio_path),
        "-filter_complex",
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=luma_radius=min(h\\,w)/20:luma_power=1:chroma_radius=min(cw\\,ch)/20:chroma_power=1[bg]; "
        "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease[fg]; "
        "[bg][fg]overlay=(W-w)/2:(H-h)/2",
        "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p", "-shortest", str(output_mp4)
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res.returncode == 0
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser(description="Package batch with 4 Reels per track.")
    ap.add_argument("--covers", type=str, required=True, help="Covers directory")
    ap.add_argument("--reels-dir", type=str, default="output/reels_bg", help="Reel backgrounds directory")
    ap.add_argument("--metadata", type=str, required=True, help="Metadata JSON path")
    ap.add_argument("--audio", type=str, default="", help="Audio directory")
    ap.add_argument("--out-dir", type=str, default="output")
    args = ap.parse_args()

    metadata = json.loads(Path(args.metadata).read_text(encoding="utf-8"))
    batch_name = f"phonk_batch_{date.today().isoformat()}"
    staging = Path(args.out_dir) / batch_name
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)

    covers_dir = Path(args.covers)
    reels_bg_dir = Path(args.reels_dir)
    audio_dir = Path(args.audio) if args.audio else None

    packaged = 0
    for track in metadata:
        slug = track["slug"]
        track_dir = staging / slug
        track_dir.mkdir(parents=True, exist_ok=True)

        # 1. Copy Primary Cover Art
        cover_src = covers_dir / f"{slug}.png"
        if cover_src.exists():
            shutil.copy(cover_src, track_dir / f"cover_{slug}.png")

        # 2. Copy Reel Backgrounds (3 motivational images)
        for i in range(1, 4):
            bg_src = reels_bg_dir / f"reel_bg_{i}_{slug}.png"
            if bg_src.exists():
                shutil.copy(bg_src, track_dir / f"reel_bg_{i}_{slug}.png")

        # 3. Copy Audio File
        audio_src = audio_dir / f"{slug}.wav" if audio_dir else None
        if audio_src and audio_src.exists():
            shutil.copy(audio_src, track_dir / f"{slug}.wav")

            # 4. Render 4 Reels (Reel 1 = Cover, Reels 2-4 = Motivational Images)
            if cover_src.exists():
                print(f"[{slug}] Rendering Reel 1 (Cover)...")
                render_reel(cover_src, audio_src, track_dir / "reel_1.mp4")

            for i in range(1, 4):
                bg_src = reels_bg_dir / f"reel_bg_{i}_{slug}.png"
                if bg_src.exists():
                    print(f"[{slug}] Rendering Reel {i+1} (Motivational #{i})...")
                    render_reel(bg_src, audio_src, track_dir / f"reel_{i+1}.mp4")

        (track_dir / "metadata.json").write_text(json.dumps(track, indent=2, ensure_ascii=False), encoding="utf-8")
        packaged += 1

    (staging / "metadata_all.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    zip_path = Path(args.out_dir) / f"{batch_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in staging.rglob("*"):
            zf.write(file, file.relative_to(staging.parent))

    print(f"\nSuccessfully packaged {packaged} tracks with 4 Reels per track -> {zip_path}")


if __name__ == "__main__":
    main()
