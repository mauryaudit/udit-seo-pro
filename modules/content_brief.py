"""
modules/content_brief.py
Auto-generates an SEO content brief from audit findings + Semrush data.
Output goes into both the Excel and PDF reports.
"""

import re


def generate_content_brief(url: str, parser, audit_results: dict, semrush_data: dict, eeat_result: dict) -> dict:
    """
    Build a structured content brief based on:
    - On-page audit findings (what's missing/weak)
    - Semrush keyword data (target keywords and volume)
    - CORE-EEAT scores (which dimensions need work)
    """

    modules = audit_results.get("modules", {})
    sm_kw = semrush_data.get("organic_keywords", {})
    sm_related = semrush_data.get("related_keywords", {})
    sm_kw_overview = semrush_data.get("keyword_overview", {})

    # ── Target Keywords ──
    primary_kw = ""
    secondary_kws = []

    if sm_kw.get("ok") and sm_kw.get("data"):
        rows = sm_kw["data"]
        # Pick keyword with best volume at position 5–20 (quick win range)
        quick_wins = [r for r in rows if 5 <= int(r.get("Po", r.get("Position", "99")) or "99") <= 20]
        if quick_wins:
            primary_kw = quick_wins[0].get("Ph", quick_wins[0].get("Keyword", ""))
        elif rows:
            primary_kw = rows[0].get("Ph", rows[0].get("Keyword", ""))
        secondary_kws = [r.get("Ph", r.get("Keyword", "")) for r in rows[1:6] if r.get("Ph") or r.get("Keyword")]

    if sm_related.get("ok") and sm_related.get("data"):
        lsi_terms = [r.get("Ph", r.get("Keyword", "")) for r in sm_related["data"][:8] if r.get("Ph") or r.get("Keyword")]
    else:
        lsi_terms = []

    # ── Current state ──
    wc = modules.get("content", {}).get("word_count", 0)
    h1s = modules.get("headings", {}).get("h1_texts", [])
    h1 = h1s[0] if h1s else parser.title.strip()

    # ── Target word count ──
    if wc < 500:
        target_wc = "1200–1800 words (major expansion needed)"
    elif wc < 900:
        target_wc = "1000–1500 words (moderate expansion)"
    else:
        target_wc = "1500–2500 words (maintain depth, update facts)"

    # ── Recommended H2 structure (from audit gaps) ──
    h2_suggestions = []
    text = parser.body_text.lower()

    eeat_dims = eeat_result.get("summary", {})

    if eeat_dims.get("C", 100) < 70:
        h2_suggestions.append("What is [Topic]? (Definition & Overview)")
        h2_suggestions.append("Key Benefits / Features of [Topic]")
        h2_suggestions.append("How [Topic] Works — Step-by-Step")

    if eeat_dims.get("E", 100) < 70:
        h2_suggestions.append("Why Trust [Brand/Author] on [Topic]")
        h2_suggestions.append("Frequently Asked Questions")

    if eeat_dims.get("O", 100) < 70:
        h2_suggestions.append("[Year] Data & Statistics on [Topic]")
        h2_suggestions.append("Expert Insights: [Quote or Research]")

    if eeat_dims.get("R", 100) < 70:
        h2_suggestions.append("Who is [Topic] For?")
        h2_suggestions.append("Comparison: [Topic] vs Alternatives")

    # Always useful
    h2_suggestions.append("How to Get Started with [Topic]")
    h2_suggestions.append("Bottom Line: Is [Topic] Right for You?")

    # ── Schema to add ──
    existing_schema_types = modules.get("schema", {}).get("types", [])
    schema_to_add = []
    for t in ["FAQPage", "HowTo", "Article", "BreadcrumbList", "Organization"]:
        if not any(t.lower() in s.lower() for s in existing_schema_types):
            schema_to_add.append(t)

    # ── GEO optimization recommendations ──
    geo_score = modules.get("geo_aeo", {}).get("score", 100)
    geo_actions = []
    if geo_score < 80:
        geo_actions.append("Add a direct answer in the first paragraph (AI Overviews pull from first 100 words)")
        geo_actions.append("Include definition-style sentences: '[Topic] is...' / '[Topic] refers to...'")
        geo_actions.append("Add author attribution with credentials to every article")
        geo_actions.append("Create /llms.txt with content permissions for AI crawlers")
    if geo_score < 60:
        geo_actions.append("Restructure content into Q&A format — at least 5 direct questions answered")
        geo_actions.append("Add specific numbers, dates, and named sources throughout")

    # ── Missing on-page elements ──
    missing = []
    for mod_key, label in [
        ("title", "Optimized title tag (50–60 chars)"),
        ("meta_description", "Meta description (120–160 chars)"),
        ("images", "Alt text on all images"),
        ("schema", "JSON-LD schema markup"),
        ("open_graph", "Open Graph tags"),
    ]:
        mod = modules.get(mod_key, {})
        if mod.get("score", 100) < 80:
            missing.append(label)

    # ── Priority actions ──
    priority_actions = []
    for issue in audit_results.get("all_issues", []):
        if issue["severity"] == "critical":
            priority_actions.append(f"[CRITICAL] {issue['msg']}")
    for issue in audit_results.get("all_issues", []):
        if issue["severity"] == "warning":
            priority_actions.append(f"[WARNING] {issue['msg']}")
            if len(priority_actions) >= 8:
                break

    return {
        "url": url,
        "current_h1": h1,
        "primary_keyword": primary_kw or "(Set after keyword research)",
        "secondary_keywords": secondary_kws or ["(Add from keyword research)"],
        "lsi_terms": lsi_terms or ["(Add semantic variants)"],
        "current_word_count": wc,
        "target_word_count": target_wc,
        "recommended_h2_structure": h2_suggestions[:8],
        "schema_to_implement": schema_to_add[:5],
        "geo_optimizations": geo_actions,
        "missing_elements": missing,
        "priority_actions": priority_actions[:10],
        "eeat_scores": eeat_dims,
        "content_grade": eeat_result.get("grade", "N/A"),
        "eeat_total": eeat_result.get("total_score", 0),
    }
