<div align="center">

# 🚀 udit-seo-pro

### Full SEO + GEO Audit with Live Semrush Data. One Command. PDF + Excel.

[![Python](https://img.shields.io/badge/Python-3.8+-blue?style=flat-square&logo=python)](https://python.org)
[![Semrush](https://img.shields.io/badge/Powered_by-Semrush_API-orange?style=flat-square)](https://semrush.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Modules](https://img.shields.io/badge/Audit_Modules-16-purple?style=flat-square)]()
[![Output](https://img.shields.io/badge/Output-PDF_+_Excel-red?style=flat-square)]()

**Everything in udit-seo-free — plus live Semrush keyword, competitor, and backlink data.**

[Quick Start](#quick-start) • [What's Different](#whats-different-from-free) • [Setup](#setup) • [Usage](#usage) • [Output](#output)

</div>

---

## ⚡ Quick Start

```bash
git clone https://github.com/yourusername/udit-seo-pro.git
cd udit-seo-pro
pip install -r requirements.txt
cp .env.example .env
# Add your Semrush API key to .env
python seo_audit.py https://yoursite.com --keyword "target keyword"
```

---

## 🆚 What's Different from Free

| Feature | udit-seo-free | udit-seo-pro |
|---------|:---:|:---:|
| 16 audit modules | ✅ | ✅ |
| CORE-EEAT 80-item score | ✅ | ✅ |
| Content brief | ✅ | ✅ |
| 4-phase action plan | ✅ | ✅ |
| PDF + Excel output | ✅ | ✅ |
| Works on bot-blocked sites | ✅ | ✅ |
| **Domain Authority Score** | ❌ | ✅ |
| **Top organic keywords + positions** | ❌ | ✅ |
| **Search volume + CPC data** | ❌ | ✅ |
| **Top 10 competitor domains** | ❌ | ✅ |
| **Backlinks overview** | ❌ | ✅ |
| **Referring domains by authority** | ❌ | ✅ |
| **Keyword research + related terms** | ❌ | ✅ |
| **Semrush data in PDF + Excel** | ❌ | ✅ |

---

## 🔧 Setup

### Step 1 — Clone and install

```bash
git clone https://github.com/yourusername/udit-seo-pro.git
cd udit-seo-pro
pip install -r requirements.txt
```

### Step 2 — Add your Semrush API key

```bash
cp .env.example .env
```

Open `.env` and fill in:

```env
SEMRUSH_API_KEY=your_key_here
SEMRUSH_DATABASE=in
```

> Get your API key: semrush.com → Profile → API → Generate Key
> Database options: `in` (India), `us`, `uk`, `au`, `ca`, `de`, `fr`, and more

### Step 3 — Run

```bash
python seo_audit.py https://yoursite.com
```

---

## 💻 Usage

```bash
# Full audit with Semrush
python seo_audit.py https://yoursite.com

# With keyword research
python seo_audit.py https://yoursite.com --keyword "sports betting india"

# Custom output name
python seo_audit.py https://yoursite.com --output brand_audit_april

# Skip Semrush (on-page only)
python seo_audit.py https://yoursite.com --no-semrush

# Different country database
python seo_audit.py https://yoursite.com --database us

# Demo mode (no URL needed)
python seo_audit.py --demo
```

---

## 📊 Semrush Data Pulled (6 API Calls)

| Data | What You Get |
|------|-------------|
| Domain Overview | Authority Score, organic traffic, keyword count, traffic value |
| Organic Keywords | Top 30 keywords with position, volume, CPC, traffic % |
| Competitors | Top 10 competing domains with common keywords + traffic |
| Backlinks Overview | Total backlinks, referring domains, follow/nofollow split |
| Referring Domains | Top 15 domains linking to you, ranked by authority |
| Keyword Research | Seed keyword volume, difficulty + 20 related terms |

---

## 📄 Output

### PDF Report (11 pages)
```
Page 1   — Cover with score ring + EEAT scores
Page 2   — Semrush domain intelligence
Page 3   — Top keywords + competitor table
Page 4   — Critical issues + warnings
Page 5   — CORE-EEAT 80-item scorecard
Pages 6-9 — Detailed per-module findings
Page 10  — Content brief + optimization guide
Page 11  — 4-phase SEO action plan
```

### Excel Workbook (9 sheets)
```
Sheet 1 — Executive Summary
Sheet 2 — All Issues (color-coded)
Sheet 3 — Passed Checks
Sheet 4 — Semrush Data (keywords, competitors, backlinks)
Sheet 5 — 4-Phase SEO Plan
Sheet 6 — CORE-EEAT Scorecard
Sheet 7 — Content Brief
Sheet 8 — Raw Data
Sheet 9 — Score Chart
```

---

## 🔬 Full Audit Coverage (16 Modules)

Title, Meta Description, Headings, Content Quality (CORE-EEAT), Images, Schema/JSON-LD, Technical SEO, Open Graph, Links, Robots.txt, Sitemap, GEO/AI Search, Core Web Vitals, Mobile SEO, International SEO, Security.

---

## 🌐 Works on Any Website

8 bypass profiles tried automatically — handles bot blocking, geo restrictions (India, Bangladesh, UK, US), gzip/brotli compression, and gracefully continues if a page can't be fetched.

---

## 🔧 Project Structure

```
udit-seo-pro/
  seo_audit.py          ← Entry point
  .env.example          ← Add your Semrush key here
  requirements.txt      ← reportlab + openpyxl
  modules/
    crawler.py          ← Universal fetcher (8 bypass profiles)
    audits.py           ← 16 audit modules
    eeat.py             ← 80-item CORE-EEAT scorer
    content_brief.py    ← Content brief generator
    phases.py           ← 4-phase plan builder
  semrush/
    client.py           ← Semrush API v3 (6 endpoints)
  reports/
    pdf_report.py       ← 11-page PDF generator
    excel_report.py     ← 9-sheet Excel generator
```

---

## 🆓 Free Version

Don't have a Semrush account? Start with **[udit-seo-free](https://github.com/yourusername/udit-seo-free)** — all 16 modules, CORE-EEAT, content brief, and 4-phase plan with zero API keys required.

---

## 📜 License

MIT

---

*Built with Python. Inspired by [AgriciDaniel/claude-seo](https://github.com/AgriciDaniel/claude-seo) and [aaron-he-zhu/seo-geo-claude-skills](https://github.com/aaron-he-zhu/seo-geo-claude-skills).*
