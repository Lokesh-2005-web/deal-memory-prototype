"""Run with:  python -m unittest discover -s tests -v   (from the project folder)"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dm.evaluate import adversarial, build, load_all, run_questions  # noqa: E402
from dm.extract import llm_extract  # noqa: E402
from dm.ledger import Ledger  # noqa: E402
from dm.query import answer  # noqa: E402


class FakeClient:
    """Stands in for the LLM so the LLM code path can be tested without a key or network."""

    def __init__(self, reply):
        self.reply = reply

    def chat(self, messages, temperature=0.0):
        return self.reply


class TestPipeline(unittest.TestCase):
    def test_gold_records_all_pass_verification(self):
        _, _, stats, _, _ = build("gold")
        self.assertEqual(stats["rejected"], 0, stats["reasons"])

    def test_answer_key_with_perfect_extraction(self):
        led, _, _, _, questions = build("gold")
        for r in run_questions(led, questions):
            self.assertTrue(r["pass"], (r["id"], r["fails"]))

    def test_adversarial_cases_behave_as_designed(self):
        _, paras, _, _ = load_all()
        for a in adversarial(paras):
            self.assertTrue(a["pass"], a)

    def test_access_filter_hides_fund_b_deal(self):
        led, _, _, _, questions = build("gold")
        q1 = next(q for q in questions if q["id"] == "Q1")
        res = answer(led, q1)
        self.assertNotIn("D07", res["deals"])
        q9 = next(q for q in questions if q["id"] == "Q9")
        self.assertIn("D07", answer(led, q9)["deals"])

    def test_llm_path_rejects_fabricated_and_paraphrased_quotes(self):
        _, paras, _, _ = load_all()
        d01 = [p for p in paras if p.deal_id == "D01"]
        reply = json.dumps([
            {"para": 2, "workstream": "systems", "event_type": "delay", "cause_tag": "sso_identity",
             "impact_months": 5, "quote": "Single sign-on for the acquired product slipped by 5 months because the "
                                          "two identity systems could not be mapped to each other."},
            {"para": 3, "workstream": "people", "event_type": "attrition", "cause_tag": "retention_lump_sum",
             "impact_months": None, "quote": "Lump-sum retention bonuses caused three senior engineers to quit."},
            {"para": 4, "workstream": "customers", "event_type": "success", "cause_tag": "communication",
             "impact_months": 3, "quote": "Weekly all-hands updates in the first 100 days kept customer churn to 2 "
                                         "accounts."},
        ])
        recs, errors = llm_extract(d01, FakeClient("```json\n" + reply + "\n```"))
        self.assertEqual(errors, [])
        led = Ledger()
        deals, _, _, _ = load_all()
        led.add_deals(deals)
        stats = led.add_records(recs, {(p.deal_id, p.para): p.text for p in paras})
        self.assertEqual(stats["verified"], 1)
        self.assertEqual(stats["rejected"], 2, stats["reasons"])

    def test_llm_garbage_reply_is_reported_not_crashing(self):
        _, paras, _, _ = load_all()
        recs, errors = llm_extract([p for p in paras if p.deal_id == "D02"], FakeClient("Sure! Here are lessons..."))
        self.assertEqual(recs, [])
        self.assertEqual(len(errors), 1)

    def test_public_folder_reads_only_saved_filings(self):
        import tempfile
        from dm.ingest import load_public
        with tempfile.TemporaryDirectory() as d:
            Path(d, "README.txt").write_text("Instructions, not a filing.\n\nMore instructions.")
            Path(d, "P99.txt").write_text("TEST FIXTURE, not a real filing.\n\nThe data migration took 4 months "
                                         "longer than planned after the merger.")
            paras = load_public(d)
        self.assertEqual({p.doc for p in paras}, {"P99.txt"})
        self.assertEqual(len(paras), 2)

    def test_llm_summary_without_citations_is_dropped(self):
        led, _, _, _, questions = build("gold")
        q1 = next(q for q in questions if q["id"] == "Q1")
        res = answer(led, q1, writer="llm", client=FakeClient("SSO was the main problem in most deals."))
        self.assertEqual(res["writer"], "template")
        self.assertIn("rejected by the citation check", res["note"])
        self.assertTrue(res["check_ok"])


if __name__ == "__main__":
    unittest.main()
