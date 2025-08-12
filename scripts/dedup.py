#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deduplicate per language across sources (wikipedia/tatoeba/udhr).
- Exact dup: MD5 of normalized text.
- Optional near-dup: character n-gram Jaccard (default off).
Writes:
  dataset/processed/<lang>.dedup.jsonl
Appends a row to reports/dedup_summary.csv
"""
import argparse, os, sys, json, hashlib, unicodedata, glob, csv
from collections import defaultdict

def norm_text(t: str) -> str:
    # keep it light: NFC + collapse whitespace
    t = unicodedata.normalize("NFC", t)
    return " ".join(t.split())

def char_ngrams(t: str, n: int = 5):
    t = unicodedata.normalize("NFKC", t).lower()
    # keep newlines/spaces—they carry weak structure
    if len(t) < n: 
        return {t} if t else set()
    return {t[i:i+n] for i in range(0, len(t) - n + 1)}

def jaccard(a, b):
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if inter == 0:
        return 0.0
    return inter / float(len(a | b))

def iter_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): 
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue

def discover_langs(in_prefix, sources):
    langs = set()
    for src in sources:
        for p in glob.glob(os.path.join(in_prefix, f"*.{src}.jsonl")):
            code = os.path.basename(p).split(".")[0]
            langs.add(code)
    return sorted(langs)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", nargs="*", help="e.g. am ka ur ... (default: auto from files)")
    ap.add_argument("--sources", nargs="+", default=["wikipedia","tatoeba","udhr"])
    ap.add_argument("--in-prefix", default="dataset/processed")
    ap.add_argument("--out-prefix", default="dataset/processed")
    ap.add_argument("--near-dup", action="store_true", help="Enable near-duplicate removal")
    ap.add_argument("--jaccard-thresh", type=float, default=0.85, help="Char ngram Jaccard threshold")
    ap.add_argument("--ngram", type=int, default=5, help="Character n for n-grams")
    ap.add_argument("--report", default="reports/dedup_summary.csv")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.report), exist_ok=True)

    langs = args.langs or discover_langs(args.in_prefix, args.sources)
    if not langs:
        print("[dedup] No languages discovered. Nothing to do.", file=sys.stderr)
        return 0

    # init CSV report if missing
    init_report = not os.path.exists(args.report)
    if init_report:
        with open(args.report, "w", encoding="utf-8", newline="") as f:
            cw = csv.writer(f)
            cw.writerow(["lang","input_total","kept","exact_dups","near_dups","sources"])

    for lang in langs:
        files = [os.path.join(args.in_prefix, f"{lang}.{src}.jsonl") for src in args.sources]
        files = [p for p in files if os.path.exists(p)]
        if not files:
            print(f"[dedup] {lang}: no input files, skipping.")
            continue

        seen_hash = set()
        kept = []
        near_dups = 0
        exact_dups = 0
        # For near-dup, store n-gram sets of already kept texts
        kept_ngrams = []

        input_total = 0
        for p in files:
            for rec in iter_jsonl(p):
                input_total += 1
                text = norm_text(rec.get("text",""))
                if not text:
                    continue
                h = hashlib.md5(text.encode("utf-8")).hexdigest()
                if h in seen_hash:
                    exact_dups += 1
                    continue

                is_near = False
                if args.near_dup and kept:
                    ng = char_ngrams(text, args.ngram)
                    # quick check vs a bounded window to avoid O(n^2) blowup (small corpora anyway)
                    for prev_ng in kept_ngrams:
                        if jaccard(ng, prev_ng) >= args.jaccard_thresh:
                            is_near = True
                            break
                    if not is_near:
                        kept_ngrams.append(ng)

                if is_near:
                    near_dups += 1
                    continue

                seen_hash.add(h)
                kept.append({
                    **rec,
                    "text": text,
                    "trace": {**rec.get("trace", {}), "dedup": "kept"},
                })

        out_path = os.path.join(args.out_prefix, f"{lang}.dedup.jsonl")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            for rec in kept:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        with open(args.report, "a", encoding="utf-8", newline="") as f:
            cw = csv.writer(f)
            cw.writerow([lang, input_total, len(kept), exact_dups, near_dups, ",".join(args.sources)])

        print(f"[dedup] {lang}: input={input_total} kept={len(kept)} exact_dups={exact_dups} near_dups={near_dups} -> {out_path}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
