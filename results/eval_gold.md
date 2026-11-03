# Evaluation report: extractor = gold

## 1a. Extraction on the 10 main documents (vs 28 hand-labelled lessons)
- Records drafted: 28; passed verification: 28; rejected: 0 
- Precision 100.0%, recall 100.0% (match on deal + paragraph + cause tag)

## 1b. Extraction on 3 HELD-OUT documents (vs 7 hand-labelled lessons)
Written after the keyword rules were fixed, in different words. This is the fair test.
- Records drafted: 7; passed verification: 7; rejected: 0 
- Precision 100.0%, recall 100.0% (match on deal + paragraph + cause tag)

## 2. Questions (10/10 passed)

| ID | Question | Result | Deals used | Abstained | Citations valid | Notes |
|---|---|---|---|---|---|---|
| Q1 | In our software deals, what caused the biggest systems-integration delays? | PASS | 6 | no | yes |  |
| Q2 | Which retention approaches worked best for engineering talent in our software deals? | PASS | 3 | no | yes |  |
| Q3 | In our last three software acquisitions, what caused the biggest systems delays? | PASS | 3 | no | yes |  |
| Q4 | What went wrong with people and retention in our software deals? | PASS | 3 | no | yes |  |
| Q5 | What caused delays in our healthcare services deals? | PASS | 1 | yes | yes |  |
| Q6 | What caused delays in our industrial hardware deals? | PASS | 1 | yes | yes |  |
| Q7 | What caused delays in our biotech deals? | PASS | 0 | yes | yes |  |
| Q8 | Which compliance or security steps delayed our integrations? | PASS | 3 | no | yes |  |
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
| answer citing only retrieved ids | True | True | yes |  |
| answer citing an id it never retrieved | False | False | yes | cited ids that were not retrieved: ['L999'] |
| LLM sentence with no citation | False | False | yes | sentence without a citation: Vendors were also slow. |

## 4. Full answers

```
Question: In our software deals, what caused the biggest systems-integration delays?
Evidence: 6 lessons from 6 deal(s) visible to groups ['corpdev']; 6 with a stated duration, 0 self-reported.
Causes ranked by number of deals (counts come from SQL over approved records):
  1. sso_identity: 4 deals, 4 lessons [L001, L007, L014, L023]
  2. data_migration: 2 deals, 2 lessons [L004, L026]
Sources:
  [L001] D01 Project Falcon (2023-03), paragraph 2: "Single sign-on for the acquired product slipped by 5 months because the two identity systems could not be mapped to each other."
  [L007] D03 Project Cobalt (2021-09), paragraph 2: "Unifying login across the two products took 8 months, far beyond the 3 months planned, mostly because of incompatible identity providers."
  [L014] D05 Project Quartz (2024-02), paragraph 2: "Single sign-on slipped by 3 months; we had learned from Falcon but still underestimated the identity mapping work."
  [L023] D09 Project Tern (2021-04), paragraph 2: "Getting single sign-on working across both products took 4 months longer than planned."
  [L026] D10 Project Slate (2020-02), paragraph 2: "Data migration for the acquired customers took 5 months longer than planned because the legacy platform exported records in a proprietary format."
  [L004] D02 Project Heron (2022-06), paragraph 2: "Moving customer records into the parent company's platform took 4 months longer than planned because of inconsistent record formats."
```

```
Question: Which retention approaches worked best for engineering talent in our software deals?
Evidence: 3 lessons from 3 deal(s) visible to groups ['corpdev']; 0 with a stated duration, 3 self-reported.
Causes ranked by number of deals (counts come from SQL over approved records):
  1. retention_staged_vesting: 3 deals, 3 lessons [L005, L015, L027]
Sources:
  [L027] D10 Project Slate (2020-02), paragraph 3: "Retention grants that vest in annual tranches over 4 years kept most of the senior engineering team through the integration."
  [L005] D02 Project Heron (2022-06), paragraph 3: "Staged equity vesting over 24 months kept all 6 core engineers through the first two years."
  [L015] D05 Project Quartz (2024-02), paragraph 3: "We used retention grants that vest over 3 years, and every key engineer stayed through the first year."
```

```
Question: In our last three software acquisitions, what caused the biggest systems delays?
Evidence: 3 lessons from 3 deal(s) visible to groups ['corpdev']; 3 with a stated duration, 0 self-reported.
Causes ranked by number of deals (counts come from SQL over approved records):
  1. sso_identity: 2 deals, 2 lessons [L001, L014]
  2. data_migration: 1 deal, 1 lesson [L004]
Sources:
  [L001] D01 Project Falcon (2023-03), paragraph 2: "Single sign-on for the acquired product slipped by 5 months because the two identity systems could not be mapped to each other."
  [L014] D05 Project Quartz (2024-02), paragraph 2: "Single sign-on slipped by 3 months; we had learned from Falcon but still underestimated the identity mapping work."
  [L004] D02 Project Heron (2022-06), paragraph 2: "Moving customer records into the parent company's platform took 4 months longer than planned because of inconsistent record formats."
```

```
Question: What went wrong with people and retention in our software deals?
Evidence: 3 lessons from 3 deal(s) visible to groups ['corpdev']; 0 with a stated duration, 3 self-reported.
Causes ranked by number of deals (counts come from SQL over approved records):
  1. retention_lump_sum: 2 deals, 2 lessons [L002, L008]
  2. talent_attrition: 1 deal, 1 lesson [L028]
Sources:
  [L002] D01 Project Falcon (2023-03), paragraph 3: "We paid retention bonuses as one lump sum at closing, and 3 of the 12 senior engineers resigned within 6 months."
  [L008] D03 Project Cobalt (2021-09), paragraph 3: "Retention payments were made up front, and a third of the acquired product team left within a year."
  [L028] D10 Project Slate (2020-02), paragraph 4: "Sales leaders left after the reorganisation was announced."
```

```
Question: What caused delays in our healthcare services deals?
Evidence: 2 lessons from 1 deal(s) visible to groups ['corpdev']; 2 with a stated duration, 0 self-reported.
Not enough evidence to rank causes (found 1 deal(s), need at least 3). Individual cases:
Sources:
  [L021] D08 Project Ember (2022-01), paragraph 2: "Merging the ERP systems took 7 months longer than planned because the two finance teams used different cost centres."
  [L022] D08 Project Ember (2022-01), paragraph 3: "The steering committee met monthly but could not resolve decision-rights disputes between the two finance teams, adding 2 months."
```

```
Question: What caused delays in our industrial hardware deals?
Evidence: 1 lessons from 1 deal(s) visible to groups ['corpdev']; 1 with a stated duration, 0 self-reported.
Not enough evidence to rank causes (found 1 deal(s), need at least 3). Individual cases:
Sources:
  [L017] D06 Project Birch (2019-05), paragraph 2: "Supplier contracts of the acquired plant needed renegotiation, which took 5 months."
```

```
Question: What caused delays in our biotech deals?
Evidence: 0 lessons from 0 deal(s) visible to groups ['corpdev']; 0 with a stated duration, 0 self-reported.
No evidence found. The ledger has nothing to rank for this question.
```

```
Question: Which compliance or security steps delayed our integrations?
Evidence: 3 lessons from 3 deal(s) visible to groups ['corpdev']; 3 with a stated duration, 0 self-reported.
Causes ranked by number of deals (counts come from SQL over approved records):
  1. security_review: 3 deals, 3 lessons [L006, L016, L024]
Sources:
  [L016] D05 Project Quartz (2024-02), paragraph 4: "SOC 2 evidence collection for the combined product delayed the first joint release by 4 months."
  [L024] D09 Project Tern (2021-04), paragraph 3: "The security review of the acquired product delayed its launch to existing customers by 3 months."
  [L006] D02 Project Heron (2022-06), paragraph 4: "The parent's security review of the acquired product added 2 months before it could be sold to existing customers."
```

```
Question: (Fund B access) In our software deals, what caused the biggest systems-integration delays?
Evidence: 8 lessons from 7 deal(s) visible to groups ['corpdev', 'fund_b']; 8 with a stated duration, 0 self-reported.
Causes ranked by number of deals (counts come from SQL over approved records):
  1. sso_identity: 5 deals, 5 lessons [L001, L007, L014, L019, L023]
  2. data_migration: 3 deals, 3 lessons [L004, L020, L026]
Sources:
  [L001] D01 Project Falcon (2023-03), paragraph 2: "Single sign-on for the acquired product slipped by 5 months because the two identity systems could not be mapped to each other."
  [L007] D03 Project Cobalt (2021-09), paragraph 2: "Unifying login across the two products took 8 months, far beyond the 3 months planned, mostly because of incompatible identity providers."
  [L014] D05 Project Quartz (2024-02), paragraph 2: "Single sign-on slipped by 3 months; we had learned from Falcon but still underestimated the identity mapping work."
  [L019] D07 Project Onyx (2023-10), paragraph 2: "Single sign-on took 6 months longer than planned because the two products used different identity providers."
  [L020] D07 Project Onyx (2023-10), paragraph 3: "Customer data had to be moved into the parent platform in stages, which added 2 months."
  [L023] D09 Project Tern (2021-04), paragraph 2: "Getting single sign-on working across both products took 4 months longer than planned."
  [L026] D10 Project Slate (2020-02), paragraph 2: "Data migration for the acquired customers took 5 months longer than planned because the legacy platform exported records in a proprietary format."
  [L004] D02 Project Heron (2022-06), paragraph 2: "Moving customer records into the parent company's platform took 4 months longer than planned because of inconsistent record formats."
```

```
DRAFT checklist for a software, mid, fintech deal (PMI lead must approve before use)
Evidence drawn from all prior software deals you can see; size and industry are not used to filter yet.
- Plan for: Single sign-on / identity systems could not be mapped between the two companies (evidence from 4 prior deals) [L001, L007, L014, L023]
- Keep doing: Retention grants that vest in stages over years (evidence from 3 prior deals) [L005, L015, L027]
- Plan for: Security and compliance review (for example SOC 2) of the acquired product (evidence from 3 prior deals) [L006, L016, L024]
- Plan for: Moving customer or business data onto the parent's platform (evidence from 2 prior deals) [L004, L026]
- Plan for: Retention pay made as a lump sum up front (evidence from 2 prior deals) [L002, L008]
No evidence in the ledger yet for workstreams: finance_ops
```
