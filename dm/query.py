"""Ask path. Filter by deal metadata and the asker's access rights BEFORE any ranking, count with SQL,
write the answer from records only, then check every citation.

Prototype simplification (stated honestly in the README): the question arrives with its filters already
chosen (questions.json). In the full design an LLM would turn free text into these filters.
"""
import re

from . import CAUSES, PROBLEM_EVENTS, WORKSTREAMS
from .check import check_citations, cited_ids


def _in(n):
    return ",".join("?" * n)


def visible_deal_ids(led, groups, f):
    where = ["(acl='public'%s)" % (" OR acl IN (%s)" % _in(len(groups)) if groups else "")]
    params = list(groups)
    for key in ("deal_type", "industry", "size_band"):
        if f.get(key):
            where.append("%s=?" % key)
            params.append(f[key])
    sql = "SELECT deal_id FROM deals WHERE " + " AND ".join(where) + " ORDER BY date DESC, deal_id"
    ids = [r[0] for r in led.con.execute(sql, params)]
    if f.get("last_n_deals"):
        ids = ids[: int(f["last_n_deals"])]
    return ids


def matching(led, groups, f):
    """Returns (rows, aggregates). Only published lessons of deals the user may see."""
    ids = visible_deal_ids(led, groups, f)
    if not ids:
        return [], []
    where = ["l.status='published'", "l.deal_id IN (%s)" % _in(len(ids))]
    params = list(ids)
    for key in ("workstream", "event_type", "cause_tag"):
        if f.get(key):
            where.append("l.%s=?" % key)
            params.append(f[key])
    if f.get("since"):
        where.append("d.date>=?")
        params.append(f["since"])
    w = " AND ".join(where)
    rows = [dict(r) for r in led.con.execute(
        "SELECT l.*, d.name AS deal_name, d.date AS deal_date FROM lessons l "
        "JOIN deals d ON d.deal_id=l.deal_id WHERE " + w + " ORDER BY l.lesson_id", params)]
    agg = [dict(r) for r in led.con.execute(
        "SELECT l.cause_tag, COUNT(DISTINCT l.deal_id) AS n_deals, COUNT(*) AS n_lessons, "
        "GROUP_CONCAT(l.lesson_id) AS ids FROM lessons l JOIN deals d ON d.deal_id=l.deal_id WHERE " + w +
        " GROUP BY l.cause_tag ORDER BY n_deals DESC, n_lessons DESC, l.cause_tag", params)]
    return rows, agg


def rank_rows(rows, question):
    """Tiny lexical ranking of evidence inside the already-filtered set (stand-in for embeddings)."""
    q = set(re.findall(r"[a-z]+", question.lower()))

    def score(r):
        words = set(re.findall(r"[a-z]+", (r["quote"] + " " + CAUSES.get(r["cause_tag"], "")).lower()))
        return -len(q & words)
    return sorted(rows, key=lambda r: (score(r), r["lesson_id"]))


def _render(q, rows, n_deals, groups, abstain, min_deals, ranking, evidence):
    measured = sum(1 for r in rows if r["evidence_type"] == "measured")
    lines = ["Question: " + q,
             "Evidence: %d lessons from %d deal(s) visible to groups %s; %d with a stated duration, %d self-reported."
             % (len(rows), n_deals, list(groups), measured, len(rows) - measured)]
    if n_deals == 0:
        lines.append("No evidence found. The ledger has nothing to rank for this question.")
    elif abstain:
        lines.append("Not enough evidence to rank causes (found %d deal(s), need at least %d). Individual cases:"
                     % (n_deals, min_deals))
    else:
        lines.append("Causes ranked by number of deals (counts come from SQL over approved records):")
        for i, rk in enumerate(ranking, 1):
            lines.append("  %d. %s: %d deal%s, %d lesson%s [%s]"
                         % (i, rk["cause"], rk["n_deals"], "" if rk["n_deals"] == 1 else "s", rk["n_lessons"],
                            "" if rk["n_lessons"] == 1 else "s", ", ".join(rk["lesson_ids"])))
    if evidence:
        lines.append("Sources:")
        for r in evidence[:8]:
            lines.append('  [%s] %s %s (%s), paragraph %d: "%s"'
                         % (r["lesson_id"], r["deal_id"], r["deal_name"], r["deal_date"], r["para"], r["quote"]))
    return "\n".join(lines)


def llm_write(client, question, ranking, evidence):
    facts = "\n".join('[%s] %s (%s): %s' % (r["lesson_id"], r["deal_name"], r["deal_date"], r["quote"])
                      for r in evidence[:12])
    rk = "; ".join("%s: %d deals" % (r["cause"], r["n_deals"]) for r in ranking)
    msgs = [{"role": "system", "content":
             "Write 2 to 4 sentences answering the question using ONLY the records given. Every sentence must end "
             "with the record ids it relies on in square brackets, like [L001, L004]. Do not add facts or numbers "
             "that are not in the records. The ranking counts were computed by code; do not change them."},
            {"role": "user", "content": "Question: %s\nRanking: %s\n\nRecords:\n%s" % (question, rk, facts)}]
    return client.chat(msgs)


def answer(led, spec, writer="template", client=None):
    f, groups = spec.get("filters", {}), spec.get("user_groups", [])
    min_deals = spec.get("min_deals", 3)
    rows, agg = matching(led, groups, f)
    deals = sorted({r["deal_id"] for r in rows})
    n_deals = len(deals)
    abstain = n_deals < min_deals
    ranking = [] if abstain else [
        {"cause": a["cause_tag"], "n_deals": a["n_deals"], "n_lessons": a["n_lessons"],
         "lesson_ids": sorted(a["ids"].split(","))} for a in agg]
    evidence = rank_rows(rows, spec["question"])
    retrieved = [r["lesson_id"] for r in rows]
    text = _render(spec["question"], rows, n_deals, groups, abstain, min_deals, ranking, evidence)
    writer_used, note = "template", ""
    if writer == "llm" and client is not None and not abstain:
        try:
            prose = llm_write(client, spec["question"], ranking, evidence)
            ok, problems = check_citations(prose, retrieved, require_every_sentence=True)
            if ok:
                text, writer_used = text + "\n\nSummary (LLM-written, citation-checked):\n" + prose, "llm"
            else:
                note = "LLM summary rejected by the citation check: %s" % "; ".join(problems)
        except Exception as e:
            note = "LLM summary failed: %s" % e
    ok, problems = check_citations(text, retrieved)
    return {"id": spec.get("id"), "question": spec["question"], "abstained": abstain, "n_deals": n_deals,
            "n_lessons": len(rows), "ranking": ranking, "deals": deals, "retrieved_ids": retrieved,
            "cited_ids": sorted(cited_ids(text)), "check_ok": ok, "check_problems": problems,
            "writer": writer_used, "note": note, "text": text + ("\n(" + note + ")" if note else "")}


def checklist(led, spec):
    """Draft checklist from published lessons of the same deal type. Items need evidence from >= min_deals deals."""
    prof, groups = spec["profile"], spec.get("user_groups", [])
    min_deals = spec.get("min_deals", 2)
    rows, _ = matching(led, groups, {"deal_type": prof["deal_type"]})
    grouped = {}
    for r in rows:
        kind = "plan_for" if r["event_type"] in PROBLEM_EVENTS else ("keep_doing" if r["event_type"] == "success" else None)
        if kind and r["cause_tag"] != "other":
            grouped.setdefault((kind, r["cause_tag"]), []).append(r)
    items = []
    for (kind, cause), rs in grouped.items():
        deals = {r["deal_id"] for r in rs}
        if len(deals) >= min_deals:
            items.append({"kind": kind, "cause": cause, "n_deals": len(deals),
                          "lesson_ids": sorted(r["lesson_id"] for r in rs)})
    items.sort(key=lambda i: (-i["n_deals"], i["kind"], i["cause"]))
    lines = ["DRAFT checklist for a %s deal (PMI lead must approve before use)" % ", ".join(prof.values()),
             "Evidence drawn from all prior %s deals you can see; size and industry are not used to filter yet."
             % prof["deal_type"]]
    for it in items:
        verb = "Plan for" if it["kind"] == "plan_for" else "Keep doing"
        lines.append("- %s: %s (evidence from %d prior deals) [%s]"
                     % (verb, CAUSES[it["cause"]], it["n_deals"], ", ".join(it["lesson_ids"])))
    seen = {r["workstream"] for r in rows}
    gaps = [w for w in WORKSTREAMS if w not in seen]
    if gaps:
        lines.append("No evidence in the ledger yet for workstreams: %s" % ", ".join(gaps))
    text = "\n".join(lines)
    retrieved = [r["lesson_id"] for r in rows]
    ok, problems = check_citations(text, retrieved)
    return {"id": spec.get("id"), "question": spec["question"], "abstained": False,
            "n_deals": len({r["deal_id"] for r in rows}), "items": items, "gaps": gaps, "deals":
            sorted({r["deal_id"] for r in rows}), "retrieved_ids": retrieved, "cited_ids": sorted(cited_ids(text)),
            "check_ok": ok, "check_problems": problems, "writer": "template", "note": "", "text": text}
