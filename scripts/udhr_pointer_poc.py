#!/usr/bin/env python3
"""
UDHR (OHCHR) pointer-only pack + local fetcher.

build: read dataset/sources/sources.csv and write pointer manifest(s) for given codes.
fetch: read pointers and materialize paragraphs locally (keep out of git).

Examples:
  # Build pointers for Dzongkha
  python scripts/udhr_pointer_poc.py build --codes dz --sources dataset/sources/sources.csv --out-dir dataset/udhr/pointers

  # Fetch to JSONL (local use only)
  python scripts/udhr_pointer_poc.py fetch --manifest dataset/udhr/pointers/dz.jsonl \
      --out dataset/processed/dz.udhr.jsonl --min-chars 60 --max-samples 150
"""
import argparse, csv, json, os, re, sys, unicodedata
from typing import List, Dict

def normalize_text(s: str) -> str:
    s = unicodedata.normalize("NFC", s or "")
    s = s.replace("\r\n","\n").replace("\r","\n")
    s = re.sub(r"[ \t]{2,}", " ", s)
    s = "\n".join(line.strip() for line in s.split("\n"))
    if s and s[0] == "\ufeff":
        s = s[1:]
    return s

def build_pointers(codes: List[str], sources_csv: str, out_dir: str):
    rows = []
    with open(sources_csv, "r", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        for r in rd:
            if r["code"] in codes and r["source_name"].lower().startswith("ohchr"):
                rows.append(r)
    os.makedirs(out_dir, exist_ok=True)
    for code in codes:
        items = [r for r in rows if r["code"] == code]
        outp = os.path.join(out_dir, f"{code}.jsonl")
        n = 0
        with open(outp, "w", encoding="utf-8") as w:
            for r in items:
                w.write(json.dumps({
                    "code": code,
                    "lang": code,
                    "source": "udhr",
                    "domain": "legal",
                    "url": r["url"],
                    "selector": "p",   # hint for fetcher
                    "license": "OHCHR terms"
                }, ensure_ascii=False) + "\n")
                n += 1
        print(f"[build] {code}: wrote {n} pointer(s) -> {outp}")

def fetch_from_pointers(manifest: str, out_jsonl: str, min_chars: int, max_samples: int):
    try:
        import requests
        from bs4 import BeautifulSoup  # pip install beautifulsoup4 lxml
    except Exception as e:
        raise RuntimeError("Missing deps: pip install requests beautifulsoup4 lxml") from e

    ptrs = []
    with open(manifest, "r", encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if line:
                ptrs.append(json.loads(line))

    kept = 0
    with open(out_jsonl, "w", encoding="utf-8") as w:
        for p in ptrs:
            url = p["url"]
            print(f"[fetch] GET {url}")
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            # naive: all <p> text on page
            texts = [normalize_text(x.get_text(" ", strip=True)) for x in soup.find_all("p")]
            for t in texts:
                if len(t) >= min_chars:
                    obj = {
                        "text": t,
                        "title": soup.title.get_text(strip=True) if soup.title else None,
                        "url": url,
                        "license": "OHCHR terms",
                        "source": "udhr",
                        "domain": "legal",
                        "lang": p.get("lang") or p.get("code"),
                        "code": p.get("code")
                    }
                    w.write(json.dumps(obj, ensure_ascii=False) + "\n")
                    kept += 1
                    if kept >= max_samples:
                        break
            if kept >= max_samples:
                break
    print(f"[fetch] Wrote {kept} rows -> {out_jsonl}  (keep these out of git)")
    return kept

def main():
    ap = argparse.ArgumentParser(description="UDHR (OHCHR) pointer pack + fetch")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("build")
    p1.add_argument("--codes", nargs="+", required=True)
    p1.add_argument("--sources", default="dataset/sources/sources.csv")
    p1.add_argument("--out-dir", default="dataset/udhr/pointers")
    p2 = sub.add_parser("fetch")
    p2.add_argument("--manifest", required=True)
    p2.add_argument("--out", required=True)
    p2.add_argument("--min-chars", type=int, default=60)
    p2.add_argument("--max-samples", type=int, default=150)
    args = ap.parse_args()
    if args.cmd == "build":
        build_pointers(args.codes, args.sources, args.out_dir)
    else:
        fetch_from_pointers(args.manifest, args.out, args.min_chars, args.max_samples)

if __name__ == "__main__":
    sys.exit(main())
