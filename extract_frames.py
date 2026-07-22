"""
Frame Extractor for Phonk Reel Backgrounds.

Extracts 1080x1920 vertical frame snapshots from local MP4 video scene packs
using ffmpeg or imageio_ffmpeg.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
ASSETS_DIR = ROOT / "assets" / "videos"
OUTPUT_DIR = ROOT / "output" / "reels_bg"


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


def extract_frames_from_video(video_path: Path, output_dir: Path, interval_seconds: int = 5):
    """Uses ffmpeg to sample 1080x1920 cropped frames every N seconds."""
    output_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg_exe = get_ffmpeg_cmd()
    
    # Safe slugified name for output frame files
    safe_stem = video_path.stem.replace(" ", "_").replace("'", "").replace('"', "")[:30]
    out_pattern = str(output_dir / f"{safe_stem}_frame_%03d.png")
    
    cmd = [
        ffmpeg_exe, "-y", "-i", str(video_path),
        "-vf", f"fps=1/{interval_seconds},scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        out_pattern
    ]
    try:
        print(f"[Frame Extractor] Extracting frames from '{video_path.name}'...")
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0:
            print(f"  -> Successfully extracted frames into {output_dir}")
        else:
            print(f"  -> ffmpeg frame extraction completed with code {res.returncode}")
    except Exception as e:
        print(f"ERROR extracting frames: {e}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description="Extract 1080x1920 frames from scene pack videos.")
    ap.add_argument("--video-dir", type=str, default="assets/videos", help="Directory containing .mp4 videos")
    ap.add_argument("--out-dir", type=str, default="output/reels_bg", help="Output folder for frame images")
    ap.add_argument("--interval", type=int, default=5, help="Extract frame every N seconds")
    args = ap.parse_args()

    v_dir = Path(args.video_dir)
    o_dir = Path(args.out_dir)

    v_dir.mkdir(parents=True, exist_ok=True)
    o_dir.mkdir(parents=True, exist_ok=True)

    videos = list(v_dir.glob("*.mp4")) + list(v_dir.glob("*.mkv")) + list(v_dir.glob("*.webm"))
    if not videos:
        print(f"No video files found in '{v_dir}'. Drop your downloaded scene pack .mp4 files there!")
        return

    for vid in videos:
        extract_frames_from_video(vid, o_dir, args.interval)

    total_frames = len(list(o_dir.glob("*.png")))
    print(f"\nFrame extraction complete! Total background images available in output/reels_bg: {total_frames}")


if __name__ == "__main__":
    main()
