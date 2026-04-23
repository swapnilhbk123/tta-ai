# pdf_generator.py  —  Generalized TTA PDF Engine
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import Flowable
import io

# ── Brand Palette ────────────────────────────────────────────────
NAVY     = colors.HexColor("#0D2B4E")
GOLD     = colors.HexColor("#C9A84C")
LIGHT_BG = colors.HexColor("#F5F7FA")
MID_GREY = colors.HexColor("#8A9BB0")
WHITE    = colors.white
TEXT     = colors.HexColor("#1A1A2E")
ACCENT   = colors.HexColor("#E8F0F8")
BORDER   = colors.HexColor("#C8D4E3")
GREEN    = colors.HexColor("#2E7D32")
RED      = colors.HexColor("#C62828")

# ── Custom Flowables ─────────────────────────────────────────────
class SideBar(Flowable):
    """Decorative gold-stripe section header bar."""
    def __init__(self, w, h, label):
        Flowable.__init__(self)
        self.bw, self.bh, self.label = w, h, label

    def draw(self):
        self.canv.setFillColor(GOLD)
        self.canv.rect(0, 0, 5, self.bh, fill=1, stroke=0)
        self.canv.setFillColor(NAVY)
        self.canv.rect(5, 0, self.bw - 5, self.bh, fill=1, stroke=0)
        self.canv.setFillColor(WHITE)
        self.canv.setFont("Helvetica-Bold", 10)
        self.canv.drawString(14, self.bh / 2 - 4, self.label)

    def wrap(self, *args):
        return self.bw, self.bh

class GoldDivider(Flowable):
    """Thin gold rule used between sections."""
    def __init__(self, w):
        Flowable.__init__(self)
        self._w = w

    def draw(self):
        self.canv.setStrokeColor(GOLD)
        self.canv.setLineWidth(1)
        self.canv.line(0, 0, self._w, 0)

    def wrap(self, *args):
        return self._w, 1

# ── Style Factory ────────────────────────────────────────────────
def make_styles():
    def s(name, **kw):
        return ParagraphStyle(name, **kw)

    return {
        "body":       s("BODY",      fontName="Helvetica",      fontSize=9,    textColor=TEXT,    leading=14, spaceAfter=3),
        "small":      s("SMALL",     fontName="Helvetica",      fontSize=8,    textColor=MID_GREY,leading=12),
        "bullet":     s("BULLET",    fontName="Helvetica",      fontSize=9,    textColor=TEXT,    leading=14, leftIndent=12, spaceAfter=2),
        "footer":     s("FOOTER",    fontName="Helvetica",      fontSize=8.5,  textColor=NAVY,    alignment=TA_CENTER, leading=12),
        "cost_big":   s("COSTBIG",   fontName="Helvetica-Bold", fontSize=22,   textColor=GOLD,    alignment=TA_CENTER),
        "cost_label": s("COSTLABEL", fontName="Helvetica-Bold", fontSize=9,    textColor=WHITE,   alignment=TA_CENTER),
        "tnc":        s("TNC",       fontName="Helvetica",      fontSize=8,    textColor=MID_GREY,leading=13),
        "intro":      s("INTRO",     fontName="Helvetica",      fontSize=9,    textColor=TEXT,    leading=15, spaceAfter=4),
    }

# ── Reusable Table Builders ──────────────────────────────────────
def kv_table(pairs, usable):
    """Horizontal key-value summary bar (e.g. dates, pax, nights)."""
    col_w = usable / len(pairs)
    kh = ParagraphStyle("kh", fontName="Helvetica-Bold", fontSize=8,  textColor=NAVY)
    kv = ParagraphStyle("kv", fontName="Helvetica",      fontSize=9,  textColor=TEXT)
    data = [
        [Paragraph(f"<b>{k}</b>", kh) for k, _ in pairs],
        [Paragraph(v, kv)              for _, v in pairs],
    ]
    t = Table(data, colWidths=[col_w] * len(pairs))
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), ACCENT),
        ("BOX",         (0, 0), (-1,-1), 0.4, BORDER),
        ("INNERGRID",   (0, 0), (-1,-1), 0.3, BORDER),
        ("ALIGN",       (0, 0), (-1,-1), "CENTER"),
        ("VALIGN",      (0, 0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",  (0, 0), (-1,-1), 4),
        ("BOTTOMPADDING",(0, 0), (-1,-1), 4),
    ]))
    return t

def day_card(styles, day_num, date_str, location, activity, detail_lines):
    """Single day block: dark header + bullet body."""
    usable = A4[0] - 30 * mm
    dn  = ParagraphStyle("dn", fontName="Helvetica-Bold", fontSize=9,   textColor=WHITE)
    dd  = ParagraphStyle("dd", fontName="Helvetica",      fontSize=8,   textColor=GOLD)
    dl  = ParagraphStyle("dl", fontName="Helvetica-Bold", fontSize=9,   textColor=WHITE)
    act = ParagraphStyle("act",fontName="Helvetica-Bold", fontSize=9.5, textColor=NAVY, leading=14)

    header_data = [[
        Paragraph(f"<b>{day_num}</b>", dn),
        Paragraph(date_str, dd),
        Paragraph(f"<b>{location.upper()}</b>", dl),
    ]]
    header = Table(header_data, colWidths=[25 * mm, 50 * mm, usable - 75 * mm])
    header.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1,-1), NAVY),
        ("VALIGN",       (0, 0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (-1,-1), 8),
        ("TOPPADDING",   (0, 0), (-1,-1), 5),
        ("BOTTOMPADDING",(0, 0), (-1,-1), 5),
    ]))

    body_rows = [[Paragraph(f"<b>&#9670; {activity}</b>", act)]]
    for line in detail_lines:
        body_rows.append([Paragraph(f"&nbsp;&nbsp;&#8226; {line}", styles["bullet"])])

    body = Table(body_rows, colWidths=[usable])
    body.setStyle(TableStyle([
        ("BOX",         (0, 0), (-1,-1), 0.4, BORDER),
        ("LEFTPADDING", (0, 0), (-1,-1), 10),
        ("TOPPADDING",  (0, 0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0), (-1,-1), 4),
    ]))

    return KeepTogether([header, body, Spacer(1, 4 * mm)])

def build_pdf(data: dict) -> bytes:
    """Build and return a PDF as bytes."""
    buf = io.BytesIO()
    usable = A4[0] - 30 * mm
    st = make_styles()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=12 * mm, bottomMargin=14 * mm,
    )
    story = []

    # ── 1. HEADER BANNER ────────────────────────────────────────
    title_para = ParagraphStyle(
        "qt", fontName="Helvetica-Bold", fontSize=14,
        textColor=WHITE, leading=18,
    )
    sub_para = ParagraphStyle(
        "qs", fontName="Helvetica", fontSize=8, textColor=GOLD,
    )
    company_para = ParagraphStyle(
        "qc", fontName="Helvetica-Bold", fontSize=10, textColor=GOLD,
        alignment=TA_CENTER,
    )
    subtitle_html = (
        f"<font size=8 color='#C9A84C'>{data.get('trip_subtitle','').upper()}</font>"
        if data.get("trip_subtitle") else ""
    )
    title_content = data.get("trip_title", "TRAVEL ITINERARY").upper()
    if subtitle_html:
        title_content += f"<br/>{subtitle_html}"

    header_data = [[
        Paragraph(title_content, title_para),
        Paragraph(data.get("company_name", "TTA Group").upper(), company_para),
    ]]
    htable = Table(header_data, colWidths=[usable - 55 * mm, 55 * mm])
    htable.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1,-1), NAVY),
        ("VALIGN",       (0, 0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (-1,-1), 12),
        ("TOPPADDING",   (0, 0), (-1,-1), 10),
        ("BOTTOMPADDING",(0, 0), (-1,-1), 10),
    ]))
    story.append(htable)
    story.append(Spacer(1, 2 * mm))
    story.append(HRFlowable(width=usable, thickness=2, color=GOLD))
    story.append(Spacer(1, 3 * mm))

    # ── 2. INTRO TEXT ────────────────────────────────────────────
    if data.get("intro_text"):
        story.append(Paragraph(data["intro_text"], st["intro"]))
        story.append(Spacer(1, 2 * mm))

    # ── 3. TRIP SUMMARY BAR ──────────────────────────────────────
    summary_pairs = [
        ("Start Date",  data.get("start_date", "-")),
        ("Passengers",  data.get("num_pax", "-")),
        ("Total Stay",  data.get("total_nights", "-")),
        ("Package Type",data.get("trip_type", "Land Package")),
    ]
    story.append(kv_table(summary_pairs, usable))
    story.append(Spacer(1, 5 * mm))

    # ── 4. COST BOX ──────────────────────────────────────────────
    currency    = data.get("currency", "USD")
    total_cost  = data.get("total_cost", "0")
    num_pax     = data.get("num_pax", "")
    per_pax     = data.get("per_pax_cost", "")

    cost_label_left  = "TOTAL GROUP COST"
    cost_label_right = f"FOR {num_pax}" if num_pax else ""
    cost_display     = f"{currency} {total_cost}"

    if per_pax:
        cost_display     = f"{currency} {total_cost}"
        cost_label_right = f"FOR {num_pax}  |  {currency} {per_pax} / PAX" if num_pax else f"{currency} {per_pax} / PAX"

    cost_data = [[
        Paragraph(cost_label_left,  st["cost_label"]),
        Paragraph(cost_display,     st["cost_big"]),
        Paragraph(cost_label_right, st["cost_label"]),
    ]]
    cost_tbl = Table(cost_data, colWidths=[usable / 3] * 3, rowHeights=[18 * mm])
    cost_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1,-1), NAVY),
        ("VALIGN",     (0, 0), (-1,-1), "MIDDLE"),
        ("ALIGN",      (0, 0), (-1,-1), "CENTER"),
    ]))
    story.append(cost_tbl)

    if data.get("roe_note"):
        story.append(Spacer(1, 1 * mm))
        story.append(Paragraph(
            f"<b>ROE Note:</b> {data['roe_note']}", st["small"]
        ))
    story.append(Spacer(1, 5 * mm))

    # ── 5. OPTIONAL COST BREAKDOWN ───────────────────────────────
    if data.get("cost_items"):
        story.append(SideBar(usable, 18, "  COST BREAKDOWN"))
        story.append(Spacer(1, 2 * mm))
        ctbl = cost_breakdown_table(data["cost_items"], usable)
        if ctbl:
            story.append(ctbl)
        story.append(Spacer(1, 5 * mm))

    # ── 6. HOTELS ────────────────────────────────────────────────
    if data.get("hotels"):
        story.append(SideBar(usable, 18, "  ACCOMMODATION OVERVIEW"))
        story.append(Spacer(1, 2 * mm))
        story.append(hotel_table(data["hotels"], usable))
        meal_note = data.get("breakfast_note", "Daily Breakfast is included at all hotels.")
        story.append(Paragraph(f"<i>{meal_note}</i>", st["small"]))
        story.append(Spacer(1, 5 * mm))

    # ── 7. DAY-WISE ITINERARY ────────────────────────────────────
    if data.get("days"):
        story.append(SideBar(usable, 18, "  DETAILED DAY-WISE ITINERARY"))
        story.append(Spacer(1, 3 * mm))
        for d in data["days"]:
            story.append(day_card(
                st,
                d.get("day_num", "Day"),
                d.get("date", ""),
                d.get("location", ""),
                d.get("activity", ""),
                d.get("details", []),
            ))

    # ── 8. INCLUSIONS ────────────────────────────────────────────
    if data.get("inclusions"):
        story.append(Spacer(1, 2 * mm))
        story.append(SideBar(usable, 18, "  WHAT IS INCLUDED"))
        story.append(Spacer(1, 3 * mm))
        for item in data["inclusions"]:
            story.append(Paragraph(
                f"<font color='#2E7D32'><b>+</b></font>  {item}", st["body"]
            ))
        story.append(Spacer(1, 3 * mm))

    # ── 9. EXCLUSIONS ────────────────────────────────────────────
    if data.get("exclusions"):
        story.append(SideBar(usable, 18, "  WHAT IS NOT INCLUDED"))
        story.append(Spacer(1, 3 * mm))
        for item in data["exclusions"]:
            story.append(Paragraph(
                f"<font color='#C62828'><b>-</b></font>  {item}", st["body"]
            ))
        story.append(Spacer(1, 3 * mm))

    # ── 10. TERMS & CONDITIONS ───────────────────────────────────
    if data.get("tnc"):
        story.append(SideBar(usable, 18, "  TERMS & CONDITIONS"))
        story.append(Spacer(1, 3 * mm))
        for i, term in enumerate(data["tnc"], 1):
            story.append(Paragraph(f"{i}. {term}", st["tnc"]))
        story.append(Spacer(1, 3 * mm))

    # ── 11. FOOTER / CONTACT ─────────────────────────────────────
    story.append(Spacer(1, 3 * mm))
    story.append(GoldDivider(usable))
    story.append(Spacer(1, 3 * mm))
    story.append(SideBar(usable, 18, "  CONTACT US"))
    story.append(Spacer(1, 3 * mm))

    contact_parts = []
    if data.get("email"):   contact_parts.append(f"<b>Email:</b> {data['email']}")
    if data.get("phone"):   contact_parts.append(f"<b>Phone:</b> {data['phone']}")
    if data.get("website"): contact_parts.append(f"<b>Website:</b> {data['website']}")
    if contact_parts:
        story.append(Paragraph("  |  ".join(contact_parts), st["footer"]))

    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        f"Warmest regards from <b>{data.get('company_name', 'TTA Group')}</b>",
        st["footer"],
    ))

    doc.build(story)
    return buf.getvalue()
