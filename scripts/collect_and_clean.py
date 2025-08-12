#!/usr/bin/env python3
"""
collect_and_clean.py  —  Phase 1 (P1-03): Collection & Normalization Pipeline

This script ingests text from supported sources and writes:
- RAW:   dataset/raw/{code}/{source}.{timestamp}.jsonl
- CLEAN: dataset/processed/{code}.{source}.jsonl  (normalized NFC, minimal cleaning)

Supported sources (subcommands):
  1) wikipedia  — from pointer-only manifests (frozen HF dumps)
  2) jsonl      — from an existing JSONL with {"text": "..."} (e.g., Tatoeba converter output)

Examples
--------
# Wikipedia (Portuguese) using a pointer manifest
python scripts/collect_and_clean.py wikipedia \
  --code pt \
  --manifest dataset/wikipedia/pointers/pt.jsonl \
  --out-prefix dataset \
  --trust-remote-code

# Ingest an already-materialized JSONL (e.g., Tatoeba subset) with a text field
python scripts/collect_and_clean.py jsonl \
  --code tok \
  --input data/tatoeba_tok.jsonl \
  --source tatoeba \
  --license "CC-BY" \
  --domain sentences \
  --out-prefix dataset
"""

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import sys
import unicodedata
from typing import Any, Dict, Iterable, List, Optional

# ---------- Utilities ----------

def normalize_text(text: str, form: str = "NFC", strip_spaces: bool = True) -> str:
    """Unicode normalize and do minimal whitespace cleanup without altering script."""
    if not isinstance(text, str):
        text = str(text)
    s = unicodedata.normalize(form, text)
    # Standardize newlines
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse long runs of spaces/tabs but keep single spaces and newlines
    if strip_spaces:
        s = re.sub(r"[ \t]{2,}", " ", s)
        # trim lines, keep paragraph structure
        s = "\n".join(line.strip() for line in s.split("\n"))
    # Strip BOM if present
    if s and s[0] == "\ufeff":
        s = s[1:]
    return s

def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def ts() -> str:
    return _dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

def ensure_dirs(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def write_jsonl(path: str, rows: Iterable[Dict[str, Any]]) -> int:
    n = 0
    ensure_dirs(os.path.dirname(path) or ".")
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    return n

# ---------- Wikipedia from pointer manifests ----------

def collect_from_wikipedia_pointers(code: str, manifest_path: str, trust_remote_code: bool = False) -> List[Dict[str, Any]]:
    """
    Read a pointer manifest and materialize snippets from the same frozen dump.
    Each output row: {text, title, url, license, source, lang, code}
    """
    try:
        from datasets import load_dataset  # type: ignore
    except Exception as e:
        raise RuntimeError("Missing dependency 'datasets'. Install with: pip install datasets") from e

    # Load pointers
    pointers: List[Dict[str, Any]] = []
    with open(manifest_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            pointers.append(json.loads(line))

    # Group by (dump, lang)
    by_cfg: Dict[str, List[Dict[str, Any]]] = {}
    for rec in pointers:
        dump = str(rec.get("dump"))
        lang = str(rec.get("lang") or code)
        key = f"{dump}.{lang}" if not dump.endswith(f".{lang}") else dump
        by_cfg.setdefault(key, []).append(rec)

    rows: List[Dict[str, Any]] = []
    for cfg, items in by_cfg.items():
        ds = load_dataset("wikimedia/wikipedia", cfg, split="train", trust_remote_code=trust_remote_code)

        # Index by page id (string and int keys)
        idx_str: Dict[str, Dict[str, Any]] = {}
        idx_int: Dict[int, Dict[str, Any]] = {}
        for ex in ds:
            pid = ex.get("pageid") or ex.get("page_id") or ex.get("id")
            if pid is None:
                continue
            title = ex.get("title")
            url = ex.get("url")
            text = ex.get("text") or ""
            rec = {"title": title, "url": url, "text": text}
            try:
                idx_int[int(pid)] = rec
            except Exception:
                pass
            idx_str[str(pid)] = rec

        for p in items:
            pid = p.get("page_id")
            rec = idx_str.get(str(pid)) or (idx_int.get(int(pid)) if isinstance(pid, (int, str)) and str(pid).isdigit() else None)
            if not rec:
                continue
            text = rec.get("text") or ""
            start = int(p.get("char_start", 0))
            end = int(p.get("char_end", len(text)))
            snippet = text[start:end]
            rows.append({
                "text": snippet,
                "title": rec.get("title"),
                "url": rec.get("url"),
                "license": "CC-BY-SA",
                "source": "wikipedia",
                "domain": "encyclopedic",
                "lang": p.get("lang") or code,
                "code": code,
            })
    return rows

# ---------- JSONL ingestion (already materialized text) ----------

def collect_from_jsonl(code: str, input_path: str, source: str, license_str: str, domain: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            text = obj.get("text")
            if not text:
                continue
            rows.append({
                "text": text,
                "title": obj.get("title"),
                "url": obj.get("url"),
                "license": license_str,
                "source": source,
                "domain": domain,
                "lang": obj.get("lang") or code,
                "code": code,
            })
    return rows

# ---------- Cleaning & writing ----------

def clean_rows(rows: List[Dict[str, Any]], normalize: str = "NFC", min_chars: int = 1, max_chars: int = 100000) -> List[Dict[str, Any]]:
    cleaned: List[Dict[str, Any]] = []
    for r in rows:
        t = normalize_text(r.get("text", ""), form=normalize, strip_spaces=True)
        if not t:
            continue
        L = len(t)
        if L < min_chars or L > max_chars:
            continue
        r2 = dict(r)
        r2["text"] = t
        r2["len_chars"] = L
        cleaned.append(r2)
    return cleaned

def write_outputs(code: str, source: str, out_prefix: str, raw_rows: List[Dict[str, Any]], processed_rows: List[Dict[str, Any]]) -> None:
    raw_dir = os.path.join(out_prefix, "raw", code)
    proc_dir = os.path.join(out_prefix, "processed")
    ensure_dirs(raw_dir)
    ensure_dirs(proc_dir)

    raw_path = os.path.join(raw_dir, f"{source}.{ts()}.jsonl")
    proc_path = os.path.join(proc_dir, f"{code}.{source}.jsonl")

    n_raw = write_jsonl(raw_path, raw_rows)
    n_proc = write_jsonl(proc_path, processed_rows)

    print(f"[{code}:{source}] wrote RAW -> {raw_path} ({n_raw} rows)")
    print(f"[{code}:{source}] wrote CLEAN -> {proc_path} ({n_proc} rows)")

# ---------- CLI ----------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="P1-03 Collection & Normalization")
    sub = ap.add_subparsers(dest="cmd", required=True)

    # Wikipedia
    ap_w = sub.add_parser("wikipedia", help="Collect from pointer-only manifest (HF dumps)")
    ap_w.add_argument("--code", required=True, help="Language code (e.g., pt)")
    ap_w.add_argument("--manifest", required=True, help="Path to pointer manifest JSONL")
    ap_w.add_argument("--out-prefix", default="dataset", help="Base output folder (default: dataset)")
    ap_w.add_argument("--normalize", default="NFC", choices=["NFC", "NFKC", "NFD", "NFKD"])
    ap_w.add_argument("--min-chars", type=int, default=1)
    ap_w.add_argument("--max-chars", type=int, default=100000)
    ap_w.add_argument("--trust-remote-code", action="store_true")
    ap_w.set_defaults(handler="wikipedia")

    # JSONL (e.g., Tatoeba converter output)
    ap_j = sub.add_parser("jsonl", help="Collect from a JSONL file that already contains text")
    ap_j.add_argument("--code", required=True, help="Language code (e.g., tok)")
    ap_j.add_argument("--input", required=True, help="Path to input JSONL with at least a 'text' field")
    ap_j.add_argument("--source", required=True, help="Source name (e.g., tatoeba)")
    ap_j.add_argument("--license", required=True, help="License string (e.g., CC-BY)")
    ap_j.add_argument("--domain", default="sentences", help="Domain tag (e.g., sentences, legal, encyclopedic)")
    ap_j.add_argument("--out-prefix", default="dataset", help="Base output folder (default: dataset)")
    ap_j.add_argument("--normalize", default="NFC", choices=["NFC", "NFKC", "NFD", "NFKD"])
    ap_j.add_argument("--min-chars", type=int, default=1)
    ap_j.add_argument("--max-chars", type=int, default=100000)
    ap_j.set_defaults(handler="jsonl")

    args = ap.parse_args(argv)

    if args.handler == "wikipedia":
        raw = collect_from_wikipedia_pointers(args.code, args.manifest, trust_remote_code=args.trust_remote_code)
        clean = clean_rows(raw, normalize=args.normalize, min_chars=args.min_chars, max_chars=args.max_chars)
        write_outputs(args.code, "wikipedia", args.out_prefix, raw, clean)
        return 0

    if args.handler == "jsonl":
        raw = collect_from_jsonl(args.code, args.input, args.source, args.license, args.domain)
        clean = clean_rows(raw, normalize=args.normalize, min_chars=args.min_chars, max_chars=args.max_chars)
        write_outputs(args.code, args.source, args.out_prefix, raw, clean)
        return 0

    ap.error("No handler matched")
    return 2

if __name__ == "__main__":
    sys.exit(main())
