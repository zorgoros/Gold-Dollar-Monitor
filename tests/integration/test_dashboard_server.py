"""The dashboard HTTP boundary is JSON-only and read-only."""

from __future__ import annotations

import json
from io import BytesIO

from market_monitor.cli import build_parser
from market_monitor.web.server import dashboard_app


class ProjectionStub:
    def latest(self):
        return {"state": "READY", "cards": [{"instrument": "USD_IRT"}]}

    def history(self, metric_names, range_key):
        if range_key == "90d":
            raise ValueError("unsupported range: 90d")
        if "secret" in metric_names:
            raise ValueError("unsupported metric: secret")
        return {"state": "READY", "range": range_key, "series": {}}

    def health(self):
        return {"state": "READY", "latest_snapshot_at": "2026-08-12T09:30:00Z"}


def request(app, path):
    status = ""
    headers = {}

    def start_response(next_status, next_headers):
        nonlocal status, headers
        status = next_status
        headers = dict(next_headers)

    route, _, query = path.partition("?")
    body = b"".join(
        app(
            {
                "REQUEST_METHOD": "GET",
                "PATH_INFO": route,
                "QUERY_STRING": query,
                "wsgi.input": BytesIO(),
            },
            start_response,
        )
    )
    return status, headers, body.decode("utf-8")


def test_latest_endpoint_returns_json():
    status, headers, body = request(dashboard_app(ProjectionStub()), "/api/v1/latest")

    assert status == "200 OK"
    assert headers["Content-Type"] == "application/json; charset=utf-8"
    assert json.loads(body)["cards"]


def test_history_rejects_unknown_range():
    status, _, body = request(
        dashboard_app(ProjectionStub()),
        "/api/v1/history?metrics=usd_market&range=90d",
    )

    assert status == "400 Bad Request"
    assert json.loads(body) == {"error": "unsupported range: 90d"}


def test_history_rejects_non_public_metric():
    status, _, body = request(
        dashboard_app(ProjectionStub()),
        "/api/v1/history?metrics=secret&range=1d",
    )
    assert status == "400 Bad Request"
    assert json.loads(body) == {"error": "unsupported metric: secret"}


def test_health_and_missing_routes_are_json():
    app = dashboard_app(ProjectionStub())
    status, _, body = request(app, "/api/v1/health")
    assert status == "200 OK" and json.loads(body)["state"] == "READY"

    status, _, body = request(app, "/")
    assert status == "404 Not Found"
    assert json.loads(body) == {"error": "not found"}


def test_unexpected_projection_failure_has_no_internal_detail():
    class Broken(ProjectionStub):
        def latest(self):
            raise RuntimeError("/private/database/path")

    status, _, body = request(dashboard_app(Broken()), "/api/v1/latest")
    assert status == "500 Internal Server Error"
    assert json.loads(body) == {"error": "dashboard unavailable"}


def test_cli_exposes_dashboard_host_and_port():
    args = build_parser().parse_args(["dashboard", "--host", "0.0.0.0", "--port", "9000"])
    assert (args.command, args.host, args.port) == ("dashboard", "0.0.0.0", 9000)
