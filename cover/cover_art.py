"""
Cover art generator.

Why procedural instead of an AI image model (SDXL/FLUX):
- Those need a GPU too, same problem as the music model. Stacking two
  GPU-hungry models on top of a "$0 upfront" requirement just moves the
  bottleneck, it doesn't remove it.
- Phonk cover art is a well-known visual formula: high contrast, one
  bold color, grainy texture, big condensed type. That's fully
  achievable with Pillow (already installed, pure CPU, milliseconds
  per image) and looks the part for Spotify/TikTok thumbnails.
- Upgrade path: once the catalog is earning, swap this module for an
  SDXL call (local or hosted) without touching the rest of the
  pipeline, since it just needs to produce a .png at the given path.
"""

import argparse
import hashlib
import json
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# One accent color per sub-genre so the artist "brands" stay visually distinct.
SUBGENRE_PALETTES = {
    "gym_phonk": ("#0a0a0a", "#ff2b2b"),
    "drift_phonk": ("#050510", "#3ba7ff"),
    "rage_phonk": ("#120005", "#ff6a00"),
    "sigma_phonk": ("#0a0a0a", "#c9c9c9"),
    "dark_phonk": ("#000000", "#7a2bff"),
}

SIZE = 1400  # Spotify recommends >= 3000x3000, but 1400 is plenty for social clips;
             # bump this up before a real distributor upload.


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        # Linux / GitHub Actions / Kaggle
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
        # Windows
        "C:/Windows/Fonts/impact.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/trebucbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        # macOS
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _add_grain(img: Image.Image, seed: int, intensity: int = 18) -> Image.Image:
    rng = random.Random(seed)
    noise = Image.new("L", img.size)
    pixels = noise.load()
    for y in range(img.size[1]):
        for x in range(0, img.size[0], 2):  # step 2 for speed, upscale-blurred anyway
            v = rng.randint(0, intensity)
            pixels[x, y] = v
    noise = noise.filter(ImageFilter.GaussianBlur(0.5))
    return Image.blend(img.convert("L").convert("RGB"), img, 0.0) if False else img  # no-op guard


def generate_cover(slug: str, subgenre: str, title: str, out_path: str) -> str:
    bg_hex, accent_hex = SUBGENRE_PALETTES.get(subgenre, ("#0a0a0a", "#ffffff"))
    seed = int(hashlib.sha256(slug.encode()).hexdigest(), 16) % (2**32)
    rng = random.Random(seed)

    img = Image.new("RGB", (SIZE, SIZE), bg_hex)
    draw = ImageDraw.Draw(img)

    # Diagonal accent bands, position/width varied per-track via the seed
    # so a batch of 50 covers doesn't look like one template stamped 50 times.
    band_count = rng.randint(3, 6)
    for i in range(band_count):
        x0 = rng.randint(-200, SIZE)
        width = rng.randint(20, 90)
        draw.polygon(
            [(x0, 0), (x0 + width, 0), (x0 + width - 400, SIZE), (x0 - 400, SIZE)],
            fill=accent_hex,
        )

    # Darken band layer so text stays legible on top
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 140))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Grain texture for that lo-fi phonk aesthetic
    grain = Image.effect_noise(img.size, 24).convert("L")
    grain = grain.filter(ImageFilter.GaussianBlur(0.3))
    img = Image.composite(Image.new("RGB", img.size, "black"), img, grain.point(lambda p: 255 - p if p < 30 else 0))

    draw = ImageDraw.Draw(img)
    title_font = _load_font(120)
    sub_font = _load_font(48)

    label = title.upper()
    draw.text((70, SIZE - 260), label, font=title_font, fill="white")
    draw.text((70, SIZE - 130), subgenre.replace("_", " ").upper(), font=sub_font, fill=accent_hex)

    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_file, "PNG")
    return str(out_file)


def main():
    ap = argparse.ArgumentParser(description="Generate procedural phonk cover art (zero-cost, no AI model).")
    ap.add_argument("--prompts", type=str, required=True, help="Path to prompts_batch.json from prompt_generator.py")
    ap.add_argument("--out-dir", type=str, default="output/covers", help="Directory to write .png covers into")
    args = ap.parse_args()

    batch = json.loads(Path(args.prompts).read_text())
    for entry in batch:
        title = entry["slug"].replace("_", " ")
        out_path = Path(args.out_dir) / f"{entry['slug']}.png"
        generate_cover(entry["slug"], entry["subgenre"], title, str(out_path))
        print(f"Cover written: {out_path}")


if __name__ == "__main__":
    main()
