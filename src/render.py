#!/usr/bin/env python3
"""
Assembles spec cards into a finished video.
  python3 src/render.py --format long    -> 1920x1080 long-form
  python3 src/render.py --format short   -> 1080x1920 Shorts (one per product)

Voiceover: drop WAV/MP3 per card into out/<date>/audio/NN.wav and it will be muxed.
On your VM, generate those with edge-tts (see narrate.sh).
"""
import argparse, json, subprocess, shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from cards import card, title_card

ROOT = Path(__file__).resolve().parent.parent


def latest_out():
    ds = sorted((ROOT / "out").glob("*/manifest.json"))
    if not ds:
        sys.exit("Run build.py first.")
    return ds[-1].parent


def dur_of(p: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def clip(png: Path, out: Path, seconds: float, size, audio: Path | None, zoom=True):
    W, H = size
    vf = (f"scale={W*2}:{H*2},zoompan=z='min(zoom+0.0004,1.08)':"
          f"d={int(seconds*30)}:s={W}x{H}:fps=30" if zoom
          else f"scale={W}:{H},fps=30")
    cmd = ["ffmpeg", "-y", "-loop", "1", "-i", str(png)]
    if audio and audio.exists():
        cmd += ["-i", str(audio), "-c:a", "aac", "-b:a", "128k", "-shortest"]
    else:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                "-c:a", "aac", "-shortest"]
    cmd += ["-t", f"{seconds}", "-vf", vf, "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-r", "30", "-preset", "veryfast", str(out)]
    subprocess.run(cmd, check=True, capture_output=True)


def concat(clips, out: Path):
    lst = out.parent / "_concat.txt"
    lst.write_text("\n".join(f"file '{c.resolve()}'" for c in clips))
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c", "copy", str(out)], check=True, capture_output=True)
    lst.unlink()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--format", choices=["long", "short"], default="long")
    ap.add_argument("--seconds", type=float, default=55.0)
    a = ap.parse_args()

    d = latest_out()
    ps = json.loads((d / "manifest.json").read_text())
    aud = d / "audio"
    work = d / f"_work_{a.format}"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    size = (1920, 1080) if a.format == "long" else (1080, 1920)
    top = max(p["discount"] for p in ps)
    head = f"Up to {top}% off" if top >= 40 else "Best value picks"

    if a.format == "long":
        clips = []
        t = title_card(head, f"{len(ps)} picks - links in description", size)
        tp = work / "000.png"; t.save(tp)
        c0 = work / "000.mp4"; clip(tp, c0, 6, size, None, zoom=False); clips.append(c0)

        for i, p in enumerate(ps, 1):
            png = work / f"{i:03d}.png"
            card(p, i, len(ps), size).save(png)
            av = aud / f"{i:02d}.wav"
            secs = dur_of(av) + 1.0 if av.exists() else a.seconds
            mp4 = work / f"{i:03d}.mp4"
            clip(png, mp4, secs, size, av if av.exists() else None)
            clips.append(mp4)

        out = d / "long.mp4"
        concat(clips, out)
        print(f"long-form -> {out}  ({dur_of(out):.0f}s)")
    else:
        for i, p in enumerate(ps, 1):
            png = work / f"s{i:03d}.png"
            card(p, i, len(ps), size).save(png)
            av = aud / f"short_{i:02d}.wav"
            secs = dur_of(av) + 0.8 if av.exists() else 30.0
            out = d / f"short_{i:02d}.mp4"
            clip(png, out, min(secs, 59), size, av if av.exists() else None)
            print(f"short {i} -> {out}  ({secs:.0f}s)")


if __name__ == "__main__":
    main()
