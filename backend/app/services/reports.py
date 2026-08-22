from __future__ import annotations

import html
import io
from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath
from urllib.parse import quote

import httpx
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.billing_models import SavedReport
from app.config import get_settings
from app.schemas import DecisionPlanResponse


class ReportStorageError(RuntimeError):
    pass


def report_storage_configured() -> bool:
    settings = get_settings()
    return bool(settings.supabase_url and settings.supabase_secret_key and settings.report_storage_bucket)


def _safe_text(value: object) -> str:
    return html.escape(str(value or ""))


def _styles():
    base = getSampleStyleSheet()
    ink = colors.HexColor("#111A3A")
    soft = colors.HexColor("#59657D")
    brand = colors.HexColor("#2438A6")
    return {
        "title": ParagraphStyle("VFTitle", parent=base["Title"], fontName="Helvetica-Bold", fontSize=24, leading=28, textColor=ink, spaceAfter=8),
        "heading": ParagraphStyle("VFHeading", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=ink, spaceBefore=14, spaceAfter=7),
        "subheading": ParagraphStyle("VFSubheading", parent=base["Heading3"], fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=ink, spaceAfter=4),
        "body": ParagraphStyle("VFBody", parent=base["BodyText"], fontName="Helvetica", fontSize=8.5, leading=12, textColor=soft, spaceAfter=5),
        "small": ParagraphStyle("VFSmall", parent=base["BodyText"], fontName="Helvetica", fontSize=7, leading=9, textColor=soft),
        "kicker": ParagraphStyle("VFKicker", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=7, leading=9, textColor=brand, spaceAfter=4),
        "footer": ParagraphStyle("VFFooter", parent=base["BodyText"], fontName="Helvetica", fontSize=6.5, leading=8, textColor=soft, alignment=TA_CENTER),
    }


def _page_footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#DDE2EB"))
    canvas.line(20 * mm, 14 * mm, A4[0] - 20 * mm, 14 * mm)
    canvas.setFillColor(colors.HexColor("#59657D"))
    canvas.setFont("Helvetica", 7)
    canvas.drawString(20 * mm, 9 * mm, "VeriFinder · Evidence-backed decision report")
    canvas.drawRightString(A4[0] - 20 * mm, 9 * mm, f"Page {document.page}")
    canvas.restoreState()


def build_plan_pdf(plan: DecisionPlanResponse) -> bytes:
    """Render a deterministic, server-side PDF with evidence and provenance intact."""
    output = io.BytesIO()
    styles = _styles()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=20 * mm,
        title=plan.title,
        author="VeriFinder",
        subject="Evidence-backed decision report",
    )
    story = [
        Paragraph("VERIFINDER · CHECK BEFORE YOU DECIDE", styles["kicker"]),
        Paragraph(_safe_text(plan.title), styles["title"]),
        Paragraph(_safe_text(plan.summary), styles["body"]),
        Spacer(1, 4 * mm),
        Table(
            [
                ["Goal", _safe_text(plan.goal)],
                ["Location", _safe_text(plan.location or "Not specified")],
                ["Generated", plan.created_at.astimezone(timezone.utc).strftime("%d %b %Y, %H:%M UTC")],
                ["Method", "Gemini evidence synthesis" if plan.ai_mode == "gemini" else "Evidence rules"],
            ],
            colWidths=[27 * mm, 132 * mm],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F3FA")),
                    ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#2438A6")),
                    ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#111A3A")),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#DDE2EB")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            ),
        ),
    ]

    if plan.questions:
        story.append(Paragraph("Open questions", styles["heading"]))
        story.append(
            ListFlowable(
                [
                    ListItem(
                        Paragraph(f"<b>{_safe_text(item.question)}</b><br/>{_safe_text(item.why_it_matters)}", styles["body"]),
                        leftIndent=12,
                    )
                    for item in plan.questions
                ],
                bulletType="1",
                leftIndent=18,
            )
        )

    story.append(Paragraph("Starting scenarios", styles["heading"]))
    if not plan.scenarios:
        story.append(Paragraph("No location scenarios were available.", styles["body"]))
    for scenario in plan.scenarios:
        metrics = " · ".join(f"<b>{_safe_text(metric.label)}:</b> {_safe_text(metric.value)}" for metric in scenario.metrics)
        sections = [
            Paragraph(_safe_text(scenario.title), styles["subheading"]),
            Paragraph(_safe_text(scenario.description), styles["body"]),
        ]
        if metrics:
            sections.append(Paragraph(metrics, styles["small"]))
        if scenario.strengths:
            sections.append(Paragraph("<b>Useful signals:</b> " + _safe_text("; ".join(scenario.strengths)), styles["small"]))
        if scenario.tradeoffs:
            sections.append(Paragraph("<b>Trade-offs:</b> " + _safe_text("; ".join(scenario.tradeoffs)), styles["small"]))
        story.extend([KeepTogether(sections), Spacer(1, 2 * mm)])

    story.extend([PageBreak(), Paragraph("Evidence ledger", styles["heading"])])
    evidence_rows = [["Classification", "Evidence", "Official source"]]
    for item in plan.evidence:
        source = "—"
        if item.source:
            source = f"{_safe_text(item.source.organisation)}<br/><link href='{_safe_text(item.source.official_url)}' color='#2438A6'>Open source</link>"
        evidence_rows.append(
            [
                Paragraph(_safe_text(item.kind.replace("_", " ").title()), styles["small"]),
                Paragraph(f"<b>{_safe_text(item.title)}</b><br/>{_safe_text(item.detail)}", styles["small"]),
                Paragraph(source, styles["small"]),
            ]
        )
    story.append(
        Table(
            evidence_rows,
            repeatRows=1,
            colWidths=[30 * mm, 91 * mm, 38 * mm],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111A3A")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 7),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#DDE2EB")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F9FC")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            ),
        )
    )

    story.append(Paragraph("Action path", styles["heading"]))
    for step in plan.steps:
        story.extend(
            [
                Paragraph(f"<b>{step.position}. {_safe_text(step.title)}</b> · {_safe_text(step.status.replace('_', ' '))}", styles["subheading"]),
                Paragraph(_safe_text(step.description), styles["body"]),
            ]
        )
    story.extend(
        [
            HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#DDE2EB"), spaceBefore=8, spaceAfter=8),
            Paragraph("Decision boundary", styles["heading"]),
            ListFlowable(
                [ListItem(Paragraph(_safe_text(item), styles["small"]), leftIndent=10) for item in plan.limitations],
                bulletType="bullet",
                leftIndent=14,
            ),
            Spacer(1, 5 * mm),
            Paragraph(
                "Generated from connected public-data sources. Re-check time-sensitive records before committing. This report is not legal, financial, immigration or professional advice.",
                styles["footer"],
            ),
        ]
    )
    document.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return output.getvalue()


def _storage_headers(content_type: str | None = None) -> dict[str, str]:
    settings = get_settings()
    if not report_storage_configured():
        raise ReportStorageError("Private report storage is not configured.")
    headers = {
        "apikey": str(settings.supabase_secret_key),
        "Authorization": f"Bearer {settings.supabase_secret_key}",
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def _object_url(path: str, *, operation: str = "object") -> str:
    settings = get_settings()
    encoded_path = quote(PurePosixPath(path).as_posix(), safe="/")
    bucket = quote(settings.report_storage_bucket, safe="")
    return f"{settings.supabase_url.rstrip('/')}/storage/v1/{operation}/{bucket}/{encoded_path}"


async def upload_pdf(path: str, pdf: bytes) -> None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            _object_url(path),
            headers={**_storage_headers("application/pdf"), "x-upsert": "false"},
            content=pdf,
        )
    if response.status_code not in {200, 201}:
        raise ReportStorageError(f"Supabase Storage rejected the report upload ({response.status_code}).")


async def signed_download_url(path: str) -> tuple[str, datetime]:
    settings = get_settings()
    ttl = max(60, min(settings.report_signed_url_ttl_seconds, 3600))
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            _object_url(path, operation="object/sign"),
            headers=_storage_headers("application/json"),
            json={"expiresIn": ttl, "download": True},
        )
    if response.status_code != 200:
        raise ReportStorageError(f"Supabase Storage could not sign the report download ({response.status_code}).")
    signed = response.json().get("signedURL") or response.json().get("signedUrl")
    if not isinstance(signed, str):
        raise ReportStorageError("Supabase Storage returned an invalid signed URL.")
    if signed.startswith("/"):
        signed = f"{settings.supabase_url.rstrip('/')}/storage/v1{signed}"
    expires_at = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(seconds=ttl)
    return signed, expires_at


async def delete_pdf(path: str) -> None:
    settings = get_settings()
    bucket = quote(settings.report_storage_bucket, safe="")
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.delete(
            f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{bucket}",
            headers=_storage_headers("application/json"),
            json={"prefixes": [PurePosixPath(path).as_posix()]},
        )
    if response.status_code not in {200, 204, 404}:
        raise ReportStorageError(f"Supabase Storage could not remove the report ({response.status_code}).")


def list_saved_reports(session: Session, subject_id: str) -> list[SavedReport]:
    return list(
        session.scalars(
            select(SavedReport)
            .where(SavedReport.subject_id == subject_id, SavedReport.status == "ready")
            .order_by(SavedReport.created_at.desc())
        )
    )
