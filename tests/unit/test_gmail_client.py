"""Unit tests for gmail_client helpers that don't require real Gmail access."""
from unittest.mock import MagicMock, patch

import pytest
from googleapiclient.errors import HttpError

from scraper.gmail_client import _extract_sender, _iter_parts, _retry_once


# ---------------------------------------------------------------------------
# _iter_parts
# ---------------------------------------------------------------------------

class TestIterParts:
    def test_flat_payload(self):
        payload = {"mimeType": "text/plain", "body": {"data": "aGVsbG8="}}
        parts = _iter_parts(payload)
        assert parts == [payload]

    def test_nested_parts(self):
        inner = {"mimeType": "application/pdf", "filename": "leaflet.pdf"}
        payload = {
            "mimeType": "multipart/mixed",
            "parts": [
                {"mimeType": "text/plain", "parts": [inner]},
            ],
        }
        parts = _iter_parts(payload)
        assert inner in parts

    def test_empty_payload(self):
        parts = _iter_parts({})
        assert parts == [{}]

    def test_multiple_parts_at_same_level(self):
        p1 = {"mimeType": "text/plain"}
        p2 = {"mimeType": "application/pdf"}
        payload = {"parts": [p1, p2]}
        parts = _iter_parts(payload)
        assert p1 in parts
        assert p2 in parts


# ---------------------------------------------------------------------------
# _extract_sender
# ---------------------------------------------------------------------------

class TestExtractSender:
    def test_from_header_found(self):
        message = {
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Letak"},
                    {"name": "From", "value": "letak@tesco.cz"},
                ]
            }
        }
        assert _extract_sender(message) == "letak@tesco.cz"

    def test_case_insensitive_header(self):
        message = {
            "payload": {
                "headers": [{"name": "from", "value": "newsletter@albert.cz"}]
            }
        }
        assert _extract_sender(message) == "newsletter@albert.cz"

    def test_no_from_header(self):
        message = {"payload": {"headers": [{"name": "Subject", "value": "Hi"}]}}
        assert _extract_sender(message) is None

    def test_missing_payload(self):
        assert _extract_sender({}) is None


# ---------------------------------------------------------------------------
# _retry_once
# ---------------------------------------------------------------------------

def _make_http_error(status: int) -> HttpError:
    resp = MagicMock()
    resp.status = status
    resp.reason = "Error"
    return HttpError(resp=resp, content=b"error")


class TestRetryOnce:
    def test_success_on_first_try(self):
        fn = MagicMock(return_value="ok")
        result = _retry_once(fn, "arg1")
        assert result == "ok"
        fn.assert_called_once_with("arg1")

    def test_retries_on_transient_500(self):
        fn = MagicMock(
            side_effect=[_make_http_error(500), "recovered"]
        )
        with patch("scraper.gmail_client.time.sleep"):
            result = _retry_once(fn)
        assert result == "recovered"
        assert fn.call_count == 2

    def test_retries_on_429(self):
        fn = MagicMock(
            side_effect=[_make_http_error(429), "ok"]
        )
        with patch("scraper.gmail_client.time.sleep"):
            result = _retry_once(fn)
        assert result == "ok"

    def test_does_not_retry_on_404(self):
        fn = MagicMock(side_effect=_make_http_error(404))
        with pytest.raises(HttpError):
            _retry_once(fn)
        fn.assert_called_once()

    def test_raises_on_second_failure(self):
        fn = MagicMock(
            side_effect=[_make_http_error(503), _make_http_error(503)]
        )
        with patch("scraper.gmail_client.time.sleep"):
            with pytest.raises(HttpError):
                _retry_once(fn)
        assert fn.call_count == 2

    def test_passes_kwargs(self):
        fn = MagicMock(return_value="ok")
        _retry_once(fn, x=1, y=2)
        fn.assert_called_once_with(x=1, y=2)
