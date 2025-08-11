# LID-25 Evaluation Set (v0.1.0)

**Purpose.** A 25-language evaluation set for Language Identification (LID) focused on (i) script diversity, (ii) typological variety, (iii) domain variety, and (iv) reproducibility/licensing via pointer-only manifests.

**Version.** v0.1.0 (frozen)  
**Repo.** <link to this repo>  
**Maintainer.** Teógenes Moura

## Composition

**Constructed (10):** Esperanto (eo), Ido (io), Interlingua (ia), Interlingue/Occidental (ie), Lojban (jbo), Volapük (vo), Lingua Franca Nova (lfn), Kotava (avk), Toki Pona (tok), Klingon (tlh; romanized).  
**Low-resource (10):** Amharic (am, Ethi), Georgian (ka, Geor), Q’eqchi’ (kek, Latn), Pular/Fula (fuf, Latn), Urdu (ur, Arab/RTL), Lao (lo, Laoo), Khmer (km, Khmr), Burmese (my, Mymr), Dzongkha (dz, Tibt), Yorùbá (yo, Latn+diacritics).  
**High/Mid (5):** English (en), Portuguese (pt), Spanish (es), Turkish (tr), Japanese (ja).

Target size: ≥200 sentences per language (min 150), stratified by length buckets (short/medium/long). See `reports/length_distribution.csv` after sampling.

## Sources & Licensing (two-track)

- **Wikipedia (encyclopedic)** — pulled from frozen **Hugging Face dumps** (`wikimedia/wikipedia`) using **pointer-only manifests** (`dump`, `page_id`, optional `rev_id`, `char_start/end`). Text is materialized locally by users via `scripts/wiki_pointer_poc.py`.  
- **Tatoeba (sentences/proverbs)** — CC-BY; small redistributable sets with attribution.  
- **UDHR (legal register)** — Official OHCHR pages or Unicode mirrors; we use **pointer-only** manifests to avoid license ambiguity.

**Repository policy.**  
- `dataset/wikipedia/pointers/` — **Redistributable pointers only** (no text).  
- `dataset/wikipedia/cc_by_sa_text/` — Optional, local **CC-BY-SA** materialization with `ATTRIBUTIONS.md`.  
- `dataset/sources/sources.csv` — URLs + license notes.  
- We recommend keeping CC-BY-SA text out of the repo and generating on demand.

## Collection & Preprocessing

1. **Collect**: Pull candidates from each source; keep original script (no romanization), NFC normalize; strip markup; preserve punctuation.  
2. **De-dup**: Exact & near-dup removal within and across languages (`scripts/dedup.py`).  
3. **Script tags**: Detect script and `is_romanized` heuristic; exclude/mark romanized variants where relevant (e.g., Urdu).  
4. **Length buckets**: short (≤60 chars), medium (61–140), long (≥141).  
5. **Sampling**: Uniform quotas per language × bucket × domain where available.  
6. **Splits**: 10% **dev**, 90% **test**, stratified by language × length × script.  
7. **Metadata**: `schemas/metadata.schema.json` validates:  
   `text|pointer, lang, code, category, source, license, len_chars, script, is_romanized, split`.

## Language Selection Rationale (camera-ready)

We selected a 25-language set to stress axes that materially impact LID performance: **script diversity** (Latin with diacritics, Arabic/RTL, Ge’ez/Ethiopic, Georgian, Lao, Khmer, Myanmar, Tibetan, mixed Japanese), **typological diversity** (isolating, agglutinative, fusional; tonal vs. non-tonal), **domain diversity** (encyclopedic, conversational, legal), and **reproducibility/licensing** (public sources with frozen snapshots or pointer-only manifests). The set includes **10 constructed languages** spanning auxiliary vs. art/logical/minimalist design, **10 low-resource languages** across regions and scripts, and **5 high/mid-resource anchors** to quantify headroom and common “attractor” errors. We prioritized languages that (a) are present in common LID baselines (or have stable community codes), (b) expose real confusions (romanization, diacritics, non-IE Latin), and (c) collectively avoid over-representing a single family, script, or domain. All selected languages have viable public sources that support ≥150–200 sentences after cleaning.

### Constructed languages — why these
Auxiliaries with European lexicon but varied regularity (**eo, ia, io, ie, lfn, vo**) test whether models lean on Romance/Germanic cognates vs. morphology; **jbo** (logical morphology) and **tok** (minimalist lexicon) stress short-snippet robustness; **tlh** (artlang, romanized) probes OOD phonotactics; **avk** (a-priori lexicon) limits trivial overlap with major European languages.

### Low-resource languages — coverage & scripts
**am** (Ethi), **ka** (Geor), **kek** (Latn), **fuf** (Latn), **ur** (Arab/RTL), **lo** (Laoo), **km** (Khmr), **my** (Mymr), **dz** (Tibt), **yo** (Latn+diacritics). This set spans Africa, the Caucasus, South/Southeast Asia, and the Americas, emphasizing distinct scripts and known misclassification patterns (e.g., Latn with diacritics into en/pt/es; romanized ur into hi/en).

### High/Mid anchors — why these 5
**en/pt/es** are strong Latin-script attractors in real settings; **tr** adds agglutinative morphology without changing script; **ja** contributes mixed scripts without dominating the corpus.

## Alternatives Considered

- **Chinese, Russian, Arabic**: high value but risk dominating analysis; we opted for **ja** (multi-script) and **ur** (Arabic script) to keep balance.  
- **Hindi**: strong candidate; deferred to avoid over-weighting Indo-Aryan given ur present.  
- **Quenya/Sindarin/Na’vi/Dothraki**: licensing/corpora less standardized; kept as swap-ins for a future expansion.  
- **Hausa/Wolof/Quechua/Malagasy**: excellent low-resource options; we prioritized script coverage first and keep these as alternates if sourcing changes.

## Known Limitations

- Wikipedia domains are encyclopedic; Tatoeba skews to short sentences; UDHR is legal register. We report per-domain metrics to avoid over-generalizing.  
- Romanization handling is heuristic; we tag `is_romanized` and analyze sensitivity but do not canonicalize across scripts.  
- Some conlangs may have community drift; we pin to specific dumps/sources for stability.

## Reproducibility

- **Pointer manifests** pin `dump` + `page_id` (+ optional `rev_id`) and offsets; the fetch script re-materializes text from the same frozen dump.  
- Optional integrity: `sha256_expected` enables strict verification during fetch.  
- All processing is scripted (`Makefile` targets `data`, `eval`, `figs`) with fixed random seeds.

## Citation

Please cite this repository (Zenodo DOI to be added on release) and all upstream data sources (Wikipedia/CC-BY-SA, Tatoeba/CC-BY, UDHR/OHCHR).
