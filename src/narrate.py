#!/usr/bin/env python3
"""
Generates Hindi voiceover per card with edge-tts (free, no API key).
  pip install edge-tts
  python3 src/narrate.py
Writes out/<date>/audio/NN.wav and short_NN.wav

Voice: hi-IN-SwaraNeural  - Female, Hindi, Indian
Speed: +28% faster than default
Language: Hindi narration, English display cards
"""
import asyncio, json, sys, subprocess
from pathlib import Path

VOICE = "hi-IN-SwaraNeural"   # Female Hindi Indian voice
RATE  = "+28%"                 # 20% faster than default (+8%)
ROOT  = Path(__file__).resolve().parent.parent


def line_long_hi(p, i, n):
    """Hindi narration script for long-form card."""
    d = ""
    if p.get("discount"):
        d = f" इसकी कीमत {int(p['mrp'])} से घटकर {int(p['price'])} रुपये हो गई है, यानी {p['discount']} प्रतिशत की छूट।"
    return (
        f"नंबर {i}। {p['brand']} का {p['name']}। "
        f"{p['hook']}। "
        f"{p['feature_1']}। "
        f"{p['feature_2']}। "
        f"{p['feature_3']}। "
        f"कीमत {int(p['price'])} रुपये।{d} "
        f"{p['verdict']}।"
    )


def line_short_hi(p):
    """Hindi narration for Shorts."""
    d = f", {p['discount']} प्रतिशत की छूट" if p.get("discount") else ""
    return (
        f"{p['hook']}। "
        f"{p['brand']} का {p['name']}। "
        f"{p['feature_1']}। "
        f"कीमत सिर्फ {int(p['price'])} रुपये{d}। "
        f"लिंक description में है।"
    )


async def say(text, out: Path):
    import edge_tts
    mp3 = out.with_suffix(".mp3")
    await edge_tts.Communicate(text, VOICE, rate=RATE).save(str(mp3))
    subprocess.run(["ffmpeg", "-y", "-i", str(mp3), "-ar", "44100", str(out)],
                   check=True, capture_output=True)
    mp3.unlink()


async def main():
    ds = sorted((ROOT / "out").glob("*/manifest.json"))
    if not ds:
        sys.exit("Run build.py first.")
    d = ds[-1].parent
    ps = json.loads((d / "manifest.json").read_text())
    (d / "audio").mkdir(exist_ok=True)
    for i, p in enumerate(ps, 1):
        await say(line_long_hi(p, i, len(ps)), d / "audio" / f"{i:02d}.wav")
        await say(line_short_hi(p), d / "audio" / f"short_{i:02d}.wav")
        print(f"narrated {i}/{len(ps)}")


if __name__ == "__main__":
    asyncio.run(main())
