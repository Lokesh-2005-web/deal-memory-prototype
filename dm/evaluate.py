"""Evaluation: extraction against hand labels, answers against a hand-written key, and adversarial checks."""
import json
from pathlib import Path

from .check import check_citations
from .extract import baseline_extract, evidence_type, llm_extract
from .ingest import load_deals, load_synthetic
from .ledger import Ledger
from .query import answer, checklist
from .verify import norm

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def load_all():
    deals = load_deals(DATA / "deals.csv")
    paras = load_synthetic(DATA / "synthetic", deals)
    gold = json.loads((DATA / "gold_lessons.json").read_text(encoding="utf-8"))
    questions = json.loads((DATA / "questions.json").read_text(encoding="utf-8"))
    return deals, paras, gold, questions


def load_heldout():
    deals = load_deals(DATA / "heldout_deals.csv")
    paras = load_synthetic(DATA / "heldout", deals)
    gold = json.loads((DATA / "heldout_gold.json").read_text(encoding="utf-8"))
    return deals, paras, gold


def heldout_eval(extractor="baseline", client=None):
    """Extraction only, on documents written after the keyword rules were fixed. No questions here."""
    deals, paras, gold = load_heldout()
    errors = []
    if extractor == "gold":
        recs = gold_records(gold, paras)
    elif extractor == "baseline":
        recs = baseline_extract(paras)
    else:
        recs, errors = llm_extract(paras, client)
    led = Ledger()
    led.add_deals(deals)
    stats = led.add_records(recs, {(p.deal_id, p.para): p.text for p in paras})
    stats["llm_errors"] = errors
    led.publish()
    return stats, score_extraction(recs, gold, led)


def gold_records(gold, paras):
    doc_of = {p.deal_id: p.doc for p in paras}
    return [dict(g, doc=doc_of[g["deal_id"]], evidence_type=evidence_type(g["impact_months"]), extractor="gold")
            for g in gold]


def build(extractor="baseline", client=None):
    deals, paras, gold, questions = load_all()
    errors = []
    if extractor == "gold":
        recs = gold_records(gold, paras)
    elif extractor == "baseline":
        recs = baseline_extract(paras)
    elif extractor == "llm":
        recs, errors = llm_extract(paras, client)
    else:
        raise ValueError(extractor)
    led = Ledger()
    led.add_deals(deals)
    stats = led.add_records(recs, {(p.deal_id, p.para): p.text for p in paras})
    stats["llm_errors"] = errors
    led.publish()  # stand-in for the human curator approving every verified draft
    return led, recs, stats, gold, questions


def score_extraction(recs, gold, led):
    """Compare VERIFIED records with gold on (deal, paragraph, cause). Also check event and duration."""
    kept = [dict(r) for r in led.con.execute("SELECT * FROM lessons WHERE status='published'")]
    gk = {(g["deal_id"], g["para"], g["cause_tag"]): g for g in gold}
    pk = {(r["deal_id"], r["para"], r["cause_tag"]): r for r in kept}
    tp = [k for k in pk if k in gk]
    fp = [k for k in pk if k not in gk]
    fn = [k for k in gk if k not in pk]
    wrong_event = [k for k in tp if pk[k]["event_type"] != gk[k]["event_type"]]
    wrong_months = [k for k in tp if (pk[k]["impact_months"] or None) != (gk[k]["impact_months"] or None)]
    p = len(tp) / len(pk) if pk else 0.0
    r = len(tp) / len(gk) if gk else 0.0

    def show(keys, src):
        return [{"deal_id": k[0], "para": k[1], "cause_tag": k[2], "quote": src[k]["quote"]} for k in keys]
    return {"gold": len(gk), "kept": len(pk), "true_pos": len(tp), "precision": round(p, 3), "recall": round(r, 3),
            "false_pos": show(fp, pk), "missed": show(fn, gk),
            "wrong_event": [{"deal_id": k[0], "para": k[1], "got": pk[k]["event_type"], "want": gk[k]["event_type"]}
                            for k in wrong_event],
            "wrong_months": [{"deal_id": k[0], "para": k[1], "got": pk[k]["impact_months"],
                              "want": gk[k]["impact_months"]} for k in wrong_months]}


def score_question(q, res):
    e = q["expect"]
    fails = []
    if q.get("kind") == "checklist":
        got = {(i["kind"], i["cause"]) for i in res["items"]}
        want = {tuple(x) for x in e["items"]}
        if got - want:
            fails.append("extra items %s" % sorted(got - want))
        if want - got:
            fails.append("missing items %s" % sorted(want - got))
    else:
        if res["abstained"] != e["abstain"]:
            fails.append("abstained=%s, expected %s" % (res["abstained"], e["abstain"]))
        if res["n_deals"] != e["n_deals"]:
            fails.append("n_deals=%d, expected %d" % (res["n_deals"], e["n_deals"]))
        if not e["abstain"]:
            top = res["ranking"][0] if res["ranking"] else None
            if not top or top["cause"] != e["top_cause"]:
                fails.append("top cause %s, expected %s" % (top and top["cause"], e["top_cause"]))
            elif top["n_deals"] != e["top_cause_deals"]:
                fails.append("top cause in %d deals, expected %d" % (top["n_deals"], e["top_cause_deals"]))
    if not res["check_ok"]:
        fails.append("citation check failed: %s" % res["check_problems"])
    return fails


def run_questions(led, questions, writer="template", client=None):
    out = []
    for q in questions:
        res = checklist(led, q) if q.get("kind") == "checklist" else answer(led, q, writer, client)
        res["fails"] = score_question(q, res)
        res["pass"] = not res["fails"]
        out.append(res)
    return out


# ------------------------------------------------------------------ adversarial checks
def adversarial(paras):
    """Feed the verifier records an LLM could plausibly produce, and the checker answers it could write."""
    text = {(p.deal_id, p.para): p.text for p in paras}
    text.update({(p.deal_id, p.para): p.text for p in load_heldout()[1]})
    word_num = {"deal_id": "H01", "para": 2, "workstream": "systems", "event_type": "delay",
                "cause_tag": "sso_identity", "impact_months": 5,
                "quote": "Customers could not log in to both products with one account until month nine, roughly "
                         "five months later than the plan."}
    good = {"deal_id": "D01", "para": 2, "workstream": "systems", "event_type": "delay", "cause_tag": "sso_identity",
            "impact_months": 5,
            "quote": "Single sign-on for the acquired product slipped by 5 months because the two identity systems "
                     "could not be mapped to each other."}
    cases = [
        ("correct record is accepted", dict(good), True),
        ("invented quote", dict(good, quote="SSO slipped badly because the vendor shipped a broken connector."), False),
        ("paraphrased quote", dict(good, quote="Single sign-on slipped 5 months because the identity systems could "
                                              "not be mapped."), False),
        ("inflated number", dict(good, impact_months=9), False),
        ("right quote, wrong paragraph", dict(good, para=3), False),
        ("paragraph that does not exist", dict(good, para=42), False),
        ("unknown cause tag", dict(good, cause_tag="bad_luck"), False),
        ("quote too short to check", dict(good, quote="slipped by 5 months"), False),
        ("duration written as a word ('five months') is accepted", dict(word_num), True),
        ("wrong duration against a word number is rejected", dict(word_num, impact_months=9), False),
        ("record with no duration is accepted",
         {"deal_id": "D06", "para": 3, "workstream": "people", "event_type": "attrition",
          "cause_tag": "talent_attrition", "impact_months": None,
          "quote": "The plant manager and two line supervisors left within 4 months."}, True),
    ]
    from .verify import verify
    results = []
    for name, rec, want in cases:
        ok, why = verify(rec, text.get((rec["deal_id"], rec["para"])))
        results.append({"case": name, "accepted": ok, "expected": want, "pass": ok == want, "reason": why})
    answers = [
        ("answer citing only retrieved ids", "SSO caused most delays [L001, L007].", ["L001", "L007"], True, True),
        ("answer citing an id it never retrieved", "SSO caused most delays [L001, L999].", ["L001"], True, False),
        ("LLM sentence with no citation", "SSO caused most delays [L001]. Vendors were also slow.", ["L001"], True,
         False),
    ]
    for name, t, ids, strict, want in answers:
        ok, probs = check_citations(t, ids, require_every_sentence=strict)
        results.append({"case": name, "accepted": ok, "expected": want, "pass": ok == want, "reason": "; ".join(probs)})
    return results


def _extraction_lines(stats, ex):
    L = ["- Records drafted: %d; passed verification: %d; rejected: %d %s"
         % (stats["produced"], stats["verified"], stats["rejected"], stats["reasons"] or "")]
    if stats.get("llm_errors"):
        L.append("- LLM reply errors: %s" % stats["llm_errors"])
    L.append("- Precision %.1f%%, recall %.1f%% (match on deal + paragraph + cause tag)"
             % (100 * ex["precision"], 100 * ex["recall"]))
    for lab, key in (("Wrong records kept", "false_pos"), ("Lessons missed", "missed")):
        for x in ex[key]:
            L.append('- %s: %s para %d tagged `%s`: "%s"' % (lab, x["deal_id"], x["para"], x["cause_tag"], x["quote"]))
    for x in ex["wrong_event"]:
        L.append("- Wrong event type: %s para %d got %s, want %s" % (x["deal_id"], x["para"], x["got"], x["want"]))
    for x in ex["wrong_months"]:
        L.append("- Wrong duration: %s para %d got %s, want %s" % (x["deal_id"], x["para"], x["got"], x["want"]))
    return L


def report(extractor, stats, ex, qres, adv, ho=None):
    L = ["# Evaluation report: extractor = %s" % extractor, ""]
    L.append("## 1a. Extraction on the 10 main documents (vs %d hand-labelled lessons)" % ex["gold"])
    L += _extraction_lines(stats, ex)
    if ho:
        L += ["", "## 1b. Extraction on 3 HELD-OUT documents (vs %d hand-labelled lessons)" % ho[1]["gold"],
              "Written after the keyword rules were fixed, in different words. This is the fair test."]
        L += _extraction_lines(*ho)
    L += ["", "## 2. Questions (%d/%d passed)" % (sum(r["pass"] for r in qres), len(qres)), "",
          "| ID | Question | Result | Deals used | Abstained | Citations valid | Notes |",
          "|---|---|---|---|---|---|---|"]
    for r in qres:
        L.append("| %s | %s | %s | %d | %s | %s | %s |" % (
            r["id"], r["question"], "PASS" if r["pass"] else "FAIL", r["n_deals"], "yes" if r["abstained"] else "no",
            "yes" if r["check_ok"] else "NO", "; ".join(r["fails"]) or r["note"] or ""))
    L += ["", "## 3. Adversarial checks (%d/%d behaved as designed)" % (sum(a["pass"] for a in adv), len(adv)), "",
          "| Case | Accepted | Should accept | OK | Reason given |", "|---|---|---|---|---|"]
    for a in adv:
        L.append("| %s | %s | %s | %s | %s |" % (a["case"], a["accepted"], a["expected"],
                                                "yes" if a["pass"] else "NO", a["reason"]))
    L += ["", "## 4. Full answers", ""]
    for r in qres:
        L += ["```", r["text"], "```", ""]
    return "\n".join(L)


def evaluate(extractor="baseline", client=None, writer="template", out_dir=None):
    led, recs, stats, gold, questions = build(extractor, client)
    ex = score_extraction(recs, gold, led)
    qres = run_questions(led, questions, writer, client)
    _, paras, _, _ = load_all()
    adv = adversarial(paras)
    ho = heldout_eval(extractor, client)
    md = report(extractor, stats, ex, qres, adv, ho)
    if out_dir:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / ("eval_%s.md" % extractor)).write_text(md, encoding="utf-8")
        (out / ("eval_%s.json" % extractor)).write_text(json.dumps(
            {"stats": stats, "extraction": ex, "heldout": {"stats": ho[0], "extraction": ho[1]},
             "questions": [{k: v for k, v in r.items() if k != "text"} for r in qres],
             "adversarial": adv}, indent=2), encoding="utf-8")
        led.export_csv(out / ("ledger_%s.csv" % extractor))
    return {"stats": stats, "extraction": ex, "heldout": ho[1], "questions": qres, "adversarial": adv,
            "markdown": md}
