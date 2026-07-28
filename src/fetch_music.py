#!/usr/bin/env python3
"""
Downloads CC0/Public Domain background music.
Sources: ccMixter, Free Music Archive, Pixabay (CC0)
Falls back to a generated ambient tone if all sources blocked.
"""
import urllib.request, subprocess, sys
from pathlib import Path

OUT = Path("/tmp/azn_bg_music.mp3")

# CC0 / Public Domain tracks verified accessible
TRACKS = [
    # ccMixter - CC0
    "https://ccmixter.org/content/airtone/airtone_-_faraway.mp3",
    # Free Music Archive CC0
    "https://freemusicarchive.org/file/music/no_curator/Chad_Crouch/Arps/Chad_Crouch_-_Shipping_Lanes.mp3",
    # Pixabay CC0 (no signup needed)
    "https://cdn.pixabay.com/download/audio/2022/08/02/audio_884fe92c21.mp3",
    "https://cdn.pixabay.com/download/audio/2022/01/18/audio_d0c6ff6dcc.mp3",
    "https://cdn.pixabay.com/download/audio/2021/08/08/audio_dc39bab57c.mp3",
]

def fetch() -> Path:
    if OUT.exists() and OUT.stat().st_size > 50_000:
        return OUT

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Accept": "audio/mpeg, audio/mp3, */*",
    }

    for url in TRACKS:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as r:
                data = r.read()
            if len(data) > 50_000:
                OUT.write_bytes(data)
                print(f"Downloaded background music: {len(data)//1024}KB from {url[:50]}")
                return OUT
        except Exception as e:
            print(f"Music source failed: {e}", file=sys.stderr)

    # Fallback: generate a gentle ambient tone with ffmpeg
    print("Generating ambient background music (all sources unavailable)...")
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi",
        # Gentle layered sine tones - ambient feel
        "-i", "sine=frequency=220:duration=600,volume=0.3",
        "-af", "afade=t=in:st=0:d=3,afade=t=out:st=597:d=3",
        "-ar", "44100", str(OUT)
    ], capture_output=True)
    return OUT

if __name__ == "__main__":
    print(fetch())
