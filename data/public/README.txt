Public filings (optional)

public_sources_ma.csv lists 10 public sources (SEC 8-K Item 2.06 filings, an HP statement, two GAO reports)
with links and a one-line summary of what each reports. The prototype cannot download them for you.

To use them:
1. Open each link in a browser.
2. Copy the main text and save it in this folder as P01.txt, P02.txt ... (use the id column).
3. Run:  python run.py public --extractor baseline     (or --extractor llm with an OpenRouter key)
4. Read results/public_ledger_<extractor>.csv by hand. There are no gold labels for these, so you are the curator.

What to expect (and say in the write-up): filings mostly report OUTCOMES (an impairment amount and a generic reason
such as lower expected growth), not operational causes. Only a few (for example P01, Versant 2004) name causes such
as founders leaving. So public filings test that the pipeline runs on real, messy text. They cannot show whether
the idea is useful; only real internal post-mortems could.
