"""
modules/phases.py
Generates a 4-phase SEO action plan based on audit results.
Inspired by the Research → Build → Optimize → Monitor framework
from aaron-he-zhu/seo-geo-claude-skills.

Each phase is tied to real audit findings, prioritized by severity.
"""

from datetime import datetime, timedelta


PHASE_DEFINITIONS = {
    1: {
        "name": "RESEARCH & FOUNDATIONS",
        "timeframe": "Week 1–2",
        "goal": "Understand the landscape, fix critical blockers, establish baselines",
        "color": "1A1A2E",
        "icon": "🔬",
    },
    2: {
        "name": "BUILD & FIX",
        "timeframe": "Week 3–6",
        "goal": "Implement on-page fixes, create optimized content, build schema",
        "color": "1A4A8A",
        "icon": "🔧",
    },
    3: {
        "name": "OPTIMIZE & AMPLIFY",
        "timeframe": "Month 2–3",
        "goal": "Technical performance, link building, GEO optimization",
        "color": "0A6A3A",
        "icon": "🚀",
    },
    4: {
        "name": "MONITOR & GROW",
        "timeframe": "Month 3+",
        "goal": "Track rankings, measure ROI, iterate and expand",
        "color": "6A1A6A",
        "icon": "📊",
    },
}


def _phase_1_tasks(audit_results, semrush_data):
    """Critical fixes + research tasks."""
    tasks = []
    modules = audit_results.get("modules", {})

    # Always: keyword research (from Semrush if available)
    tasks.append({
        "priority": 1,
        "task": "Run keyword research — identify 20–30 primary + long-tail keywords",
        "why": "Foundation for all content and optimization decisions",
        "source": "Semrush organic_keywords" if semrush_data.get("organic_keywords", {}).get("ok") else "Manual research",
        "effort": "Medium",
        "impact": "High",
    })

    # Critical fixes from audit
    for issue in audit_results.get("all_issues", []):
        if issue["severity"] == "critical":
            tasks.append({
                "priority": 2,
                "task": f"FIX CRITICAL: {issue['msg']}",
                "why": "Critical issues actively harm rankings — fix before any other SEO work",
                "source": f"On-page audit — {issue['module']}",
                "effort": "Varies",
                "impact": "Very High",
            })

    # Competitor analysis
    tasks.append({
        "priority": 3,
        "task": "Identify top 5 organic competitors and analyze their top pages",
        "why": "Understand who you're competing against and what content wins",
        "source": "Semrush competitor data" if semrush_data.get("competitors", {}).get("ok") else "Manual SERP analysis",
        "effort": "Medium",
        "impact": "High",
    })

    # GSC baseline
    tasks.append({
        "priority": 4,
        "task": "Verify Google Search Console setup and submit sitemap",
        "why": "GSC is the primary source of truth for impressions, clicks, and indexing",
        "source": "Google Search Console",
        "effort": "Low",
        "impact": "High",
    })

    # Semrush domain overview
    if semrush_data.get("domain_overview", {}).get("ok"):
        summary = semrush_data["domain_overview"].get("summary", {})
        tasks.append({
            "priority": 1,
            "task": f"Review Semrush baseline: {summary.get('organic_keywords', 'N/A')} organic keywords, "
                    f"{summary.get('organic_traffic', 'N/A')} monthly organic traffic",
            "why": "Establish numeric baselines to measure SEO growth",
            "source": "Semrush domain_rank",
            "effort": "Low",
            "impact": "High",
        })

    return tasks


def _phase_2_tasks(audit_results, semrush_data):
    """On-page fixes and content creation."""
    tasks = []
    modules = audit_results.get("modules", {})

    # Title/meta fixes
    title_score = modules.get("title", {}).get("score", 100)
    meta_score = modules.get("meta_description", {}).get("score", 100)

    if title_score < 80:
        tasks.append({
            "priority": 1,
            "task": "Rewrite all page titles — include primary keyword in first 60 chars",
            "why": f"Title score: {title_score}/100 — titles directly affect CTR and rankings",
            "source": "On-page audit",
            "effort": "Low",
            "impact": "High",
        })

    if meta_score < 80:
        tasks.append({
            "priority": 1,
            "task": "Write meta descriptions for all key pages (120–160 chars, include a CTA)",
            "why": f"Meta description score: {meta_score}/100 — directly impacts organic CTR",
            "source": "On-page audit",
            "effort": "Low",
            "impact": "High",
        })

    # Heading fixes
    h_score = modules.get("headings", {}).get("score", 100)
    if h_score < 80:
        tasks.append({
            "priority": 2,
            "task": "Fix heading structure — ensure one H1 per page, logical H2/H3 hierarchy",
            "why": f"Heading score: {h_score}/100 — headings signal content structure to Google",
            "source": "On-page audit",
            "effort": "Low",
            "impact": "Medium",
        })

    # Content
    content_score = modules.get("content", {}).get("score", 100)
    wc = modules.get("content", {}).get("word_count", 0)
    if content_score < 80 or wc < 600:
        tasks.append({
            "priority": 2,
            "task": f"Expand thin content pages — current avg: {wc} words, target 800–1500+ for competitive pages",
            "why": "Thin content ranks poorly and signals low value to Google",
            "source": "On-page audit + CORE-EEAT framework",
            "effort": "High",
            "impact": "High",
        })

    # Schema
    schema_score = modules.get("schema", {}).get("score", 100)
    if schema_score < 70:
        tasks.append({
            "priority": 2,
            "task": "Implement JSON-LD schema: Organization, Website, BreadcrumbList, Article/Product",
            "why": f"Schema score: {schema_score}/100 — enables rich results and AI understanding",
            "source": "Schema audit",
            "effort": "Medium",
            "impact": "High",
        })

    # Open Graph
    og_score = modules.get("open_graph", {}).get("score", 100)
    if og_score < 80:
        tasks.append({
            "priority": 3,
            "task": "Add complete Open Graph tags (og:title, og:description, og:image 1200x630px) to all pages",
            "why": f"OG score: {og_score}/100 — affects social sharing appearance and click-through",
            "source": "Social tags audit",
            "effort": "Low",
            "impact": "Medium",
        })

    # Image optimization
    img_score = modules.get("images", {}).get("score", 100)
    if img_score < 80:
        missing_alt = modules.get("images", {}).get("missing_alt_count", 0)
        tasks.append({
            "priority": 2,
            "task": f"Fix {missing_alt} images missing alt text — add descriptive, keyword-rich alt attributes",
            "why": f"Image score: {img_score}/100 — alt text is an accessibility requirement and ranking signal",
            "source": "Image audit",
            "effort": "Low",
            "impact": "Medium",
        })

    # Content gap (from Semrush)
    if semrush_data.get("organic_keywords", {}).get("ok"):
        kws = semrush_data["organic_keywords"].get("data", [])[:5]
        if kws:
            top_kws = ", ".join(r.get("Keyword", r.get("Ph", "")) for r in kws if r.get("Keyword") or r.get("Ph"))
            tasks.append({
                "priority": 3,
                "task": f"Create content targeting your top Semrush keywords: {top_kws}",
                "why": "Target keywords with existing ranking potential — easier wins",
                "source": "Semrush organic_keywords",
                "effort": "High",
                "impact": "High",
            })

    return tasks


def _phase_3_tasks(audit_results, semrush_data):
    """Technical, links, GEO."""
    tasks = []
    modules = audit_results.get("modules", {})

    # Technical
    tech_score = modules.get("technical", {}).get("score", 100)
    ttfb = modules.get("technical", {}).get("ttfb_ms", 0)
    if ttfb > 800:
        tasks.append({
            "priority": 1,
            "task": f"Improve server response time — current TTFB: {ttfb}ms, target <800ms",
            "why": "Slow TTFB is a Core Web Vitals issue and direct ranking factor",
            "source": "Technical audit",
            "effort": "High",
            "impact": "High",
        })

    # CWV
    cwv_score = modules.get("core_web_vitals", {}).get("score", 100)
    if cwv_score < 80:
        tasks.append({
            "priority": 2,
            "task": "Fix Core Web Vitals signals — add image dimensions, use fetchpriority='high' on LCP image, reduce render-blocking scripts",
            "why": "CWV are confirmed Google ranking factors since 2021",
            "source": "CWV signals audit",
            "effort": "High",
            "impact": "High",
        })

    # Mobile
    mobile_score = modules.get("mobile", {}).get("score", 100)
    if mobile_score < 80:
        tasks.append({
            "priority": 2,
            "task": "Fix mobile SEO issues — ensure all pages pass Google Mobile-Friendly Test",
            "why": f"Mobile score: {mobile_score}/100 — Google uses mobile-first indexing",
            "source": "Mobile audit",
            "effort": "Medium",
            "impact": "High",
        })

    # Links / internal linking
    links_score = modules.get("links", {}).get("score", 100)
    if links_score < 80:
        tasks.append({
            "priority": 2,
            "task": "Improve internal linking — build topic clusters, link related pages with descriptive anchor text",
            "why": f"Links score: {links_score}/100 — internal links distribute PageRank and aid crawlability",
            "source": "Links audit + internal-linking-optimizer framework",
            "effort": "Medium",
            "impact": "High",
        })

    # GEO
    geo_score = modules.get("geo_aeo", {}).get("score", 100)
    if geo_score < 80:
        tasks.append({
            "priority": 2,
            "task": "Optimize for AI search (GEO): add llms.txt, write definition-style Q&A content, ensure author attribution",
            "why": f"GEO score: {geo_score}/100 — AI Overviews now appear on 50%+ of informational queries",
            "source": "GEO/AEO audit",
            "effort": "Medium",
            "impact": "High",
        })

    # Backlinks from Semrush
    bl_data = semrush_data.get("backlinks_overview", {})
    if bl_data.get("ok"):
        tasks.append({
            "priority": 3,
            "task": "Audit backlink profile — identify toxic links to disavow, high-DA opportunities for outreach",
            "why": "Backlink profile is a top-3 ranking factor — quality matters more than quantity",
            "source": "Semrush backlinks_overview",
            "effort": "High",
            "impact": "High",
        })

    # Security
    sec_score = modules.get("security", {}).get("score", 100)
    if sec_score < 80:
        tasks.append({
            "priority": 3,
            "task": "Implement security headers: HSTS, X-Frame-Options, Content-Security-Policy",
            "why": "Security signals influence trust scores and indirectly affect rankings",
            "source": "Security audit",
            "effort": "Low",
            "impact": "Medium",
        })

    return tasks


def _phase_4_tasks(audit_results, semrush_data):
    """Monitoring, reporting, iteration."""
    tasks = []
    modules = audit_results.get("modules", {})

    tasks.append({
        "priority": 1,
        "task": "Set up weekly keyword rank tracking — monitor top 50 keywords in Semrush Position Tracking",
        "why": "You can't improve what you don't measure — track positions weekly",
        "source": "Semrush position tracking + rank-tracker framework",
        "effort": "Low",
        "impact": "High",
    })

    tasks.append({
        "priority": 1,
        "task": "Create monthly SEO performance report — organic traffic, rankings, conversions from GSC + GA4",
        "why": "Stakeholder reporting demonstrates ROI and guides budget decisions",
        "source": "performance-reporter framework + Google Analytics",
        "effort": "Medium",
        "impact": "High",
    })

    tasks.append({
        "priority": 2,
        "task": "Set up Semrush alerts for: ranking drops >5 positions, new competitor pages, backlink changes",
        "why": "Proactive monitoring prevents traffic losses before they compound",
        "source": "alert-manager framework",
        "effort": "Low",
        "impact": "High",
    })

    tasks.append({
        "priority": 2,
        "task": "Quarterly content refresh cycle — update top-10 ranking pages to maintain freshness",
        "why": "Content decay causes ranking drops — proactive refresh beats reactive",
        "source": "content-refresher framework",
        "effort": "High",
        "impact": "High",
    })

    tasks.append({
        "priority": 3,
        "task": "Conduct competitor gap analysis quarterly — find new keyword opportunities as market shifts",
        "why": "SEO is a moving target — competitors gain and lose ground continuously",
        "source": "Semrush content_gap + competitor-analysis framework",
        "effort": "Medium",
        "impact": "Medium",
    })

    # Domain authority
    tasks.append({
        "priority": 3,
        "task": "Monitor domain authority score (CITE framework) — track Authority Score in Semrush monthly",
        "why": "Domain authority is a lagging indicator — track over 6–12 months for trend signals",
        "source": "Semrush domain_rank history + domain-authority-auditor framework",
        "effort": "Low",
        "impact": "Medium",
    })

    return tasks


def generate_phase_plan(audit_results, semrush_data):
    """
    Generate a complete 4-phase SEO plan based on audit findings
    and available Semrush data.
    """
    return {
        1: {
            **PHASE_DEFINITIONS[1],
            "tasks": _phase_1_tasks(audit_results, semrush_data),
        },
        2: {
            **PHASE_DEFINITIONS[2],
            "tasks": _phase_2_tasks(audit_results, semrush_data),
        },
        3: {
            **PHASE_DEFINITIONS[3],
            "tasks": _phase_3_tasks(audit_results, semrush_data),
        },
        4: {
            **PHASE_DEFINITIONS[4],
            "tasks": _phase_4_tasks(audit_results, semrush_data),
        },
    }
