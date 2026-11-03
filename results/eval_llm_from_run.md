# LLM run, as printed on the machine where it was run

Model: `nvidia/nemotron-3-ultra-550b-a55b:free` (OpenRouter free tier), one run, 3 November 2026.
Command: `python run.py eval --extractor llm`. Sections 1 to 3 of `results/eval_llm.md` are copied below exactly as printed (the full answers in section 4 were not copied).

```
Extraction, main 10 docs: precision 100.0%, recall 100.0%
Extraction, 3 held-out docs: precision 100.0%, recall 85.7%
Questions passed: 9/10
Adversarial checks OK: 14/14
Full report: results/eval_llm.md
```

# Evaluation report: extractor = llm

## 1a. Extraction on the 10 main documents (vs 28 hand-labelled lessons)
- Records drafted: 28; passed verification: 28; rejected: 0
- Precision 100.0%, recall 100.0% (match on deal + paragraph + cause tag)
- Wrong duration: D01 para 3 got 6.0, want None
- Wrong duration: D02 para 3 got 24.0, want None
- Wrong duration: D06 para 3 got 4.0, want None

## 1b. Extraction on 3 HELD-OUT documents (vs 7 hand-labelled lessons)
Written after the keyword rules were fixed, in different words. This is the fair test.
- Records drafted: 7; passed verification: 6; rejected: 1 {'impact_months is not written in the quote': 1}
- Precision 100.0%, recall 85.7% (match on deal + paragraph + cause tag)
- Lessons missed: H03 para 2 tagged `governance`: "Nobody could say who had the final call on the warehouse system choice, so the decision dragged on for a quarter."

## 2. Questions (9/10 passed)

| ID | Question | Result | Deals used | Abstained | Citations valid | Notes |
|---|---|---|---|---|---|---|
| Q1 | In our software deals, what caused the biggest systems-integration delays? | PASS | 6 | no | yes |  |
| Q2 | Which retention approaches worked best for engineering talent in our software deals? | PASS | 3 | no | yes |  |
| Q3 | In our last three software acquisitions, what caused the biggest systems delays? | PASS | 3 | no | yes |  |
| Q4 | What went wrong with people and retention in our software deals? | PASS | 3 | no | yes |  |
| Q5 | What caused delays in our healthcare services deals? | PASS | 1 | yes | yes |  |
| Q6 | What caused delays in our industrial hardware deals? | PASS | 1 | yes | yes |  |
| Q7 | What caused delays in our biotech deals? | PASS | 0 | yes | yes |  |
| Q8 | Which compliance or security steps delayed our integrations? | FAIL | 5 | no | yes | n_deals=5, expected 3 |
| Q9 | (Fund B access) In our software deals, what caused the biggest systems-integration delays? | PASS | 7 | no | yes |  |
| Q10 | Draft an integration checklist for a new mid-size fintech software deal. | PASS | 6 | no | yes |  |

## 3. Adversarial checks (14/14 behaved as designed)

| Case | Accepted | Should accept | OK | Reason given |
|---|---|---|---|---|
| correct record is accepted | True | True | yes |  |
| invented quote | False | False | yes | quote not found verbatim in cited paragraph |
| paraphrased quote | False | False | yes | quote not found verbatim in cited paragraph |
| inflated number | False | False | yes | impact_months is not written in the quote |
| right quote, wrong paragraph | False | False | yes | quote not found verbatim in cited paragraph |
| paragraph that does not exist | False | False | yes | cited paragraph does not exist |
| unknown cause tag | False | False | yes | unknown cause_tag |
| quote too short to check | False | False | yes | quote too short |
| duration written as a word ('five months') is accepted | True | True | yes |  |
| wrong duration against a word number is rejected | False | False | yes | impact_months is not written in the quote |
| record with no duration is accepted | True | True | yes |  |

(The remaining 3 rows of section 3, the citation-check cases, were not copied.)
