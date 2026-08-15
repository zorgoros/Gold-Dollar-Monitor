"""Small read-only WSGI API for the separate dashboard application."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

from ..settings import Settings
from ..storage.database import open_migrated
from ..storage.repositories import Repository
from .projection import DashboardProjection

log = logging.getLogger(__name__)
StartResponse = Callable[[str, list[tuple[str, str]]], Any]
WsgiApp = Callable[[dict[str, Any], StartResponse], list[bytes]]


def _json_response(
    start_response: StartResponse, status: str, payload: dict[str, Any]
) -> list[bytes]:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    start_response(
        status,
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store"),
        ],
    )
    return [body]


def dashboard_app(projection: DashboardProjection) -> WsgiApp:
    """Build a JSON-only WSGI application around a dashboard projection."""

    def app(environ: dict[str, Any], start_response: StartResponse) -> list[bytes]:
        if environ.get("REQUEST_METHOD", "GET") != "GET":
            return _json_response(start_response, "405 Method Not Allowed", {"error": "read only"})

        path = str(environ.get("PATH_INFO", "/"))
        try:
            if path == "/api/v1/latest":
                return _json_response(start_response, "200 OK", projection.latest())
            if path == "/api/v1/history":
                query = parse_qs(str(environ.get("QUERY_STRING", "")))
                metrics = tuple(
                    name.strip()
                    for name in query.get("metrics", [""])[0].split(",")
                    if name.strip()
                )
                range_key = query.get("range", ["1d"])[0]
                return _json_response(
                    start_response,
                    "200 OK",
                    projection.history(metrics, range_key),
                )
            if path == "/api/v1/health":
                return _json_response(start_response, "200 OK", projection.health())
            return _json_response(start_response, "404 Not Found", {"error": "not found"})
        except ValueError as exc:
            return _json_response(start_response, "400 Bad Request", {"error": str(exc)})
        except Exception:
            log.exception("dashboard_request_failed", extra={"path": path})
            return _json_response(
                start_response,
                "500 Internal Server Error",
                {"error": "dashboard unavailable"},
            )

    return app


def serve_dashboard(settings: Settings, host: str, port: int) -> None:
    """Serve the local API until interrupted; the browser UI is served by Vite."""
    conn = open_migrated(settings.db_path)
    projection = DashboardProjection(Repository(conn), settings)
    try:
        with make_server(host, port, dashboard_app(projection)) as server:
            print(f"dashboard API listening on http://{host}:{port}/api/v1/")
            server.serve_forever()
    finally:
        conn.close()
