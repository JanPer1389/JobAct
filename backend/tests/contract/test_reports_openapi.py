"""The report HTTP surface stays deliberately limited to the v1 contract."""

from jobact.apps.api.main import create_app


def test_openapi_exposes_the_report_and_manual_recovery_endpoints() -> None:
    schema = create_app().openapi()
    paths = schema["paths"]

    assert {
        "/api/v1/reports",
        "/api/v1/reports/{report_id}",
        "/api/v1/reports/{report_id}/manual-recovery",
        "/api/v1/reports/{report_id}/revision",
        "/api/v1/reports/{report_id}/confirm",
        "/api/v1/reports/{report_id}/ready-for-signature",
        "/api/v1/reports/{report_id}/sign",
    } <= set(paths)
    assert set(paths["/api/v1/reports"]) == {"get", "post"}
    assert set(paths["/api/v1/reports/{report_id}"]) == {"get"}
    assert set(paths["/api/v1/reports/{report_id}/manual-recovery"]) == {"get"}
    assert set(paths["/api/v1/reports/{report_id}/revision"]) == {"patch"}
    assert set(paths["/api/v1/reports/{report_id}/confirm"]) == {"post"}
    assert set(paths["/api/v1/reports/{report_id}/ready-for-signature"]) == {"post"}
    assert set(paths["/api/v1/reports/{report_id}/sign"]) == {"post"}
    report_properties = schema["components"]["schemas"]["ReportResponse"][
        "properties"
    ]
    assert {"workflow_state", "pdf_media_asset_id"} <= set(report_properties)
    assert set(paths["/api/v1/reports/{report_id}/audits"]) == {"get", "post"}
    assert set(paths["/api/v1/reports/{report_id}/audits/{attempt_id}"]) == {"get"}
    assert set(paths["/api/v1/reports/{report_id}/audits/{attempt_id}/acknowledge"]) == {"post"}
