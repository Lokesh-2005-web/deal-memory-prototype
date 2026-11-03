"""Step 'Check' (code, exact): every citation in an answer must point to a record that was actually retrieved."""
import re


def cited_ids(text):
    ids = set()
    for grp in re.findall(r"\[([^\]]*)\]", text):
        ids.update(re.findall(r"L\d+", grp))
    return ids


def check_citations(text, retrieved_ids, require_every_sentence=False):
    """Return (ok, problems). Use require_every_sentence=True for LLM-written prose."""
    problems = []
    bad = sorted(cited_ids(text) - set(retrieved_ids))
    if bad:
        problems.append("cited ids that were not retrieved: %s" % bad)
    if require_every_sentence:
        if not cited_ids(text):
            problems.append("no citations at all")
        for s in re.split(r"(?<=[.!?])\s+", text.strip()):
            if s and not re.search(r"\[[^\]]*L\d+[^\]]*\]", s):
                problems.append("sentence without a citation: %s" % s[:60])
    return (not problems), problems
