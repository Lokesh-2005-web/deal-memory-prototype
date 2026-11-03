"""Deal Memory prototype command line.

  python run.py eval --extractor baseline        # no API key needed
  python run.py eval --extractor gold            # tests the ask path alone, with perfect extraction
  python run.py eval --extractor llm             # needs OPENROUTER_API_KEY (free key at openrouter.ai)
  python run.py ask Q1 --extractor baseline      # one question from data/questions.json
  python run.py public --extractor baseline      # run extraction + verification on your saved public filings
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # works from any folder

from dm.evaluate import DATA, ROOT, build, evaluate
from dm.extract import OpenRouterClient, baseline_extract, llm_extract
from dm.ingest import load_public
from dm.ledger import Ledger
from dm.query import answer, checklist


def get_client(args):
    if args.extractor == "llm" or getattr(args, "writer", "template") == "llm":
        return OpenRouterClient(model=args.model)
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("eval", "ask", "public"):
        p = sub.add_parser(name)
        p.add_argument("--extractor", choices=["baseline", "gold", "llm"], default="baseline")
        p.add_argument("--model", default=None, help="OpenRouter model id (default from OPENROUTER_MODEL)")
        if name != "public":
            p.add_argument("--writer", choices=["template", "llm"], default="template",
                           help="'llm' adds a citation-checked LLM summary to each answer")
        if name == "ask":
            p.add_argument("qid", help="question id from data/questions.json, e.g. Q1")
    args = ap.parse_args(argv)
    client = get_client(args)

    if args.cmd == "eval":
        res = evaluate(args.extractor, client, args.writer, out_dir=ROOT / "results")
        q = res["questions"]
        ex = res["extraction"]
        ho = res["heldout"]
        print("Extraction, main 10 docs: precision %.1f%%, recall %.1f%%" % (100 * ex["precision"], 100 * ex["recall"]))
        print("Extraction, 3 held-out docs: precision %.1f%%, recall %.1f%%"
              % (100 * ho["precision"], 100 * ho["recall"]))
        print("Questions passed: %d/%d" % (sum(r["pass"] for r in q), len(q)))
        print("Adversarial checks OK: %d/%d" % (sum(a["pass"] for a in res["adversarial"]), len(res["adversarial"])))
        print("Full report: results/eval_%s.md" % args.extractor)
        return 0

    if args.cmd == "ask":
        led, _, _, _, questions = build(args.extractor, client)
        spec = next((q for q in questions if q["id"] == args.qid), None)
        if spec is None:
            print("No question %s. Available: %s" % (args.qid, [q["id"] for q in questions]))
            return 1
        res = checklist(led, spec) if spec.get("kind") == "checklist" else answer(led, spec, args.writer, client)
        print(res["text"])
        print("\nCitation check: %s" % ("passed" if res["check_ok"] else "FAILED %s" % res["check_problems"]))
        return 0

    if args.cmd == "public":
        paras = load_public(DATA / "public")
        if not paras:
            print("No .txt files in data/public. See data/public/README.txt for how to save the filings.")
            return 1
        led = Ledger()
        led.add_deals({p.deal_id: {"deal_id": p.deal_id, "name": p.doc, "date": "", "deal_type": "public_filing",
                                   "size_band": "", "industry": "", "acl": "public"} for p in paras})
        if args.extractor == "llm":
            recs, errors = llm_extract(paras, client)
        elif args.extractor == "baseline":
            recs, errors = baseline_extract(paras), []
        else:
            print("There are no gold labels for public filings; use baseline or llm.")
            return 1
        stats = led.add_records(recs, {(p.deal_id, p.para): p.text for p in paras})
        out = ROOT / "results"
        out.mkdir(exist_ok=True)
        led.export_csv(out / ("public_ledger_%s.csv" % args.extractor))
        print(json.dumps({k: v for k, v in stats.items()}, indent=2))
        if errors:
            print("LLM errors:", errors)
        print("Draft records written to results/public_ledger_%s.csv. No gold labels exist for these, so read and "
              "judge them by hand: this is the curator step." % args.extractor)
        return 0


if __name__ == "__main__":
    sys.exit(main())
