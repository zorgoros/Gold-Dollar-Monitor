"""Provider tests run entirely off captured fixtures — no network in CI."""

import json
from pathlib import Path

import httpx
import pytest

from market_monitor.domain.enums import Instrument, Unit
from market_monitor.domain.errors import ProviderParseError, ProviderUnavailable, RateLimitError
from market_monitor.providers.gold_api import GoldApiProvider
from market_monitor.providers.tgju import TgjuProvider

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
ALL = list(Instrument)


def client_returning(payload, status: int = 200) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if isinstance(payload, str):
            return httpx.Response(status, text=payload)
        return httpx.Response(status, json=payload)

    return httpx.Client(transport=httpx.MockTransport(handler))


@pytest.fixture
def tgju_payload():
    return json.loads((FIXTURES / "tgju_call1_ajax.json").read_text(encoding="utf-8"))


def test_rial_instruments_are_converted_to_toman(tgju_payload):
    quotes = TgjuProvider(client_returning(tgju_payload)).fetch_quotes(ALL)

    # Fixture prints 1,878,000 rial. Published as toman that would be a 10x error.
    assert quotes[Instrument.USD_IRR_FREE].normalized_value == 187_800.0
    assert quotes[Instrument.USD_IRR_FREE].unit is Unit.TOMAN_PER_USD
    assert quotes[Instrument.GOLD_18K].normalized_value == 19_205_600.0
    assert quotes[Instrument.EMAMI_COIN].normalized_value == 189_485_000.0


def test_ounce_is_left_in_its_canonical_unit(tgju_payload):
    quote = TgjuProvider(client_returning(tgju_payload)).fetch_quotes(ALL)[Instrument.XAU_USD]
    assert quote.normalized_value == 4396.28
    assert quote.unit is Unit.USD_PER_TROY_OUNCE
    assert quote.currency == "USD"


def test_provenance_is_captured(tgju_payload):
    quote = TgjuProvider(client_returning(tgju_payload)).fetch_quotes(ALL)[Instrument.GOLD_18K]
    assert quote.raw_value == "192,056,000"
    assert quote.provider_symbol == "geram18"
    assert quote.raw_payload_hash
    assert quote.metadata["source_unit"] == "rial/gram"


def test_previous_close_timestamp_is_preserved_not_replaced(tgju_payload):
    """00:00:00 means yesterday's close; the validator decides staleness, not the adapter."""
    quote = TgjuProvider(client_returning(tgju_payload)).fetch_quotes(ALL)[Instrument.USD_IRR_FREE]
    assert quote.source_timestamp is not None
    assert quote.source_timestamp.strftime("%Y-%m-%d %H:%M") == "2026-08-11 00:00"
    assert quote.source_timestamp.tzinfo is not None


def test_layout_change_fails_loudly_instead_of_producing_a_number():
    with pytest.raises(ProviderParseError):
        TgjuProvider(client_returning({"unexpected": {}})).fetch_quotes(ALL)


def test_missing_symbol_is_a_parse_error(tgju_payload):
    del tgju_payload["current"]["geram18"]
    with pytest.raises(ProviderParseError):
        TgjuProvider(client_returning(tgju_payload)).fetch_quotes(ALL)


def test_non_json_body_is_a_parse_error():
    with pytest.raises(ProviderParseError):
        TgjuProvider(client_returning("<html>maintenance</html>")).fetch_quotes(ALL)


def test_server_error_is_transient_and_rate_limit_is_typed():
    with pytest.raises(ProviderUnavailable):
        TgjuProvider(client_returning({}, status=503)).fetch_quotes(ALL)
    with pytest.raises(RateLimitError):
        TgjuProvider(client_returning({}, status=429)).fetch_quotes(ALL)


def test_timeout_maps_to_provider_unavailable():
    def handler(request):
        raise httpx.ConnectTimeout("slow", request=request)

    provider = TgjuProvider(httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(ProviderUnavailable):
        provider.fetch_quotes(ALL)


def test_gold_api_fallback_parses_the_ounce():
    payload = json.loads((FIXTURES / "goldapi_xau_usd.json").read_text(encoding="utf-8"))[
        "response"
    ]
    quotes = GoldApiProvider(client_returning(payload)).fetch_quotes([Instrument.XAU_USD])
    assert quotes[Instrument.XAU_USD].normalized_value == pytest.approx(float(payload["price"]))
    assert quotes[Instrument.XAU_USD].provider == "gold-api"


def test_gold_api_ignores_instruments_it_cannot_serve():
    assert GoldApiProvider(client_returning({})).fetch_quotes([Instrument.GOLD_18K]) == {}
