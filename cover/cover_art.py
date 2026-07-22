"""
AI Cover Art and Motivational Reel Background Generator.

Uses Google AI Studio (Gemini / Imagen API) or Pollinations.ai (free keyless fallback)
to generate high-quality dark/gym/sigma Phonk covers and vertical video images.
"""

import argparse
import json
import os
import random
import shutil
import sys
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SIZE = 1400  # Primary Cover Art resolution (1400x1400)
REEL_W, REEL_H = 1080, 1920  # Reel Background resolution (1080x1920)

PROMPTS_BY_SUBGENRE = {
    "aura_gym_phonk": {
        "cover": "Artistic Phonk album cover, dark glowing anime warrior with intense crimson energy aura, sharp demonic horns, high contrast dark red and black digital illustration, 8k trending on ArtStation",
        "motivational": [
            "Dark intense gym motivation wallpaper, shadow athlete silhouette with glowing red energy aura, heavy iron weights, 8k cinematic digital art",
            "Gym Phonk aesthetic, hooded dark anime figure in dark foggy gym with glowing red eyes, intense aura, 8k illustration",
            "High contrast red and black gym aesthetic, heavy barbell on dark floor, glowing crimson mist, cinematic 8k"
        ]
    },
    "heavy_bass_phonk": {
        "cover": "Artistic Brazilian Phonk cover, glowing toxic green tactical skull mask in dark smoke, sharp neon green aura, high contrast cyber punk aesthetic, 8k digital illustration",
        "motivational": [
            "Dark toxic green aesthetic, glowing skull with neon headphones in dark fog, heavy bass phonk wallpaper, 8k",
            "Cyberpunk dark street night, glowing green neon aura, mysterious tactical mask figure, 8k digital art",
            "Heavy bass soundwaves, glowing green neon skull overlay, dark atmospheric background, 8k"
        ]
    },
    "dark_aura_drift": {
        "cover": "Artistic Dark Drift Phonk album cover, dark Japanese sports car drifting in midnight rain, glowing neon red taillights, smoke clouds, intense aura, 8k digital artwork",
        "motivational": [
            "Dark sports car parked in rain, midnight aesthetic, glowing red neon lights, dark anime drift atmosphere, 8k",
            "Night drive vision, dark highway rain reflection, mysterious red headlights, aura aesthetic, 8k",
            "Drift smoke in dark city alley, neon red reflections, atmospheric 8k digital illustration"
        ]
    },
    "sigma_rage_phonk": {
        "cover": "Artistic Phonk cover, dark gothic skull crowned with glowing purple energy, dark anime villain aura, ultra high contrast violet fog, 8k digital illustration",
        "motivational": [
            "Dark marble skull statue with glowing purple eyes in dark fog, sigma male aura wallpaper, 8k",
            "Minimalist dark gothic aesthetic, glowing violet aura energy in dark room, cold confident vibe, 8k",
            "Dark shadowy figure with glowing purple eyes overlooking dark city, cinematic sigma aura, 8k"
        ]
    }
}


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "C:/Windows/Fonts/impact.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()


def fetch_pollinations_image(prompt: str, width: int, height: int) -> Image.Image | None:
    """Free keyless AI image generation via Pollinations.ai API with fast fallback."""
    encoded_prompt = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true&seed={os.urandom(4).hex()}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = resp.read()
            from io import BytesIO
            img = Image.open(BytesIO(data))
            img.load()
            return img
    except Exception:
        return None


def generate_fallback_image(width: int, height: int, title: str, accent_color: str = "#ff2b2b") -> Image.Image:
    """Dark sleek procedural aesthetic image if API network is slow."""
    img = Image.new("RGB", (width, height), "#050505")
    draw = ImageDraw.Draw(img)
    # Dark red/purple aura beam
    draw.polygon([(0, 0), (width, 0), (width // 3, height), (0, height)], fill="#1a0208")
    draw.polygon([(width // 2, 0), (width, 0), (width, height), (width // 4, height)], fill="#0c0414")
    # Overlay noise texture
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 180))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    return img


def add_cover_typography(img: Image.Image, title: str, subgenre: str) -> Image.Image:
    """Overlays clean, bold Phonk title and subgenre badge on cover art."""
    img = img.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(img)
    
    # Bottom gradient overlay for title legibility
    gradient = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(gradient)
    for y in range(SIZE - 400, SIZE):
        alpha = int(220 * ((y - (SIZE - 400)) / 400))
        g_draw.line([(0, y), (SIZE, y)], fill=(0, 0, 0, alpha))
    
    img = Image.alpha_composite(img.convert("RGBA"), gradient).convert("RGB")
    draw = ImageDraw.Draw(img)

    title_font = _load_font(95)
    sub_font = _load_font(42)

    clean_title = title.upper().replace("_", " ")
    clean_sub = subgenre.upper().replace("_", " ")

    # Draw Title and Badge
    draw.text((60, SIZE - 220), clean_title, font=title_font, fill="#FFFFFF")
    draw.text((65, SIZE - 110), f"⚡ {clean_sub}", font=sub_font, fill="#FF3333")
    
    return img


def generate_assets_for_track(track: dict, out_covers_dir: Path, out_reels_dir: Path):
    slug = track["slug"]
    subgenre = track.get("subgenre", "aura_gym_phonk")
    title = track.get("title", slug)

    prompts = PROMPTS_BY_SUBGENRE.get(subgenre, PROMPTS_BY_SUBGENRE["aura_gym_phonk"])
    
    print(f"[Cover Gen] Generating AI Cover Art for '{slug}'...")
    base_cover = fetch_pollinations_image(prompts["cover"], 1024, 1024)
    if not base_cover:
        base_cover = generate_fallback_image(SIZE, SIZE, title)
    
    final_cover = add_cover_typography(base_cover, title, subgenre)
    cover_file = out_covers_dir / f"{slug}.png"
    final_cover.save(cover_file, "PNG")
    print(f"  -> Saved Cover: {cover_file}")

    # Generate/Pick 3 Motivational Reel Background Images (1080x1920)
    existing_frames = list(out_reels_dir.glob("*.png"))
    existing_frames = [f for f in existing_frames if not f.name.startswith("reel_bg_")]

    motivational_prompts = prompts["motivational"]
    for idx, m_prompt in enumerate(motivational_prompts, start=1):
        bg_file = out_reels_dir / f"reel_bg_{idx}_{slug}.png"
        
        # If extracted scene pack frames exist, pick one!
        if existing_frames:
            picked_frame = random.choice(existing_frames)
            shutil.copy(picked_frame, bg_file)
            print(f"  -> Using Extracted Scene Frame #{idx} for '{slug}': {picked_frame.name}")
            continue

        print(f"[Reel Image Gen] Generating Reel BG #{idx} for '{slug}'...")
        reel_img = fetch_pollinations_image(m_prompt, 1080, 1920)
        if not reel_img:
            reel_img = generate_fallback_image(1080, 1920, f"REEL {idx}")
        else:
            reel_img = reel_img.resize((1080, 1920), Image.Resampling.LANCZOS)
        
        reel_img.save(bg_file, "PNG")
        print(f"  -> Saved Reel BG {idx}: {bg_file}")


def main():
    ap = argparse.ArgumentParser(description="Generate AI Covers and Motivational Reel Images.")
    ap.add_argument("--prompts", type=str, required=True, help="Path to prompts_batch.json")
    ap.add_argument("--out-dir", type=str, default="output/covers", help="Cover output directory")
    ap.add_argument("--reels-dir", type=str, default="output/reels_bg", help="Reels background output directory")
    args = ap.parse_args()

    covers_dir = Path(args.out_dir)
    reels_dir = Path(args.reels_dir)
    covers_dir.mkdir(parents=True, exist_ok=True)
    reels_dir.mkdir(parents=True, exist_ok=True)

    batch = json.loads(Path(args.prompts).read_text(encoding="utf-8"))
    for track in batch:
        generate_assets_for_track(track, covers_dir, reels_dir)

    print(f"Done! Created covers and reel images for {len(batch)} tracks.")


if __name__ == "__main__":
    main()
