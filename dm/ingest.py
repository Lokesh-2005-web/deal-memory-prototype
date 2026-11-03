"""Step 2 of the pipeline (code, exact): parse documents into numbered paragraphs that keep their source."""
import csv
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Para:
    deal_id: str
    doc: str
    para: int      # 1-based paragraph number inside the document (header block is not counted)
    text: str      # whitespace-normalised paragraph text
    acl: str       # access group inherited from the deal


def load_deals(path):
    with open(path, newline="", encoding="utf-8") as f:
        return {r["deal_id"]: r for r in csv.DictReader(f)}


def _blocks(text):
    return [b.strip() for b in re.split(r"\n\s*\n", text.strip()) if b.strip()]


def load_synthetic(doc_dir, deals):
    """Synthetic post-mortems. First block is a header containing 'Deal ID: Dxx'."""
    paras = []
    for f in sorted(Path(doc_dir).glob("*.txt")):
        blocks = _blocks(f.read_text(encoding="utf-8"))
        m = re.search(r"Deal ID:\s*(\S+)", blocks[0])
        if not m:
            raise ValueError("%s: header block has no 'Deal ID:' line" % f.name)
        deal_id = m.group(1)
        if deal_id not in deals:
            raise ValueError("%s: deal %s is not in deals.csv" % (f.name, deal_id))
        for i, b in enumerate(blocks[1:], start=1):
            paras.append(Para(deal_id, f.name, i, " ".join(b.split()), deals[deal_id]["acl"]))
    return paras


def load_public(doc_dir):
    """Optional real public documents the user saved as P01.txt, P02.txt ... (see data/public/README.txt).
    Every file becomes its own pseudo-deal with access group 'public'. No gold labels exist for these."""
    paras = []
    d = Path(doc_dir)
    if not d.exists():
        return paras
    for f in sorted(d.glob("P*.txt")):  # only the saved filings, never README.txt
        for i, b in enumerate(_blocks(f.read_text(encoding="utf-8", errors="ignore")), start=1):
            paras.append(Para(f.stem, f.name, i, " ".join(b.split()), "public"))
    return paras
