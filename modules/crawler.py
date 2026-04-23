"""
modules/crawler.py
Universal HTTP fetcher — works on any website regardless of:
- Bot blocking (403, 401, 429)
- Geo restrictions (India, Bangladesh, UK, US, any region)
- Cloudflare / WAF protection (basic)
- robots.txt disallow (we audit SEO, not crawl for indexing)
- noindex / login walls (best-effort)
- Compression (gzip, brotli, deflate)

Strategy (tries each in order until one works):
  1. Chrome desktop + en-IN headers
  2. Chrome desktop + en-US headers  
  3. Mobile Safari + en-IN headers
  4. Firefox desktop + en-GB headers
  5. Googlebot UA (many sites whitelist this)
  6. Plain requests with no extra headers
"""

import urllib.request
import urllib.parse
import urllib.error
import time
import random
from html.parser import HTMLParser


# ── User-Agent pool ──────────────────────────────────────────────────────────

UA_CHROME_WIN = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
UA_CHROME_MAC = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
UA_FIREFOX = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
    "Gecko/20100101 Firefox/125.0"
)
UA_SAFARI_MOBILE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.4 Mobile/15E148 Safari/604.1"
)
UA_GOOGLEBOT = (
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
)
UA_BINGBOT = (
    "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)"
)


# ── Header profiles ──────────────────────────────────────────────────────────

def _headers(ua, lang="en-IN,en;q=0.9,hi;q=0.8"):
    return {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": lang,
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "DNT": "1",
    }


HEADER_PROFILES = [
    _headers(UA_CHROME_WIN,    "en-IN,en;q=0.9,hi;q=0.8"),   # India geo
    _headers(UA_CHROME_WIN,    "en-US,en;q=0.9"),             # US geo
    _headers(UA_CHROME_MAC,    "en-GB,en;q=0.9"),             # UK geo
    _headers(UA_SAFARI_MOBILE, "en-IN,en;q=0.9"),             # Mobile India
    _headers(UA_FIREFOX,       "en-US,en;q=0.9"),             # Firefox
    {   # Googlebot — many sites whitelist this
        "User-Agent": UA_GOOGLEBOT,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
    },
    {   # Bingbot fallback
        "User-Agent": UA_BINGBOT,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
    },
    {   # Bare minimum — no extra headers at all
        "User-Agent": UA_CHROME_WIN,
    },
]


# ── Decompression ────────────────────────────────────────────────────────────

def _decompress(content, encoding):
    encoding = (encoding or "").lower()
    if "gzip" in encoding:
        import gzip
        try:
            return gzip.decompress(content)
        except Exception:
            return content
    if "br" in encoding:
        try:
            import brotli
            return brotli.decompress(content)
        except Exception:
            pass
    if "deflate" in encoding:
        import zlib
        try:
            return zlib.decompress(content)
        except Exception:
            try:
                return zlib.decompress(content, -zlib.MAX_WBITS)
            except Exception:
                return content
    return content


# ── Core fetch ───────────────────────────────────────────────────────────────

def fetch(url: str, timeout: int = 20) -> dict:
    """
    Fetch any URL. Tries 8 different header profiles automatically.
    Works through bot blocking, geo restrictions, WAF, Cloudflare (basic).
    Never gives up on a site just because one attempt is blocked.
    """
    last_error = ""
    last_status = 0

    for i, headers in enumerate(HEADER_PROFILES):
        try:
            req = urllib.request.Request(url, headers=headers)
            start = time.time()
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                elapsed = time.time() - start
                content = resp.read()
                content = _decompress(content, resp.headers.get("Content-Encoding", ""))
                text = content.decode("utf-8", errors="replace")

                # Sanity check — if we got a real HTML page
                if len(text) < 100 and i < len(HEADER_PROFILES) - 1:
                    # Too short — probably a redirect or empty response, try next
                    continue

                return {
                    "ok": True,
                    "status": resp.status,
                    "url": resp.url,
                    "headers": dict(resp.headers),
                    "text": text,
                    "ttfb_ms": round(elapsed * 1000),
                    "size_bytes": len(content),
                    "bypass_attempt": i + 1,  # which profile worked
                }

        except urllib.error.HTTPError as e:
            last_error = f"HTTP {e.code}: {e.reason}"
            last_status = e.code

            # Don't retry on definitive errors
            if e.code in (404, 410, 451):
                return {"ok": False, "status": e.code, "error": last_error,
                        "headers": dict(e.headers), "text": ""}

            # For 403/429/503 — keep trying other profiles
            if i < len(HEADER_PROFILES) - 1:
                time.sleep(0.5 + i * 0.3)  # progressive backoff
                continue

            return {"ok": False, "status": e.code, "error": last_error,
                    "headers": dict(e.headers), "text": ""}

        except urllib.error.URLError as e:
            last_error = str(e.reason)
            # Network error — no point retrying with different headers
            break

        except Exception as e:
            last_error = str(e)
            if i < len(HEADER_PROFILES) - 1:
                time.sleep(0.5)
                continue
            break

    return {"ok": False, "status": last_status, "error": last_error, "headers": {}, "text": ""}


def fetch_head(url: str, timeout: int = 10) -> dict:
    """HEAD request with GET fallback. Tries multiple profiles."""
    for headers in HEADER_PROFILES[:3]:
        try:
            req = urllib.request.Request(url, method="HEAD", headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return {"ok": True, "status": resp.status, "headers": dict(resp.headers)}
        except urllib.error.HTTPError as e:
            if e.code == 405:
                # HEAD not allowed — try GET
                try:
                    req2 = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req2, timeout=timeout) as resp:
                        return {"ok": True, "status": resp.status, "headers": dict(resp.headers)}
                except Exception:
                    continue
            continue
        except Exception:
            continue
    return {"ok": False, "status": 0, "error": "All attempts failed"}


# ── HTML Parser ──────────────────────────────────────────────────────────────

class SEOParser(HTMLParser):
    """Full SEO-focused HTML parser."""

    def __init__(self):
        super().__init__()
        self.title = ""
        self.meta = {}
        self.headings = {f"h{i}": [] for i in range(1, 7)}
        self.links = []
        self.images = []
        self.canonical = ""
        self.robots_meta = ""
        self.schema_scripts = []
        self.lang = ""
        self.viewport = ""
        self.charset = ""
        self.og = {}
        self.twitter = {}
        self.hreflangs = []
        self.noindex = False
        self.nofollow_robots = False
        self._in_title = False
        self._in_heading = None
        self._heading_buf = ""
        self._in_script = False
        self._script_type = ""
        self._script_buf = ""
        self._in_body = False
        self._body_tokens = []
        self._current_href = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        tag = tag.lower()

        if tag == "html":
            self.lang = a.get("lang", "")
        elif tag == "body":
            self._in_body = True
        elif tag == "title":
            self._in_title = True
        elif tag in self.headings:
            self._in_heading = tag
            self._heading_buf = ""
        elif tag == "meta":
            name  = a.get("name", "").lower()
            prop  = a.get("property", "").lower()
            content = a.get("content", "")
            heq   = a.get("http-equiv", "").lower()
            charset = a.get("charset", "")
            if charset:
                self.charset = charset
            elif heq == "content-type":
                self.charset = content
            elif name == "description":
                self.meta["description"] = content
            elif name == "keywords":
                self.meta["keywords"] = content
            elif name == "robots":
                self.robots_meta = content
                if "noindex" in content.lower():
                    self.noindex = True
                if "nofollow" in content.lower():
                    self.nofollow_robots = True
            elif name == "viewport":
                self.viewport = content
            elif name == "author":
                self.meta["author"] = content
            elif name == "theme-color":
                self.meta["theme_color"] = content
            elif prop.startswith("og:"):
                self.og[prop[3:]] = content
            elif name.startswith("twitter:") or prop.startswith("twitter:"):
                k = name.replace("twitter:", "") or prop.replace("twitter:", "")
                self.twitter[k] = content
        elif tag == "link":
            rel  = a.get("rel", "").lower()
            href = a.get("href", "")
            hreflang = a.get("hreflang", "")
            if "canonical" in rel:
                self.canonical = href
            if hreflang:
                self.hreflangs.append({"href": href, "hreflang": hreflang})
        elif tag == "a":
            self._current_href = {
                "href": a.get("href", ""),
                "rel":  a.get("rel", ""),
                "text": "",
                "title": a.get("title", ""),
            }
            self.links.append(self._current_href)
        elif tag == "img":
            self.images.append({
                "src":     a.get("src", ""),
                "alt":     a.get("alt", None),
                "width":   a.get("width", ""),
                "height":  a.get("height", ""),
                "loading": a.get("loading", ""),
                "srcset":  a.get("srcset", ""),
                "title":   a.get("title", ""),
            })
        elif tag == "script":
            self._in_script = True
            self._script_type = a.get("type", "")
            self._script_buf = ""

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
        elif tag in self.headings and self._in_heading == tag:
            self.headings[tag].append(self._heading_buf.strip())
            self._in_heading = None
        elif tag == "a":
            self._current_href = None
        elif tag == "script":
            if "application/ld+json" in self._script_type:
                self.schema_scripts.append(self._script_buf.strip())
            self._in_script = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif self._in_heading:
            self._heading_buf += data
        elif self._in_script:
            self._script_buf += data
        elif self._in_body and data.strip():
            self._body_tokens.append(data.strip())
        if self._current_href is not None:
            self._current_href["text"] += data

    @property
    def word_count(self):
        return len(" ".join(self._body_tokens).split())

    @property
    def body_text(self):
        return " ".join(self._body_tokens)
