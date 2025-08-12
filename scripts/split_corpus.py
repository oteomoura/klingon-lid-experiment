#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deterministic train/dev/test split with stratification by length & source.
- Inputs: dataset/processed/<lang>.dedup.tagged.jsonl (from P1-04/05)
- Buckets by char length: short (<=50), medium (51-150), long (>=151)
- Stratifies per (source, length_bucket) cell
- Optionally drops romanized lines from TRAIN only
- Outputs:
    dataset/splits/{train,dev,test}/{lang}.jsonl
    dataset/splits/{train,dev,test}.jsonl (concatenated)
    reports/split_summary.csv
"""
import argparse, os, sys, json, csv, glob, random, math
from collections import defaultdict
from pathlib import Path

def read_jsonl(p):
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if not line: continue
            try:
                yield json.loads(line)
            except Exception:
                continue

def len_bucket(s: str):
    n = len(s or "")
    if n <= 50: return "short"
    if n <= 150: return "medium"
    return "long"

def split_counts(n, r_train, r_dev, r_test):
    # integer apportionment that sums to n
    t = int(round(n * r_train))
    d = int(round(n * r_dev))
    # ensure sum matches
    e = n - (t + d)
    return t, d, e

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", nargs="*", help="default: infer from *.dedup.tagged.jsonl")
    ap.add_argument("--in-prefix", default="dataset/processed")
    ap.add_argument("--in-suffix", default=".dedup.tagged.jsonl")
    ap.add_argument("--out-prefix", default="dataset/splits")
    ap.add_argument("--report", default="reports/split_summary.csv")

    ap.add_argument("--train-r", type=float, default=0.8)
    ap.add_argument("--dev-r",   type=float, default=0.1)
    ap.add_argument("--test-r",  type=float, default=0.1)

    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--filter-romanized-train", action="store_true",
                    help="drop lines with is_romanized==true from TRAIN only")
    args = ap.parse_args()

    random.seed(args.seed)
    os.makedirs(os.path.dirname(args.report), exist_ok=True)
    Path(args.out_prefix, "train").mkdir(parents=True, exist_ok=True)
    Path(args.out_prefix, "dev").mkdir(parents=True, exist_ok=True)
    Path(args.out_prefix, "test").mkdir(parents=True, exist_ok=True)

    files = glob.glob(os.path.join(args.in_prefix, f"*{args.in_suffix}"))
    langs = args.langs or sorted({Path(p).name.split(".")[0] for p in files})
    if not langs:
        print("[split] No languages discovered.", file=sys.stderr)
        return 0

    # init report
    new_report = not os.path.exists(args.report)
    if new_report:
        with open(args.report, "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerow(
                ["lang","total","train","dev","test",
                 "train_short","train_medium","train_long",
                 "dev_short","dev_medium","dev_long",
                 "test_short","test_medium","test_long",
                 "train_dropped_romanized"]
            )

    concat = {"train": [], "dev": [], "test": []}

    for lang in langs:
        inp = os.path.join(args.in_prefix, f"{lang}{args.in_suffix}")
        if not os.path.exists(inp):
            print(f"[split] {lang}: missing {inp}, skipping.")
            continue

        # collect items grouped by (source, length_bucket)
        by_cell = defaultdict(list)
        total = 0
        train_dropped_romanized = 0

        for rec in read_jsonl(inp):
            text = rec.get("text","")
            src = rec.get("source", rec.get("domain","unknown"))
            bucket = len_bucket(text)
            key = (src, bucket)
            by_cell[key].append(rec)
            total += 1

        # split per cell
        out_map = {"train": [], "dev": [], "test": []}
        tb = {"train":{"short":0,"medium":0,"long":0},
              "dev":{"short":0,"medium":0,"long":0},
              "test":{"short":0,"medium":0,"long":0}}

        for (src, bucket), items in by_cell.items():
            random.shuffle(items)
            n = len(items)
            n_tr, n_dev, n_te = split_counts(n, args.train_r, args.dev_r, args.test_r)

            tr = items[:n_tr]
            dv = items[n_tr:n_tr+n_dev]
            te = items[n_tr+n_dev:n_tr+n_dev+n_te]

            # Optionally drop romanized from TRAIN only
            if args.filter_romanized_train:
                kept = []
                for r in tr:
                    if r.get("is_romanized", False):
                        train_dropped_romanized += 1
                        continue
                    kept.append(r)
                tr = kept

            out_map["train"].extend(tr)
            out_map["dev"].extend(dv)
            out_map["test"].extend(te)
            tb["train"][bucket] += len(tr)
            tb["dev"][bucket] += len(dv)
            tb["test"][bucket] += len(te)

        # write per-lang
        for split in ("train","dev","test"):
            p = Path(args.out_prefix, split, f"{lang}.jsonl")
            with open(p, "w", encoding="utf-8") as f:
                for r in out_map[split]:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            concat[split].extend(out_map[split])

        # append summary
        with open(args.report, "a", encoding="utf-8", newline="") as f:
            csv.writer(f).writerow([
                lang, total,
                len(out_map["train"]), len(out_map["dev"]), len(out_map["test"]),
                tb["train"]["short"], tb["train"]["medium"], tb["train"]["long"],
                tb["dev"]["short"], tb["dev"]["medium"], tb["dev"]["long"],
                tb["test"]["short"], tb["test"]["medium"], tb["test"]["long"],
                train_dropped_romanized
            ])

        print(f"[split] {lang}: total={total} -> train={len(out_map['train'])} dev={len(out_map['dev'])} test={len(out_map['test'])} (dropped_rom_train={train_dropped_romanized})")

    # write concatenated splits
    for split in ("train","dev","test"):
        outp = Path(args.out_prefix, f"{split}.jsonl")
        with open(outp, "w", encoding="utf-8") as f:
            for r in concat[split]:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"[split] done. Wrote {sum(len(v) for v in concat.values())} examples across splits.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
