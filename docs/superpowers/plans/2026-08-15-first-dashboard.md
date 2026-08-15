# First Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task by task. Steps use checkbox syntax for tracking.

**Goal:** Build a local, read-only Persian RTL Ayar Market dashboard over the bot's existing data.

**Architecture:** `src/market_monitor/web/` is the only web boundary. Its Python projection reads stored snapshots, metrics, and signals; its server returns JSON and static files. `src/market_monitor/web/static/` is the separate browser UI. It has no SQL, formulas, provider code, or Telegram parsing.

**Tech Stack:** Python 3.12+, stdlib WSGI/JSON server, SQLite through `Repository`, vanilla HTML/CSS/ES modules, Canvas 2D charts, pytest, Ruff, mypy, and in-app-browser review.

## Global Constraints

- Match the selected option-3 hierarchy in `docs/superpowers/specs/2026-08-15-first-dashboard-design.md`.
- Use existing formulas and reporting gates. Do not add a formula, migration, write endpoint, or runtime dependency.
- Keep gold-implied USD and AED-implied USD as two separately named routes. Never average them.
- Detailed analysis must use the current Tehran-session alignment gate. A failed gate returns an unavailable state, not an unaligned comparison.
- UI files remain under `web/static/`; Python projection and HTTP code remain outside it.
- Preserve the existing 201 passing tests.

---

### Task 1: Repository history query and dashboard projection

**Files:**
- Create: `src/market_monitor/web/__init__.py`
- Create: `src/market_monitor/web/projection.py`
- Modify: `src/market_monitor/storage/repositories.py`
- Create: `tests/unit/test_dashboard_projection.py`
- Modify: `tests/integration/test_database.py`

**Interfaces:**
- Consumes: `Repository.latest_snapshot()`, `Settings`, `validate_snapshot()`, `base_analysis()`, `prepare()`, and `widget_payload()`.
- Produces: `DashboardProjection.latest() -> dict[str, Any]`, `DashboardProjection.history(metric_names: tuple[str, ...], range_key: str) -> dict[str, Any]`, and `Repository.metric_history()`.

- [ ] **Step 1: Write failing repository tests**

    def test_metric_history_returns_requested_points_in_time_order(repo, snapshot):
        old_id = repo.save_snapshot(snapshot(at=AT - timedelta(hours=2)))
        new_id = repo.save_snapshot(snapshot(at=AT))
        repo.save_metrics(old_id, [Metric("usd_market", 180_000, "toman/usd", "1.2")], AT - timedelta(hours=2))
        repo.save_metrics(new_id, [Metric("usd_market", 185_400, "toman/usd", "1.2")], AT)

        points = repo.metric_history(("usd_market",), AT - timedelta(days=1), AT)

        assert [(point.name, point.value, point.at) for point in points] == [
            ("usd_market", 180_000.0, AT - timedelta(hours=2)),
            ("usd_market", 185_400.0, AT),
        ]

- [ ] **Step 2: Verify red**

Run: `/private/tmp/market-dashboard-venv/bin/python -m pytest tests/integration/test_database.py::test_metric_history_returns_requested_points_in_time_order -q`

Expected: FAIL because `Repository.metric_history` does not exist.

- [ ] **Step 3: Add the minimal typed query**

    @dataclass(frozen=True)
    class MetricHistoryPoint:
        name: str
        value: float
        at: datetime

    def metric_history(
        self, names: tuple[str, ...], start: datetime, end: datetime
    ) -> list[MetricHistoryPoint]:
        placeholders = ", ".join("?" for _ in names)
        rows = self.conn.execute(
            "SELECT metric_name, metric_value, created_at FROM metrics "
            f"WHERE metric_name IN ({placeholders}) AND created_at BETWEEN ? AND ? "
            "ORDER BY created_at, metric_name",
            (*names, to_iso(start), to_iso(end)),
        ).fetchall()
        return [
            MetricHistoryPoint(row["metric_name"], float(row["metric_value"]), from_iso(row["created_at"]))
            for row in rows
        ]

Keep the empty-name check in the projection so this query always receives a non-empty tuple.

- [ ] **Step 4: Verify green**

Run: `/private/tmp/market-dashboard-venv/bin/python -m pytest tests/integration/test_database.py::test_metric_history_returns_requested_points_in_time_order -q`

Expected: PASS.

- [ ] **Step 5: Write failing projection tests**

    def test_latest_keeps_usd_reference_routes_separate(repo, snapshot, settings):
        repo.save_snapshot(snapshot(aed=True, coin=True))

        payload = DashboardProjection(repo, settings).latest()

        usd = next(card for card in payload["cards"] if card["instrument"] == "USD_IRT")
        assert [item["name"] for item in usd["references"]] == ["gold", "aed"]
        assert "composite" not in payload

    def test_latest_hides_detail_when_analysis_alignment_fails(repo, snapshot, settings):
        repo.save_snapshot(snapshot())

        payload = DashboardProjection(repo, settings).latest()

        assert payload["analysis"]["state"] == "UNAVAILABLE"
        assert "content" not in payload["analysis"]

Also test an empty database, missing optional AED/coin data, exclusion of `coin_premium_world_pct`, and an incomplete 30-day history range.

- [ ] **Step 6: Verify red**

Run: `/private/tmp/market-dashboard-venv/bin/python -m pytest tests/unit/test_dashboard_projection.py -q`

Expected: FAIL because `market_monitor.web` does not exist.

- [ ] **Step 7: Implement the projection**

    class DashboardProjection:
        def latest(self) -> dict[str, Any]:
            snapshot = self._repo.latest_snapshot()
            if snapshot is None:
                return {"state": "NO_DATA", "cards": [], "analysis": {"state": "UNAVAILABLE"}}
            verdict = self._snapshot_verdict(snapshot)
            observation = base_analysis(self._repo, self._settings, snapshot, verdict)
            if observation is None:
                return {"state": "UNAVAILABLE", "cards": [], "analysis": {"state": "UNAVAILABLE"}}
            prepared = prepare(
                self._repo, self._settings, snapshot, verdict,
                ReportType.AYAR_ANALYSIS, observation,
            )
            return self._latest_payload(observation, prepared)

`_snapshot_verdict()` calls `validate_snapshot()` with settings-defined mandatory instruments and snapshot window. `_latest_payload()` calls `widget_payload(observation)`. It exposes the prepared analysis only when it is not gated. It never returns rendered report text or diagnostics.

`history()` accepts only `1d`, `7d`, and `30d`, and only an internal allow-list for the shown market/reference metrics. It uses latest-snapshot time as the end, calls `metric_history()`, and returns points plus requested range, earliest stored point, and `coverage_complete`.

- [ ] **Step 8: Verify green and commit**

Run: `/private/tmp/market-dashboard-venv/bin/python -m pytest tests/unit/test_dashboard_projection.py tests/integration/test_database.py -q`

Expected: PASS.

Stage: `git add src/market_monitor/web/__init__.py src/market_monitor/web/projection.py src/market_monitor/storage/repositories.py tests/unit/test_dashboard_projection.py tests/integration/test_database.py`

Commit: `git commit -m "Add dashboard data projection"`

### Task 2: Read-only HTTP server and CLI entry point

**Files:**
- Create: `src/market_monitor/web/server.py`
- Modify: `src/market_monitor/cli.py`
- Modify: `pyproject.toml`
- Create: `tests/integration/test_dashboard_server.py`
- Modify: `docs/ops/STRUCTURE.md`

**Interfaces:**
- Consumes: `DashboardProjection` from Task 1.
- Produces: `dashboard_app(projection: DashboardProjection) -> Callable[..., list[bytes]]`, `serve_dashboard(settings: Settings, host: str, port: int) -> None`, and `market-monitor dashboard --host HOST --port PORT`.

- [ ] **Step 1: Write failing HTTP tests**

    def test_latest_endpoint_returns_json(dashboard_app):
        status, headers, body = request(dashboard_app, "/api/v1/latest")

        assert status == "200 OK"
        assert headers["Content-Type"] == "application/json; charset=utf-8"
        assert json.loads(body)["cards"]

    def test_history_rejects_unknown_range(dashboard_app):
        status, _, body = request(dashboard_app, "/api/v1/history?metrics=usd_market&range=90d")

        assert status == "400 Bad Request"
        assert json.loads(body) == {"error": "unsupported range: 90d"}

Also cover `/api/v1/health`, invalid metric names, missing routes, index/CSS/JS MIME types, and generic 500 behavior.

- [ ] **Step 2: Verify red**

Run: `/private/tmp/market-dashboard-venv/bin/python -m pytest tests/integration/test_dashboard_server.py -q`

Expected: FAIL because `market_monitor.web.server` does not exist.

- [ ] **Step 3: Implement the server**

    def dashboard_app(projection: DashboardProjection) -> Callable[..., list[bytes]]:
        def app(environ: dict[str, Any], start_response: StartResponse) -> list[bytes]:
            path = environ.get("PATH_INFO", "/")
            if path == "/api/v1/latest":
                return json_response(start_response, "200 OK", projection.latest())
            if path == "/api/v1/history":
                return history_response(environ, start_response, projection)
            if path == "/api/v1/health":
                return json_response(start_response, "200 OK", projection.health())
            return static_response(path, start_response)
        return app

`static_response()` has an explicit file allow-list. It maps `/` to `index.html`, rejects traversal, and never exposes database paths, errors, provider payloads, or secrets. `history_response()` returns only known request errors as 400 JSON. It returns `{"error": "dashboard unavailable"}` for unexpected failures.

Add package-data configuration for `web/static/*`. Add one `web/` row to `docs/ops/STRUCTURE.md`. State that `web/static/` is the UI-only directory and `web/` Python files own projection/transport.

- [ ] **Step 4: Add the CLI command**

    dashboard = sub.add_parser("dashboard", help="serve the read-only local dashboard")
    dashboard.add_argument("--host", default="127.0.0.1")
    dashboard.add_argument("--port", type=int, default=8000)

`cmd_dashboard()` opens the migrated repository, creates `DashboardProjection`, and calls `serve_dashboard()`. It must not create a Telegram publisher.

- [ ] **Step 5: Verify green and commit**

Run: `/private/tmp/market-dashboard-venv/bin/python -m pytest tests/integration/test_dashboard_server.py tests/unit/test_dashboard_projection.py -q`

Expected: PASS.

Stage: `git add src/market_monitor/web src/market_monitor/cli.py pyproject.toml tests/integration/test_dashboard_server.py docs/ops/STRUCTURE.md`

Commit: `git commit -m "Add dashboard web server"`

### Task 3: Option-3 RTL dashboard UI and verification

**Files:**
- Create: `src/market_monitor/web/static/index.html`
- Create: `src/market_monitor/web/static/styles.css`
- Create: `src/market_monitor/web/static/app.js`
- Create: `tests/unit/test_dashboard_static.py`
- Modify: `README.md`
- Modify: `docs/OPERATIONS.md`
- Modify: `docs/ops/LEDGER.md`
- Modify: `docs/ops/HANDOFF.md`

**Interfaces:**
- Consumes: `/api/v1/latest`, `/api/v1/history`, and public card/analysis JSON only.
- Produces: a default `بازار` view, a separate `تحلیل` view, and 1D/7D/30D chart controls.

- [ ] **Step 1: Write failing static-contract tests**

    def test_dashboard_html_declares_rtl_market_and_analysis_views():
        html = static_file("index.html")

        assert 'lang="fa"' in html and 'dir="rtl"' in html
        assert 'data-view="market"' in html
        assert 'data-view="analysis"' in html

    def test_dashboard_script_uses_only_public_endpoints():
        script = static_file("app.js")

        assert "/api/v1/latest" in script and "/api/v1/history" in script
        assert "telegram" not in script.lower()
        assert "3.6725" not in script

Add a README assertion for `market-monitor dashboard` and `read-only`.

- [ ] **Step 2: Verify red**

Run: `/private/tmp/market-dashboard-venv/bin/python -m pytest tests/unit/test_dashboard_static.py -q`

Expected: FAIL because static files do not exist.

- [ ] **Step 3: Build the semantic HTML and CSS**

Use right-to-left landmarks: header, market/analysis tab buttons, main, live state, price tape, chart, short analysis summary, and analysis panel. Use visible button labels and one `aria-live="polite"` status region.

Implement the selected option-3 visual system: graphite background, warm text, steel-blue dividers, jade positive movement, vermilion high-gap warning, 8px frames, tabular figures, and grid layout. Stack at 768px and use one column at 375px. Do not use gradients, glass effects, gauges, emoji, or card-inside-card layouts. Respect reduced motion and keyboard focus.

- [ ] **Step 4: Build the minimal interaction layer**

Fetch `/api/v1/latest` on load. Render market cards from API-provided values. Render only the short analysis summary on `بازار`; render detailed analysis only when the JSON state is available. Switch tabs without reload. Range buttons request `/api/v1/history`. Draw a Canvas 2D line chart only from returned points and provide a visible data table for non-canvas readers. Disable ranges with incomplete coverage and show a short Persian message. Keep all UI text free of technical diagnostics.

- [ ] **Step 5: Verify green**

Run: `/private/tmp/market-dashboard-venv/bin/python -m pytest tests/unit/test_dashboard_static.py -q`

Expected: PASS.

- [ ] **Step 6: Complete local review and documentation**

Document `market-monitor dashboard --host 127.0.0.1 --port 8000` in README and OPERATIONS. State that it is local, read-only, and not a production server. Run:

    /private/tmp/market-dashboard-venv/bin/python -m pytest
    /private/tmp/market-dashboard-venv/bin/ruff check src tests scripts
    /private/tmp/market-dashboard-venv/bin/ruff format --check src tests scripts
    /private/tmp/market-dashboard-venv/bin/mypy src

Start the dashboard with a temporary fixture database. In the in-app browser, check 1440px, 1024px, 768px, and 375px; switch `بازار`/`تحلیل`; change range; check unavailable history; tab through controls; and check the console. Compare 1440px hierarchy with option 3 and fix visual defects.

- [ ] **Step 7: Record and commit**

Mark TASK-007 P1–P3 complete only after all checks pass. Update HANDOFF with final commit, test results, preview result, and merge target. Keep the MEMORY worktree entry until merge/removal.

Stage: `git add src/market_monitor/web/static tests/unit/test_dashboard_static.py README.md docs/OPERATIONS.md docs/ops/LEDGER.md docs/ops/HANDOFF.md`

Commit: `git commit -m "Add RTL dashboard interface"`
