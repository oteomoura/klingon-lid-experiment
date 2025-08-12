# init_other_sources.sh — Tatoeba + UDHR ingesters + Makefile targets
set -euo pipefail
mkdir -p scripts dataset/processed dataset/udhr/pointers dataset/tatoeba data/tatoeba

# --- scripts/tatoeba_to_jsonl.py ---
cat > scripts/tatoeba_to_jsonl.py <<'PY'
#!/usr/bin/env python3
"""
Tatoeba -> JSONL converter for LID (monolingual).
Input: Tatoeba sentences file (CSV/TSV, can be .bz2). Expected columns: id, lang, text.
Output: dataset/processed/{code}.tatoeba.jsonl

Examples:
  python scripts/tatoeba_to_jsonl.py \
    --input data/tatoeba/sentences.csv.bz2 --langs eo ia jbo tok \
    --samples 120 --out-prefix dataset

Notes:
- License: CC-BY 2.0 FR (add attribution in your paper/ATTRIBUTIONS).
- We keep short normalization (NFC + whitespace cleanup) and minimal length filtering.
"""
import argparse, csv, os, bz2, gzip, io, json, re, unicodedata, sys
from typing import Iterable, Dict, List, TextIO

def open_maybe_compressed(path: str) -> TextIO:
    if path.endswith(".bz2"):
        return io.TextIOWrapper(bz2.BZ2File(path, "rb"), encoding="utf-8", newline="")
    if path.endswith(".gz"):
        return io.TextIOWrapper(gzip.GzipFile(path, "rb"), encoding="utf-8", newline="")
    return open(path, "r", encoding="utf-8", newline="")

def normalize_text(s: str) -> str:
    if not isinstance(s, str):
        s = str(s)
    s = unicodedata.normalize("NFC", s)
    s = s.replace("\r\n","\n").replace("\r","\n")
    s = re.sub(r"[ \t]{2,}", " ", s)
    s = "\n".join(line.strip() for line in s.split("\n"))
    if s and s[0] == "\ufeff":
        s = s[1:]
    return s

def read_rows(path: str):
    with open_maybe_compressed(path) as f:
        # Try TSV then CSV
        sample = f.read(4096)
        f.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters="\t,;")
        rd = csv.reader(f, dialect)
        for row in rd:
            if len(row) < 3:
                continue
            # Tatoeba exports: id, lang, text
            yield row[0], row[1], row[2]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Path to Tatoeba sentences file (.csv/.tsv/.bz2/.gz)")
    ap.add_argument("--langs", nargs="+", required=True, help="Language codes to extract (e.g., eo ia jbo tok)")
    ap.add_argument("--samples", type=int, default=120, help="Max samples per language")
    ap.add_argument("--min-chars", type=int, default=10)
    ap.add_argument("--max-chars", type=int, default=400)
    ap.add_argument("--out-prefix", default="dataset")
    args = ap.parse_args()

    per_lang = {c: 0 for c in args.langs}
    out_files = {c: open(os.path.join(args.out_prefix, "processed", f"{c}.tatoeba.jsonl"), "w", encoding="utf-8") for c in args.langs}
    kept = 0
    for sid, lang, text in read_rows(args.input):
        if lang not in per_lang:
            continue
        if per_lang[lang] >= args.samples:
            continue
        t = normalize_text(text)
        L = len(t)
        if L < args.min_chars or L > args.max_chars:
            continue
        obj = {
            "text": t,
            "license": "CC-BY-2.0-FR",
            "source": "tatoeba",
            "domain": "sentences",
            "lang": lang,
            "code": lang,
            "url": f"https://tatoeba.org/sentences/show/{sid}"
        }
        out_files[lang].write(json.dumps(obj, ensure_ascii=False) + "\n")
        per_lang[lang] += 1
        kept += 1
        # early exit if all caps reached
        if all(per_lang[c] >= args.samples for c in per_lang):
            break
    for f in out_files.values():
        f.close()
    print(f"Kept {kept} sentences across {len(args.langs)} languages -> {args.out_prefix}/processed/*.tatoeba.jsonl")
if __name__ == "__main__":
    sys.exit(main())
PY
chmod +x scripts/tatoeba_to_jsonl.py

# --- scripts/udhr_pointer_poc.py ---
cat > scripts/udhr_pointer_poc.py <<'PY'
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
PY
chmod +x scripts/udhr_pointer_poc.py

# --- Makefile additions (append if you already have one) ---
cat > Makefile.other_sources.append <<'MK'
# ---- Tatoeba + UDHR ingestion (P1-03) ----
PY ?= python

# Tatoeba
TATOEBA_INPUT ?= data/tatoeba/sentences.csv.bz2
TATOEBA_LANGS ?= en pt es tr ja eo ia jbo tok yo lfn io ie vo avk
TATOEBA_SAMPLES ?= 120

.PHONY: tatoeba-all tatoeba-one
tatoeba-all: ## Convert Tatoeba sentences to JSONL for TATOEBA_LANGS
	@for L in $(TATOEBA_LANGS); do \
		echo "==> $$L (tatoeba)"; \
		$(PY) scripts/tatoeba_to_jsonl.py --input $(TATOEBA_INPUT) --langs $$L --samples $(TATOEBA_SAMPLES) --out-prefix dataset || exit $$?; \
	done

tatoeba-one: ## One language: make tatoeba-one L=eo INPUT=path/to/sentences.csv.bz2
	@test -n "$(L)" || (echo "Usage: make tatoeba-one L=<code>"; exit 2)
	@$(PY) scripts/tatoeba_to_jsonl.py --input $(INPUT) --langs $(L) --samples $(TATOEBA_SAMPLES) --out-prefix dataset

# UDHR (OHCHR)
UDHR_LANGS ?= am ka kek fuf ur lo km my dz yo
UDHR_MIN_CHARS ?= 60
UDHR_MAX_SAMPLES ?= 150

.PHONY: udhr-pointers udhr-fetch udhr-one
udhr-pointers: ## Build UDHR pointer manifests for UDHR_LANGS (reads dataset/sources/sources.csv)
	@mkdir -p dataset/udhr/pointers
	@$(PY) scripts/udhr_pointer_poc.py build --codes $(UDHR_LANGS) --sources dataset/sources/sources.csv --out-dir dataset/udhr/pointers

udhr-fetch: ## Fetch UDHR pages listed in pointers and write processed JSONL (keep out of git)
	@for L in $(UDHR_LANGS); do \
		mani=dataset/udhr/pointers/$$L.jsonl; \
		out=dataset/processed/$$L.udhr.jsonl; \
		if [ ! -f $$mani ]; then echo "skip $$L (no $$mani)"; continue; fi; \
		echo "==> $$L (udhr fetch)"; \
		$(PY) scripts/udhr_pointer_poc.py fetch --manifest $$mani --out $$out --min-chars $(UDHR_MIN_CHARS) --max-samples $(UDHR_MAX_SAMPLES); \
	done
MK

# .gitignore additions (optional safety)
if [ -f .gitignore ]; then
  {
    echo 'dataset/processed/*.jsonl'
    echo 'dataset/raw/**/*.jsonl'
  } >> .gitignore
fi

echo "Done. Now append Makefile.other_sources.append to your Makefile (or rename if you don't have one)."
echo "Install deps: pip install requests beautifulsoup4 lxml"
PY

