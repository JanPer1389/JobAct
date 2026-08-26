"""ReportLab implementation for the signed service-report PDF."""

from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


class ReportLabPdfRenderer:
    """Render the stable report context assembled by ``GeneratePdfActivity``."""

    async def render(self, context: dict) -> bytes:
        buffer = BytesIO()
        document = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=1.5 * cm,
            leftMargin=1.5 * cm,
            topMargin=1.5 * cm,
            bottomMargin=1.5 * cm,
        )
        styles = getSampleStyleSheet()
        heading = styles["Heading1"]
        normal = styles["BodyText"]

        customer = context["customer"]
        gps = context["gps"]
        metadata = [
            ["Report", context["report_number"]],
            ["Customer", customer["name"]],
            ["Address", customer["address"]],
            ["Phone", customer["phone"]],
            ["Service", customer["service_type"]],
            ["Timestamp", context["timestamp"].isoformat()],
            ["GPS", _format_gps(gps)],
        ]
        story = [Paragraph(context["header"], heading), Spacer(1, 0.35 * cm)]
        details = Table(metadata, colWidths=[3 * cm, 14 * cm])
        details.setStyle(_table_style())
        story.extend([details, Spacer(1, 0.5 * cm)])

        story.append(Paragraph("Work summary", styles["Heading2"]))
        story.extend([Paragraph(context["work_completed"], normal), Spacer(1, 0.35 * cm)])
        story.append(Paragraph("Materials", styles["Heading2"]))
        materials = [["Material", "Quantity"]] + [
            [material["label"], material["qty"]] for material in context["materials"]
        ]
        material_table = Table(materials, colWidths=[12 * cm, 5 * cm])
        material_table.setStyle(_table_style(header=True))
        story.extend([material_table, Spacer(1, 0.35 * cm)])
        story.append(Paragraph(f"Amount: {context['amount']}", normal))
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph(f"Signed by: {context['signer_name']}", styles["Heading2"]))
        signature_png = context.get("signature_png")
        if signature_png:
            signature = Image(BytesIO(signature_png), width=7 * cm, height=2.5 * cm)
            story.extend([Spacer(1, 0.15 * cm), signature])

        document.build(story)
        return buffer.getvalue()


def _format_gps(gps: dict[str, Any]) -> str:
    latitude = gps.get("latitude")
    longitude = gps.get("longitude")
    if latitude is None or longitude is None:
        return "Unavailable"
    return f"{latitude:.6f}, {longitude:.6f}"


def _table_style(*, header: bool = False) -> TableStyle:
    commands: list[tuple] = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        commands.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
    return TableStyle(commands)
