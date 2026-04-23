"""
modules/audits.py
All on-page + technical + content + GEO audit modules.
Each returns: { score, issues: [{severity, msg}], passes: [str], ...data }
"""

import json
import re
import urllib.parse
from modules.crawler import fetch, fetch_head, SEOParser


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def _issue(severity, msg):
    return {"severity": severity, "msg": msg}


def _base(url):
    p = urllib.parse.urlparse(url)
    return f"{p.scheme}://{p.netloc}"


# ══════════════════════════════════════════════
# 1. TITLE
# ══════════════════════════════════════════════

def audit_title(parser, url):
    title = parser.title.strip()
    issues, passes, score = [], [], 100

    if not title:
        issues.append(_issue("critical", "Missing <title> tag — critical for SEO"))
        score -= 40
    else:
        ln = len(title)
        if ln < 30:
            issues.append(_issue("warning", f"Title too short ({ln} chars). Optimal: 50–60 chars."))
            score -= 15
        elif ln > 60:
            issues.append(_issue("warning", f"Title too long ({ln} chars). Google truncates at ~60."))
            score -= 10
        else:
            passes.append(f"Title length optimal: {ln} chars")

        if title.upper() == title:
            issues.append(_issue("warning", "Title is all-caps — looks spammy to search engines"))
            score -= 5

        kw_count = sum(1 for w in title.lower().split() if len(w) > 3)
        if kw_count >= 2:
            passes.append(f"Title contains keyword-length words: {kw_count}")

    return {"title": title, "score": max(0, score), "issues": issues, "passes": passes}


# ══════════════════════════════════════════════
# 2. META DESCRIPTION
# ══════════════════════════════════════════════

def audit_meta_description(parser):
    desc = parser.meta.get("description", "").strip()
    issues, passes, score = [], [], 100

    if not desc:
        issues.append(_issue("critical", "Missing meta description — directly affects click-through rate"))
        score -= 40
    else:
        ln = len(desc)
        if ln < 70:
            issues.append(_issue("warning", f"Meta description short ({ln} chars). Aim for 120–160."))
            score -= 15
        elif ln > 160:
            issues.append(_issue("warning", f"Meta description too long ({ln} chars). Will be truncated in SERPs."))
            score -= 10
        else:
            passes.append(f"Meta description length optimal: {ln} chars")

        if desc.lower().count(desc.split()[0].lower()) > 3 if desc.split() else False:
            issues.append(_issue("info", "Possible keyword stuffing in meta description"))
            score -= 5

    return {"description": desc[:200] if desc else "", "score": max(0, score), "issues": issues, "passes": passes}


# ══════════════════════════════════════════════
# 3. HEADINGS
# ══════════════════════════════════════════════

def audit_headings(parser):
    issues, passes, score = [], [], 100
    h1s = parser.headings["h1"]
    h2s = parser.headings["h2"]
    h3s = parser.headings["h3"]

    if not h1s:
        issues.append(_issue("critical", "No H1 tag found — every page needs exactly one H1"))
        score -= 30
    elif len(h1s) > 1:
        issues.append(_issue("warning", f"Multiple H1 tags ({len(h1s)}) — use only one per page"))
        score -= 15
    else:
        ln = len(h1s[0])
        passes.append(f"Single H1 found: \"{h1s[0][:80]}\"")
        if ln > 70:
            issues.append(_issue("info", f"H1 is long ({ln} chars) — consider tightening to <70 chars"))
            score -= 5

    if not h2s:
        issues.append(_issue("warning", "No H2 tags — subheadings improve structure and scanning"))
        score -= 10
    else:
        passes.append(f"{len(h2s)} H2 subheadings found")

    if h3s:
        passes.append(f"{len(h3s)} H3 tags found")

    total_h = sum(len(v) for v in parser.headings.values())
    if total_h > 30:
        issues.append(_issue("info", f"High heading count ({total_h}) — ensure logical hierarchy"))

    return {
        "h1_count": len(h1s), "h1_texts": h1s,
        "h2_count": len(h2s), "h3_count": len(h3s),
        "total_headings": total_h,
        "score": max(0, score), "issues": issues, "passes": passes
    }


# ══════════════════════════════════════════════
# 4. CONTENT QUALITY (CORE-EEAT signals)
# ══════════════════════════════════════════════

def audit_content(parser, url):
    issues, passes, score = [], [], 100
    text = parser.body_text
    wc = parser.word_count

    # Word count
    if wc < 300:
        issues.append(_issue("critical", f"Thin content: {wc} words. Minimum 600 words recommended."))
        score -= 30
    elif wc < 600:
        issues.append(_issue("warning", f"Low word count: {wc} words. Aim for 800+ for competitive topics."))
        score -= 15
    elif wc > 500:
        passes.append(f"Good content depth: {wc} words")

    # Experience/Expertise signals
    if parser.meta.get("author"):
        passes.append(f"Author attribution present: {parser.meta['author']} (E-E-A-T signal)")
    else:
        issues.append(_issue("info", "No author attribution — weakens E-E-A-T for AI/search"))
        score -= 5

    # Q&A patterns (GEO / AEO signal)
    q_patterns = ["what is", "how to", "why does", "when should", "who is", "which", "what are", "how do"]
    q_count = sum(1 for p in q_patterns if p in text.lower())
    if q_count >= 3:
        passes.append(f"Strong Q&A content signals ({q_count} patterns) — good for AI citations")
    else:
        issues.append(_issue("info", "Low Q&A patterns — AI engines favor direct question-answers"))
        score -= 5

    # Reading level / sentences
    sentences = len(re.findall(r'[.!?]+', text))
    if sentences > 0 and wc > 0:
        avg_sentence = wc / sentences
        if avg_sentence > 25:
            issues.append(_issue("info", f"Average sentence length is long ({avg_sentence:.0f} words) — aim for <20"))
            score -= 5
        else:
            passes.append(f"Good sentence length: ~{avg_sentence:.0f} words average")

    # Duplicate/thin signals
    if parser.meta.get("keywords"):
        issues.append(_issue("info", "Meta keywords tag found — Google ignores it, may hint keyword stuffing"))

    return {
        "word_count": wc,
        "author": parser.meta.get("author", ""),
        "score": max(0, score), "issues": issues, "passes": passes
    }


# ══════════════════════════════════════════════
# 5. IMAGES
# ══════════════════════════════════════════════

def audit_images(parser):
    images = parser.images
    issues, passes, score = [], [], 100
    missing_alt, empty_alt, no_dims, no_lazy, no_srcset = [], [], [], [], []

    for img in images:
        src = img["src"]
        if img["alt"] is None:
            missing_alt.append(src)
        elif img["alt"] == "":
            empty_alt.append(src)
        if not img["width"] or not img["height"]:
            no_dims.append(src)
        if img["loading"] != "lazy":
            no_lazy.append(src)
        if not img["srcset"]:
            no_srcset.append(src)

    total = len(images)
    if total == 0:
        passes.append("No images found on page (N/A)")
    else:
        if missing_alt:
            issues.append(_issue("critical", f"{len(missing_alt)}/{total} images missing alt attribute (accessibility + SEO)"))
            score -= min(40, len(missing_alt) * 8)
        else:
            passes.append("All images have alt attributes")

        if empty_alt:
            issues.append(_issue("warning", f"{len(empty_alt)}/{total} images have empty alt text — OK for decorative only"))
            score -= 5

        if no_dims:
            issues.append(_issue("warning", f"{len(no_dims)}/{total} images missing width/height — causes Cumulative Layout Shift (CLS)"))
            score -= 10

        if no_lazy:
            issues.append(_issue("info", f"{len(no_lazy)}/{total} images missing loading='lazy'"))
            score -= 5

        if len(no_srcset) > total // 2:
            issues.append(_issue("info", f"{len(no_srcset)}/{total} images missing srcset — responsive images recommended"))
            score -= 5

    return {
        "total": total,
        "missing_alt_count": len(missing_alt),
        "missing_alt_examples": missing_alt[:5],
        "no_dimensions_count": len(no_dims),
        "score": max(0, score), "issues": issues, "passes": passes
    }


# ══════════════════════════════════════════════
# 6. SCHEMA MARKUP
# ══════════════════════════════════════════════

def audit_schema(parser):
    scripts = parser.schema_scripts
    issues, passes, score = [], [], 60
    found_types, invalid = [], []

    if not scripts:
        issues.append(_issue("warning", "No JSON-LD schema markup found — strongly recommended"))
    else:
        for s in scripts:
            try:
                data = json.loads(s)
                # Handle top-level array e.g. [{...}, {...}]
                if isinstance(data, list):
                    items = data
                elif "@graph" in data and isinstance(data["@graph"], list):
                    items = data["@graph"]
                else:
                    items = [data]
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    t = item.get("@type", item.get("type", "Unknown"))
                    if isinstance(t, list):
                        t = ", ".join(str(x) for x in t)
                    elif not isinstance(t, str):
                        t = str(t)
                    found_types.append(t)
                    score += 5
            except json.JSONDecodeError:
                invalid.append("Invalid JSON-LD block")
                score -= 10

        if found_types:
            passes.append(f"Found {len(scripts)} JSON-LD block(s): {', '.join(found_types)}")

        all_types = " ".join(found_types).lower()
        for rec, desc in [
            ("organization", "brand identity for knowledge graph"),
            ("website", "sitelinks search box"),
            ("breadcrumb", "breadcrumb rich results"),
            ("faqpage", "FAQ rich results (healthcare/gov only now)"),
        ]:
            if rec not in all_types:
                issues.append(_issue("info", f"Consider adding {rec.title()} schema ({desc})"))
            else:
                passes.append(f"{rec.title()} schema present")

    if invalid:
        issues.append(_issue("critical", f"{len(invalid)} invalid JSON-LD block(s) — fix malformed markup"))
        score -= 20

    return {
        "count": len(scripts), "types": found_types,
        "score": min(100, max(0, score)), "issues": issues, "passes": passes
    }


# ══════════════════════════════════════════════
# 7. TECHNICAL SEO
# ══════════════════════════════════════════════

def audit_technical(parser, response, url):
    issues, passes, score = [], [], 100
    headers = {k.lower(): v for k, v in response.get("headers", {}).items()}

    # HTTPS
    if url.startswith("https://"):
        passes.append("HTTPS enabled — secure connection")
    else:
        issues.append(_issue("critical", "Not using HTTPS — Google penalizes non-HTTPS sites"))
        score -= 25

    # Canonical
    if parser.canonical:
        passes.append(f"Canonical set: {parser.canonical[:80]}")
        resolved_url = response.get("url", url)
        if parser.canonical != resolved_url and parser.canonical.rstrip("/") != resolved_url.rstrip("/"):
            issues.append(_issue("info", "Canonical URL differs from page URL — verify intentional"))
    else:
        issues.append(_issue("warning", "No canonical tag — add to prevent duplicate content issues"))
        score -= 10

    # Noindex
    if parser.noindex:
        issues.append(_issue("critical", "PAGE HAS NOINDEX DIRECTIVE — will NOT appear in search results!"))
        score -= 40
    elif parser.robots_meta:
        passes.append(f"Robots meta: {parser.robots_meta}")

    # Viewport
    if parser.viewport:
        passes.append(f"Viewport meta present: {parser.viewport}")
    else:
        issues.append(_issue("warning", "Missing viewport meta — page is not mobile-friendly"))
        score -= 15

    # Lang
    if parser.lang:
        passes.append(f"HTML lang declared: {parser.lang}")
    else:
        issues.append(_issue("warning", "Missing lang attribute on <html> — affects language targeting"))
        score -= 5

    # Charset
    if parser.charset:
        passes.append(f"Charset declared: {parser.charset}")
    else:
        issues.append(_issue("info", "Charset not explicitly declared"))

    # Security headers
    for h, desc in [
        ("strict-transport-security", "HSTS — forces HTTPS"),
        ("x-frame-options", "Clickjacking protection"),
        ("x-content-type-options", "MIME-sniffing protection"),
        ("content-security-policy", "Content Security Policy"),
        ("permissions-policy", "Permissions Policy"),
    ]:
        if h in headers:
            passes.append(f"Security header present: {h}")
        else:
            issues.append(_issue("info", f"Missing security header: {h} ({desc})"))

    # TTFB
    ttfb = response.get("ttfb_ms", 0)
    if ttfb > 0:
        if ttfb < 800:
            passes.append(f"TTFB: {ttfb}ms (good — under 800ms)")
        elif ttfb < 1800:
            issues.append(_issue("warning", f"TTFB: {ttfb}ms — borderline slow, aim for <800ms"))
            score -= 10
        else:
            issues.append(_issue("critical", f"TTFB: {ttfb}ms — very slow, major Core Web Vitals issue"))
            score -= 20

    # Page size
    size = response.get("size_bytes", 0)
    if size > 0:
        if size < 100_000:
            passes.append(f"Page size: {size//1000}KB (good, under 100KB)")
        elif size < 200_000:
            issues.append(_issue("info", f"Page size: {size//1000}KB — aim for under 100KB HTML"))
            score -= 5
        else:
            issues.append(_issue("warning", f"Page size: {size//1000}KB — large page, affects load speed"))
            score -= 10

    # Hreflang
    if parser.hreflangs:
        passes.append(f"{len(parser.hreflangs)} hreflang tags found (international targeting)")
    
    return {
        "ttfb_ms": ttfb,
        "page_size_bytes": size,
        "hreflang_count": len(parser.hreflangs),
        "score": max(0, score), "issues": issues, "passes": passes
    }


# ══════════════════════════════════════════════
# 8. OPEN GRAPH / SOCIAL
# ══════════════════════════════════════════════

def audit_open_graph(parser):
    issues, passes, score = [], [], 100
    og, tw = parser.og, parser.twitter

    for key, desc in [
        ("title", "Controls headline in social previews"),
        ("description", "Controls summary in social previews"),
        ("image", "Controls image in social previews — 1200x630px recommended"),
        ("url", "Canonical URL for social sharing"),
        ("type", "Content type (website / article / product)"),
    ]:
        if key in og:
            passes.append(f"og:{key} set")
        else:
            sev = "warning" if key in ["title", "description", "image"] else "info"
            issues.append(_issue(sev, f"Missing og:{key} — {desc}"))
            score -= 12 if sev == "warning" else 5

    if og.get("image"):
        passes.append("OG image present — social cards will work")

    if tw.get("card"):
        passes.append(f"Twitter card type: {tw['card']}")
    else:
        issues.append(_issue("info", "Missing twitter:card — set to 'summary_large_image' for best previews"))
        score -= 5

    if not tw.get("title") and not tw.get("site"):
        issues.append(_issue("info", "No twitter:title or twitter:site — add for Twitter/X optimization"))
        score -= 5

    return {
        "og": og, "twitter": tw,
        "score": max(0, score), "issues": issues, "passes": passes
    }


# ══════════════════════════════════════════════
# 9. LINKS
# ══════════════════════════════════════════════

def audit_links(parser, base_url):
    issues, passes, score = [], [], 100
    base_domain = urllib.parse.urlparse(base_url).netloc.replace("www.", "")
    internal, external, nofollow_external, broken_anchors = [], [], [], []

    for link in parser.links:
        href = link.get("href", "")
        rel = link.get("rel", "")
        text = link.get("text", "").strip()

        if not href or href.startswith("javascript:") or href.startswith("mailto:") or href == "#":
            if not text:
                broken_anchors.append(href)
            continue

        parsed = urllib.parse.urlparse(href)
        link_domain = parsed.netloc.replace("www.", "")

        if not link_domain or link_domain == base_domain:
            internal.append({"href": href, "text": text, "rel": rel})
        else:
            external.append({"href": href, "text": text, "rel": rel})
            if "nofollow" in rel:
                nofollow_external.append(href)

    # Internal link health
    if len(internal) == 0:
        issues.append(_issue("warning", "No internal links found — weak internal linking structure"))
        score -= 20
    elif len(internal) < 3:
        issues.append(_issue("warning", f"Only {len(internal)} internal links — add more for better crawlability"))
        score -= 10
    else:
        passes.append(f"{len(internal)} internal links found")

    # Anchor text quality
    generic_anchors = ["click here", "read more", "here", "link", "more"]
    bad_anchors = [l for l in internal if l["text"].lower() in generic_anchors]
    if bad_anchors:
        issues.append(_issue("info", f"{len(bad_anchors)} links with generic anchor text ('click here', 'read more') — use descriptive anchors"))
        score -= 5

    # External links
    passes.append(f"{len(external)} external links found")
    if nofollow_external:
        passes.append(f"{len(nofollow_external)} external links are nofollowed")

    if parser.hreflangs:
        passes.append(f"{len(parser.hreflangs)} hreflang links (international SEO)")

    return {
        "internal_count": len(internal),
        "external_count": len(external),
        "nofollow_count": len(nofollow_external),
        "hreflang_count": len(parser.hreflangs),
        "score": max(0, score), "issues": issues, "passes": passes
    }


# ══════════════════════════════════════════════
# 10. ROBOTS.TXT
# ══════════════════════════════════════════════

def audit_robots_txt(url):
    issues, passes, score = [], [], 100
    robots_url = _base(url) + "/robots.txt"
    resp = fetch(robots_url)

    if not resp["ok"]:
        issues.append(_issue("warning", f"robots.txt not found or inaccessible (status: {resp['status']})"))
        score -= 20
        return {"found": False, "sitemap_mentioned": False, "score": score, "issues": issues, "passes": passes}

    text = resp["text"].lower()
    passes.append("robots.txt found and accessible")

    if "sitemap:" in text:
        passes.append("Sitemap directive present in robots.txt")
    else:
        issues.append(_issue("info", "Add Sitemap: directive to robots.txt for better discovery"))
        score -= 5

    lines = [l.strip() for l in resp["text"].split("\n")]
    ua_star = False
    blanket_block = False
    for line in lines:
        if line.lower() == "user-agent: *":
            ua_star = True
        if ua_star and line.lower() == "disallow: /":
            blanket_block = True
            break

    if blanket_block:
        issues.append(_issue("critical", "robots.txt has 'Disallow: /' for all agents — SITE IS BLOCKED FROM GOOGLE!"))
        score -= 50
    else:
        passes.append("robots.txt is not blocking all crawlers")

    # Check for important paths
    for path in ["/wp-admin", "/admin", "/login", "/?s="]:
        if path in resp["text"]:
            passes.append(f"Disallow rule found for {path} (good)")

    return {
        "found": True,
        "sitemap_mentioned": "sitemap:" in text,
        "blanket_block": blanket_block,
        "snippet": resp["text"][:400],
        "score": max(0, score), "issues": issues, "passes": passes
    }


# ══════════════════════════════════════════════
# 11. SITEMAP
# ══════════════════════════════════════════════

def audit_sitemap(url):
    issues, passes, score = [], [], 100
    sitemap_url = _base(url) + "/sitemap.xml"
    resp = fetch(sitemap_url, timeout=10)

    if not resp["ok"]:
        issues.append(_issue("warning", "sitemap.xml not found at default location — submit one to GSC"))
        score -= 20
        return {"found": False, "url_count": 0, "score": score, "issues": issues, "passes": passes}

    text = resp["text"]
    passes.append("sitemap.xml found and accessible")

    url_count = max(text.lower().count("<url>"), text.lower().count("<loc>"))
    passes.append(f"Approximately {url_count} URLs in sitemap")

    if "sitemapindex" in text.lower():
        passes.append("Sitemap index file detected (multiple child sitemaps)")

    if "<lastmod>" not in text.lower():
        issues.append(_issue("info", "No <lastmod> in sitemap — add for better crawl prioritization"))
        score -= 5

    if "<priority>" not in text.lower():
        issues.append(_issue("info", "No <priority> values in sitemap — consider adding"))

    if "<changefreq>" not in text.lower():
        issues.append(_issue("info", "No <changefreq> in sitemap — consider adding for crawl hints"))

    if url_count > 50000:
        issues.append(_issue("warning", f"Sitemap has {url_count} URLs — split into multiple sitemaps (50K limit)"))
        score -= 10

    if url_count > 130000:
        issues.append(_issue("critical", f"Sitemap has {url_count} URLs — far exceeds 50K limit, causing crawl waste"))
        score -= 20

    return {
        "found": True, "url_count": url_count,
        "score": max(0, score), "issues": issues, "passes": passes
    }


# ══════════════════════════════════════════════
# 12. GEO / AEO (AI Search Optimization)
# ══════════════════════════════════════════════

def audit_geo_aeo(parser, url):
    issues, passes, score = [], [], 100
    text = parser.body_text.lower()

    # llms.txt
    llms_resp = fetch_head(_base(url) + "/llms.txt")
    if llms_resp.get("ok") and llms_resp["status"] == 200:
        passes.append("llms.txt found — AI crawlers have access instructions")
    else:
        issues.append(_issue("info", "No llms.txt found — add /llms.txt to guide AI crawlers (Anthropic, OpenAI, Perplexity)"))
        score -= 5

    # ai.txt
    ai_resp = fetch_head(_base(url) + "/ai.txt")
    if ai_resp.get("ok") and ai_resp["status"] == 200:
        passes.append("ai.txt found")
    else:
        issues.append(_issue("info", "No ai.txt found — emerging standard for AI permissions"))
        score -= 3

    # Q&A patterns (directly answerable questions)
    q_patterns = ["what is", "how to", "why does", "when should", "who is", "which is", "what are", "how do", "can you", "should i"]
    found_q = sum(1 for q in q_patterns if q in text)
    if found_q >= 4:
        passes.append(f"Strong conversational Q&A content ({found_q} patterns) — high AI citation potential")
    elif found_q >= 2:
        passes.append(f"Some Q&A content patterns ({found_q}) — good start for AEO")
    else:
        issues.append(_issue("warning", "Very low Q&A patterns — AI engines cite content with direct answers"))
        score -= 10

    # Factual density signals
    has_numbers = bool(re.search(r'\d+', text))
    if has_numbers:
        passes.append("Numerical data present — AI engines cite specific stats")
    else:
        issues.append(_issue("info", "No numerical data found — stats and specifics improve AI citations"))
        score -= 5

    # Schema
    if parser.schema_scripts:
        passes.append("Structured data present — improves AI engine entity understanding")
    else:
        issues.append(_issue("warning", "No schema markup — AI engines rely heavily on structured data for understanding"))
        score -= 10

    # Author
    if parser.meta.get("author"):
        passes.append(f"Author attribution: {parser.meta['author']} — strengthens E-E-A-T for AI citations")
    else:
        issues.append(_issue("info", "No author attribution — reduces likelihood of AI citation"))
        score -= 5

    # OG image for AI card rendering
    if parser.og.get("image"):
        passes.append("OG image present — AI-powered SERPs can display visual cards")
    else:
        issues.append(_issue("info", "No OG image — AI Overviews and social cards may lack visual"))
        score -= 3

    # Definition-style content (good for featured snippets + AI)
    definition_patterns = ["is defined as", "refers to", "is a type of", "is the process of", "means that"]
    found_def = sum(1 for p in definition_patterns if p in text)
    if found_def >= 2:
        passes.append("Definition-style content found — high featured snippet / AI overview potential")
    else:
        issues.append(_issue("info", "Add clear definition-style sentences (X is... / X refers to...) for AI overview eligibility"))
        score -= 5

    return {"score": min(100, max(0, score)), "issues": issues, "passes": passes}


# ══════════════════════════════════════════════
# 13. CORE WEB VITALS signals (from observable HTML)
# ══════════════════════════════════════════════

def audit_cwv_signals(parser, response):
    """
    We cannot measure CWV directly without a headless browser,
    but we can check all HTML-level signals that affect LCP/CLS/INP.
    """
    issues, passes, score = [], [], 100
    text = response.get("text", "")

    # LCP candidate — largest visible element hints
    has_hero_img = any(
        "hero" in ((img.get("src") or "") + (img.get("alt") or "") + (img.get("title") or "")).lower()
        for img in parser.images
    )
    if has_hero_img:
        passes.append("Hero image detected — ensure it has fetchpriority='high'")
        if "fetchpriority" not in text.lower():
            issues.append(_issue("warning", "Hero/LCP image likely missing fetchpriority='high' — slows LCP"))
            score -= 10

    # CLS — image dimensions
    no_dims = sum(1 for img in parser.images if not img["width"] or not img["height"])
    if no_dims:
        issues.append(_issue("warning", f"{no_dims} images missing width/height dimensions — causes layout shift (CLS)"))
        score -= min(20, no_dims * 5)
    else:
        passes.append("All images have width/height set — no CLS from images")

    # INP — heavy scripts
    script_count = text.lower().count("<script")
    if script_count > 20:
        issues.append(_issue("warning", f"{script_count} script tags — large number may increase INP (interaction delays)"))
        score -= 10
    elif script_count <= 10:
        passes.append(f"{script_count} script tags — reasonable JavaScript footprint")

    # Render-blocking CSS
    blocking_css = len(re.findall(r'<link[^>]+rel=["\']stylesheet["\'][^>]*>', text, re.I))
    if blocking_css > 3:
        issues.append(_issue("info", f"{blocking_css} render-blocking stylesheets — consider critical CSS inlining"))
        score -= 5

    # Font loading
    if "font-display" not in text.lower() and ("@font-face" in text.lower() or "fonts.googleapis" in text.lower()):
        issues.append(_issue("info", "Web fonts loaded without font-display — may cause flash of invisible text (FOIT)"))
        score -= 5

    # TTFB from response
    ttfb = response.get("ttfb_ms", 0)
    if ttfb > 0:
        if ttfb < 800:
            passes.append(f"TTFB: {ttfb}ms (good — indicates good server response for LCP)")
        else:
            issues.append(_issue("warning", f"TTFB: {ttfb}ms — slow server response directly impacts LCP"))
            score -= 15

    passes.append("Note: Full CWV measurement requires Google PageSpeed Insights or Chrome DevTools")

    return {"script_count": script_count, "score": max(0, score), "issues": issues, "passes": passes}


# ══════════════════════════════════════════════
# 14. MOBILE SEO
# ══════════════════════════════════════════════

def audit_mobile(parser, response):
    issues, passes, score = [], [], 100
    text = response.get("text", "")

    if parser.viewport:
        if "width=device-width" in parser.viewport:
            passes.append("Viewport contains width=device-width — mobile responsive")
        else:
            issues.append(_issue("warning", f"Viewport is set but missing width=device-width: {parser.viewport}"))
            score -= 15
    else:
        issues.append(_issue("critical", "No viewport meta tag — page will not render correctly on mobile"))
        score -= 30

    # Touch icons
    if "apple-touch-icon" in text.lower():
        passes.append("Apple touch icon found")
    else:
        issues.append(_issue("info", "No apple-touch-icon — add for iOS home screen bookmark"))
        score -= 3

    # Theme color
    if parser.meta.get("theme_color"):
        passes.append(f"Theme color defined: {parser.meta['theme_color']}")
    else:
        issues.append(_issue("info", "No theme-color meta — adds branded color to browser chrome on mobile"))
        score -= 3

    # Font size warning (can only hint)
    if "font-size: 10px" in text or "font-size:10px" in text:
        issues.append(_issue("warning", "Possible 10px font-size found — minimum 16px recommended for mobile"))
        score -= 10

    # Tap target sizes (hint)
    btn_count = text.lower().count("<button")
    link_count = len(parser.links)
    if btn_count + link_count > 50:
        issues.append(_issue("info", f"High interactive element count ({btn_count + link_count}) — verify tap targets are 44x44px min"))
        score -= 5

    return {"score": max(0, score), "issues": issues, "passes": passes}


# ══════════════════════════════════════════════
# 15. INTERNATIONAL SEO
# ══════════════════════════════════════════════

def audit_international(parser, url):
    issues, passes, score = [], [], 80  # default lower — most sites don't need this

    hreflangs = parser.hreflangs
    if not hreflangs:
        issues.append(_issue("info", "No hreflang tags — add if targeting multiple language/region markets"))
        return {"hreflang_count": 0, "score": score, "issues": issues, "passes": passes}

    passes.append(f"{len(hreflangs)} hreflang tags found")
    score = 100

    # Check for x-default
    xdefault = any(h["hreflang"] == "x-default" for h in hreflangs)
    if xdefault:
        passes.append("x-default hreflang present — correct fallback for unmatched locales")
    else:
        issues.append(_issue("warning", "Missing x-default hreflang — add for users in unmatched regions"))
        score -= 10

    # Check for self-referencing
    page_url = url
    self_ref = any(h["href"] == page_url or h["href"].rstrip("/") == page_url.rstrip("/") for h in hreflangs)
    if self_ref:
        passes.append("Self-referencing hreflang present (correct)")
    else:
        issues.append(_issue("warning", "No self-referencing hreflang on this page — Google requires it"))
        score -= 10

    # Language codes
    valid_lang_pattern = re.compile(r'^[a-z]{2}(-[A-Z]{2})?$|^x-default$')
    invalid_codes = [h["hreflang"] for h in hreflangs if not valid_lang_pattern.match(h["hreflang"])]
    if invalid_codes:
        issues.append(_issue("warning", f"Invalid hreflang codes: {', '.join(invalid_codes[:5])}"))
        score -= 15

    return {"hreflang_count": len(hreflangs), "has_xdefault": xdefault, "score": max(0, score), "issues": issues, "passes": passes}


# ══════════════════════════════════════════════
# 16. SECURITY
# ══════════════════════════════════════════════

def audit_security(response, url):
    issues, passes, score = [], [], 100
    headers = {k.lower(): v for k, v in response.get("headers", {}).items()}

    # HTTPS
    if url.startswith("https://"):
        passes.append("HTTPS active")
    else:
        issues.append(_issue("critical", "HTTP only — implement HTTPS immediately"))
        score -= 30

    # HSTS
    if "strict-transport-security" in headers:
        passes.append(f"HSTS enabled: {headers['strict-transport-security']}")
    else:
        issues.append(_issue("warning", "No HSTS header — browsers may allow HTTP downgrade attacks"))
        score -= 15

    # Clickjacking
    if "x-frame-options" in headers or "frame-ancestors" in headers.get("content-security-policy", ""):
        passes.append("Clickjacking protection active (X-Frame-Options or CSP)")
    else:
        issues.append(_issue("warning", "No X-Frame-Options — page can be embedded in iframes (clickjacking risk)"))
        score -= 10

    # MIME sniffing
    if "x-content-type-options" in headers:
        passes.append("X-Content-Type-Options set (MIME sniffing protection)")
    else:
        issues.append(_issue("info", "Missing X-Content-Type-Options: nosniff"))
        score -= 5

    # CSP
    if "content-security-policy" in headers:
        passes.append("Content Security Policy (CSP) header present")
    else:
        issues.append(_issue("info", "No Content Security Policy — consider adding to prevent XSS"))
        score -= 5

    # Server info leakage
    server = headers.get("server", "")
    if server and any(v in server.lower() for v in ["apache/", "nginx/", "iis/"]):
        issues.append(_issue("info", f"Server header reveals version info: {server} — consider hiding this"))
        score -= 5
    elif not server:
        passes.append("Server header not exposing version info")

    # X-Powered-By
    powered = headers.get("x-powered-by", "")
    if powered:
        issues.append(_issue("info", f"X-Powered-By header present: {powered} — remove to reduce fingerprinting"))
        score -= 5

    return {"score": max(0, score), "issues": issues, "passes": passes}
