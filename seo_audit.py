#!/usr/bin/env python3
"""
udit-seo-pro — Full SEO + GEO Audit in One Command
Combines the best of:
  - AgriciDaniel/claude-seo (13 sub-skills, technical SEO, schema, GEO)
  - aaron-he-zhu/seo-geo-claude-skills (CORE-EEAT, CITE, 4-phase framework)
  + Semrush API integration (domain overview, keywords, backlinks, competitors)
  + Phase-wise SEO action plan
  + PDF + Excel export in one run

Usage:
    python seo_audit.py https://yoursite.com
    python seo_audit.py https://yoursite.com --output betmaan_q2
    python seo_audit.py https://yoursite.com --keyword "sports betting india"
    python seo_audit.py https://yoursite.com --no-semrush   (skip API calls)
    python seo_audit.py --demo                              (run on demo page)
"""

import sys
import os
import json
import time
import argparse
from datetime import datetime
from pathlib import Path


# ── Load .env ────────────────────────────────────────────────────────────────
def load_env():
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())


load_env()

# ── Imports ──────────────────────────────────────────────────────────────────
from modules.crawler import fetch, SEOParser
from modules.audits import (
    audit_title, audit_meta_description, audit_headings,
    audit_content, audit_images, audit_schema, audit_technical,
    audit_open_graph, audit_links, audit_robots_txt, audit_sitemap,
    audit_geo_aeo, audit_cwv_signals, audit_mobile, audit_international,
    audit_security,
)
from modules.phases import generate_phase_plan
from modules.eeat import score_eeat
from modules.content_brief import generate_content_brief
from reports.pdf_report import generate_pdf
from reports.excel_report import generate_excel
import semrush.client as sm


# ──────────────────────────────────────────────────────────────────────────────
# SEMRUSH DATA PULLER
# ──────────────────────────────────────────────────────────────────────────────

def pull_semrush_data(url: str, seed_keyword: str = "", database: str = "in") -> dict:
    from urllib.parse import urlparse
    domain = urlparse(url).netloc

    print("  [Semrush] Pulling domain overview...")
    data = {"domain_overview": sm.domain_overview(domain, database)}

    print("  [Semrush] Pulling organic keywords...")
    data["organic_keywords"] = sm.organic_keywords(domain, database, limit=30)

    print("  [Semrush] Pulling organic competitors...")
    data["competitors"] = sm.organic_competitors(domain, database, limit=10)

    print("  [Semrush] Pulling backlinks overview...")
    data["backlinks_overview"] = sm.backlinks_overview(domain)

    print("  [Semrush] Pulling referring domains...")
    data["referring_domains"] = sm.referring_domains(domain, limit=15)

    if seed_keyword:
        print(f"  [Semrush] Keyword research for: '{seed_keyword}'...")
        data["keyword_overview"] = sm.keyword_overview(seed_keyword, database)
        data["related_keywords"] = sm.related_keywords(seed_keyword, database, limit=20)

    # Summarize what worked
    ok_count = sum(1 for v in data.values() if isinstance(v, dict) and v.get("ok"))
    fail_count = len(data) - ok_count
    print(f"  [Semrush] {ok_count} datasets pulled successfully, {fail_count} failed")

    return data


# ──────────────────────────────────────────────────────────────────────────────
# CORE AUDIT RUNNER
# ──────────────────────────────────────────────────────────────────────────────

def run_audit(url: str, response=None) -> dict:
    """Run all 16 audit modules against a URL. Returns full results dict."""

    if response is None:
        print(f"  Fetching page (trying up to 8 bypass profiles)...")
        response = fetch(url)
        if not response["ok"]:
            print(f"  WARNING: Could not fetch page directly (status: {response['status']})")
            print(f"  Error: {response.get('error', 'Unknown')}")
            print(f"  Continuing audit with Semrush data + technical checks only...")
            # Create a minimal response so audit can continue
            response = {
                "ok": False, "status": response["status"],
                "url": url, "headers": {},
                "text": "", "ttfb_ms": 0, "size_bytes": 0
            }
        else:
            attempt = response.get("bypass_attempt", 1)
            if attempt > 1:
                print(f"  Page fetched successfully (bypass profile #{attempt} worked)")
            else:
                print(f"  Page fetched successfully")

    print(f"  Parsing HTML ({len(response.get('text', ''))} chars)...")
    parser = SEOParser()
    parser.feed(response.get("text", ""))

    modules = {}

    print("  Auditing title & meta description...")
    modules["title"] = audit_title(parser, url)
    modules["meta_description"] = audit_meta_description(parser)

    print("  Auditing headings & content quality...")
    modules["headings"] = audit_headings(parser)
    modules["content"] = audit_content(parser, url)

    print("  Auditing images...")
    modules["images"] = audit_images(parser)

    print("  Auditing schema markup...")
    modules["schema"] = audit_schema(parser)

    print("  Auditing technical SEO...")
    modules["technical"] = audit_technical(parser, response, url)

    print("  Auditing Open Graph / social tags...")
    modules["open_graph"] = audit_open_graph(parser)

    print("  Auditing links...")
    modules["links"] = audit_links(parser, url)

    print("  Checking robots.txt...")
    modules["robots_txt"] = audit_robots_txt(url)

    print("  Checking sitemap.xml...")
    modules["sitemap"] = audit_sitemap(url)

    print("  Auditing GEO / AI search readiness...")
    modules["geo_aeo"] = audit_geo_aeo(parser, url)

    print("  Auditing Core Web Vitals signals...")
    modules["core_web_vitals"] = audit_cwv_signals(parser, response)

    print("  Auditing mobile SEO...")
    modules["mobile"] = audit_mobile(parser, response)

    print("  Auditing international SEO...")
    modules["international"] = audit_international(parser, url)

    print("  Auditing security...")
    modules["security"] = audit_security(response, url)

    # Overall score
    scores = [m.get("score", 0) for m in modules.values()]
    overall = round(sum(scores) / len(scores)) if scores else 0

    # Flatten all issues/passes
    all_issues = []
    all_passes = []
    for mod_name, mod_data in modules.items():
        for issue in mod_data.get("issues", []):
            all_issues.append({"module": mod_name, **issue})
        for p in mod_data.get("passes", []):
            all_passes.append({"module": mod_name, "msg": p})

    return {
        "url": url,
        "audit_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "modules": modules,
        "overall_score": overall,
        "all_issues": all_issues,
        "all_passes": all_passes,
    }


# ──────────────────────────────────────────────────────────────────────────────
# DEMO MODE (no live URL needed)
# ──────────────────────────────────────────────────────────────────────────────

DEMO_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Best Sports Betting Site in India - Betmaan India</title>
<meta name="description" content="Betmaan India offers cricket betting, football, kabaddi and casino games. Get 100% welcome bonus up to Rs.10000. Fast withdrawals, 24/7 support.">
<meta name="author" content="Betmaan Marketing Team">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="canonical" href="https://betmaanindia.com/">
<meta property="og:title" content="Betmaan India - Best Betting Site">
<meta property="og:description" content="Sports betting and casino games in India">
<meta property="og:image" content="https://betmaanindia.com/og.jpg">
<meta property="og:url" content="https://betmaanindia.com/">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Organization","name":"Betmaan India","url":"https://betmaanindia.com","logo":"https://betmaanindia.com/logo.png"}
</script>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"WebSite","name":"Betmaan India","url":"https://betmaanindia.com","potentialAction":{"@type":"SearchAction","target":{"@type":"EntryPoint","urlTemplate":"https://betmaanindia.com/search?q={search_term_string}"},"query-input":"required name=search_term_string"}}
</script>
</head>
<body>
<h1>Welcome to Betmaan India — Best Sports Betting Platform</h1>
<h2>Cricket Betting</h2>
<p>What is live cricket betting? Live betting lets you place wagers on cricket matches as they happen, including ball-by-ball markets. Betmaan India offers the most comprehensive live cricket betting markets in India, covering IPL, Test matches, T20 Internationals, and ODIs.</p>
<p>How to place a cricket bet? Simply register, deposit, and navigate to the cricket section. Select your market, enter your stake, and confirm. Our minimum bet is just Rs.10, making it accessible for everyone.</p>
<h2>Casino Games</h2>
<p>Play 500+ slot games, live dealer roulette, blackjack, and teen patti. Our live casino is powered by Evolution Gaming and Pragmatic Play — two of the world's leading providers.</p>
<h3>Welcome Bonus</h3>
<p>Why choose Betmaan? We offer a 100% first deposit bonus up to Rs.10,000, same-day withdrawals, and 24/7 customer support in Hindi and English. Our platform is licensed and regulated to ensure fair play.</p>
<h3>Payment Methods</h3>
<p>Betmaan India supports UPI, NetBanking, Paytm, PhonePe, and cryptocurrency deposits. All transactions are encrypted with 256-bit SSL. When should I withdraw? You can withdraw any time — minimum withdrawal is Rs.500.</p>
<img src="/hero-banner.jpg" alt="Betmaan India Welcome Bonus" width="1200" height="500" loading="eager">
<img src="/cricket-betting.jpg" alt="Live Cricket Betting Markets" width="600" height="400" width="600" height="400" loading="lazy">
<img src="/casino-games.jpg" width="600" height="400" loading="lazy">
<img src="/payment-methods.jpg" alt="UPI NetBanking Crypto Payment" width="400" height="200" loading="lazy">
<a href="/sports/cricket">Cricket Betting</a>
<a href="/sports/football">Football Betting</a>
<a href="/casino">Casino Games</a>
<a href="/promotions">Promotions</a>
<a href="/responsible-gambling">Responsible Gambling</a>
<a href="https://responsible-gambling.org" rel="nofollow">Responsible Gambling Resources</a>
<a href="https://trustpilot.com/review/betmaanindia.com" rel="nofollow">Our Reviews</a>
</body>
</html>"""

DEMO_RESPONSE = {
    "ok": True, "status": 200, "url": "https://betmaanindia.com/",
    "headers": {
        "Content-Type": "text/html; charset=utf-8",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "X-Frame-Options": "SAMEORIGIN",
        "X-Content-Type-Options": "nosniff",
    },
    "text": DEMO_HTML,
    "ttfb_ms": 410,
    "size_bytes": len(DEMO_HTML.encode()),
}


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="udit-seo-pro: Full SEO + GEO audit with Semrush + Phase-wise plan. PDF + Excel output.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python seo_audit.py https://betmaanindia.com
  python seo_audit.py https://thenetwallet.com --output netwallet_audit
  python seo_audit.py https://betmaanindia.com --keyword "sports betting india"
  python seo_audit.py https://betmaanindia.com --no-semrush
  python seo_audit.py --demo

Setup:
  1. Copy .env.example to .env
  2. Add your Semrush API key to .env
  3. Run: python seo_audit.py https://yoursite.com
        """
    )
    parser.add_argument("url", nargs="?", help="URL to audit (include https://)")
    parser.add_argument("--output", "-o", default="seo_report", help="Output filename prefix (default: seo_report)")
    parser.add_argument("--keyword", "-k", default="", help="Seed keyword for Semrush keyword research")
    parser.add_argument("--no-semrush", action="store_true", help="Skip Semrush API calls")
    parser.add_argument("--database", "-d", default="in", help="Semrush database/country (default: in)")
    parser.add_argument("--json", action="store_true", help="Also save raw JSON")
    parser.add_argument("--demo", action="store_true", help="Run against built-in demo page (no URL needed)")
    args = parser.parse_args()

    if not args.url and not args.demo:
        parser.print_help()
        sys.exit(1)

    print()
    print("=" * 65)
    print("  udit-seo-pro v1.0 — Full SEO + GEO Audit in One Command")
    print("  Audit: 16 modules | Semrush: 6 data points | Output: PDF + Excel")
    print("=" * 65)

    # ── Audit ──
    if args.demo:
        url = "https://betmaanindia.com/"
        print(f"\n[DEMO MODE] Auditing demo page for: {url}")
        print("\n[Step 1/3] Running on-page audit (16 modules)...")
        audit_results = run_audit(url, response=DEMO_RESPONSE)
    else:
        url = args.url if args.url.startswith("http") else "https://" + args.url
        print(f"\nTarget URL: {url}")
        print(f"\n[Step 1/3] Running on-page audit (16 modules)...")
        audit_results = run_audit(url)

    overall = audit_results["overall_score"]
    critical = len([i for i in audit_results["all_issues"] if i["severity"] == "critical"])
    warnings = len([i for i in audit_results["all_issues"] if i["severity"] == "warning"])
    infos = len([i for i in audit_results["all_issues"] if i["severity"] == "info"])
    passes = len(audit_results["all_passes"])

    print(f"\n  Audit complete: Score {overall}/100 | {critical} critical | {warnings} warnings | {infos} info | {passes} passed")

    # ── Semrush ──
    semrush_data = {}
    if not args.no_semrush and not args.demo:
        semrush_key = os.environ.get("SEMRUSH_API_KEY", "")
        if semrush_key and semrush_key != "your_semrush_api_key_here":
            print(f"\n[Step 2/3] Pulling Semrush data (database: {args.database})...")
            semrush_data = pull_semrush_data(url, args.keyword, args.database)
        else:
            print("\n[Step 2/3] Semrush skipped — add SEMRUSH_API_KEY to .env to enable")
    elif args.demo:
        print("\n[Step 2/3] Semrush skipped in demo mode")
        # Simulate Semrush data for demo
        semrush_data = {
            "domain_overview": {
                "ok": True, "source": "semrush",
                "summary": {
                    "domain": "betmaanindia.com",
                    "semrush_rank": "2,847,291",
                    "organic_keywords": "1,247",
                    "organic_traffic": "8,340",
                    "organic_cost": "$4,120",
                    "adwords_keywords": "0",
                    "authority_score": "18",
                },
                "data": []
            },
            "organic_keywords": {
                "ok": True, "source": "semrush",
                "data": [
                    {"Ph": "betmaan india", "Po": "1", "Nq": "12100", "Cp": "0.45", "Tr": "24.3"},
                    {"Ph": "betmaan login", "Po": "2", "Nq": "8100", "Cp": "0.32", "Tr": "15.1"},
                    {"Ph": "sports betting india", "Po": "14", "Nq": "22200", "Cp": "1.20", "Tr": "3.2"},
                    {"Ph": "cricket betting site india", "Po": "8", "Nq": "18100", "Cp": "0.98", "Tr": "5.7"},
                    {"Ph": "online casino india", "Po": "22", "Nq": "33100", "Cp": "1.65", "Tr": "1.4"},
                ]
            },
            "competitors": {
                "ok": True, "source": "semrush",
                "data": [
                    {"Dn": "betway.in", "Np": "847", "Or": "45,210", "Ot": "182,400"},
                    {"Dn": "dream11.com", "Np": "634", "Or": "289,100", "Ot": "4,200,000"},
                    {"Dn": "1xbet.com", "Np": "523", "Or": "67,800", "Ot": "341,200"},
                ]
            },
        }
    else:
        print("\n[Step 2/3] Semrush skipped (--no-semrush flag)")

    # ── CORE-EEAT Scoring ──
    print("\n[Step 3a/4] Running CORE-EEAT 80-item content quality score...")
    _eeat_parser = SEOParser()
    html_src = DEMO_HTML if args.demo else fetch(url).get("text", "")
    _eeat_parser.feed(html_src)
    eeat_result = score_eeat(_eeat_parser, url)
    es = eeat_result
    print(f"  EEAT: {es['total_score']}/100 Grade {es['grade']}  "
          f"C:{es['summary']['C']} O:{es['summary']['O']} R:{es['summary']['R']} E:{es['summary']['E']}")

    # ── Content Brief ──
    print("\n[Step 3b/4] Generating content brief...")
    content_brief = generate_content_brief(url, _eeat_parser, audit_results, semrush_data, eeat_result)
    print(f"  Brief ready: {len(content_brief.get('recommended_h2_structure',[]))} H2 suggestions")

    # ── Phase Plan ──
    print("\n[Step 4/4] Generating 4-phase SEO action plan...")
    phase_plan = generate_phase_plan(audit_results, semrush_data)
    total_tasks = sum(len(p["tasks"]) for p in phase_plan.values())
    print(f"  Generated {total_tasks} prioritized tasks across 4 phases")

    # ── Reports ──
    base = args.output
    pdf_path = f"{base}.pdf"
    xlsx_path = f"{base}.xlsx"

    print(f"\n  Generating PDF report (cover ring + EEAT + content brief + plan)...")
    generate_pdf(audit_results, phase_plan, semrush_data, pdf_path,
                 eeat_result=eeat_result, content_brief=content_brief)

    print(f"  Generating Excel workbook (9 sheets)...")
    generate_excel(audit_results, phase_plan, semrush_data, xlsx_path,
                   eeat_result=eeat_result, content_brief=content_brief)

    if args.json:
        json_path = f"{base}.json"
        with open(json_path, "w") as f:
            def default(o):
                if hasattr(o, "__dict__"):
                    return o.__dict__
                return str(o)
            json.dump({"audit": audit_results, "semrush": {k: {"ok": v.get("ok"), "rows": len(v.get("data", []))} for k, v in semrush_data.items() if isinstance(v, dict)}}, f, indent=2, default=default)
        print(f"  JSON saved: {json_path}")

    print()
    print("=" * 65)
    print(f"  DONE")
    print(f"  Overall Score  : {overall}/100")
    print(f"  Critical Issues: {critical}")
    print(f"  PDF Report     : {pdf_path}")
    print(f"  Excel Report   : {xlsx_path}")
    print("=" * 65)
    print()


if __name__ == "__main__":
    main()
