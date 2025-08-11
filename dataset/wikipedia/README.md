# Wikipedia Pointer Pack (Two-Track)

This folder implements the **pointer-only** approach for Wikipedia text:

- `pointers/` — **Redistributable manifests only** (no text). Each JSONL line stores the *dump id*, *page id*, and *char offsets*. Use the fetch script to materialize locally.
- `cc_by_sa_text/` — (Optional) Locally **materialized** snippets for evaluation, which are licensed **CC BY-SA**. You may keep these out of the repo if you prefer.

## Why pointers?
Wikipedia pages change. We avoid drift and license complexity by pointing to **frozen dumps** on Hugging Face (`wikimedia/wikipedia`), e.g. `20231101.pt`. No text is kept in the repo.

## Typical workflow
1. Build pointer manifests (no text committed):
   ```bash
   python scripts/wiki_pointer_poc.py build --config 20231101.pt --lang pt --samples 50 --out dataset/wikipedia/pointers/pt.jsonl --trust-remote-code
   ```
2. Fetch locally when running experiments (materializes text under CC BY-SA):
   ```bash
   python scripts/wiki_pointer_poc.py fetch --manifest dataset/wikipedia/pointers/pt.jsonl --out dataset/wikipedia/cc_by_sa_text/pt.samples.jsonl --trust-remote-code
   ```

## Notes
- If you later want extra reproducibility, you can add a `sha256_expected` field to each pointer and verify on fetch.
- If you plan to commit the **CC BY-SA** pack, keep it clearly separated and include `ATTRIBUTIONS.md`.
