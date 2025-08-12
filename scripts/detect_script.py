#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
Detect primary Unicode script per line and flag romanization.
- Uses 'regex' (\p{Script=...}) when available; otherwise a coarse fallback.
- Expected-script map used to set is_romanized=True when non-Latin langs show Latin.
Reads *.dedup.jsonl (by default), writes <lang>.dedup.tagged.jsonl
Also writes reports/script_summary.csv
"""


import argparse, os, sys, json, glob, csv, unicodedata

try:
    import regex as re  # pip install regex
    HAVE_REGEX = True
except Exception:
    HAVE_REGEX = False

# Expected script per language code (project codes)
EXPECTED = {
    # non-Latin
    "am": "Ethiopic", "ka": "Georgian", "ur": "Arabic", "lo": "Lao",
    "km": "Khmer", "my": "Myanmar", "dz": "Tibetan", "ja": "Japanese",
    # Latin-family (expected Latin)
    "yo": "Latin", "en": "Latin", "pt": "Latin", "es": "Latin", "tr": "Latin",
    "eo": "Latin", "ia": "Latin", "io": "Latin", "ie": "Latin", "lfn": "Latin",
    "vo": "Latin", "avk": "Latin", "jbo": "Latin", "tok": "Latin",
    "kek": "Latin", "fuf": "Latin",
}

# For Japanese, treat Han/Hiragana/Katakana as expected
JP_SCRIPTS = {"Han","Hiragana","Katakana"}

def script_counts_regex(text: str):
    counts = {}
    # Common scripts we care about; add more if needed
    scripts = ["Latin","Cyrillic","Greek","Arabic","Hebrew","Devanagari","Ethiopic",
               "Georgian","Lao","Khmer","Myanmar","Thai","Han","Hiragana","Katakana",
               "Hangul","Tibetan"]
    for s in scripts:
        m = re.findall(rf"\p{{Script={s}}}+", text)
        if m:
            counts[s] = sum(len(x) for x in m)
    return counts

def script_counts_fallback(text: str):
    # Extremely coarse: bucket by Unicode block name fragments
    buckets = {
        "Latin": ("LATIN",),
        "Cyrillic": ("CYRILLIC",),
        "Greek": ("GREEK",),
        "Arabic": ("ARABIC",),
        "Hebrew": ("HEBREW",),
        "Devanagari": ("DEVANAGARI",),
        "Ethiopic": ("ETHIOPIC",),
        "Georgian": ("GEORGIAN",),
        "Lao": ("LAO",),
        "Khmer": ("KHMER",),
        "Myanmar": ("MYANMAR",),
        "Thai": ("THAI",),
        "Tibetan": ("TIBETAN",),
        "Han": ("CJK UNIFIED IDEOGRAPHS","CJK COMPATIBILITY IDEOGRAPHS","IDEOGRAPHIC"),
        "Hiragana": ("HIRAGANA",),
        "Katakana": ("KATAKANA",),
        "Hangul": ("HANGUL",),
    }
    counts = {k:0 for k in buckets}
    for ch in text:
        if ch.isspace():
            continue
        try:
            name = unicodedata.name(ch)
        except Exception:
            continue
        for k, keys in buckets.items():
            if any(part in name for part in keys):
                counts[k] += 1
                break
    return {k:v for k,v in counts.items() if v>0}

def primary_script(counts: dict):
    if not counts:
        return "Unknown", 0, 0
    s, n = max(counts.items(), key=lambda kv: kv[1])
    total = sum(counts.values())
    pct = (n / total) if total else 0.0
    return s, n, pct

def is_romanized(lang: str, prim: str, pct: float):
    exp = EXPECTED.get(lang, "Latin")
    if lang == "ja":
        # If Japanese and primary is among JP scripts, it's not romanized
        if prim in JP_SCRIPTS:
            return False
        # Latin majority suggests romaji
        return prim == "Latin" and pct >= 0.6
    if exp != "Latin" and prim == "Latin" and pct >= 0.6:
        return True
    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", nargs="*", help="if omitted, infer from input files")
    ap.add_argument("--in-prefix", default="dataset/processed")
    ap.add_argument("--in-pattern", default="*.dedup.jsonl", help="e.g. *.wikipedia.jsonl")
    ap.add_argument("--out-suffix", default=".dedup.tagged.jsonl")
    ap.add_argument("--report", default="reports/script_summary.csv")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.report), exist_ok=True)

    files = glob.glob(os.path.join(args.in_prefix, args.in_pattern))
    if not files:
        print("[script] No input files matched pattern.", file=sys.stderr)
        return 0

    langs = args.langs or sorted({os.path.basename(p).split(".")[0] for p in files})

    init_report = not os.path.exists(args.report)
    if init_report:
        with open(args.report, "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerow(["lang","lines","primary_count","latin_majority","romanized_est"])

    for lang in langs:
        inp = os.path.join(args.in_prefix, f"{lang}.dedup.jsonl")
        if not os.path.exists(inp):
            print(f"[script] {lang}: missing {inp}, skipping.")
            continue

        outp = os.path.join(args.in_prefix, f"{lang}{args.out_suffix}")
        total = 0
        latin_majority = 0
        rom_est = 0

        with open(outp, "w", encoding="utf-8") as fo:
            for rec in iter_jsonl(inp):
                total += 1
                text = rec.get("text","")
                counts = script_counts_regex(text) if HAVE_REGEX else script_counts_fallback(text)
                prim, n, pct = primary_script(counts)
                romanized = is_romanized(lang, prim, pct)
                if prim == "Latin" and pct >= 0.6:
                    latin_majority += 1
                if romanized:
                    rom_est += 1
                rec["script"] = {
                    "primary": prim,
                    "primary_ratio": round(pct, 4),
                    "counts": counts
                }
                rec["is_romanized"] = bool(romanized)
                fo.write(json.dumps(rec, ensure_ascii=False) + "\n")

        with open(args.report, "a", encoding="utf-8", newline="") as f:
            csv.writer(f).writerow([lang, total, latin_majority, latin_majority, rom_est])

        print(f"[script] {lang}: lines={total} primary_tagged={latin_majority} romanized_est={rom_est} -> {outp}")

    return 0

def iter_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: 
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue

if __name__ == "__main__":
    raise SystemExit(main())
