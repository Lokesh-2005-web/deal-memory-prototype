# Deal Memory: prototype

The smallest version of the design in the brief that can be tested. It builds a **lessons ledger** from post-acquisition review documents. Each lesson carries a verbatim quote and its source paragraph, and **code** (never the model) checks the quote, does the counting across deals, filters by access rights and checks citations. It then answers integration questions with counts and sources, and says "not enough evidence" when it should.

All deal documents here are **synthetic** (made up and labelled as such). No real company, client or personal data is used.

## Run it

Python 3.8 or newer. No packages to install (standard library only).

```bash
python run.py eval --extractor baseline   # full evaluation, no API key needed
python run.py eval --extractor gold       # same, with perfect extraction (tests the ask path alone)
python run.py ask Q1                      # one question; see data/questions.json for Q1 to Q10
python run.py ask Q10                     # draft integration checklist
python -m unittest discover -s tests -v   # 8 unit tests
```

Reports are written to `results/` (`eval_<extractor>.md` is the readable one; `ledger_<extractor>.csv` is the ledger).

### With a real LLM (OpenRouter, free tier)

1. Create a free account at openrouter.ai and make an API key.
2. Choose a free model at openrouter.ai/models (free model names change over time).
3. Set the key and model, then run:

```bash
# macOS / Linux
export OPENROUTER_API_KEY=sk-or-...
export OPENROUTER_MODEL=<model id ending in :free>
# Windows PowerShell
$env:OPENROUTER_API_KEY="sk-or-..."
$env:OPENROUTER_MODEL="<model id ending in :free>"

python run.py eval --extractor llm
python run.py eval --extractor baseline --writer llm   # LLM writes the answer prose, then it is citation-checked
```

Free models are rate limited. The full run is 13 calls (one per document), plus one per question if `--writer llm` is set.

**Model used for the reported LLM results:** `nvidia/nemotron-3-ultra-550b-a55b:free` (OpenRouter free tier, temperature 0, one run on 3 November 2026). The printed report from that run is saved in `results/eval_llm_from_run.md`. Free models can change or disappear, so a rerun may give different numbers.

## What is in `data/`

| File | What it is |
|---|---|
| `deals.csv` | 10 synthetic deals: date, type, size band, industry, access group (`D07` is visible only to `fund_b`) |
| `synthetic/D01..D10_*.txt` | 10 synthetic post-mortems, 2 to 4 lessons each, with one deliberately vague sentence ("minor delays") that should produce no lesson |
| `gold_lessons.json` | 28 hand-labelled lessons for those documents: the answer key for extraction |
| `questions.json` | 10 test questions with hand-worked expected answers: 6 answerable, 3 that should abstain (1 deal or none), 1 checklist |
| `heldout/H01..H03_*.txt`, `heldout_gold.json` | 3 more synthetic documents with 7 labelled lessons, **written after the keyword rules were fixed**, in different words. The fair test of extraction. |
| `public/public_sources_ma.csv` | 10 real public sources (SEC 8-K filings, GAO reports) with links. Save their text as `P01.txt`... and run `python run.py public`. See `public/README.txt`. |

## How the code maps to the brief's architecture

| Brief step | File | Exact or probabilistic |
|---|---|---|
| Ingest | `dm/ingest.py` | Exact (code) |
| Extract | `dm/extract.py`: `baseline_extract` (keyword rules) and `llm_extract` (OpenRouter) | Probabilistic, never trusted |
| Verify | `dm/verify.py`: quote must be verbatim in the cited paragraph; a claimed duration must be written in the quote as a duration | Exact (code) |
| Curate | `Ledger.publish()` in `dm/ledger.py` | Human in the real design; **simulated here** (auto-approve) |
| Ledger | SQLite in `dm/ledger.py` | Exact (code) |
| Filter, Count | `dm/query.py`: access filter and deal metadata first, then SQL `COUNT(DISTINCT deal_id)` | Exact (code) |
| Rank, Write | `dm/query.py`: lexical ranking; template answer, or optional LLM prose | Probabilistic |
| Check | `dm/check.py`: every cited id must have been retrieved; LLM prose must cite in every sentence | Exact (code) |

## Results

| Test | Keyword baseline | LLM (`nemotron-3-ultra-550b-a55b:free`) |
|---|---|---|
| Extraction, 10 main documents (28 lessons) | precision 92.6%, recall 89.3% | precision 100%, recall 100% |
| Extraction, 3 held-out documents (7 lessons) | precision 100%, **recall 28.6%** (2 of 7) | precision 100%, **recall 85.7%** (6 of 7) |
| Questions Q1 to Q10 | 10/10 pass | 9/10 pass (Q8 failed, see below) |
| Abstention (Q5, Q6, Q7) | all 3 correctly said "not enough evidence" | same |
| Access control (Q1 vs Q9) | `D07` hidden from `corpdev`, visible to `fund_b` | same |
| Adversarial checks (invented quote, paraphrase, inflated number, wrong paragraph, unknown tag, uncited id, uncited LLM sentence...) | 14/14 behaved as designed | 14/14 (same verifier code) |

## Where it fails (honest list)

1. **The keyword baseline is overfit; the LLM closes most of the gap.** The baseline's rules were written while reading the 10 main documents, so its 89% recall flatters it. On held-out documents in other words it found 2 of 7 lessons. It missed "could not log in to both products with one account" (SSO), "porting the loan book" (data migration), "HIPAA controls audit" (compliance review), "paid their full retention award on day one" (lump-sum retention) and "who had the final call" (governance). The LLM found 6 of 7, with no wrong records kept.
2. **The LLM's one held-out miss was the verifier's doing.** The model drafted the governance lesson ("the decision dragged on for a quarter") but attached a number of months to it. "A quarter" is not written as months, so the verifier rejected the whole record. This is a deliberate trade: a rejected draft can be restored by a person, but an invented number cannot be audited.
3. **The LLM gave durations to lessons that are not delays.** "Left within 6 months" (D01), "vesting over 24 months" (D02) and "left within 4 months" (D06) all got an `impact_months`. They passed verification because the numbers really are in the quotes. Same lesson as item 6: verification checks provenance, not meaning.
4. **Q8 failed under the LLM.** It counted 5 deals instead of 3 for compliance and security delays. Every cause tag was correct (100% on the main set), so the model must have filed two other deals' lessons under the `legal_compliance` workstream. The extraction score checks deal, paragraph and cause tag, but not workstream, so the error only surfaced in the answer. Planned fix: derive the workstream from the cause tag in code (the mapping is fixed in `dm/__init__.py`) instead of asking the model for it.
5. **Baseline context errors.** The baseline tagged "kept customer churn to 2 accounts" as customer churn and "kept staff attrition low" as attrition. Both are really communication successes. It also missed "Customer data had to be moved into the parent platform in stages".
6. **Verification does not catch wrong labels.** Both mislabelled baseline records above passed verification, because the quote was real and verbatim. Verification proves *provenance*, not *meaning*. Checking the meaning is what the human curator is for, and in this prototype the curator is simulated.
7. **10/10 on questions overstates robustness.** The baseline's extraction errors happened to fall where no test question looks, so they changed no answer. The LLM's workstream error did hit a question (Q8). A bigger question set would expose more.
8. **A verifier bug, found by the tests and fixed.** The first version accepted a claimed "9-month delay" because the quote said "until month nine". The check now requires the number to be written as a duration ("5 months", "five extra months").
9. **Not built:** turning a free-text question into filters (questions arrive pre-parsed in `questions.json`); embedding search (ranking is lexical); a curator interface; checklist filtering by size and industry (it uses deal type only); review-by dates are stored but not enforced.
10. **Same author, same style; one run.** All synthetic documents were written in one style. Real post-mortems are longer, messier and more sanitised, so 100% on the main set says little. The LLM was run once, on one free model.
11. **Two kinds of LLM test.** The unit tests feed `llm_extract` a scripted fake reply (one real quote, one invented, one with a false duration) and confirm that only the real one survives; they need no key. The real-model numbers above come from one run on a personal machine, because the build environment could not reach openrouter.ai.
