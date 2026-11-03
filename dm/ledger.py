"""Lessons ledger (code + SQLite). The knowledge lives here, not in model weights."""
import csv
import re
import sqlite3

from .verify import verify

SCHEMA = """
CREATE TABLE IF NOT EXISTS deals (
  deal_id TEXT PRIMARY KEY, name TEXT, date TEXT, deal_type TEXT, size_band TEXT, industry TEXT, acl TEXT);
CREATE TABLE IF NOT EXISTS lessons (
  lesson_id TEXT PRIMARY KEY, deal_id TEXT, doc TEXT, para INTEGER, workstream TEXT, event_type TEXT,
  cause_tag TEXT, impact_months REAL, quote TEXT, evidence_type TEXT,
  status TEXT,           -- draft | published | rejected
  reject_reason TEXT, extractor TEXT, review_by TEXT,
  UNIQUE(deal_id, para, cause_tag));
"""


def _review_by(date):
    m = re.match(r"(\d{4})(-\d{2})", date or "")
    return "%d%s" % (int(m.group(1)) + 3, m.group(2)) if m else ""


class Ledger:
    def __init__(self, path=":memory:"):
        self.con = sqlite3.connect(path)
        self.con.row_factory = sqlite3.Row
        self.con.executescript(SCHEMA)

    def add_deals(self, deals):
        for d in deals.values():
            self.con.execute("INSERT OR REPLACE INTO deals VALUES (?,?,?,?,?,?,?)",
                             (d["deal_id"], d.get("name", ""), d.get("date", ""), d.get("deal_type", ""),
                              d.get("size_band", ""), d.get("industry", ""), d.get("acl", "public")))
        self.con.commit()

    def add_records(self, records, para_index):
        """Verify every drafted record against its source paragraph, then store it as draft or rejected."""
        stats = {"produced": 0, "verified": 0, "rejected": 0, "duplicate": 0, "reasons": {}}
        for r in records:
            stats["produced"] += 1
            ok, why = verify(r, para_index.get((r.get("deal_id"), r.get("para"))))
            n = self.con.execute("SELECT COUNT(*) FROM lessons").fetchone()[0] + 1
            deal = self.con.execute("SELECT date FROM deals WHERE deal_id=?", (r.get("deal_id"),)).fetchone()
            try:
                self.con.execute(
                    "INSERT INTO lessons VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    ("L%03d" % n, r.get("deal_id"), r.get("doc"), r.get("para"), r.get("workstream"),
                     r.get("event_type"), r.get("cause_tag"), r.get("impact_months"), r.get("quote"),
                     r.get("evidence_type"), "draft" if ok else "rejected", why, r.get("extractor"),
                     _review_by(deal["date"] if deal else "")))
            except sqlite3.IntegrityError:
                stats["duplicate"] += 1
                continue
            if ok:
                stats["verified"] += 1
            else:
                stats["rejected"] += 1
                stats["reasons"][why] = stats["reasons"].get(why, 0) + 1
        self.con.commit()
        return stats

    def publish(self, ids=None):
        """The curator step. In this prototype it is a function call; in the real design it is a person."""
        if ids is None:
            cur = self.con.execute("UPDATE lessons SET status='published' WHERE status='draft'")
        else:
            cur = self.con.execute("UPDATE lessons SET status='published' WHERE status='draft' AND lesson_id IN (%s)"
                                   % ",".join("?" * len(ids)), list(ids))
        self.con.commit()
        return cur.rowcount

    def export_csv(self, path):
        rows = self.con.execute("SELECT * FROM lessons ORDER BY lesson_id").fetchall()
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(rows[0].keys() if rows else [])
            for r in rows:
                w.writerow(list(r))
