from datetime import UTC, datetime

import pytest

from jobact.shared.infrastructure.pdf.reportlab_renderer import ReportLabPdfRenderer


@pytest.mark.asyncio
async def test_render_embeds_cyrillic_font_for_russian_report_content() -> None:
    """Removing the Unicode font registration must make this PDF lose Cyrillic support."""
    pdf = await ReportLabPdfRenderer().render(
        {
            "header": "\u041e\u0442\u0447\u0451\u0442 \u043e \u0432\u044b\u043f\u043e\u043b\u043d\u0435\u043d\u043d\u044b\u0445 \u0440\u0430\u0431\u043e\u0442\u0430\u0445",
            "report_number": "JA-2026-0002",
            "customer": {
                "name": "\u0410\u043d\u0442\u043e\u043d \u041f\u0443\u043f\u043a\u0438\u043d",
                "address": "\u041c\u043e\u0441\u043a\u0432\u0430",
                "phone": "+7 900 123-45-67",
                "service_type": "\u0420\u0435\u043c\u043e\u043d\u0442",
            },
            "timestamp": datetime(2026, 8, 28, tzinfo=UTC),
            "gps": {"latitude": 55.7558, "longitude": 37.6173},
            "work_completed": "\u0417\u0430\u043c\u0435\u043d\u0438\u043b\u0438 \u0441\u043c\u0435\u0441\u0438\u0442\u0435\u043b\u044c \u0438 \u043f\u0440\u043e\u0432\u0435\u0440\u0438\u043b\u0438 \u043e\u0442\u0441\u0443\u0442\u0441\u0442\u0432\u0438\u0435 \u043f\u0440\u043e\u0442\u0435\u0447\u0435\u043a.",
            "materials": [{"label": "\u0421\u043c\u0435\u0441\u0438\u0442\u0435\u043b\u044c", "qty": "1"}],
            "amount": "1266.95 RUB",
            "signature_png": None,
            "signer_name": "\u0410\u043d\u0442\u043e\u043d \u041f\u0443\u043f\u043a\u0438\u043d",
        }
    )

    assert b"NotoSans" in pdf
