#!/usr/bin/env python3
"""
Pulls the next unpublished batch from your Google Sheet -> data/products.csv
and marks those rows as 'in_progress'.

Sheet tab 'products' columns (row 1 = headers, must match exactly):
  asin | name | brand | mrp | price | category | hook |
  feature_1 | feature_2 | feature_3 | verdict | status

status: blank/'ready' = eligible, 'in_progress' = picked up, 'done' = published

Auth: set GOOGLE_CREDS env var to the JSON of a service account key,
      and share the sheet with that service account's email (Viewer+Editor).
"""
import csv, json, os, sys
from pathlib import Path

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

ROOT = Path(__file__).resolve().parent.parent
SHEET_ID = os.environ.get("GSHEET_ID")
TAB = os.environ.get("GSHEET_TAB", "products")
BATCH = int(os.environ.get("BATCH_SIZE", "8"))
COLS = ["asin", "name", "brand", "mrp", "price", "category", "hook",
        "feature_1", "feature_2", "feature_3", "verdict"]


def svc():
    raw = os.environ.get("GOOGLE_CREDS")
    if not raw:
        sys.exit("GOOGLE_CREDS not set")
    info = json.loads(raw)
    creds = Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return build("sheets", "v4", credentials=creds).spreadsheets()


def main():
    if not SHEET_ID:
        sys.exit("GSHEET_ID not set")
    s = svc()
    vals = s.values().get(spreadsheetId=SHEET_ID, range=f"{TAB}!A1:L1000"
                          ).execute().get("values", [])
    if len(vals) < 2:
        sys.exit("Sheet is empty")

    hdr = [h.strip() for h in vals[0]]
    missing = [c for c in COLS if c not in hdr]
    if missing:
        sys.exit(f"Sheet missing columns: {missing}")
    si = hdr.index("status") if "status" in hdr else None

    picked, rownums = [], []
    for n, row in enumerate(vals[1:], start=2):
        row = row + [""] * (len(hdr) - len(row))
        st = (row[si].strip().lower() if si is not None else "")
        if st in ("", "ready"):
            rec = {c: row[hdr.index(c)].strip() for c in COLS}
            if not rec["asin"] or not rec["price"]:
                continue
            picked.append(rec)
            rownums.append(n)
        if len(picked) >= BATCH:
            break

    if not picked:
        sys.exit("No rows with status ready/blank. Add products to the sheet.")

    out = ROOT / "data" / "products.csv"
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(picked)
    print(f"Pulled {len(picked)} products -> {out}")

    if si is not None:
        col = chr(ord("A") + si)
        s.values().batchUpdate(spreadsheetId=SHEET_ID, body={
            "valueInputOption": "RAW",
            "data": [{"range": f"{TAB}!{col}{r}", "values": [["in_progress"]]}
                     for r in rownums]}).execute()
        print(f"Marked rows {rownums} in_progress")


if __name__ == "__main__":
    main()
