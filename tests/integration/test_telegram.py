"""Telegram is mocked end to end — CI never touches the real API."""

import httpx
import pytest

from market_monitor.domain.enums import DeliveryStatus, ReportType
from market_monitor.domain.errors import AuthenticationError, TelegramDeliveryError
from market_monitor.domain.models import Report
from market_monitor.jobs.report import publish, report_key, scheduled_slot
from market_monitor.publishers.telegram import TelegramPublisher
from market_monitor.timeutil import now_utc
from tests.conftest import AT

TOKEN = "123456:secret-token-value"


def publisher_for(handler, **kwargs) -> TelegramPublisher:
    return TelegramPublisher(
        token=TOKEN,
        chat_id="@channel",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        **kwargs,
    )


def a_report(key: str = "k") -> Report:
    return Report(
        report_type=ReportType.SCHEDULED_SUMMARY,
        report_key=key,
        content="گزارش",
        channel="telegram",
        generated_at=now_utc(),
        model_version="1.0",
    )


def test_successful_send_returns_the_message_id():
    def handler(request):
        assert request.url.path.endswith("/sendMessage")
        body = request.read().decode()
        assert "گزارش" in body
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 4242}})

    assert publisher_for(handler).publish(a_report()) == 4242


def test_server_error_is_retried_then_reported():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(500, json={"ok": False})

    with pytest.raises(TelegramDeliveryError):
        publisher_for(handler, max_retries=2).publish(a_report())
    assert calls["n"] == 2


def test_bad_request_is_not_retried():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(400, json={"ok": False, "description": "bad entity"})

    with pytest.raises(TelegramDeliveryError):
        publisher_for(handler).publish(a_report())
    assert calls["n"] == 1


def test_forbidden_is_an_auth_error_not_a_delivery_retry():
    def handler(request):
        return httpx.Response(403, json={"ok": False, "description": "bot is not a member"})

    with pytest.raises(AuthenticationError):
        publisher_for(handler).publish(a_report())


def test_the_token_never_appears_in_an_error_message():
    def handler(request):
        return httpx.Response(400, json={"ok": False, "description": "nope"})

    with pytest.raises(TelegramDeliveryError) as caught:
        publisher_for(handler).publish(a_report())
    assert TOKEN not in str(caught.value)


def test_missing_credentials_fail_before_any_request():
    with pytest.raises(AuthenticationError):
        TelegramPublisher(token="", chat_id="@channel")


class FakePublisher:
    channel = "telegram"

    def __init__(self):
        self.sent = 0

    def publish(self, report):
        self.sent += 1
        return 100 + self.sent


def test_a_second_run_of_the_same_slot_does_not_send_twice(repo, snapshot):
    from market_monitor.analysis.engine import analyze
    from tests.integration.test_engine import CONFIG

    analysis = analyze(snapshot(), repo, CONFIG)
    publisher = FakePublisher()

    first = publish(repo, a_report("slot-1"), publisher, analysis)
    second = publish(repo, a_report("slot-1"), publisher, analysis)

    assert first.published and first.report.telegram_message_id == 101
    assert second.skipped_duplicate and not second.published
    assert publisher.sent == 1


def test_a_failed_delivery_is_recorded_and_can_be_retried_later(repo, snapshot):
    from market_monitor.analysis.engine import analyze
    from tests.integration.test_engine import CONFIG

    analysis = analyze(snapshot(), repo, CONFIG)

    class Failing:
        channel = "telegram"

        def publish(self, report):
            raise TelegramDeliveryError("network down")

    with pytest.raises(TelegramDeliveryError):
        publish(repo, a_report("slot-2"), Failing(), analysis)
    assert not repo.already_delivered("slot-2")

    outcome = publish(repo, a_report("slot-2"), FakePublisher(), analysis)
    assert outcome.published


def test_slot_key_groups_a_run_with_its_scheduled_time():
    slots = ["09:00", "13:00", "17:00", "21:00"]
    # AT is 09:30 UTC == 13:00 Tehran
    assert scheduled_slot(AT, slots).endswith("13:00")


def test_an_off_schedule_run_gets_its_own_key():
    from datetime import timedelta

    slot = scheduled_slot(AT + timedelta(hours=5), ["09:00", "13:00"])
    assert slot.endswith("adhoc")


def test_report_key_includes_model_version():
    key = report_key(ReportType.SCHEDULED_SUMMARY, "2026-08-12 13:00", "1.0")
    assert key == "scheduled_summary|2026-08-12 13:00|1.0"


def test_delivery_status_enum_covers_the_duplicate_case():
    assert DeliveryStatus.SKIPPED_DUPLICATE.value == "SKIPPED_DUPLICATE"
