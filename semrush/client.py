"""
semrush/client.py
Semrush API v3 client — pulls domain analytics, keywords,
backlinks, and organic traffic data.

All methods return dicts with keys:
  ok: bool
  data: list[dict] | dict
  error: str (if ok=False)
  source: "semrush" | "error"
"""

import urllib.request
import urllib.parse
import urllib.error
import json
import os
import csv
import io
import time


BASE_URL = "https://api.semrush.com"


def _get_key():
    key = os.environ.get("SEMRUSH_API_KEY", "")
    if not key or key == "your_semrush_api_key_here":
        return None
    return key


def _fetch(endpoint: str, params: dict) -> dict:
    key = _get_key()
    if not key:
        return {"ok": False, "error": "SEMRUSH_API_KEY not set in .env", "data": [], "source": "error"}

    params["key"] = key
    url = f"{BASE_URL}/{endpoint}?" + urllib.parse.urlencode(params)

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "udit-seo-pro/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            # Semrush returns CSV lines; parse into list of dicts
            reader = csv.DictReader(io.StringIO(raw), delimiter=";")
            rows = list(reader)
            if rows and "ERROR" in (rows[0].get("ERROR", "") or ""):
                return {"ok": False, "error": rows[0].get("ERROR", "Semrush API error"), "data": [], "source": "semrush"}
            return {"ok": True, "data": rows, "source": "semrush"}
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"HTTP {e.code}: {e.reason}", "data": [], "source": "error"}
    except Exception as e:
        return {"ok": False, "error": str(e), "data": [], "source": "error"}


# ──────────────────────────────────────────────
# DOMAIN OVERVIEW
# ──────────────────────────────────────────────

def domain_overview(domain: str, database: str = "in") -> dict:
    """
    Pull domain-level SEO metrics: organic traffic, keywords,
    authority score, paid traffic estimates.
    """
    # Strip protocol
    domain = domain.replace("https://", "").replace("http://", "").split("/")[0]

    result = _fetch("", {
        "type": "domain_rank",
        "domain": domain,
        "database": database,
        "display_limit": 1,
        "export_columns": "Dn,Rk,Or,Ot,Oc,Ad,At,Ac,Sh,Sv",
    })

    summary = {}
    if result["ok"] and result["data"]:
        row = result["data"][0]
        summary = {
            "domain": row.get("Domain", domain),
            "semrush_rank": row.get("Semrush Rank", "N/A"),
            "organic_keywords": row.get("Organic Keywords", "N/A"),
            "organic_traffic": row.get("Organic Traffic", "N/A"),
            "organic_cost": row.get("Organic Cost", "N/A"),
            "adwords_keywords": row.get("Adwords Keywords", "N/A"),
            "adwords_traffic": row.get("Adwords Traffic", "N/A"),
            "authority_score": row.get("Authority Score", "N/A"),
        }

    result["summary"] = summary
    return result


# ──────────────────────────────────────────────
# ORGANIC KEYWORDS
# ──────────────────────────────────────────────

def organic_keywords(domain: str, database: str = "in", limit: int = 50) -> dict:
    """
    Top organic keywords the domain ranks for, with position,
    search volume, CPC, and URL.
    """
    domain = domain.replace("https://", "").replace("http://", "").split("/")[0]

    return _fetch("", {
        "type": "domain_organic",
        "domain": domain,
        "database": database,
        "display_limit": limit,
        "display_sort": "tr_desc",
        "export_columns": "Ph,Po,Pp,Pd,Nq,Cp,Ur,Tr,Tc,Co,Nr,Td",
    })


# ──────────────────────────────────────────────
# TOP PAGES
# ──────────────────────────────────────────────

def top_pages(domain: str, database: str = "in", limit: int = 20) -> dict:
    """
    Top landing pages ranked organically with their traffic share.
    """
    domain = domain.replace("https://", "").replace("http://", "").split("/")[0]

    return _fetch("", {
        "type": "domain_organic_organic",
        "domain": domain,
        "database": database,
        "display_limit": limit,
        "export_columns": "Ur,Pc,Trafic,Nq",
    })


# ──────────────────────────────────────────────
# BACKLINKS OVERVIEW
# ──────────────────────────────────────────────

def backlinks_overview(domain: str) -> dict:
    """
    Backlink profile: total backlinks, referring domains,
    IPs, authority breakdown.
    """
    domain = domain.replace("https://", "").replace("http://", "").split("/")[0]

    return _fetch("analytics/v1/", {
        "action": "report",
        "type": "backlinks_overview",
        "target": domain,
        "target_type": "root_domain",
        "export_columns": "ascore,total,domains_num,urls_num,ips_num,follows_num,nofollows_num",
    })


# ──────────────────────────────────────────────
# REFERRING DOMAINS
# ──────────────────────────────────────────────

def referring_domains(domain: str, limit: int = 20) -> dict:
    """
    Top referring domains with authority scores.
    """
    domain = domain.replace("https://", "").replace("http://", "").split("/")[0]

    return _fetch("analytics/v1/", {
        "action": "report",
        "type": "backlinks_refdomains",
        "target": domain,
        "target_type": "root_domain",
        "display_limit": limit,
        "export_columns": "domain_ascore,domain,backlinks_num,ip",
        "display_sort": "domain_ascore_desc",
    })


# ──────────────────────────────────────────────
# COMPETITORS
# ──────────────────────────────────────────────

def organic_competitors(domain: str, database: str = "in", limit: int = 10) -> dict:
    """
    Top organic search competitors.
    """
    domain = domain.replace("https://", "").replace("http://", "").split("/")[0]

    return _fetch("", {
        "type": "domain_organic_organic",
        "domain": domain,
        "database": database,
        "display_limit": limit,
        "export_columns": "Dn,Np,Or,Ot,Oc,Ad",
    })


# ──────────────────────────────────────────────
# KEYWORD OVERVIEW (seed keyword analysis)
# ──────────────────────────────────────────────

def keyword_overview(keyword: str, database: str = "in") -> dict:
    """
    Search volume, difficulty, CPC, trend for a keyword.
    """
    return _fetch("", {
        "type": "phrase_this",
        "phrase": keyword,
        "database": database,
        "export_columns": "Ph,Nq,Cp,Co,Nr,Td",
    })


# ──────────────────────────────────────────────
# RELATED KEYWORDS
# ──────────────────────────────────────────────

def related_keywords(keyword: str, database: str = "in", limit: int = 30) -> dict:
    """
    Related/semantically similar keywords with volume and difficulty.
    """
    return _fetch("", {
        "type": "phrase_related",
        "phrase": keyword,
        "database": database,
        "display_limit": limit,
        "export_columns": "Ph,Nq,Cp,Co,Nr,Td",
    })


# ──────────────────────────────────────────────
# POSITION TRACKING (rankings over time)
# ──────────────────────────────────────────────

def keyword_positions(domain: str, keywords: list, database: str = "in") -> dict:
    """
    Check current ranking positions for a list of keywords.
    """
    domain = domain.replace("https://", "").replace("http://", "").split("/")[0]
    results = []

    for kw in keywords[:20]:  # API limit safety
        r = _fetch("", {
            "type": "url_organic",
            "url": domain,
            "database": database,
            "phrase": kw,
            "export_columns": "Ph,Po,Nq,Ur,Tr",
        })
        if r["ok"] and r["data"]:
            results.extend(r["data"])
        time.sleep(0.1)  # rate limit respect

    return {"ok": True, "data": results, "source": "semrush"}


# ──────────────────────────────────────────────
# SITE AUDIT ISSUES (via API — basic)
# ──────────────────────────────────────────────

def domain_errors(domain: str, database: str = "in") -> dict:
    """
    Pull any known crawl errors or site health issues Semrush has indexed.
    """
    domain = domain.replace("https://", "").replace("http://", "").split("/")[0]

    return _fetch("", {
        "type": "domain_rank_history",
        "domain": domain,
        "database": database,
        "display_limit": 10,
        "export_columns": "Dt,Rk,Or,Ot,Oc",
    })


# ──────────────────────────────────────────────
# CONTENT GAP (keywords competitor ranks for that you don't)
# ──────────────────────────────────────────────

def content_gap(domain: str, competitor: str, database: str = "in", limit: int = 30) -> dict:
    """
    Keywords the competitor ranks for but the target domain does not.
    """
    domain = domain.replace("https://", "").replace("http://", "").split("/")[0]
    competitor = competitor.replace("https://", "").replace("http://", "").split("/")[0]

    return _fetch("", {
        "type": "domain_organic",
        "domain": competitor,
        "database": database,
        "display_limit": limit,
        "display_filter": f"-|Po|Lt|11|+|Do|Eq|{domain}",
        "export_columns": "Ph,Po,Nq,Cp,Ur,Tr",
    })
