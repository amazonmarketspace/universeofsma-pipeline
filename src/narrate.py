#!/usr/bin/env python3
"""
Generates voiceover per card with edge-tts (free, no API key).
  pip install edge-tts
  python3 src/narrate.py
Writes out/<date>/audio/NN.wav and short_NN.wav
"""
import asyncio, json, sys, subprocess
from pathlib import Path

VOICE = "en-IN-PrabhatNeural"      # or en-IN-NeerjaNeural / hi-IN-MadhurNeural
ROOT = Path(__file__).resolve().parent.parent


def line_long(p, i, n):
    d = f" down from {int(p['mrp'])}, that's {p['discount']} percent off" if p["discount"] else ""
    return (f"Number {i}. {p['brand']} {p['name']}. {p['hook']}. "
            f"{p['feature_1']}. {p['feature_2']}. {p['feature_3']}. "
            f"It's {int(p['price'])} rupees{d}. {p['verdict']}.")


def line_short(p):
    d = f", {p['discount']} percent off" if p["discount"] else ""
    return (f"{p['hook']}. The {p['brand']} {p['name']}. {p['feature_1']}. "
            f"{int(p['price'])} rupees{d}. Link in the description.")


async def say(text, out: Path):
    import edge_tts
    mp3 = out.with_suffix(".mp3")
    await edge_tts.Communicate(text, VOICE, rate="+8%").save(str(mp3))
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
        await say(line_long(p, i, len(ps)), d / "audio" / f"{i:02d}.wav")
        await say(line_short(p), d / "audio" / f"short_{i:02d}.wav")
        print(f"narrated {i}/{len(ps)}")


if __name__ == "__main__":
    asyncio.run(main())
