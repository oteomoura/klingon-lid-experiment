#!/usr/bin/env python3
"""
Tatoeba -> JSONL (chatty, robust)

- Accepts project codes in --langs (2-letter like 'en, pt' or 3-letter like 'eng, por').
- Internally maps to Tatoeba's ISO-639-3 for matching.
- Writes: dataset/processed/{project_code}.tatoeba.jsonl
- Always prints a code mapping + kept counts and writes a JSON + CSV summary.

Usage (examples)
  python -u scripts/tatoeba_to_jsonl.py \
    --input data/tatoeba/sentences.csv \
    --langs en pt es tr ja eo ia io ie jbo tok yo lfn vo avk \
    --samples 120 --min-chars 3 --out-prefix dataset

  python -u scripts/tatoeba_to_jsonl.py \
    --input data/tatoeba/sentences.csv \
    --langs am ka ur lo km my dz yo \
    --samples 120 --min-chars 3 --out-prefix dataset
"""
from __future__ import annotations
import argparse, csv, os, bz2, gzip, io, json, re, unicodedata, sys, datetime as dt
from typing import Dict, List, Tuple, TextIO

# 2-letter/community -> iso3 (Tatoeba uses iso3 in the dump)
ISO1_TO_ISO3: Dict[str, str] = {
    # anchors
    "en":"eng","pt":"por","es":"spa","tr":"tur","ja":"jpn",
    # conlangs
    "eo":"epo","ia":"ina","io":"ido","ie":"ile","jbo":"jbo","tok":"tok","yo":"yor","lfn":"lfn","vo":"vol","avk":"avk",
    # low-resource (subset)
    "am":"amh","ka":"kat","ur":"urd","lo":"lao","km":"khm","my":"mya","dz":"dzo",
}

# Preferred project code for a given iso3 (for filenames/fields)
ISO3_TO_PROJECT: Dict[str, str] = {
    "eng":"en","por":"pt","spa":"es","tur":"tr","jpn":"ja",
    "epo":"eo","ina":"ia","ido":"io","ile":"ie","yor":"yo","vol":"vo","lfn":"lfn","jbo":"jbo","avk":"avk","tok":"tok",
    "amh":"am","kat":"ka","urd":"ur","lao":"lo","khm":"km","mya":"my","dzo":"dz","kek":"kek","fuf":"fuf",
}

def open_maybe_compressed(path: str) -> TextIO:
    if path.endswith(".bz2"):
        return io.TextIOWrapper(bz2.BZ2File(path, "rb"), encoding="utf-8", newline="")
    if path.endswith(".gz"):
        return io.TextIOWrapper(gzip.GzipFile(path, "rb"), encoding="utf-8", newline="")
    return open(path, "r", encoding="utf-8", newline="")

def normalize_text(s: str) -> str:
    s = unicodedata.normalize("NFC", s or "")
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"[ \t]{2,}", " ", s)
    s = "\n".join(line.strip() for line in s.split("\n"))
    if s and s[0] == "\ufeff":
        s = s[1:]
    return s

def build_code_maps(lang_args: List[str]) -> Tuple[Dict[str,str], Dict[str,str]]:
    """
    Returns:
      iso3_to_project: iso3 -> project_code (for filenames/fields)
      project_to_iso3: project_code -> iso3 (for trace)
    """
    iso3_to_project: Dict[str,str] = {}
    project_to_iso3: Dict[str,str] = {}
    rows = []
    for code in lang_args:
        c = code.strip().lower()
        if len(c) == 2:
            iso3 = ISO1_TO_ISO3.get(c, c)
            project = c
        elif len(c) == 3:
            iso3 = c
            project = ISO3_TO_PROJECT.get(c, c)  # prefer 2-letter if we know it
        else:
            iso3 = c
            project = c
        iso3_to_project[iso3] = project
        project_to_iso3[project] = iso3
        rows.append((project, iso3))
    # Pretty print
    print("\n[Tatoeba] Code mapping (project_code -> iso3):", flush=True)
    for project, iso3 in rows:
        print(f"  {project:>5}  ->  {iso3}", flush=True)
    print("", flush=True)
    return iso3_to_project, project_to_iso3

def row_iter(path: str):
    """Stream rows (id, iso3, text) from Tatoeba sentences file. Default is TSV."""
    f = open_maybe_compressed(path)
    # Prefer TSV; fall back to Sniffer if needed
    try:
        rd = csv.reader(f, delimiter="\t")
        first = next(rd)
        if len(first) < 3:  # not TSV? try sniffer on a sample
            f.seek(0)
            sample = f.read(4096)
            f.seek(0)
            dialect = csv.Sniffer().sniff(sample, delimiters="\t,;")
            rd = csv.reader(f, dialect)
            first = next(rd)
        yield first[0], first[1].strip().lower(), first[2]
        for row in rd:
            if len(row) < 3:
                continue
            yield row[0], row[1].strip().lower(), row[2]
    finally:
        f.close()

def main() -> int:
    ap = argparse.ArgumentParser(description="Convert Tatoeba sentences to JSONL per language (chatty)")
    ap.add_argument("--input", required=True, help="Path to Tatoeba sentences file (.csv/.tsv/.bz2/.gz)")
    ap.add_argument("--langs", nargs="+", required=True, help="Project codes (2- or 3-letter)")
    ap.add_argument("--samples", type=int, default=120, help="Max samples per project code")
    ap.add_argument("--min-chars", type=int, default=10)
    ap.add_argument("--max-chars", type=int, default=400)
    ap.add_argument("--out-prefix", default="dataset")
    ap.add_argument("--log-dir", default="dataset/tatoeba/logs")
    ap.add_argument("--summary-csv", default="reports/tatoeba_summary.csv")
    args = ap.parse_args()

    os.makedirs(os.path.join(args.out_prefix, "processed"), exist_ok=True)
    os.makedirs(args.log_dir, exist_ok=True)
    os.makedirs(os.path.dirname(args.summary_csv), exist_ok=True)

    iso3_to_project, project_to_iso3 = build_code_maps(args.langs)

    # Prepare outputs
    out_files: Dict[str, TextIO] = {}
    kept_per_project = {pc: 0 for pc in iso3_to_project.values()}
    caps = {pc: args.samples for pc in iso3_to_project.values()}

    for pc in iso3_to_project.values():
        out_path = os.path.join(args.out_prefix, "processed", f"{pc}.tatoeba.jsonl")
        out_files[pc] = open(out_path, "w", encoding="utf-8")

    total_seen_iso3: Dict[str, int] = {}

    # Stream and dispatch
    all_done = False
    for sid, lang_iso3, text in row_iter(args.input):
        total_seen_iso3[lang_iso3] = total_seen_iso3.get(lang_iso3, 0) + 1
        if lang_iso3 not in iso3_to_project:
            continue
        pc = iso3_to_project[lang_iso3]
        if caps[pc] <= 0:
            # Check if every project is full; if so, break early
            all_done = all(caps[p] <= 0 for p in caps)
            if all_done:
                break
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
            "lang": pc,
            "code": pc,
            "tatoeba_lang": lang_iso3,
            "url": f"https://tatoeba.org/sentences/show/{sid}"
        }
        out_files[pc].write(json.dumps(obj, ensure_ascii=False) + "\n")
        kept_per_project[pc] += 1
        caps[pc] -= 1

        if all(caps[p] <= 0 for p in caps):
            break

    for f in out_files.values():
        f.close()

    # Console summary
    print("[Tatoeba] Kept per project code:", flush=True)
    for pc in sorted(kept_per_project):
        iso3 = project_to_iso3.get(pc, "?")
        total = total_seen_iso3.get(iso3, 0)
        print(f"  {pc:>5} (iso3={iso3}): kept={kept_per_project[pc]}  seen_in_dump={total}", flush=True)

    # CSV summary (append)
    write_header = not os.path.exists(args.summary_csv)
    with open(args.summary_csv, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["project_code","iso3","kept","seen_in_dump","samples_cap","input","min_chars","max_chars"])
        for pc, kept in kept_per_project.items():
            iso3 = project_to_iso3.get(pc, "?")
            w.writerow([pc, iso3, kept, total_seen_iso3.get(iso3, 0), args.samples, args.input, args.min_chars, args.max_chars])

    # JSON log
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log = {
        "timestamp": ts,
        "input": args.input,
        "samples_cap": args.samples,
        "min_chars": args.min_chars,
        "max_chars": args.max_chars,
        "mapping": [{"project_code": pc, "iso3": project_to_iso3.get(pc)} for pc in iso3_to_project.values()],
        "kept_per_project": kept_per_project,
        "total_seen_iso3": total_seen_iso3,
    }
    with open(os.path.join(args.log_dir, f"ingest_{ts}.json"), "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

    print(f"[Tatoeba] Log written: {os.path.join(args.log_dir, f'ingest_{ts}.json')}", flush=True)
    print(f"[Tatoeba] CSV summary appended: {args.summary_csv}", flush=True)
    return 0

if __name__ == "__main__":
    sys.exit(main()) 
