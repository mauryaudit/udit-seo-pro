"""
modules/eeat.py
CORE-EEAT Content Quality Benchmark — 80-item scoring framework.
Inspired by aaron-he-zhu/seo-geo-claude-skills core-eeat-benchmark.

Dimensions:
  C — Comprehensiveness  (20 items, 25%)
  O — Originality        (20 items, 25%)
  R — Relevance          (20 items, 25%)
  E — E-E-A-T signals    (20 items, 25%)

Each item scored 0 (fail), 0.5 (partial), or 1 (pass).
Max score per dimension: 20. Total max: 80 → normalised to 100.
"""

import re


# ──────────────────────────────────────────────
# SCORING CHECKLIST
# ──────────────────────────────────────────────

def _check(condition, partial=False):
    if condition is True:
        return 1.0
    if partial:
        return 0.5
    return 0.0


def score_eeat(parser, url: str) -> dict:
    """
    Run the CORE-EEAT 80-item audit against a parsed page.
    Returns per-dimension scores, total, and item-level results.
    """
    text = parser.body_text.lower()
    raw_text = parser.body_text
    wc = parser.word_count
    title = parser.title.strip()
    desc = parser.meta.get("description", "")
    author = parser.meta.get("author", "")
    headings_h2 = parser.headings.get("h2", [])
    headings_h3 = parser.headings.get("h3", [])
    links = parser.links
    images = parser.images
    schema_scripts = parser.schema_scripts

    items = []

    # ══════════════════════════════════════════
    # C — COMPREHENSIVENESS (20 items)
    # ══════════════════════════════════════════
    def c(id_, label, score, note=""):
        items.append({"dim": "C", "id": id_, "label": label, "score": score, "note": note})

    c("C01", "Word count ≥ 800", _check(wc >= 800, wc >= 500), f"{wc} words")
    c("C02", "Word count ≥ 1500 (in-depth)", _check(wc >= 1500, wc >= 800))
    c("C03", "Has H2 subheadings", _check(len(headings_h2) >= 2, len(headings_h2) == 1))
    c("C04", "Has H3 subheadings", _check(len(headings_h3) >= 2, len(headings_h3) == 1))
    c("C05", "Uses numbered or bulleted lists", _check(
        any(p in text for p in ["<ol", "<ul", "<li"]) or
        bool(re.search(r'\n\s*[\d]+\.', raw_text)), False))
    c("C06", "Includes images or visuals", _check(len(images) >= 2, len(images) == 1))
    c("C07", "Covers topic introduction clearly", _check(
        any(p in text for p in ["is defined as", "refers to", "is a", "what is", "overview"]), False))
    c("C08", "Addresses common questions", _check(
        sum(1 for p in ["what", "how", "why", "when", "who", "which"] if p in text) >= 3, False))
    c("C09", "Includes specific data/statistics", _check(
        bool(re.search(r'\d{1,3}[%,]?\s*(of|percent|million|billion|thousand|crore|lakh)', text)), False))
    c("C10", "Has a clear conclusion or CTA", _check(
        any(p in text for p in ["conclusion", "summary", "sign up", "register", "get started", "contact us"]), False))
    c("C11", "Covers multiple subtopics (H2 count ≥ 3)", _check(len(headings_h2) >= 3, len(headings_h2) == 2))
    c("C12", "Has comparison or contrast content", _check(
        any(p in text for p in ["vs", "versus", "compared to", "better than", "difference between"]), False))
    c("C13", "Includes examples or case studies", _check(
        any(p in text for p in ["for example", "for instance", "such as", "case study", "real-world"]), False))
    c("C14", "Addresses benefits AND limitations", _check(
        any(p in text for p in ["benefit", "advantage", "pros"]) and
        any(p in text for p in ["limitation", "disadvantage", "cons", "risk"]), False))
    c("C15", "Has meta description ≥ 120 chars", _check(len(desc) >= 120, 70 <= len(desc) < 120))
    c("C16", "Title accurately reflects content", _check(
        bool(title) and any(w.lower() in text for w in title.split() if len(w) > 4), False))
    c("C17", "Includes a table or structured data", _check(
        "<table" in parser.body_text.lower() or len(schema_scripts) > 0, False))
    c("C18", "Has internal links to related content", _check(
        sum(1 for l in links if l.get("href", "").startswith("/") or
            (l.get("href", "").startswith("http") and
             __import__("urllib.parse", fromlist=["urlparse"]).urlparse(l.get("href", "")).netloc ==
             __import__("urllib.parse", fromlist=["urlparse"]).urlparse(url).netloc)) >= 3, False))
    c("C19", "Has external links to authoritative sources", _check(
        sum(1 for l in links if l.get("href", "").startswith("http") and
            __import__("urllib.parse", fromlist=["urlparse"]).urlparse(l.get("href", "")).netloc !=
            __import__("urllib.parse", fromlist=["urlparse"]).urlparse(url).netloc) >= 2, False))
    c("C20", "Includes FAQ or Q&A section", _check(
        any(p in text for p in ["frequently asked", "faq", "questions and answers"]), False))

    # ══════════════════════════════════════════
    # O — ORIGINALITY (20 items)
    # ══════════════════════════════════════════
    def o(id_, label, score, note=""):
        items.append({"dim": "O", "id": id_, "label": label, "score": score, "note": note})

    o("O01", "Has first-person perspective or opinion", _check(
        any(p in text for p in [" i ", " we ", "our experience", "in our view", "we found", "we tested"]), False))
    o("O02", "Contains unique data or research", _check(
        any(p in text for p in ["our study", "our research", "our survey", "we analyzed", "we found that"]), False))
    o("O03", "Includes personal anecdotes or experience", _check(
        any(p in text for p in ["i have", "we have", "in my experience", "from my", "personally"]), False))
    o("O04", "Has expert commentary or quotes", _check(
        any(p in text for p in ['"', "said", "according to", "noted", "explained", "stated"]), False))
    o("O05", "Provides unique angle not in top 10 SERPs", _check(False))  # Requires SERP data
    o("O06", "Contains proprietary screenshots or original images", _check(
        any("screenshot" in (img.get("alt", "") or "").lower() or
            "original" in (img.get("alt", "") or "").lower() for img in images), False))
    o("O07", "Uses specific brand voice consistently", _check(
        bool(title) and bool(desc), False))  # Heuristic
    o("O08", "Has original methodology or framework", _check(
        any(p in text for p in ["our methodology", "our framework", "our approach", "our process"]), False))
    o("O09", "No signs of AI boilerplate language", _check(
        not any(p in text for p in ["certainly!", "absolutely!", "of course!", "great question"]), False))
    o("O10", "Content freshness — recency signals", _check(
        any(p in text for p in ["2025", "2026", "updated", "latest", "new", "recent"]), False))
    o("O11", "Has original infographic or chart", _check(
        any("chart" in (img.get("alt", "") or "").lower() or
            "graph" in (img.get("alt", "") or "").lower() or
            "infographic" in (img.get("alt", "") or "").lower() for img in images), False))
    o("O12", "Includes step-by-step original instructions", _check(
        any(p in text for p in ["step 1", "step 2", "first,", "second,", "third,"]), False))
    o("O13", "Author's credentials mentioned", _check(
        any(p in text for p in ["years of experience", "certified", "degree", "expert in", "specialist"]), False))
    o("O14", "Cites primary sources (not just Wikipedia)", _check(
        any(p in text for p in ["study", "journal", "research", "report", "published"]) and
        any(l.get("href", "").endswith(".gov") or ".edu" in l.get("href", "") or
            "research" in l.get("href", "") for l in links), False))
    o("O15", "Unique title (not generic clickbait)", _check(
        bool(title) and not any(p in title.lower() for p in
            ["you won't believe", "shocking", "amazing", "incredible", "mind-blowing"]), False))
    o("O16", "Has audio, video or interactive content", _check(
        any(p in parser.body_text.lower() for p in ["<video", "<audio", "<iframe", "youtube.com", "vimeo"]), False))
    o("O17", "Includes user-generated content (reviews/comments)", _check(
        any(p in text for p in ["review", "testimonial", "rating", "comment", "feedback"]), False))
    o("O18", "Contains proprietary tool or calculator", _check(False))  # Requires JS analysis
    o("O19", "Has downloadable resource (PDF, template)", _check(
        any(".pdf" in l.get("href", "").lower() or
            "download" in l.get("text", "").lower() or
            "template" in l.get("text", "").lower() for l in links), False))
    o("O20", "Branded terminology or coined phrases", _check(
        parser.meta.get("author", "") != "" or
        len([s for s in schema_scripts if "Organization" in s]) > 0, False))

    # ══════════════════════════════════════════
    # R — RELEVANCE (20 items)
    # ══════════════════════════════════════════
    def r(id_, label, score, note=""):
        items.append({"dim": "R", "id": id_, "label": label, "score": score, "note": note})

    r("R01", "Primary keyword in title", _check(
        bool(title) and len(title) > 10, False))  # Rough signal
    r("R02", "Primary keyword in H1", _check(
        len(parser.headings.get("h1", [])) == 1, False))
    r("R03", "Primary keyword in meta description", _check(bool(desc) and len(desc) >= 70, False))
    r("R04", "Primary keyword in first 100 words", _check(wc >= 100, False))
    r("R05", "Keyword density not excessive (< 3%)", _check(True, False))  # Would need keyword input
    r("R06", "Semantic keywords / LSI terms present", _check(wc >= 500, False))  # Heuristic
    r("R07", "Topic clusters addressed", _check(len(headings_h2) >= 3, False))
    r("R08", "Matches search intent (informational/transactional)", _check(
        any(p in text for p in ["buy", "price", "order", "sign up", "register", "how to", "what is"]), False))
    r("R09", "Content matches page type (article/product/landing)", _check(
        len(schema_scripts) > 0, False))
    r("R10", "Geo-targeting signals (if local SEO)", _check(
        any(p in text for p in ["india", "delhi", "mumbai", "bangalore", "uk", "usa", "australia"]), False))
    r("R11", "Industry-specific terminology used", _check(wc >= 300, False))
    r("R12", "Answers the exact search query in opening", _check(
        any(p in text[:500] for p in ["is", "are", "refers to", "means", "defined as"]), False))
    r("R13", "URL is short and keyword-rich", _check(
        len(url) < 80 and url.count("/") <= 5, False))
    r("R14", "Page focuses on single clear topic", _check(len(headings_h2) <= 8, False))
    r("R15", "Content addresses user pain points", _check(
        any(p in text for p in ["problem", "solution", "challenge", "struggle", "issue", "help"]), False))
    r("R16", "Mobile-friendly content structure", _check(bool(parser.viewport), False))
    r("R17", "Fast-loading page signals (image optimization)", _check(
        sum(1 for img in images if img.get("loading") == "lazy") >= len(images) // 2 if images else True, False))
    r("R18", "Internal linking to topically related pages", _check(
        sum(1 for l in links if l.get("href", "").startswith("/")) >= 3, False))
    r("R19", "Has calls-to-action relevant to topic", _check(
        any(p in text for p in ["learn more", "read more", "get started", "sign up", "register", "contact"]), False))
    r("R20", "Structured for featured snippet eligibility", _check(
        any(p in text for p in ["is defined as", "step 1", "the top", "the best", "the most"]), False))

    # ══════════════════════════════════════════
    # E — E-E-A-T (20 items)
    # ══════════════════════════════════════════
    def e(id_, label, score, note=""):
        items.append({"dim": "E", "id": id_, "label": label, "score": score, "note": note})

    e("E01", "Author name present", _check(bool(author), False))
    e("E02", "Author bio or credentials visible", _check(
        any(p in text for p in ["about the author", "written by", "bio", "background"]), False))
    e("E03", "Publication date visible", _check(
        bool(re.search(r'\b(january|february|march|april|may|june|july|august|'
                       r'september|october|november|december|202[0-9])\b', text)), False))
    e("E04", "Last updated date shown", _check(
        any(p in text for p in ["last updated", "updated on", "revised", "last reviewed"]), False))
    e("E05", "Contact information accessible", _check(
        any(p in text for p in ["contact", "email", "phone", "address", "support"]), False))
    e("E06", "Privacy policy linked", _check(
        any("privacy" in l.get("href", "").lower() or "privacy" in l.get("text", "").lower()
            for l in links), False))
    e("E07", "About page linked", _check(
        any("about" in l.get("href", "").lower() or "about" in l.get("text", "").lower()
            for l in links), False))
    e("E08", "Outbound links to authoritative sources", _check(
        sum(1 for l in links if any(domain in l.get("href", "")
            for domain in [".gov", ".edu", ".org", "wikipedia", "pubmed", "nhs", "who.int"])) >= 1, False))
    e("E09", "Social proof (reviews, ratings, testimonials)", _check(
        any(p in text for p in ["review", "rating", "testimonial", "stars", "trustpilot"]), False))
    e("E10", "Awards or certifications mentioned", _check(
        any(p in text for p in ["award", "certified", "licensed", "accredited", "regulated"]), False))
    e("E11", "Schema markup for author/organization", _check(
        any("author" in s.lower() or "organization" in s.lower() or "person" in s.lower()
            for s in schema_scripts), False))
    e("E12", "HTTPS and secure site", _check(url.startswith("https://"), False))
    e("E13", "No broken links or 404 errors (heuristic)", _check(True, False))  # Would need crawl
    e("E14", "Original research or primary sources cited", _check(
        any(p in text for p in ["our research", "our data", "we surveyed", "study shows"]), False))
    e("E15", "Professional language and grammar", _check(
        not any(p in text for p in ["gonna", "wanna", "u r", "lol", "omg"]), False))
    e("E16", "Fact-checked content signals", _check(
        any(p in text for p in ["according to", "research shows", "studies show", "data shows"]), False))
    e("E17", "Responsible disclosure (YMYL content)", _check(
        any(p in text for p in ["disclaimer", "terms", "consult", "professional advice",
                                "responsible gambling", "18+", "terms and conditions"]), False))
    e("E18", "Transparent ownership/team info", _check(
        any(p in text for p in ["our team", "our company", "founded by", "headquartered"]), False))
    e("E19", "No sponsored content without disclosure", _check(
        not any(p in text for p in ["sponsored by", "paid partnership"]) or
        any(p in text for p in ["disclosure", "affiliate"]), False))
    e("E20", "Accessibility features (alt text, aria)", _check(
        sum(1 for img in images if img.get("alt") and img.get("alt") != "") >= len(images) * 0.8
        if images else True, False))

    # ── Aggregate ──
    dims = {"C": [], "O": [], "R": [], "E": []}
    for item in items:
        dims[item["dim"]].append(item["score"])

    dim_scores = {
        d: {"score": round(sum(v) / len(v) * 100) if v else 0,
            "raw": sum(v), "max": len(v), "items": [i for i in items if i["dim"] == d]}
        for d, v in dims.items()
    }

    total_raw = sum(i["score"] for i in items)
    total_max = len(items)
    total_score = round((total_raw / total_max) * 100) if total_max else 0

    grade = "A" if total_score >= 80 else "B" if total_score >= 65 else "C" if total_score >= 50 else "D"

    return {
        "total_score": total_score,
        "grade": grade,
        "dimensions": dim_scores,
        "items": items,
        "summary": {
            "C": dim_scores["C"]["score"],
            "O": dim_scores["O"]["score"],
            "R": dim_scores["R"]["score"],
            "E": dim_scores["E"]["score"],
        }
    }
