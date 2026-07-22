"""
LLM + RAG Prompt Generator for Phonk Pipeline.

Specialized exclusively in Aura, Dark Gym, Heavy Bass, and Aggressive Drift Phonk.
Maintains a local memory ledger (prompts_history.json) to prevent repetition
and ensure continuous evolution of tracks.

Integrates with Gemini API / Groq API (built-in urllib fallback).
"""

import argparse
import json
import os
import random
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
HISTORY_FILE = ROOT_DIR / "output" / "prompts_history.json"

AURA_SUBGENRES = {
    "aura_gym_phonk": {
        "bpm_range": (155, 170),
        "keys": ["C minor", "D minor", "F minor", "G minor", "F# minor"],
        "themes": ["heavy pr 808 drop", "aggressive Memphis vocal chop", "raw power gym motivation"],
    },
    "heavy_bass_phonk": {
        "bpm_range": (145, 160),
        "keys": ["A minor", "E minor", "C# minor", "B minor"],
        "themes": ["sub-bass distorted glides", "screeching tape synth", "relentless basslines"],
    },
    "dark_aura_drift": {
        "bpm_range": (150, 165),
        "keys": ["D minor", "G minor", "F minor"],
        "themes": ["night drive aura", "cold menacing atmosphere", "heavy cowbell drops"],
    },
    "sigma_rage_phonk": {
        "bpm_range": (160, 175),
        "keys": ["C# minor", "F# minor", "E minor"],
        "themes": ["explosive rage lead", "unhinged 808 distortion", "high-energy workout peak"],
    },
}

DEFAULT_DURATION = 120  # 2 minutes per track


def load_history() -> list:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_history(history: list):
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")


def call_gemini_api(system_prompt: str, user_prompt: str, api_key: str) -> str | None:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"{system_prompt}\n\n{user_prompt}"}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.8,
            "responseMimeType": "application/json"
        }
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            text = res_json["candidates"][0]["content"]["parts"][0]["text"]
            return text
    except Exception as e:
        print(f"[LLM] Gemini API call failed ({e}), trying fallback...", file=sys.stderr)
        return None


def call_groq_api(system_prompt: str, user_prompt: str, api_key: str) -> str | None:
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.8,
        "response_format": {"type": "json_object"}
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            return res_json["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[LLM] Groq API call failed ({e}), trying fallback...", file=sys.stderr)
        return None


def get_serialized_title(subgenre: str, index: int, history: list) -> str:
    """Generates structured serialized track titles like LVBEL C1, AURA C2, SHADOW V3."""
    prefixes = {
        "aura_gym_phonk": "AURA C",
        "heavy_bass_phonk": "BASS V",
        "dark_aura_drift": "DRIFT X",
        "sigma_rage_phonk": "SIGMA C"
    }
    prefix = prefixes.get(subgenre, "AURA C")
    
    # Calculate next sequence number from history
    existing_nums = [
        int(item["title"].split()[-1]) for item in history 
        if item.get("title", "").startswith(prefix) and item.get("title", "").split()[-1].isdigit()
    ]
    next_num = (max(existing_nums) + 1) if existing_nums else (index + 1)
    return f"{prefix}{next_num}"


def fallback_prompt_generator(subgenre: str, index: int, history_slugs: set, history: list, rng: random.Random) -> dict:
    cfg = AURA_SUBGENRES[subgenre]
    bpm = rng.randint(*cfg["bpm_range"])
    key = rng.choice(cfg["keys"])
    theme = rng.choice(cfg["themes"])
    title = get_serialized_title(subgenre, index, history)
    
    slug_base = f"{title.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}"
    slug = slug_base
    counter = 1
    while slug in history_slugs:
        slug = f"{slug_base}_{counter}"
        counter += 1

    caption = (
        f"A heavy dark {subgenre.replace('_', ' ')} track titled '{title}' at {bpm} BPM in {key}. "
        f"Featuring {theme}, distorted 808 sub-bass glides, sharp cowbell riffs, and tape-saturated Memphis vocal chops. "
        f"Structure: 0-30s dark atmospheric build, 30-60s explosive 808 drop, 60-90s pitch-down breakdown, "
        f"90-120s ultimate high-aura climax drop. Instrumental, high-energy gym motivation."
    )

    return {
        "subgenre": subgenre,
        "slug": slug,
        "title": title,
        "caption": caption,
        "lyrics": "",
        "bpm": bpm,
        "keyscale": key,
        "timesignature": "4",
        "duration": DEFAULT_DURATION,
        "language": "en",
        "mood": "aura_dark_gym",
        "theme": theme,
        "cover_prompt": "Artistic Phonk album cover, dark glowing anime warrior with intense crimson energy aura, high contrast 8k digital illustration",
        "motivational_prompt": "Dark intense gym motivation wallpaper, shadow athlete silhouette with glowing red energy aura, heavy iron weights, 8k cinematic digital art"
    }


def generate_batch(count: int = 4, seed: int | None = None) -> list[dict]:
    rng = random.Random(seed)
    history = load_history()
    history_slugs = {item.get("slug") for item in history if "slug" in item}
    recent_captions = [item.get("caption", "") for item in history[-10:]]

    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")

    system_prompt = (
        "You are an expert Phonk music producer and visual art director specialized in Dark Gym Phonk, Heavy Bass Phonk, and Aura Phonk. "
        "Your goal is to generate dynamic, detailed, 2-minute track concepts and their accompanying aesthetic visual prompts. "
        "Every track must have a time-structured arrangement (0-30s intro/build, 30-60s 808 drop, 60-90s breakdown, 90-120s climax). "
        "You MUST return a JSON object with a key 'prompts' containing an array of track objects. "
        "Each track object must have fields: 'subgenre', 'title', 'caption', 'bpm', 'keyscale', 'cover_prompt', and 'motivational_prompt'. "
        "For 'cover_prompt', write a highly detailed Midjourney-style image prompt for the 1:1 album cover based on the track's theme. "
        "For 'motivational_prompt', write a highly detailed 9:16 vertical image prompt for a dark aesthetic gym/sigma reel background."
    )

    user_prompt = (
        f"Generate {count} unique Phonk track concepts. "
        f"Subgenres to select from: {list(AURA_SUBGENRES.keys())}. "
        f"Recent track captions to AVOID repeating: {json.dumps(recent_captions[-4:])}. "
        f"Ensure visually striking and unique cover and motivational prompts for each."
    )

    llm_response = None
    if gemini_key:
        llm_response = call_gemini_api(system_prompt, user_prompt, gemini_key)
    if not llm_response and groq_key:
        llm_response = call_groq_api(system_prompt, user_prompt, groq_key)

    prompts = []
    if llm_response:
        try:
            parsed = json.loads(llm_response)
            items = parsed.get("prompts", [])
            for i, item in enumerate(items[:count]):
                subgenre = item.get("subgenre", "aura_gym_phonk")
                if subgenre not in AURA_SUBGENRES:
                    subgenre = "aura_gym_phonk"
                slug_base = f"{subgenre}_{datetime.now().strftime('%Y%m%d')}_{i+1:02d}"
                slug = slug_base
                c = 1
                while slug in history_slugs:
                    slug = f"{slug_base}_{c}"
                    c += 1

                prompts.append({
                    "subgenre": subgenre,
                    "slug": slug,
                    "title": item.get("title", f"AURA PHONK {i+1}"),
                    "caption": item.get("caption"),
                    "lyrics": "",
                    "bpm": item.get("bpm", 160),
                    "keyscale": item.get("keyscale", "D minor"),
                    "timesignature": "4",
                    "duration": DEFAULT_DURATION,
                    "language": "en",
                    "mood": "aura_dark_gym",
                    "cover_prompt": item.get("cover_prompt", "Artistic Phonk album cover, dark aesthetic, 8k trending on ArtStation"),
                    "motivational_prompt": item.get("motivational_prompt", "Dark intense gym motivation wallpaper, glowing aura, 8k cinematic")
                })
                history_slugs.add(slug)
        except Exception as e:
            print(f"[LLM] Error parsing LLM response ({e}), falling back to internal generator...", file=sys.stderr)

    # Fill remaining using robust fallback
    subgenre_list = list(AURA_SUBGENRES.keys())
    while len(prompts) < count:
        idx = len(prompts)
        sg = subgenre_list[idx % len(subgenre_list)]
        track = fallback_prompt_generator(sg, idx, history_slugs, history, rng)
        prompts.append(track)
        history_slugs.add(track["slug"])

    # Update history ledger (keep last 200 entries)
    updated_history = history + prompts
    save_history(updated_history[-200:])

    return prompts


def main():
    ap = argparse.ArgumentParser(description="LLM+RAG Prompt Generator for Aura Dark Gym Phonk.")
    ap.add_argument("--count", type=int, default=4, help="How many prompts to generate (default 4).")
    ap.add_argument("--seed", type=int, default=None, help="Random seed.")
    ap.add_argument("--out", type=str, default="output/prompts_batch.json", help="Output file path.")
    args = ap.parse_args()

    batch = generate_batch(args.count, args.seed)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(batch, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(batch)} Aura Phonk prompts to {out_path} (Duration: {DEFAULT_DURATION}s each)")


if __name__ == "__main__":
    main()
