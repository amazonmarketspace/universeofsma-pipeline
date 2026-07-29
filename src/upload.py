#!/usr/bin/env python3
"""
Uploads rendered videos to YouTube.
  python3 src/upload.py --privacy public

Env (GitHub secrets):
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
"""
import argparse, json, os, sys
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

ROOT = Path(__file__).resolve().parent.parent
TOKEN_URI = "https://oauth2.googleapis.com/token"

# Smartphone & accessories focused tags — boosts YouTube search ranking
BASE_TAGS = [
    # Category
    "smartphone accessories", "mobile accessories india", "best smartphone accessories",
    "amazon india deals", "amazon finds india", "tech deals india",
    # Purchase intent
    "buy online india", "best price india", "amazon sale",
    # Product types
    "power bank", "fast charger", "gan charger", "wireless charger",
    "car charger", "usb c charger", "mobile charger india",
    # Discount / deal
    "amazon discount", "best deals amazon", "budget tech india",
    # Hindi search terms
    "सस्ता मोबाइल एक्सेसरी", "अमेज़न ऑफर",
]


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


def product_tags(p: dict) -> list:
    """Generate product-specific tags from product data."""
    tags = []
    # Brand tag
    tags.append(p.get("brand", "").lower())
    # Product name words
    name_words = p.get("name", "").lower().replace("-", " ").split()
    tags.extend([w for w in name_words if len(w) > 3][:4])
    # Category
    tags.append(p.get("category", ""))
    # Discount tag
    if p.get("discount", 0) >= 50:
        tags.append(f"{p['discount']}% off amazon")
    tags.append(f"rs {int(p.get('price', 0))} india")
    return [t for t in tags if t]


def push(svc, path: Path, title: str, desc: str, tags: list, privacy: str):
    body = {
        "snippet": {
            "title": title[:100],
            "description": desc[:4900],
            "tags": tags[:30],          # YouTube allows up to 500 chars total
            "categoryId": "28",         # Science & Technology
            "defaultLanguage": "hi",    # Hindi narration
            "defaultAudioLanguage": "hi",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
            "madeForKids": False,
        }
    }
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
    ap.add_argument("--privacy", default="public",
                    choices=["private", "unlisted", "public"])
    ap.add_argument("--shorts-only", action="store_true")
    ap.add_argument("--max-long", type=int, default=5,
                    help="Max long-form videos to upload per run")
    ap.add_argument("--max-short", type=int, default=5,
                    help="Max Shorts to upload per run")
    a = ap.parse_args()

    d = latest()
    ps = json.loads((d / "manifest.json").read_text())
    desc = (d / "description.txt").read_text()
    svc = yt()

    top = max(p["discount"] for p in ps)

    # Upload long-form (up to --max-long, default 5)
    if not a.shorts_only and (d / "long.mp4").exists():
        title = (
            f"Top {len(ps)} Smartphone Accessories on Amazon India "
            f"| Up to {top}% Off | Best Deals {{}}"
        ).format("2026")[:100]

        # Combine base tags + product-specific tags
        all_tags = BASE_TAGS.copy()
        for p in ps:
            all_tags.extend(product_tags(p))
        # Deduplicate, keep order
        seen = set()
        unique_tags = []
        for t in all_tags:
            t = t.strip()
            if t and t.lower() not in seen:
                seen.add(t.lower())
                unique_tags.append(t)

        print("Uploading long-form video...")
        push(svc, d / "long.mp4", title, desc, unique_tags[:30], a.privacy)

    # Upload Shorts (up to --max-short, default 5)
    count = 0
    for i, p in enumerate(ps, 1):
        if count >= a.max_short:
            break
        f = d / f"short_{i:02d}.mp4"
        if not f.exists():
            continue

        st = f"{p['brand']} {p['name']} - ₹{int(p['price'])} | {p['discount']}% Off Amazon #shorts"[:100]
        sd = (
            f"{p['hook']}\n\n"
            f"✅ {p['name']}\n"
            f"💰 Price: ₹{int(p['price'])} (was ₹{int(p['mrp'])}, {p['discount']}% off)\n"
            f"🔗 {p['url']}\n\n"
            f"As an Amazon Associate I earn from qualifying purchases.\n"
            f"Prices correct at time of recording.\n\n"
            f"#shorts #amazonfinds #smartphoneaccessories #techdeals #india "
            f"#{p['brand'].lower().replace(' ','')} #mobilegadgets #amazonsale"
        )

        short_tags = BASE_TAGS[:10] + product_tags(p) + [
            "shorts", "youtube shorts", "tech shorts india",
            "amazon shorts", "mobile accessories shorts"
        ]
        seen2 = set()
        unique_short_tags = []
        for t in short_tags:
            t = t.strip()
            if t and t.lower() not in seen2:
                seen2.add(t.lower())
                unique_short_tags.append(t)

        print(f"Uploading Short {i}: {p['name'][:40]}...")
        push(svc, f, st, sd, unique_short_tags[:30], a.privacy)
        count += 1


if __name__ == "__main__":
    main()
