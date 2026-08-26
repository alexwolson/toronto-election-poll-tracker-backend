# Borealis Forum microdata → audited corpus crosswalk, and forecast-value verdict

**Research date:** 2026-08-25
**Scope:** the 37 approved UofT Borealis Forum Research SPSS `.sav` microdata files (2013 [10.5683/SP3/2ANYFR], 2014 [10.5683/SP3/IM2A0R], 2018 [10.5683/SP2/QCPM89]), now downloaded locally.
**Access boundary:** raw `.sav`/`.docx` bytes stay under gitignored `data/source_documents/`. This note and its companion CSV carry only non-restricted metadata (filenames, fieldwork dates, sample sizes, tested-candidate universe, corpus mapping) — no shares, no respondent data. Rights and retrieval route: [borealis-forum-retrieval.md](borealis-forum-retrieval.md).

This is the **post-access** complement to the pre-access [borealis-forum-codebook-screening.md](borealis-forum-codebook-screening.md) (+ `-manifest.csv`): that screen was built from public codebooks and mapped to the **legacy proxy queue**; this crosswalk is built from the actual `.sav` microdata (real n, real weight-variable presence, real value-label candidate sets) and mapped to the **audited `historical_mayoral/` corpus** (`poll_samples.csv`).

## Verdict: not worth ingesting to improve the 2026 mayoral forecast

The juice is not worth the squeeze **for forecast quality**. The value is archival/completeness only, and ROADMAP already calls Borealis material "optional."

**Why (mechanism, OBSERVED):**
- The 2026 forecast *point* estimate comes from 2026 polls; the historical corpus never touches it.
- The historical corpus feeds only the **uncertainty calibration** — the Dirichlet bridge concentration κ, fit by margin-PIT across whole election **cycles** (ADR 0042), an **n=6/7** fit "a single cycle could move." The unit of evidence is the *cycle*.
- The endpoint selector structurally excludes pre-Final-Ballot polls: `backend/model/mayoral_endpoint.py:378` → `if sample.fieldwork_end < boundary_date: continue`. Boundaries (from `data/raw/elections/mayoral_elections.csv`): **2014 → 2014-09-12**, **2018 → 2018-07-30**.

**Applied to this drop:**
- **24 files** match samples already in the corpus. The in-window (post-boundary) 2014/2018 ones that actually score were already ingested from first-party Forum releases; the microdata just duplicates their provenance.
- **13 files** are genuinely new to the corpus, **but all 7 ballot-bearing new waves are pre-nomination** (2013–May 2014) → structurally excluded → **zero endpoint/qualification value**. The remaining new 2018 files are non-ballot.
- The single genuinely *in-window* new poll is **2018 Oct 19 (n=265)** — tiny, and in an already-qualified cycle. Not in the proposed step-2 set.
- Borealis adds **no new election cycle**, which is the only lever that moves the calibration.

**Conditional exception (the one real future value):** the designed-but-unbuilt **dynamic within-cycle mayoral (drift) model** would consume dense within-cycle polling. The 2013–2014 Forum series is ~monthly trial heats across a whole campaign — exactly that. If that model is ever built, this data becomes genuine fuel. Until then the endpoint discards all of it by design.

**What would actually move the 2026 model:** post-Final-Ballot **2026** polls (the live gating input — cycle is M1/Pre-Final), or a **new cycle type the calibration lacks** (non-landslide / incumbent-defeat, which could also let the incumbency variant qualify, ADR 0039). Borealis has neither.

## Crosswalk summary

Full machine-readable table: [`borealis-forum-microdata-crosswalk.csv`](borealis-forum-microdata-crosswalk.csv) (37 `.sav` rows + 26 corpus-gap rows). Match logic is date-first (raw microdata n runs a few % above published n — the screening signature), one-to-one, with a Δn tolerance so a same-date but wildly-different-n file is not falsely matched.

| Outcome | Count | Meaning |
|---|---:|---|
| Matched (already in corpus) | 24 | Provenance duplicate of an existing sample; in-window ones already scored from first-party releases |
| Genuinely new | 13 | 7 ballot waves (2013 ×5 + 2014 FO4M/FO7N) — **all pre-nomination**; 4 non-ballot 2018; 2 late-2014 (FOCA/FOCK) |
| Corpus gaps | 26 | Forum samples in the corpus with **no** Borealis `.sav` (late-2013/mid-late-2014 waves, all 2022/2023) — the two archives only partially overlap |

Weighting (OBSERVED): 2018 and 2014 files carry a `Weights` variable; **2013 files are unweighted raw** — any derived shares would not reproduce Forum's published (weighted) toplines exactly.

## If ingestion is ever done anyway (archival)

A drafted ingestion spec exists (steps 1+2: provenance-attach + new ballot waves) including a required `poll_sources.py` change to teach the artifact verifier the SPSS `$FL2` signature. It is **deferred** per this verdict. The cheapest worthwhile archival slice would be provenance-attaching only the already-scoring **in-window** 2014/2018 samples (link-rot insurance on real inputs), not the pre-nomination bulk the endpoint never reads.
