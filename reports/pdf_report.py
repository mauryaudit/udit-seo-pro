"""
reports/pdf_report.py — udit-seo-pro
Professional multi-section PDF: cover + score ring, Semrush, critical issues,
CORE-EEAT scorecard, module findings, content brief, 4-phase plan.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether, Flowable
)

W, H = A4

DARK_NAVY  = colors.HexColor("#1A1A2E")
DARK_BLUE  = colors.HexColor("#1A4A8A")
GREEN      = colors.HexColor("#1A7A3A")
RED        = colors.HexColor("#CC2200")
ORANGE     = colors.HexColor("#DD7700")
BLUE_INFO  = colors.HexColor("#2244AA")
PURPLE     = colors.HexColor("#6A1A6A")
LIGHT_BG   = colors.HexColor("#F5F5FC")
MID_GRAY   = colors.HexColor("#DDDDEE")
WHITE      = colors.white

PHASE_COLORS = {1: DARK_NAVY, 2: DARK_BLUE, 3: colors.HexColor("#0A6A3A"), 4: PURPLE}

MODULE_LABELS = {
    "title": "Title Tag", "meta_description": "Meta Description",
    "headings": "Heading Structure", "content": "Content Quality (E-E-A-T)",
    "images": "Image Optimization", "schema": "Schema / Structured Data",
    "technical": "Technical SEO", "open_graph": "Open Graph / Social",
    "links": "Links", "robots_txt": "Robots.txt",
    "sitemap": "XML Sitemap", "geo_aeo": "GEO / AI Search",
    "core_web_vitals": "Core Web Vitals", "mobile": "Mobile SEO",
    "international": "International SEO", "security": "Security",
}

def _sh(s):
    if not isinstance(s, (int, float)): return "#888888"
    return "#1A7A3A" if s >= 80 else ("#DD7700" if s >= 60 else "#CC2200")

def _sc(s):
    return GREEN if s >= 80 else (ORANGE if s >= 60 else RED)

def _sev_hex(s):
    return {"critical": "#CC2200", "warning": "#DD7700"}.get(s, "#2244AA")

def _sev_lbl(s):
    return {"critical": "CRITICAL", "warning": "WARNING"}.get(s, "INFO")

def _tbl_base(hc=None):
    hc = hc or DARK_NAVY
    return [
        ("BACKGROUND",    (0, 0), (-1, 0), hc),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ("GRID",          (0, 0), (-1, -1), 0.4, MID_GRAY),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
    ]

def make_styles():
    base = getSampleStyleSheet()
    def ps(name, **kw): return ParagraphStyle(name, parent=base["Normal"], **kw)
    return {
        "title":    ps("T",  fontSize=22, textColor=DARK_NAVY, leading=26, spaceAfter=3),
        "subtitle": ps("ST", fontSize=9,  textColor=colors.HexColor("#666677"), spaceAfter=2),
        "h1":       ps("H1", fontSize=13, textColor=DARK_NAVY, spaceBefore=10, spaceAfter=5, fontName="Helvetica-Bold"),
        "h2":       ps("H2", fontSize=10, textColor=colors.HexColor("#333366"), spaceBefore=7, spaceAfter=4, fontName="Helvetica-Bold"),
        "body":     ps("B",  fontSize=9,  leading=13),
        "small":    ps("SM", fontSize=8,  leading=11, textColor=colors.HexColor("#555555")),
        "pass_":    ps("P",  fontSize=9,  leading=12, textColor=GREEN, leftIndent=8),
        "footer":   ps("F",  fontSize=7,  textColor=colors.HexColor("#AAAAAA"), alignment=TA_CENTER),
    }


class ScoreRing(Flowable):
    """Draws a score ring using ReportLab canvas primitives."""
    def __init__(self, score, w=48*mm, h=48*mm):
        super().__init__()
        self.score = score
        self.width = w
        self.height = h

    def draw(self):
        cx, cy = self.width / 2, self.height / 2
        r_out = min(cx, cy) - 2*mm
        r_in  = r_out - 7*mm
        score = max(0, min(100, self.score))
        sc    = _sc(score)

        # Grey background
        self.canv.setFillColor(colors.HexColor("#EEEEEE"))
        self.canv.circle(cx, cy, r_out, fill=1, stroke=0)
        # Score arc
        self.canv.setFillColor(sc)
        self.canv.wedge(cx-r_out, cy-r_out, cx+r_out, cy+r_out,
                        90 - (score/100)*360, (score/100)*360, fill=1, stroke=0)
        # White hole
        self.canv.setFillColor(WHITE)
        self.canv.circle(cx, cy, r_in, fill=1, stroke=0)
        # Labels
        self.canv.setFillColor(sc)
        self.canv.setFont("Helvetica-Bold", 16)
        self.canv.drawCentredString(cx, cy + 1.5*mm, str(score))
        self.canv.setFillColor(colors.HexColor("#888888"))
        self.canv.setFont("Helvetica", 7)
        self.canv.drawCentredString(cx, cy - 4*mm, "/ 100")


def generate_pdf(results, phase_plan, semrush_data, output_path,
                 eeat_result=None, content_brief=None):

    doc = SimpleDocTemplate(output_path, pagesize=A4,
        topMargin=16*mm, bottomMargin=16*mm,
        leftMargin=17*mm, rightMargin=17*mm,
        title="SEO Audit Report", author="udit-seo-pro")

    S  = make_styles()
    story = []
    overall  = results["overall_score"]
    critical = len([i for i in results["all_issues"] if i["severity"] == "critical"])
    warnings = len([i for i in results["all_issues"] if i["severity"] == "warning"])
    infos    = len([i for i in results["all_issues"] if i["severity"] == "info"])
    passes   = len(results["all_passes"])

    def hr(c=MID_GRAY, t=1):
        return HRFlowable(width="100%", thickness=t, color=c)

    def section(title, c=DARK_NAVY):
        story.append(Spacer(1, 2*mm))
        story.append(Paragraph(title, S["h1"]))
        story.append(hr(c))
        story.append(Spacer(1, 3*mm))

    # ─── COVER ───────────────────────────────────────────────────────────────
    banner = Table([[
        Paragraph('<font color="white" size="17"><b>SEO AUDIT REPORT</b></font>',
                  ParagraphStyle("BH", fontSize=17, textColor=WHITE, leading=21)),
        Paragraph(f'<font color="#AAAACC" size="8">{results["url"]}</font><br/>'
                  f'<font color="#888899" size="7">{results["audit_date"]}</font>',
                  ParagraphStyle("BS", fontSize=8, textColor=WHITE, alignment=2, leading=10)),
    ]], colWidths=[110*mm, 57*mm])
    banner.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), DARK_NAVY),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (0, 0), 10),
    ]))
    story.append(banner)
    story.append(Spacer(1, 4*mm))

    # Score ring + stat cards
    stat_rows = [
        [Paragraph(f'<font size="14" color="#CC2200"><b>{critical}</b></font><br/><font size="7" color="#888888">Critical</font>', S["body"])],
        [Paragraph(f'<font size="14" color="#DD7700"><b>{warnings}</b></font><br/><font size="7" color="#888888">Warnings</font>', S["body"])],
        [Paragraph(f'<font size="14" color="#2244AA"><b>{infos}</b></font><br/><font size="7" color="#888888">Info</font>', S["body"])],
        [Paragraph(f'<font size="14" color="#1A7A3A"><b>{passes}</b></font><br/><font size="7" color="#888888">Passed</font>', S["body"])],
    ]
    stats = Table(stat_rows, colWidths=[26*mm])
    stats.setStyle(TableStyle([
        ("ALIGN",    (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",   (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT_BG, WHITE, LIGHT_BG, WHITE]),
        ("BOX",      (0, 0), (-1, -1), 0.5, MID_GRAY),
        ("INNERGRID",(0, 0), (-1, -1), 0.3, MID_GRAY),
    ]))

    eeat_s = eeat_result["total_score"] if eeat_result else "—"
    eeat_g = eeat_result["grade"] if eeat_result else "—"
    eeat_C = eeat_result["summary"].get("C", 0) if eeat_result else 0
    eeat_O = eeat_result["summary"].get("O", 0) if eeat_result else 0
    eeat_R = eeat_result["summary"].get("R", 0) if eeat_result else 0
    eeat_E = eeat_result["summary"].get("E", 0) if eeat_result else 0

    eeat_box = Table([
        [Paragraph(f'<font size="13" color="{_sh(eeat_s if isinstance(eeat_s, int) else 50)}"><b>{eeat_s}</b></font><br/><font size="7" color="#888888">CORE-EEAT / Grade {eeat_g}</font>', S["body"])],
        [Paragraph(f'<font size="8"><b>C:{eeat_C}  O:{eeat_O}  R:{eeat_R}  E:{eeat_E}</b></font>', S["small"])],
    ], colWidths=[57*mm])
    eeat_box.setStyle(TableStyle([
        ("ALIGN",    (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",   (0, 0), (-1, -1), "MIDDLE"),
        ("BOX",      (0, 0), (-1, -1), 0.5, MID_GRAY),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT_BG, WHITE]),
        ("INNERGRID",(0, 0), (-1, -1), 0.3, MID_GRAY),
    ]))

    cover_row = Table([[ScoreRing(overall), stats, eeat_box]],
                      colWidths=[50*mm, 28*mm, 60*mm])
    cover_row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",  (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(cover_row)
    story.append(Spacer(1, 4*mm))

    # Module grid (2 columns) on cover
    mini = [["Module", "Score", "Module", "Score"]]
    mod_list = list(MODULE_LABELS.items())
    for i in range(0, len(mod_list), 2):
        k1, l1 = mod_list[i]
        s1 = results["modules"].get(k1, {}).get("score", 0)
        if i+1 < len(mod_list):
            k2, l2 = mod_list[i+1]
            s2 = results["modules"].get(k2, {}).get("score", 0)
            mini.append([l1, Paragraph(f'<font color="{_sh(s1)}"><b>{s1}</b></font>', S["body"]),
                         l2, Paragraph(f'<font color="{_sh(s2)}"><b>{s2}</b></font>', S["body"])])
        else:
            mini.append([l1, Paragraph(f'<font color="{_sh(s1)}"><b>{s1}</b></font>', S["body"]), "", ""])

    mini_tbl = Table(mini, colWidths=[67*mm, 18*mm, 67*mm, 18*mm])
    mini_tbl.setStyle(TableStyle(_tbl_base() + [
        ("ALIGN", (0, 0), (0, -1), "LEFT"), ("ALIGN", (2, 0), (2, -1), "LEFT"),
        ("LEFTPADDING", (0, 0), (0, -1), 6), ("LEFTPADDING", (2, 0), (2, -1), 6),
    ]))
    story.append(mini_tbl)
    story.append(PageBreak())

    # ─── SEMRUSH ─────────────────────────────────────────────────────────────
    semrush_ok = any(v.get("ok") for v in semrush_data.values() if isinstance(v, dict))
    if semrush_ok:
        section("Semrush Domain Intelligence")
        sm_ov = semrush_data.get("domain_overview", {})
        if sm_ov.get("ok") and sm_ov.get("summary"):
            s = sm_ov["summary"]
            rows = [
                ["Authority Score", s.get("authority_score","N/A"), "Organic Keywords", s.get("organic_keywords","N/A")],
                ["Monthly Organic Traffic", s.get("organic_traffic","N/A"), "Traffic Value", f"${s.get('organic_cost','N/A')}"],
                ["Paid Keywords", s.get("adwords_keywords","N/A"), "Semrush Rank", s.get("semrush_rank","N/A")],
            ]
            ov_tbl = Table(rows, colWidths=[52*mm, 33*mm, 52*mm, 33*mm])
            ov_tbl.setStyle(TableStyle([
                ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME",  (2, 0), (2, -1), "Helvetica-Bold"),
                ("FONTSIZE",  (0, 0), (-1, -1), 9),
                ("GRID",      (0, 0), (-1, -1), 0.4, MID_GRAY),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT_BG, WHITE, LIGHT_BG]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("ALIGN", (1, 0), (1, -1), "CENTER"), ("ALIGN", (3, 0), (3, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (0, -1), 6), ("LEFTPADDING", (2, 0), (2, -1), 6),
            ]))
            story.append(ov_tbl)
            story.append(Spacer(1, 4*mm))

        kw = semrush_data.get("organic_keywords", {})
        if kw.get("ok") and kw.get("data"):
            story.append(Paragraph("Top Organic Keywords", S["h2"]))
            kw_rows = [["Keyword", "Position", "Search Volume", "CPC", "Traffic %"]]
            for row in kw["data"][:20]:
                kw_rows.append([row.get("Ph", row.get("Keyword","")),
                                 row.get("Po", row.get("Position","")),
                                 row.get("Nq", row.get("Search Volume","")),
                                 f"${row.get('Cp', row.get('CPC','?'))}",
                                 row.get("Tr", row.get("Traffic (%)","")),])
            t = Table(kw_rows, colWidths=[65*mm, 22*mm, 28*mm, 22*mm, 28*mm])
            t.setStyle(TableStyle(_tbl_base(DARK_BLUE) + [
                ("ALIGN", (0, 1), (0, -1), "LEFT"), ("LEFTPADDING", (0, 0), (0, -1), 5),
            ]))
            story.append(t)
            story.append(Spacer(1, 4*mm))

        comp = semrush_data.get("competitors", {})
        if comp.get("ok") and comp.get("data"):
            story.append(Paragraph("Top Organic Competitors", S["h2"]))
            c_rows = [["Domain", "Common Keywords", "Their Organic KWs", "Their Traffic"]]
            for row in comp["data"][:8]:
                c_rows.append([row.get("Dn", row.get("Domain","")),
                                row.get("Np", row.get("Common Keywords","")),
                                row.get("Or", row.get("Organic Keywords","")),
                                row.get("Ot", row.get("Organic Traffic",""))])
            t = Table(c_rows, colWidths=[60*mm, 35*mm, 35*mm, 35*mm])
            t.setStyle(TableStyle(_tbl_base(DARK_BLUE) + [
                ("ALIGN", (0, 1), (0, -1), "LEFT"), ("LEFTPADDING", (0, 0), (0, -1), 5),
            ]))
            story.append(t)
        story.append(PageBreak())

    # ─── CRITICAL ISSUES ────────────────────────────────────────────────────
    section("Critical Issues & Warnings", RED)
    ci = [i for i in results["all_issues"] if i["severity"] == "critical"]
    wi = [i for i in results["all_issues"] if i["severity"] == "warning"]

    if ci:
        rows = [["Module", "Issue"]]
        for i in ci:
            rows.append([MODULE_LABELS.get(i["module"], i["module"]), i["msg"]])
        t = Table(rows, colWidths=[50*mm, 115*mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), RED), ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#FFF0EE"), WHITE]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#FFCCCC")),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"), ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 4*mm))
    else:
        story.append(Paragraph("<font color='#1A7A3A'><b>No critical issues found.</b></font>", S["body"]))
        story.append(Spacer(1, 3*mm))

    if wi:
        story.append(Paragraph("Warnings", S["h2"]))
        rows = [["Module", "Issue"]]
        for i in wi:
            rows.append([MODULE_LABELS.get(i["module"], i["module"]), i["msg"]])
        t = Table(rows, colWidths=[50*mm, 115*mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), ORANGE), ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#FFF8EE"), WHITE]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#FFDDAA")),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"), ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(t)
    story.append(PageBreak())

    # ─── CORE-EEAT ─────────────────────────────────────────────────────────
    if eeat_result:
        section("CORE-EEAT Content Quality Scorecard")
        dims = eeat_result.get("dimensions", {})
        dim_labels = {"C": "Comprehensiveness", "O": "Originality", "R": "Relevance", "E": "E-E-A-T"}

        dim_cells = []
        for d, dl in dim_labels.items():
            ds = eeat_result["summary"].get(d, 0)
            dim_cells.append(Paragraph(
                f'<font size="15" color="{_sh(ds)}"><b>{ds}</b></font><br/><font size="7" color="#888888">{dl}</font>',
                ParagraphStyle("DC", fontSize=10, alignment=TA_CENTER)))

        dim_cells.append(Paragraph(
            f'<font size="15" color="{_sh(eeat_result["total_score"])}"><b>{eeat_result["total_score"]}</b></font>'
            f'<br/><font size="7" color="#888888">Total — Grade {eeat_result["grade"]}</font>',
            ParagraphStyle("DC2", fontSize=10, alignment=TA_CENTER)))

        top = Table([dim_cells], colWidths=[34*mm]*5)
        top.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX",   (0, 0), (-1, -1), 1, MID_GRAY), ("INNERGRID", (0, 0), (-1, -1), 0.5, MID_GRAY),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT_BG]),
            ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(top)
        story.append(Spacer(1, 4*mm))

        for d_key, d_label in dim_labels.items():
            dd = dims.get(d_key, {})
            d_score = dd.get("score", 0)
            story.append(Paragraph(f'<b>{d_label}</b> — <font color="{_sh(d_score)}">{d_score}/100</font>', S["h2"]))
            item_rows = [["ID", "Check", "Result"]]
            for item in dd.get("items", []):
                sv = item["score"]
                s_str = "Pass" if sv >= 1 else ("Partial" if sv >= 0.5 else "Fail")
                s_c = "#1A7A3A" if sv >= 1 else ("#DD7700" if sv >= 0.5 else "#CC2200")
                item_rows.append([item["id"], item["label"],
                                   Paragraph(f'<font color="{s_c}"><b>{s_str}</b></font>', S["body"])])
            it = Table(item_rows, colWidths=[12*mm, 130*mm, 23*mm])
            it.setStyle(TableStyle(_tbl_base() + [
                ("ALIGN", (1, 0), (1, -1), "LEFT"), ("LEFTPADDING", (1, 0), (1, -1), 5),
            ]))
            story.append(it)
            story.append(Spacer(1, 3*mm))
        story.append(PageBreak())

    # ─── DETAILED MODULE FINDINGS ────────────────────────────────────────────
    section("Detailed Module Findings")
    for mod_key, label in MODULE_LABELS.items():
        mod = results["modules"].get(mod_key, {})
        if not mod:
            continue
        s = mod.get("score", 0)

        hdr = Table([[
            Paragraph(f"<b>{label}</b>", ParagraphStyle("MH", fontSize=10, textColor=DARK_NAVY)),
            Paragraph(f'<font color="{_sh(s)}"><b>{s}/100</b></font>',
                      ParagraphStyle("MS", fontSize=10, alignment=2)),
        ]], colWidths=[140*mm, 25*mm])
        hdr.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
            ("LEFTPADDING", (0, 0), (0, 0), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(KeepTogether([hdr]))
        story.append(Spacer(1, 1.5*mm))

        for key, lbl in [("title","Title"),("description","Description"),("word_count","Words"),
                          ("ttfb_ms","TTFB"),("page_size_bytes","Page Size"),("total","Images"),
                          ("missing_alt_count","Missing Alt"),("count","Schema Blocks"),
                          ("types","Schema Types"),("internal_count","Internal Links"),
                          ("external_count","External Links"),("url_count","Sitemap URLs"),
                          ("hreflang_count","Hreflang")]:
            val = mod.get(key)
            if val is not None and val != "" and val != []:
                disp = (f"{val//1000}KB" if key=="page_size_bytes" and isinstance(val,int) else
                        f"{val}ms" if key=="ttfb_ms" and isinstance(val,int) else
                        ", ".join(val) if isinstance(val,list) else str(val))
                story.append(Paragraph(f"<b>{lbl}:</b> {disp[:100]}", S["small"]))

        for issue in mod.get("issues", []):
            story.append(Paragraph(
                f'<font color="{_sev_hex(issue["severity"])}"><b>[{_sev_lbl(issue["severity"])}]</b></font> {issue["msg"]}',
                S["body"]))
        for p in mod.get("passes", []):
            story.append(Paragraph(f"<font color='#1A7A3A'>&#10003;</font> {p}", S["pass_"]))
        story.append(Spacer(1, 3*mm))

    story.append(PageBreak())

    # ─── CONTENT BRIEF ───────────────────────────────────────────────────────
    if content_brief:
        section("Content Brief & Optimization Guide")
        cb = content_brief
        brief_rows = [
            ["URL", cb.get("url","")[:80]],
            ["Current H1", cb.get("current_h1","")[:80]],
            ["Primary Keyword", cb.get("primary_keyword","")],
            ["Secondary Keywords", ", ".join(cb.get("secondary_keywords",[]))[:80]],
            ["LSI / Semantic Terms", ", ".join(cb.get("lsi_terms",[]))[:80]],
            ["Current Word Count", str(cb.get("current_word_count",0))],
            ["Target Word Count", cb.get("target_word_count","")],
            ["CORE-EEAT Total", f"{cb.get('eeat_total','N/A')}/100 — Grade {cb.get('content_grade','N/A')}"],
            ["C / O / R / E", f"C:{cb['eeat_scores'].get('C',0)}  O:{cb['eeat_scores'].get('O',0)}  R:{cb['eeat_scores'].get('R',0)}  E:{cb['eeat_scores'].get('E',0)}"],
        ]
        bt = Table(brief_rows, colWidths=[52*mm, 113*mm])
        bt.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT_BG, WHITE]),
            ("GRID", (0, 0), (-1, -1), 0.4, MID_GRAY),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"), ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(bt)
        story.append(Spacer(1, 4*mm))

        story.append(Paragraph("Recommended H2 Structure", S["h2"]))
        for i, h2 in enumerate(cb.get("recommended_h2_structure",[]), 1):
            story.append(Paragraph(f"{i}. {h2}", S["body"]))
        story.append(Spacer(1, 3*mm))

        if cb.get("schema_to_implement"):
            story.append(Paragraph("Schema Markup to Add", S["h2"]))
            for st in cb["schema_to_implement"]:
                story.append(Paragraph(f"• {st}", S["body"]))
            story.append(Spacer(1, 3*mm))

        if cb.get("geo_optimizations"):
            story.append(Paragraph("GEO / AI Search Optimizations", S["h2"]))
            for a in cb["geo_optimizations"]:
                story.append(Paragraph(f"• {a}", S["body"]))
            story.append(Spacer(1, 3*mm))

        if cb.get("priority_actions"):
            story.append(Paragraph("Priority Actions", S["h2"]))
            for i, action in enumerate(cb["priority_actions"], 1):
                c_ = "#CC2200" if "[CRITICAL]" in action else "#DD7700"
                clean = action.replace("[CRITICAL] ","").replace("[WARNING] ","")
                story.append(Paragraph(f'<font color="{c_}"><b>{i}.</b></font> {clean}', S["body"]))

        story.append(PageBreak())

    # ─── 4-PHASE PLAN ────────────────────────────────────────────────────────
    section("4-Phase SEO Action Plan")
    for phase_num, phase_data in phase_plan.items():
        pc = PHASE_COLORS[phase_num]
        ph_hdr = Table([[Paragraph(
            f'<font color="white" size="11"><b>Phase {phase_num}: {phase_data["name"]}</b></font>'
            f'<br/><font color="#CCCCEE" size="8">{phase_data["timeframe"]} — {phase_data["goal"]}</font>',
            ParagraphStyle("PH", fontSize=11, textColor=WHITE, leading=15))
        ]], colWidths=[170*mm])
        ph_hdr.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), pc),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ]))
        story.append(ph_hdr)
        story.append(Spacer(1, 2*mm))
        tasks = phase_data.get("tasks", [])
        if tasks:
            t_rows = [["#", "Task", "Source", "Effort", "Impact"]]
            for i, task in enumerate(tasks, 1):
                t_rows.append([str(i), task["task"][:88], task.get("source","")[:38],
                                task.get("effort",""), task.get("impact","")])
            tt = Table(t_rows, colWidths=[8*mm, 88*mm, 40*mm, 17*mm, 17*mm])
            tt.setStyle(TableStyle(_tbl_base(pc) + [
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (3, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (1, 0), (1, -1), 5),
                ("WORDWRAP", (1, 0), (1, -1), True),
            ]))
            story.append(tt)
        story.append(Spacer(1, 5*mm))

    story.append(Spacer(1, 4*mm))
    story.append(HRFlowable(width="100%", thickness=1, color=MID_GRAY))
    story.append(Paragraph(
        f"udit-seo-pro v1.0 | {results['audit_date']} | {results['url']}"
        " | Methodology: AgriciDaniel/claude-seo + aaron-he-zhu/seo-geo-claude-skills",
        S["footer"]
    ))

    doc.build(story)
    print(f"  PDF saved: {output_path}")
