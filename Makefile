# ---- Wikipedia pointer-only pipeline (P1-03) ----
# Override at call time, e.g.:
#   make wiki-all WIKI_SAMPLES=200 LANGS="en pt es"
WIKIDUMP      ?= 20231101
LANGS         ?= en pt es tr ja eo io ia ie lfn vo avk jbo
WIKI_SAMPLES  ?= 120
PY            ?= python -u
SHELL := /bin/bash

PTR_DIR       := dataset/wikipedia/pointers
OUT_PREFIX    := dataset

.PHONY: wiki-all wiki-pointers wiki-collect wiki-one help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## ' Makefile | sed 's/:.*##/: /'

wiki-all: wiki-pointers wiki-collect ## Build pointers + collect/clean for all LANGS

wiki-pointers: ## Build pointer-only manifests for all LANGS (no text committed)
	@mkdir -p $(PTR_DIR)
	@for L in $(LANGS); do \
		echo "==> $$L (pointers from dump $(WIKIDUMP).$$L)"; \
		$(PY) scripts/wiki_pointer_poc.py build \
			--config $(WIKIDUMP).$$L --lang $$L \
			--samples $(WIKI_SAMPLES) \
			--out $(PTR_DIR)/$$L.jsonl \
			--trust-remote-code || echo "skip $$L (dump missing?)"; \
	done

wiki-collect: ## Materialize locally + normalize (kept uncommitted by .gitignore)
	@for L in $(LANGS); do \
		if [ -f $(PTR_DIR)/$$L.jsonl ]; then \
			echo "==> $$L (collect from pointers)"; \
			$(PY) scripts/collect_and_clean.py wikipedia \
				--code $$L \
				--manifest $(PTR_DIR)/$$L.jsonl \
				--out-prefix $(OUT_PREFIX) \
				--trust-remote-code; \
		else \
			echo "skip $$L (no pointers at $(PTR_DIR)/$$L.jsonl)"; \
		fi; \
	done

wiki-one: ## Run pointer build + collect for one language: make wiki-one L=pt
	@test -n "$(L)" || (echo "Usage: make wiki-one L=<lang>"; exit 2)
	@mkdir -p $(PTR_DIR)
	@echo "==> $(L) (pointers from dump $(WIKIDUMP).$(L))"
	@$(PY) scripts/wiki_pointer_poc.py build \
		--config $(WIKIDUMP).$(L) --lang $(L) \
		--samples $(WIKI_SAMPLES) \
		--out $(PTR_DIR)/$(L).jsonl \
		--trust-remote-code || (echo "skip $(L) (dump missing?)"; exit 0)
	@echo "==> $(L) (collect from pointers)"
	@$(PY) scripts/collect_and_clean.py wikipedia \
		--code $(L) \
		--manifest $(PTR_DIR)/$(L).jsonl \
		--out-prefix $(OUT_PREFIX) \
		--trust-remote-code
# ---- Tatoeba + UDHR ingestion (P1-03) ----
PY ?= python -u

# Project codes we use elsewhere (script maps these to ISO-639-3 internally)
TATOEBA_LANGS ?= en pt es tr ja eo ia io ie jbo tok yo lfn vo avk
TATOEBA_INPUT ?= data/tatoeba/sentences.csv
TATOEBA_SAMPLES ?= 120

.PHONY: tatoeba-all
tatoeba-all: ## Convert Tatoeba sentences to JSONL for all TATOEBA_LANGS at once (prints summary)
	@set -euo pipefail; \
	$(PY) scripts/tatoeba_to_jsonl.py \
	  --input $(TATOEBA_INPUT) \
	  --langs $(TATOEBA_LANGS) \
	  --samples $(TATOEBA_SAMPLES) \
	  --out-prefix dataset; \
	echo; \
	echo "Last Tatoeba log:"; \
	ls -1t dataset/tatoeba/logs/ingest_*.json | head -n1 || true; \
	echo; \
	echo "Summary (tail of reports/tatoeba_summary.csv):"; \
	[ -f reports/tatoeba_summary.csv ] && tail -n 20 reports/tatoeba_summary.csv || echo "No summary yet."

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

UDHR_UNI_LANGS ?= am ka kek fuf ur lo km my dz yo
UDHR_MAX_SAMPLES ?= 120
UDHR_MIN_CHARS ?= 80

UDHR_BACKEND ?= auto  # auto|zip|hf

.PHONY: udhr-unicode
udhr-unicode:
	$(PY) scripts/udhr_unicode_fetch.py \
	  --langs $(UDHR_UNI_LANGS) \
	  --max-samples $(UDHR_MAX_SAMPLES) \
	  --min-chars $(UDHR_MIN_CHARS) \
	  --out-prefix dataset \
	  --backend $(UDHR_BACKEND)


# ---- Dedup & script tagging (P1-04/05) ----
PY ?= python -u
LANGS ?=
LANGS_FLAG := $(if $(strip $(LANGS)),--langs $(LANGS),)

dedup-all:
	$(PY) scripts/dedup.py $(LANGS_FLAG) --in-prefix dataset/processed --out-prefix dataset/processed --sources wikipedia tatoeba udhr

dedup-all-near:
	$(PY) scripts/dedup.py $(LANGS_FLAG) --in-prefix dataset/processed --out-prefix dataset/processed --sources wikipedia tatoeba udhr --near-dup --jaccard-thresh 0.85 --ngram 5

tag-scripts:
	$(PY) scripts/detect_script.py $(LANGS_FLAG) --in-prefix dataset/processed --in-pattern "*.dedup.jsonl" --report reports/script_summary.csv

# ---- Split (P1-06) ----
PY ?= python -u
LANGS ?=
LANGS_FLAG := $(if $(strip $(LANGS)),--langs $(LANGS),)

.PHONY: split-all
split-all: ## Make train/dev/test splits with length+source stratification
	$(PY) scripts/split_corpus.py $(LANGS_FLAG) --in-prefix dataset/processed --in-suffix .dedup.tagged.jsonl --out-prefix dataset/splits --report reports/split_summary.csv

.PHONY: split-all-strict
split-all-strict: ## Same, but drop romanized lines from TRAIN only
	$(PY) scripts/split_corpus.py $(LANGS_FLAG) --in-prefix dataset/processed --in-suffix .dedup.tagged.jsonl --out-prefix dataset/splits --report reports/split_summary.csv --filter-romanized-train
