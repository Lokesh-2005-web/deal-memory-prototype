"""Step 4 of the pipeline (code, exact): reject any drafted record that its source does not support.

The LLM is never trusted: the quote must exist verbatim in the cited paragraph, and any number it reports
(impact_months) must be written in that quote.
"""
import re

from . import CAUSES, EVENTS, WORKSTREAMS

NUMWORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
            "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12}


def norm(s):
    return " ".join((s or "").split())


def number_in_text(n, text):
    """True only if n is written as a DURATION in months ('5 months', 'five extra months').
    A bare number elsewhere does not count: 'until month nine' must not support a claimed 9-month delay.
    (Bug found by the adversarial test set; the first version accepted any occurrence of the number.)"""
    t = text.lower()
    forms = {str(int(n)) if float(n).is_integer() else str(n)}
    forms.update(w for w, v in NUMWORDS.items() if v == n)
    return any(re.search(r"\b%s\s+(?:extra\s+|more\s+|additional\s+)?months?\b" % re.escape(f), t) for f in forms)


def verify(rec, para_text, min_words=6):
    """Return (ok, reason). reason is '' when ok."""
    if para_text is None:
        return False, "cited paragraph does not exist"
    q = norm(rec.get("quote"))
    if len(q.split()) < min_words:
        return False, "quote too short"
    if q not in norm(para_text):
        return False, "quote not found verbatim in cited paragraph"
    if rec.get("cause_tag") not in CAUSES:
        return False, "unknown cause_tag"
    if rec.get("workstream") not in WORKSTREAMS:
        return False, "unknown workstream"
    if rec.get("event_type") not in EVENTS:
        return False, "unknown event_type"
    im = rec.get("impact_months")
    if im is not None:
        try:
            im = float(im)
        except (TypeError, ValueError):
            return False, "impact_months is not a number"
        if not number_in_text(im, q):
            return False, "impact_months is not written in the quote"
    return True, ""
