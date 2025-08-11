#!/usr/bin/env python3
"""
wiki_pointer_poc.py

Proof-of-concept for a pointer-only Wikipedia pack:
- build: create pointer manifests from a frozen HF dump (no text in repo)
- fetch: materialize snippets locally (for evaluation), with optional hash verification

Usage examples:
  # Build 50 pointers for Portuguese from the 20231101 dump
  python wiki_pointer_poc.py build --config 20231101.pt --lang pt --samples 50 --out dataset/wikipedia/pointers/pt.jsonl --trust-remote-code

  # Fetch the text for those pointers (CC-BY-SA), verifying hashes
  python wiki_pointer_poc.py fetch --manifest dataset/wikipedia/pointers/pt.jsonl --out dataset/wikipedia/cc_by_sa_text/pt.samples.jsonl --trust-remote-code

Install deps:
  pip install datasets
"""

import argparse
import hashlib
import json
import os
import random
import sys
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    from datasets import load_dataset  # type: ignore
except Exception as e:
    load_dataset = None  # will error later if used
    _import_error = e


def _get_field(ex: Dict[str, Any], *candidates: str):
    for c in candidates:
        if c in ex and ex[c] is not None:
            return ex[c]
    return None


def _as_str(x) -> Optional[str]:
    if x is None:
        return None
    try:
        return str(x)
    except Exception:
        return None


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _load_hf_dataset(config: str, trust_remote_code: bool):
    if load_dataset is None:
        raise RuntimeError(
            "datasets library not available. Try: pip install datasets\n"
            f"Original import error: {_import_error}"
        )
    return load_dataset("wikimedia/wikipedia", config, split="train", trust_remote_code=trust_remote_code)


def cmd_build(args: argparse.Namespace) -> int:
    random.seed(args.seed)
    ds = _load_hf_dataset(args.config, args.trust_remote_code)

    candidates: List[Tuple[str, str, int, Optional[str]]] = []  # (page_id, title, len_chars, url)
    # Robust across schema variants
    for ex in ds:
        text = _get_field(ex, "text") or ""
        if not text:
            continue
        L = len(text)
        if not (args.min_chars <= L <= args.max_chars):
            continue

        pageid = _get_field(ex, "pageid", "page_id", "id")
        title = _get_field(ex, "title")
        url = _get_field(ex, "url")
        if pageid is None or title is None:
            continue

        candidates.append((_as_str(pageid), str(title), L, _as_str(url)))

    if not candidates:
        print("No candidates found. Try adjusting --min-chars/--max-chars.", file=sys.stderr)
        return 2

    random.shuffle(candidates)
    chosen = candidates[: args.samples]

    out_path = args.out
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for pid, title, L, url in chosen:
            # Simple slice from start; PoC keeps it straightforward
            char_start = 0
            char_end = min(L, args.max_chars)

            rec = {
                "lang": args.lang,
                "dump": args.config,       # e.g., "20231101.pt"
                "page_id": pid,            # string form for stability
                "rev_id": None,            # optional; fill if available later
                "title": title,
                "url_hint": url,           # optional convenience
                "char_start": char_start,
                "char_end": char_end,
                "sha256_expected": None    # can fill later if you want strict verification
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"Wrote {len(chosen)} pointers -> {out_path}")
    return 0


def _group_pointers_by_cfg(pointers: Iterable[Dict[str, Any]]):
    by_cfg: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for rec in pointers:
        dump = rec.get("dump")
        lang = rec.get("lang")
        if not dump or not lang:
            raise ValueError("Each pointer requires 'dump' and 'lang'.")
        key = (str(dump), str(lang))
        by_cfg.setdefault(key, []).append(rec)
    return by_cfg


def cmd_fetch(args: argparse.Namespace) -> int:
    # Load pointers
    with open(args.manifest, "r", encoding="utf-8") as f:
        pointers = [json.loads(line) for line in f if line.strip()]

    by_cfg = _group_pointers_by_cfg(pointers)

    out_path = args.out
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    out = open(out_path, "w", encoding="utf-8")

    total = 0
    fetched = 0
    mismatches = 0
    missing = 0

    for (dump, lang), items in by_cfg.items():
        ds = _load_hf_dataset(dump, args.trust_remote_code)

        # Build indices that cover common field names; keep both str and int keys
        idx_by_str: Dict[str, Dict[str, Any]] = {}
        idx_by_int: Dict[int, Dict[str, Any]] = {}

        for ex in ds:
            pid = _get_field(ex, "pageid", "page_id", "id")
            if pid is None:
                continue
            title = _get_field(ex, "title")
            text = _get_field(ex, "text") or ""
            url = _get_field(ex, "url")
            rec = {"title": title, "text": text, "url": url}
            s_pid = _as_str(pid)
            if s_pid is not None and s_pid not in idx_by_str:
                idx_by_str[s_pid] = rec
            try:
                i_pid = int(pid)
                if i_pid not in idx_by_int:
                    idx_by_int[i_pid] = rec
            except Exception:
                pass

        for rec in items:
            total += 1
            pid = rec.get("page_id")
            s_pid = _as_str(pid)
            ex = None
            if s_pid and s_pid in idx_by_str:
                ex = idx_by_str[s_pid]
            else:
                try:
                    i_pid = int(pid)
                    ex = idx_by_int.get(i_pid)
                except Exception:
                    ex = None

            if not ex:
                missing += 1
                continue

            text = ex.get("text") or ""
            start = int(rec.get("char_start", 0))
            end = int(rec.get("char_end", len(text)))
            snippet = text[start:end]

            # Hash check (optional)
            expected = rec.get("sha256_expected")
            if expected:
                actual = _sha256_text(snippet)
                status = "ok" if actual == expected else "hash_mismatch"
                mismatches += int(status == "hash_mismatch")
            else:
                status = "ok"

            out.write(json.dumps({
                "lang": rec.get("lang"),
                "title": ex.get("title"),
                "url": ex.get("url"),
                "license": "CC-BY-SA",
                "attribution": f"Text from '{ex.get('title')}' (Wikipedia), CC BY-SA; contributors listed in page history.",
                "text": snippet,
                "status": status
            }, ensure_ascii=False) + "\n")
            fetched += 1

    out.close()
    print(f"Processed pointers: {total}")
    print(f"Fetched:           {fetched}")
    print(f"Missing pages:     {missing}")
    print(f"Hash mismatches:   {mismatches}")
    print(f"Wrote samples ->   {out_path}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Pointer-only Wikipedia pack PoC")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build", help="Create pointer manifest (no text)")
    p_build.add_argument("--config", required=True, help="HF config like 20231101.en")
    p_build.add_argument("--lang", required=True, help="Language code (e.g., en)")
    p_build.add_argument("--out", required=True, help="Output JSONL manifest path")
    p_build.add_argument("--samples", type=int, default=50)
    p_build.add_argument("--min-chars", type=int, default=200)
    p_build.add_argument("--max-chars", type=int, default=1200)
    p_build.add_argument("--seed", type=int, default=13)
    p_build.add_argument("--trust-remote-code", action="store_true")
    p_build.set_defaults(func=cmd_build)

    p_fetch = sub.add_parser("fetch", help="Fetch text for pointers (CC-BY-SA)")
    p_fetch.add_argument("--manifest", required=True)
    p_fetch.add_argument("--out", required=True)
    p_fetch.add_argument("--trust-remote-code", action="store_true")
    p_fetch.set_defaults(func=cmd_fetch)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
