from __future__ import annotations

import socket

import pytest

from linkedin_gif_studio.sources import _assert_public_http_url, extract_public_sources


def test_private_and_local_source_urls_are_blocked() -> None:
    with pytest.raises(ValueError, match="blocked"):
        _assert_public_http_url("http://127.0.0.1/private")
    with pytest.raises(ValueError, match="blocked"):
        _assert_public_http_url("http://localhost/private")


def test_public_source_is_extracted_with_injected_network_functions(monkeypatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))],
    )
    results = extract_public_sources(
        ["https://example.com/article"],
        fetcher=lambda _: "<html><body><article>Grounded public evidence.</article></body></html>",
        extractor=lambda *_args, **_kwargs: "Grounded public evidence.",
    )
    assert results[0].error is None
    assert results[0].text == "Grounded public evidence."

