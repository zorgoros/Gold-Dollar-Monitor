import logging

from market_monitor.observability.logging import configure

TOKEN = "8862059587:AAtest-token-value"


def test_httpx_request_urls_are_not_logged():
    """httpx logs full URLs at INFO, and the Telegram URL embeds the bot token."""
    configure("INFO")
    assert logging.getLogger("httpx").getEffectiveLevel() >= logging.WARNING


def test_a_token_bearing_url_is_dropped_at_info(caplog):
    configure("INFO")
    with caplog.at_level(logging.INFO):
        logging.getLogger("httpx").info(
            'HTTP Request: POST https://api.telegram.org/bot%s/sendMessage "200 OK"', TOKEN
        )
    assert TOKEN not in caplog.text
