"""Deterministic ReportLab PDF builder for synthetic AURORA-101 protocols."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from protocol215.fixtures import (
    PAGE_APPENDIX,
    PAGE_DATA,
    PAGE_DAY1_PK_FASTING,
    PAGE_DESIGN,
    PAGE_ECG,
    PAGE_ELIGIBILITY,
    PAGE_LAB,
    PAGE_OBJECTIVES,
    PAGE_SITE,
    PAGE_SOA,
    PAGE_SYNOPSIS,
    PAGE_TITLE,
    PAGE_TREATMENT,
    STUDY_ID,
    STUDY_TITLE,
)


def load_protocol_source(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ProtoTitle",
            parent=base["Title"],
            fontName="Times-Bold",
            fontSize=18,
            leading=22,
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "subtitle": ParagraphStyle(
            "ProtoSubtitle",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=12,
            leading=16,
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "h1": ParagraphStyle(
            "ProtoH1",
            parent=base["Heading1"],
            fontName="Times-Bold",
            fontSize=14,
            leading=18,
            spaceBefore=6,
            spaceAfter=8,
        ),
        "body": ParagraphStyle(
            "ProtoBody",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=10,
            leading=14,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
        ),
        "meta": ParagraphStyle(
            "ProtoMeta",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=10,
            leading=13,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "ProtoSmall",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=8,
            leading=10,
        ),
        "tablecell": ParagraphStyle(
            "ProtoCell",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=8,
            leading=10,
        ),
        "footer": ParagraphStyle(
            "ProtoFooter",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=8,
            alignment=TA_RIGHT,
        ),
        "banner": ParagraphStyle(
            "ProtoBanner",
            parent=base["Normal"],
            fontName="Times-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#8b1e1e"),
            spaceAfter=10,
        ),
    }


def _add_page_number(
    canvas: Any,
    doc: Any,
    *,
    version: str,
    study_id: str,
) -> None:
    canvas.saveState()
    page = canvas.getPageNumber()
    text = f"{study_id} Protocol {version}  |  Page {page}"
    canvas.setFont("Times-Roman", 8)
    canvas.drawRightString(letter[0] - 0.75 * inch, 0.5 * inch, text)
    canvas.drawString(0.75 * inch, 0.5 * inch, "SYNTHETIC — NOT FOR CLINICAL USE")
    canvas.restoreState()


def build_story(source: dict[str, Any]) -> list[Any]:
    styles = _styles()
    version = str(source["version"])
    story: list[Any] = []

    # Page 1 — Title
    story.append(Spacer(1, 1.5 * inch))
    story.append(Paragraph("SYNTHETIC CLINICAL PROTOCOL", styles["subtitle"]))
    story.append(Paragraph(STUDY_TITLE, styles["title"]))
    story.append(Paragraph(f"Study ID: {STUDY_ID}", styles["meta"]))
    story.append(Paragraph(f"Protocol Version: {version}", styles["meta"]))
    story.append(Paragraph(f"Document ID: {source['document_id']}", styles["meta"]))
    story.append(
        Paragraph("Sponsor: Synthetic Aurora Research Consortium (fictional)", styles["meta"])
    )
    story.append(Spacer(1, 0.4 * inch))
    story.append(
        Paragraph(
            "All names, contacts, sites, participants, and data in this document are fictional. "
            "This document is a proof-of-concept fixture for Protocol 215 and must never be used "
            "for real clinical, regulatory, or patient-care purposes.",
            styles["body"],
        )
    )
    if source.get("adversarial_banner"):
        story.append(Paragraph(str(source["adversarial_banner"]), styles["banner"]))
    story.append(PageBreak())  # -> page 2

    # Page 2 — Synopsis
    story.append(
        Paragraph(f"1. Synopsis  [{source['sections']['synopsis']['section_id']}]", styles["h1"])
    )
    for para in source["sections"]["synopsis"]["paragraphs"]:
        story.append(Paragraph(str(para), styles["body"]))
    story.append(PageBreak())  # -> 3

    # Page 3 — Objectives
    story.append(
        Paragraph(
            f"2. Objectives  [{source['sections']['objectives']['section_id']}]", styles["h1"]
        )
    )
    for para in source["sections"]["objectives"]["paragraphs"]:
        story.append(Paragraph(str(para), styles["body"]))
    story.append(PageBreak())

    # Page 4 — Design
    story.append(
        Paragraph(f"3. Study Design  [{source['sections']['design']['section_id']}]", styles["h1"])
    )
    for para in source["sections"]["design"]["paragraphs"]:
        story.append(Paragraph(str(para), styles["body"]))
    story.append(PageBreak())

    # Page 5 — Eligibility
    story.append(
        Paragraph(
            f"4. Eligibility Summary  [{source['sections']['eligibility']['section_id']}]",
            styles["h1"],
        )
    )
    for para in source["sections"]["eligibility"]["paragraphs"]:
        story.append(Paragraph(str(para), styles["body"]))
    story.append(PageBreak())

    # Page 6 — Treatment
    story.append(
        Paragraph(
            f"5. Treatment Overview  [{source['sections']['treatment']['section_id']}]",
            styles["h1"],
        )
    )
    for para in source["sections"]["treatment"]["paragraphs"]:
        story.append(Paragraph(str(para), styles["body"]))
    story.append(PageBreak())

    # Page 7 — SOA table
    story.append(
        Paragraph(
            f"6. Schedule of Activities  [{source['sections']['soa']['section_id']}]",
            styles["h1"],
        )
    )
    story.append(Paragraph(str(source["sections"]["soa"]["intro"]), styles["body"]))
    header = [Paragraph(h, styles["tablecell"]) for h in source["sections"]["soa"]["table_header"]]
    rows = [header]
    for row in source["sections"]["soa"]["table_rows"]:
        rows.append([Paragraph(str(c), styles["tablecell"]) for c in row])
    table = Table(rows, colWidths=[1.6 * inch, 1.0 * inch, 1.0 * inch, 1.0 * inch, 1.6 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d9e2dc")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(table)
    story.append(PageBreak())

    # Page 8 — Day 1 / PK / fasting
    day1 = source["sections"]["day1"]
    story.append(Paragraph(f"7. Day 1 Visit  [{day1['section_id']}]", styles["h1"]))
    for para in day1["paragraphs"]:
        story.append(Paragraph(str(para), styles["body"]))

    pk = source["sections"]["pk"]
    story.append(Paragraph(f"7.1 Pharmacokinetic Sampling  [{pk['section_id']}]", styles["h1"]))
    story.append(Paragraph(str(pk["intro"]), styles["body"]))
    for item in pk["timepoints"]:
        story.append(Paragraph(f"• {item}", styles["body"]))

    fasting = source["sections"]["fasting"]
    story.append(Paragraph(f"7.2 Post-Dose Fasting  [{fasting['section_id']}]", styles["h1"]))
    for para in fasting["paragraphs"]:
        story.append(Paragraph(str(para), styles["body"]))
    story.append(PageBreak())

    # Page 9 — ECG
    ecg = source["sections"]["ecg"]
    story.append(Paragraph(f"8. Electrocardiogram Schedule  [{ecg['section_id']}]", styles["h1"]))
    for para in ecg["paragraphs"]:
        story.append(Paragraph(str(para), styles["body"]))
    story.append(PageBreak())

    # Page 10 — Lab
    lab = source["sections"]["laboratory"]
    story.append(Paragraph(f"9. Laboratory Processing  [{lab['section_id']}]", styles["h1"]))
    for para in lab["paragraphs"]:
        story.append(Paragraph(str(para), styles["body"]))
    contact = source["sections"]["lab_contact"]
    story.append(
        Paragraph(f"9.1 Central Laboratory Contact  [{contact['section_id']}]", styles["h1"])
    )
    for para in contact["paragraphs"]:
        story.append(Paragraph(str(para), styles["body"]))
    story.append(PageBreak())

    # Page 11 — Site
    site = source["sections"]["site_responsibilities"]
    story.append(Paragraph(f"10. Site Responsibilities  [{site['section_id']}]", styles["h1"]))
    for para in site["paragraphs"]:
        story.append(Paragraph(str(para), styles["body"]))
    story.append(PageBreak())

    # Page 12 — Data
    data = source["sections"]["data_collection"]
    story.append(
        Paragraph(f"11. Data-Collection Requirements  [{data['section_id']}]", styles["h1"])
    )
    for para in data["paragraphs"]:
        story.append(Paragraph(str(para), styles["body"]))
    story.append(PageBreak())

    # Page 13 — Appendix
    appendix = source["sections"]["appendix"]
    story.append(Paragraph(f"12. Appendix  [{appendix['section_id']}]", styles["h1"]))
    for para in appendix["paragraphs"]:
        story.append(Paragraph(str(para), styles["body"]))
    story.append(
        Paragraph(
            f"Stable page map (generator contract): title={PAGE_TITLE}, synopsis={PAGE_SYNOPSIS}, "
            f"objectives={PAGE_OBJECTIVES}, design={PAGE_DESIGN}, eligibility={PAGE_ELIGIBILITY}, "
            f"treatment={PAGE_TREATMENT}, soa={PAGE_SOA}, day1_pk_fasting={PAGE_DAY1_PK_FASTING}, "
            f"ecg={PAGE_ECG}, lab={PAGE_LAB}, site={PAGE_SITE}, data={PAGE_DATA}, "
            f"appendix={PAGE_APPENDIX}.",
            styles["small"],
        )
    )

    # Silence unused version in story builder path when only used by callback
    _ = version
    return story


def render_protocol_pdf(source: dict[str, Any], output_path: Path) -> int:
    """Render PDF; return page count."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    version = str(source["version"])
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.85 * inch,
        title=f"{STUDY_ID} Protocol {version}",
        author="Protocol 215 Synthetic Fixture Generator",
    )
    story = build_story(source)

    def _on_page(canvas: Any, doc_obj: Any) -> None:
        _add_page_number(canvas, doc_obj, version=version, study_id=STUDY_ID)

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)

    from pypdf import PdfReader

    return len(PdfReader(str(output_path)).pages)
