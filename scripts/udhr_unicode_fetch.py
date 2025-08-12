#!/usr/bin/env python3
"""
UDHR -> JSONL fetcher (single file, two backends).

Backends
- zip  : parse UDHR XML bulk zip (already cached at dataset/udhr/cache/udhr_xml.zip)
- hf   : use Hugging Face dataset cis-lmu/udhr-lid (CC0 packaging)
- auto : prefer cached zip; otherwise fall back to hf

Usage
  python scripts/udhr_unicode_fetch.py \
    --langs am ka kek fuf ur lo km my dz yo \
    --max-samples 120 --min-chars 80 --out-prefix dataset [--backend auto|zip|hf]
"""
import argparse, os, sys, json, re, zipfile, datetime as dt
from xml.etree import ElementTree as ET

# Project code -> ISO-639-3 in UDHR
MAP = {"am":"amh","ka":"kat","kek":"kek","fuf":"fuf","ur":"urd","lo":"lao","km":"khm","my":"mya","dz":"dzo","yo":"yor"}

CACHE_ZIP = os.path.join("dataset","udhr","cache","udhr_xml.zip")

def _pick_xml_name(namelist, iso3: str):
    exact = f"udhr_{iso3}.xml"
    if exact in namelist:
        return exact
    import fnmatch
    cands = sorted([n for n in namelist if fnmatch.fnmatch(n.lower(), f"udhr_{iso3}*.xml")])
    return cands[0] if cands else None

def _xml_to_paragraphs(xml_bytes: bytes):
    root = ET.fromstring(xml_bytes)
    paras = []
    for el in root.iter():
        tag = el.tag.lower()
        if tag.endswith("para") or tag.endswith("p"):
            txt = "".join(el.itertext()).strip()
            if txt:
                paras.append(re.sub(r"\s+", " ", txt))
    return paras

def write_jsonl(out_path: str, code: str, texts, meta: dict, cap: int):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    n = 0
    with open(out_path, "w", encoding="utf-8") as w:
        for t in texts:
            if not t or not isinstance(t, str):
                continue
            if len(t) < meta["min_chars"]:
                continue
            obj = {
                "text": t,
                "domain": "legal",
                "lang": code, "code": code,
                **meta["license_fields"],
                "source": meta["source"],
                "provider": meta["provider"],
                "trace": meta.get("trace", {}),
            }
            w.write(json.dumps(obj, ensure_ascii=False) + "\n")
            n += 1
            if n >= cap:
                break
    return n

def fetch_zip(codes, max_samples, min_chars, out_prefix):
    kept = {}
    if not (os.path.exists(CACHE_ZIP) and os.path.getsize(CACHE_ZIP) > 0):
        print(f"[udhr] zip backend: cache not found at {CACHE_ZIP}", file=sys.stderr)
        return None  # signal “no zip”
    with zipfile.ZipFile(CACHE_ZIP, "r") as zf:
        names = set(zf.namelist())
        for code in codes:
            iso3 = MAP.get(code)
            if not iso3:
                print(f"[udhr] zip: skip {code} (no iso3)", file=sys.stderr)
                kept[code] = 0; continue
            xml_name = _pick_xml_name(names, iso3)
            if not xml_name:
                print(f"[udhr] zip: {code} ({iso3}) not in zip", file=sys.stderr)
                kept[code] = 0; continue
            paras = _xml_to_paragraphs(zf.read(xml_name))
            meta = {
                "min_chars": min_chars,
                "license_fields": {
                    "license": "UDHR text (public document); packaging: UDHR in XML",
                    "license_url": "https://efele.net/udhr/",
                },
                "source": "udhr-xml",
                "provider": "efele.net",
                "trace": {"xml": xml_name},
            }
            outp = os.path.join(out_prefix, "processed", f"{code}.udhr.jsonl")
            n = write_jsonl(outp, code, paras, meta, max_samples)
            kept[code] = n
            print(f"[udhr][zip] {code} ({iso3}) -> {outp} kept={n}")
    return kept

def fetch_hf(codes, max_samples, min_chars, out_prefix):
    try:
        from datasets import load_dataset
    except Exception as e:
        raise RuntimeError("pip install datasets") from e

    ds = load_dataset("cis-lmu/udhr-lid", split="test")
    kept = {}
    for code in codes:
        iso3 = MAP.get(code)
        if not iso3:
            print(f"[udhr] hf: skip {code} (no iso3)", file=sys.stderr)
            kept[code] = 0
            continue

        # Correct columns: iso639-3 for the code, sentence for the text
        sub = ds.filter(lambda ex: ex.get("iso639-3") == iso3)
        texts = [ (ex.get("sentence") or "").strip() for ex in sub ]

        meta = {
            "min_chars": min_chars,
            "license_fields": {
                "license": "CC0-1.0 (dataset packaging); UDHR text is a public document",
                "license_url": "https://huggingface.co/datasets/cis-lmu/udhr-lid",
            },
            "source": "udhr-lid",
            "provider": "Hugging Face / cis-lmu",
            "trace": {"iso3": iso3},
        }
        outp = os.path.join(out_prefix, "processed", f"{code}.udhr.jsonl")
        n = write_jsonl(outp, code, texts, meta, max_samples)
        kept[code] = n
        print(f"[udhr][hf]  {code} ({iso3}) -> {outp} kept={n}")
    return kept

    try:
        from datasets import load_dataset
    except Exception as e:
        raise RuntimeError("pip install datasets") from e

    ds = load_dataset("cis-lmu/udhr-lid", split="test")
    kept = {}
    for code in codes:
        iso3 = MAP.get(code)
        if not iso3:
            print(f"[udhr] hf: skip {code} (no iso3)", file=sys.stderr)
            kept[code] = 0
            continue

        # Correct columns: iso639-3 for the code, sentence for the text
        sub = ds.filter(lambda ex: ex.get("iso639-3") == iso3)
        texts = [ (ex.get("sentence") or "").strip() for ex in sub ]

        meta = {
            "min_chars": min_chars,
            "license_fields": {
                "license": "CC0-1.0 (dataset packaging); UDHR text is a public document",
                "license_url": "https://huggingface.co/datasets/cis-lmu/udhr-lid",
            },
            "source": "udhr-lid",
            "provider": "Hugging Face / cis-lmu",
            "trace": {"iso3": iso3},
        }
        outp = os.path.join(out_prefix, "processed", f"{code}.udhr.jsonl")
        n = write_jsonl(outp, code, texts, meta, max_samples)
        kept[code] = n
        print(f"[udhr][hf]  {code} ({iso3}) -> {outp} kept={n}")
    return kept

    try:
        from datasets import load_dataset  # already used elsewhere in repo
    except Exception as e:
        raise RuntimeError("pip install datasets") from e
    ds = load_dataset("cis-lmu/udhr-lid")["test"]
    kept = {}
    for code in codes:
        iso3 = MAP.get(code)
        if not iso3:
            print(f"[udhr] hf: skip {code} (no iso3)", file=sys.stderr)
            kept[code] = 0; continue
        sub = ds.filter(lambda ex: ex.get("language") == iso3)
        texts = [ (ex.get("text") or "").strip() for ex in sub ]
        meta = {
            "min_chars": min_chars,
            "license_fields": {
                "license": "CC0-1.0 (dataset packaging); UDHR text is a public document",
                "license_url": "https://huggingface.co/datasets/cis-lmu/udhr-lid",
            },
            "source": "udhr-lid",
            "provider": "Hugging Face / cis-lmu",
            "trace": {"iso3": iso3},
        }
        outp = os.path.join(out_prefix, "processed", f"{code}.udhr.jsonl")
        n = write_jsonl(outp, code, texts, meta, max_samples)
        kept[code] = n
        print(f"[udhr][hf]  {code} ({iso3}) -> {outp} kept={n}")
    return kept

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", nargs="+", required=True)
    ap.add_argument("--max-samples", type=int, default=120)
    ap.add_argument("--min-chars", type=int, default=80)
    ap.add_argument("--out-prefix", default="dataset")
    ap.add_argument("--backend", choices=["auto","zip","hf"], default="auto")
    args = ap.parse_args()

    if args.backend == "zip":
        kept = fetch_zip(args.langs, args.max_samples, args.min_chars, args.out_prefix)
        if kept is None:
            print("[udhr] zip cache missing; try --backend hf or download the ZIP to dataset/udhr/cache/udhr_xml.zip", file=sys.stderr)
            return 2
    elif args.backend == "hf":
        kept = fetch_hf(args.langs, args.max_samples, args.min_chars, args.out_prefix)
    else:  # auto
        kept = fetch_zip(args.langs, args.max_samples, args.min_chars, args.out_prefix)
        if kept is None:
            print("[udhr] auto: falling back to Hugging Face")
            kept = fetch_hf(args.langs, args.max_samples, args.min_chars, args.out_prefix)

    # tiny log
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = os.path.join("dataset","udhr","cache","ingest_log.txt")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as lg:
        lg.write(f"{ts} kept {kept}\n")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
