from unittest.mock import MagicMock

import httpx
import pytest

from src.finance.fetcher import FetchError, fetch_html


def test_http_success_returns_html(mocker):
    mock_response = MagicMock(status_code=200, text="<html>OK</html>")
    mock_response.raise_for_status = MagicMock()
    mocker.patch("httpx.get", return_value=mock_response)
    mocker.patch("time.sleep")
    html = fetch_html("https://example.com/report")
    assert "OK" in html


def test_retries_on_5xx(mocker):
    bad = MagicMock(status_code=503)
    bad.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError("fail", request=MagicMock(), response=bad)
    )
    good = MagicMock(status_code=200, text="<html>OK</html>")
    good.raise_for_status = MagicMock()
    get_mock = mocker.patch("httpx.get", side_effect=[bad, bad, good])
    mocker.patch("time.sleep")
    html = fetch_html("https://example.com/report")
    assert "OK" in html
    assert get_mock.call_count == 3


def test_falls_back_to_playwright_when_validator_fails(mocker):
    mock_response = MagicMock(status_code=200, text="<html>tiny</html>")
    mock_response.raise_for_status = MagicMock()
    mocker.patch("httpx.get", return_value=mock_response)
    mocker.patch("time.sleep")
    playwright_mock = mocker.MagicMock(return_value="<html>Total Receipts ...</html>")
    html = fetch_html(
        "https://example.com/report",
        validator=lambda t: "Total Receipts" in t,
        playwright_fetch=playwright_mock,
    )
    assert "Total Receipts" in html
    playwright_mock.assert_called_once()


def test_validator_fails_no_playwright_raises(mocker):
    mock_response = MagicMock(status_code=200, text="<html>tiny</html>")
    mock_response.raise_for_status = MagicMock()
    mocker.patch("httpx.get", return_value=mock_response)
    mocker.patch("time.sleep")
    with pytest.raises(FetchError):
        fetch_html(
            "https://example.com/report",
            validator=lambda t: "Total Receipts" in t,
        )


def test_raises_after_max_retries(mocker):
    mock_response = MagicMock(status_code=500)
    mock_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "fail", request=MagicMock(), response=mock_response
        )
    )
    mocker.patch("httpx.get", return_value=mock_response)
    mocker.patch("time.sleep")
    with pytest.raises(FetchError):
        fetch_html("https://example.com/report")


def test_falls_back_to_playwright_after_http_exhausted(mocker):
    mock_response = MagicMock(status_code=500)
    mock_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "fail", request=MagicMock(), response=mock_response
        )
    )
    mocker.patch("httpx.get", return_value=mock_response)
    mocker.patch("time.sleep")
    pw_mock = mocker.MagicMock(return_value="<html>from playwright</html>")
    html = fetch_html("https://example.com/report", playwright_fetch=pw_mock)
    assert "playwright" in html
    pw_mock.assert_called_once()


def test_playwright_fallback_failure_raises(mocker):
    mock_response = MagicMock(status_code=500)
    mock_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "fail", request=MagicMock(), response=mock_response
        )
    )
    mocker.patch("httpx.get", return_value=mock_response)
    mocker.patch("time.sleep")
    pw_mock = mocker.MagicMock(side_effect=RuntimeError("pw broke"))
    with pytest.raises(FetchError):
        fetch_html("https://example.com/report", playwright_fetch=pw_mock)


def test_handles_request_error(mocker):
    """Connection errors trigger retries and ultimately FetchError."""
    mocker.patch(
        "httpx.get",
        side_effect=httpx.RequestError("connect failed", request=MagicMock()),
    )
    mocker.patch("time.sleep")
    with pytest.raises(FetchError):
        fetch_html("https://example.com/report")
