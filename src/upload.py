#!/usr/bin/env python3
"""
Uploads the rendered long-form video and Shorts to YouTube.

  python3 src/upload.py --privacy private     # test first
  python3 src/upload.py --privacy public

Env (GitHub secrets):
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
Get the refresh token once by running src/yt_auth.py locally.
"""
import argparse, json, os, sys
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

ROOT = Path(__file__).resolve().parent.parent
TOKEN_URI = "https://oauth2.googleapis.com/token"


def yt():
    for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"):
        if not os.environ.get(k):
            sys.exit(f"{k} not set")
    creds = Credentials(
        None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        token_uri=TOKEN_URI,
        scopes=["https://www.googleapis.com/auth/youtube.upload"])
    return build("youtube", "v3", credentials=creds)


def latest():
    ds = sorted((ROOT / "out").glob("*/manifest.json"))
    if not ds:
        sys.exit("Nothing rendered.")
    return ds[-1].parent


def push(svc, path: Path, title: str, desc: str, tags: list, privacy: str):
    body = {"snippet": {"title": title[:100], "description": desc[:4900],
                        "tags": tags[:15], "categoryId": "28"},
            "status": {"privacyStatus": privacy,
                       "selfDeclaredMadeForKids": False}}
    media = MediaFileUpload(str(path), chunksize=-1, resumable=True,
                            mimetype="video/mp4")
    req = svc.videos().insert(part="snippet,status", body=body, media_body=media)
    res = None
    while res is None:
        _, res = req.next_chunk()
    vid = res["id"]
    print(f"  https://youtu.be/{vid}  [{privacy}]")
    return vid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--privacy", default="private",
                    choices=["private", "unlisted", "public"])
    ap.add_argument("--shorts-only", action="store_true")
    a = ap.parse_args()

    d = latest()
    ps = json.loads((d / "manifest.json").read_text())
    desc = (d / "description.txt").read_text()
    svc = yt()
    top = max(p["discount"] for p in ps)
    tags = ["amazon finds", "smartphone accessories", "tech deals india",
            "budget gadgets", "amazon india"]

    if not a.shorts_only and (d / "long.mp4").exists():
        title = (f"Top {len(ps)} Smartphone Accessories on Amazon India "
                 f"| Up to {top}% Off")
        print("long-form:")
        push(svc, d / "long.mp4", title, desc, tags, a.privacy)

    for i, p in enumerate(ps, 1):
        f = d / f"short_{i:02d}.mp4"
        if not f.exists():
            continue
        st = f"{p['name']} - Rs{int(p['price'])} #shorts"
        sd = (f"{p['hook']}\n\n{p['name']} - {p['url']}\n\n"
              "As an Amazon Associate I earn from qualifying purchases.\n"
              "Prices correct at time of recording.\n\n#shorts #amazonfinds")
        print(f"short {i}:")
        push(svc, f, st, sd, tags, a.privacy)


if __name__ == "__main__":
    main()
