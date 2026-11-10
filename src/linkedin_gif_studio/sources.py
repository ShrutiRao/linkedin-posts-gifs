from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlsplit

import trafilatura


@dataclass(frozen=True)
class SourceExtraction:
    url: str
    text: str | None
    error: str | None


def _assert_public_http_url(url: str, resolver: Callable[..., list] | None = None) -> None:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only public http(s) URLs are supported")
    if parsed.username or parsed.password:
        raise ValueError("URLs containing credentials are not supported")
    host = parsed.hostname.lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        raise ValueError("Local and private hosts are blocked")
    try:
        literal = ipaddress.ip_address(host)
        addresses = [literal]
    except ValueError:
        addresses = []
        resolver = resolver or socket.getaddrinfo
        for item in resolver(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM):
            addresses.append(ipaddress.ip_address(item[4][0]))
    if not addresses or any(
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
        for address in addresses
    ):
        raise ValueError("Local and private hosts are blocked")


def extract_public_sources(
    urls: list[str],
    fetcher: Callable[[str], str | None] = trafilatura.fetch_url,
    extractor: Callable[..., str | None] = trafilatura.extract,
    max_chars_per_source: int = 6_000,
) -> list[SourceExtraction]:
    results: list[SourceExtraction] = []
    for url in urls:
        try:
            _assert_public_http_url(url)
            downloaded = fetcher(url)
            if not downloaded:
                raise ValueError("The page could not be downloaded")
            text = extractor(downloaded, include_comments=False, include_tables=False)
            if not text or not text.strip():
                raise ValueError("No readable article text was found")
            results.append(SourceExtraction(url=url, text=text.strip()[:max_chars_per_source], error=None))
        except Exception as exc:
            results.append(SourceExtraction(url=url, text=None, error=str(exc)))
    return results
