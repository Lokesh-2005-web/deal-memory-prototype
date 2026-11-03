"""Step 3 of the pipeline: draft lesson records from free text.

Two extractors share one output format so they can be compared on the same test set:
  baseline_extract : keyword rules, no AI. The yardstick the LLM has to beat.
  llm_extract      : an LLM through OpenRouter (needs your own free API key). NOT run in the build environment.
Neither is trusted: every record goes through verify.py before it can reach the ledger.
"""
import json
import os
import re
import time
import urllib.error
import urllib.request

from . import CAUSES, EVENTS, WORKSTREAMS

# (cause_tag, workstream, regex). First matching rule per sentence wins, so order matters.
RULES = [
    ("sso_identity", "systems", r"single sign-on|\bSSO\b|identity (systems?|providers?)|unifying login"),
    ("data_migration", "systems", r"data migration|migrat\w+|moving customer records|customer records into"),
    ("erp_finance_systems", "finance_ops", r"general ledgers?|charts? of accounts|\bERP\b"),
    ("vendor_contracts", "finance_ops", r"vendor|supplier|licen[cs]e contracts?"),
    ("security_review", "legal_compliance", r"security review|SOC 2|penetration test"),
    ("retention_lump_sum", "people", r"lump sum|up front|upfront"),
    ("retention_staged_vesting", "people", r"\bvest(s|ing|ed)?\b|\bstaged\b"),
    ("customer_churn", "customers", r"cancel\w*|churn|synerg\w+"),
    ("governance", "governance", r"decision[- ]rights|owned integration decisions|steering committee"),
    ("talent_attrition", "people", r"attrition|\bleft\b|resigned|departed"),
    ("communication", "people", r"town halls?|all-hands|communicat\w+"),
]
SENT = re.compile(r"(?<=[.!?])\s+")
_ATTR = re.compile(r"\b(resign\w*|left|departed|quit)\b", re.I)
_SUCC = re.compile(r"\b(kept|stayed|retained|smooth\w*|without|ahead of)\b|\bno customer\b|caused no", re.I)
_DELAY = re.compile(r"\b(slip\w*|delay\w*|late|longer|behind|add\w*|stall\w*|overran|took|could not be \w+)\b", re.I)
_MISS = re.compile(r"\b(below|missed|shortfall|cancel\w*)\b", re.I)


def evidence_type(impact):
    return "measured" if impact is not None else "self_reported"


def _event(cause, s):
    if cause == "talent_attrition" or _ATTR.search(s):
        return "attrition"
    if _SUCC.search(s):
        return "success"
    if _DELAY.search(s):
        return "delay"
    if _MISS.search(s):
        return "miss"
    return "decision"


def _impact(s, event):
    if event != "delay":
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s+months?\b", s)
    return float(m.group(1)) if m else None


def baseline_extract(paras):
    out, seen = [], set()
    for p in paras:
        for s in SENT.split(p.text):
            for cause, ws, pat in RULES:
                if re.search(pat, s, re.I):
                    if (p.deal_id, p.para, cause) not in seen:
                        seen.add((p.deal_id, p.para, cause))
                        ev = _event(cause, s)
                        imp = _impact(s, ev)
                        out.append({"deal_id": p.deal_id, "doc": p.doc, "para": p.para, "workstream": ws,
                                    "event_type": ev, "cause_tag": cause, "impact_months": imp, "quote": s,
                                    "evidence_type": evidence_type(imp), "extractor": "baseline"})
                    break
    return out


# ---------------------------------------------------------------- LLM extractor
class OpenRouterClient:
    """Minimal OpenRouter chat client (stdlib only). Free-tier models are rate limited: keep tests small.
    Model names on free tiers change; pick one at https://openrouter.ai/models and set OPENROUTER_MODEL."""

    def __init__(self, api_key=None, model=None):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise RuntimeError("Set OPENROUTER_API_KEY (free key from openrouter.ai) to use the LLM extractor.")
        self.model = model or os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")

    def chat(self, messages, temperature=0.0):
        body = json.dumps({"model": self.model, "messages": messages, "temperature": temperature}).encode()
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions", data=body,
            headers={"Authorization": "Bearer " + self.api_key, "Content-Type": "application/json"})
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    return json.load(r)["choices"][0]["message"]["content"]
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < 3:
                    time.sleep(10 * (attempt + 1))
                    continue
                raise


SYSTEM_PROMPT = (
    "You extract integration lessons from post-acquisition review documents. "
    "Return ONLY a JSON array, no prose and no markdown. Each element must be an object with keys: "
    '"para" (integer paragraph number), '
    '"workstream" (one of %s), "event_type" (one of %s), "cause_tag" (one of %s), '
    '"impact_months" (number, or null), "quote" (one sentence copied character for character from that paragraph). '
    "Rules: copy the quote exactly and never paraphrase it. Set impact_months only if a duration in months is "
    "written in the quote. Skip paragraphs that contain no concrete lesson. If a paragraph only says something vague "
    "such as 'minor delays' with no cause, skip it. Use cause_tag 'other' only if nothing else fits."
) % (WORKSTREAMS, EVENTS, list(CAUSES))


def _parse_json_list(text):
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    data = json.loads(t)
    if not isinstance(data, list):
        raise ValueError("model did not return a JSON list")
    return data


def llm_extract(paras, client):
    """Returns (records, errors). One call per document."""
    docs = {}
    for p in paras:
        docs.setdefault((p.deal_id, p.doc), []).append(p)
    records, errors = [], []
    for (deal_id, doc), ps in docs.items():
        body = "\n".join("[P%d] %s" % (p.para, p.text) for p in ps)
        msgs = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": "Document: %s\nDeal: %s\n\n%s" % (doc, deal_id, body)}]
        try:
            items = _parse_json_list(client.chat(msgs))
        except Exception as e:  # a bad reply for one document must not stop the run
            errors.append("%s: %s" % (doc, e))
            continue
        for it in items:
            if not isinstance(it, dict):
                continue
            try:
                para = int(it.get("para"))
            except (TypeError, ValueError):
                para = -1
            imp = it.get("impact_months")
            records.append({"deal_id": deal_id, "doc": doc, "para": para, "workstream": it.get("workstream"),
                            "event_type": it.get("event_type"), "cause_tag": it.get("cause_tag"),
                            "impact_months": imp, "quote": it.get("quote", ""),
                            "evidence_type": evidence_type(imp), "extractor": "llm"})
    return records, errors
