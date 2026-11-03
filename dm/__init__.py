"""Deal Memory prototype: a cited, curator-checked lessons ledger for post-merger integration.

Exact (code):      parsing, quote verification, ledger, access filtering, SQL counts, citation check.
Probabilistic (AI): drafting lesson records from free text, and wording an answer (optional).
"""

# Controlled vocabulary: a fixed list of cause tags is what makes cross-deal counting possible.
CAUSES = {
    "sso_identity": "Single sign-on / identity systems could not be mapped between the two companies",
    "data_migration": "Moving customer or business data onto the parent's platform",
    "erp_finance_systems": "Consolidating finance / ERP systems and charts of accounts",
    "vendor_contracts": "Overlapping or hard-to-exit vendor and supplier contracts",
    "security_review": "Security and compliance review (for example SOC 2) of the acquired product",
    "retention_lump_sum": "Retention pay made as a lump sum up front",
    "retention_staged_vesting": "Retention grants that vest in stages over years",
    "talent_attrition": "Key people leaving (not tied to a specific retention design)",
    "customer_churn": "Customers cancelling or overlapping contracts, missed revenue synergies",
    "governance": "Unclear decision rights or ownership of integration decisions",
    "communication": "Staff and customer communication in the first 100 days",
    "other": "Anything else",
}
WORKSTREAMS = ["systems", "people", "customers", "finance_ops", "legal_compliance", "governance"]
EVENTS = ["delay", "attrition", "success", "miss", "decision"]
PROBLEM_EVENTS = {"delay", "attrition", "miss"}
