"""
Generate sample_resume.pdf from sample_resume.txt for demos and application runner.
Run from repo root: python backend/tests/fixtures/make_sample_resume_pdf.py
"""
import textwrap
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.lib.enums import TA_LEFT

SCRIPT_DIR = Path(__file__).resolve().parent
TXT_PATH = SCRIPT_DIR / "sample_resume.txt"
PDF_PATH = SCRIPT_DIR / "sample_resume.pdf"

MARGIN = 0.75 * inch


def _p(s, style):
    return Paragraph(s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), style)


def main():
    text = TXT_PATH.read_text(encoding="utf-8")
    lines = [line.rstrip() for line in text.splitlines()]

    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=letter,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )

    title_style = ParagraphStyle(
        name="Title",
        fontName="Helvetica-Bold",
        fontSize=18,
        spaceAfter=6,
        alignment=TA_LEFT,
    )
    contact_style = ParagraphStyle(
        name="Contact",
        fontName="Helvetica",
        fontSize=9,
        spaceAfter=2,
        textColor="dimgray",
        alignment=TA_LEFT,
    )
    section_style = ParagraphStyle(
        name="Section",
        fontName="Helvetica-Bold",
        fontSize=11,
        spaceBefore=14,
        spaceAfter=6,
        alignment=TA_LEFT,
    )
    job_style = ParagraphStyle(
        name="Job",
        fontName="Helvetica-Bold",
        fontSize=10,
        spaceAfter=2,
        alignment=TA_LEFT,
    )
    body_style = ParagraphStyle(
        name="Body",
        fontName="Helvetica",
        fontSize=10,
        spaceAfter=4,
        alignment=TA_LEFT,
    )

    story = []
    i = 0

    # Name
    if i < len(lines) and lines[i].strip():
        story.append(_p(lines[i].strip(), title_style))
        i += 1

    # Contact (until blank or section header)
    contact = []
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.strip() in ("EDUCATION", "EXPERIENCE", "SKILLS"):
            break
        contact.append(line.strip())
        i += 1
    if contact:
        story.append(_p("<br/>".join(contact), contact_style))
        story.append(Spacer(1, 0.2 * inch))

    # Sections
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line == "EDUCATION":
            story.append(_p("EDUCATION", section_style))
            i += 1
            while i < len(lines) and lines[i].strip() and lines[i].strip() != "EXPERIENCE":
                story.append(_p(lines[i].strip(), body_style))
                i += 1
            continue
        if line == "EXPERIENCE":
            story.append(_p("EXPERIENCE", section_style))
            i += 1
            while i < len(lines):
                if lines[i].strip() == "SKILLS":
                    break
                ln = lines[i].strip()
                if ln:
                    if "—" in ln or "–" in ln or " - " in ln:
                        story.append(_p(ln, job_style))
                    else:
                        for w in textwrap.wrap(ln, width=80):
                            story.append(_p(w, body_style))
                i += 1
            continue
        if line == "SKILLS":
            story.append(_p("SKILLS", section_style))
            i += 1
            if i < len(lines):
                story.append(_p(lines[i].strip(), body_style))
            break
        i += 1

    doc.build(story)
    print(f"Wrote {PDF_PATH}")


if __name__ == "__main__":
    main()
