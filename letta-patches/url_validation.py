"""Locally-patched MCP URL validator (bind-mounted over /app/letta/helpers/url_validation.py).

Upstream Letta rejects EVERY non-global IP for MCP server URLs, which makes a
self-hosted MCP on loopback (Eva's SearXNG MCP at 127.0.0.1:3010) impossible to
connect to. On this single-user, non-exposed box where the user owns every MCP
endpoint, that guard is counter-productive. This patch keeps the part that
matters for SSRF — blocking link-local / cloud-metadata (169.254.x / fe80::) and
the known metadata hostnames — but permits loopback and private (RFC1918 / ULA)
targets. Keep this in sync with upstream's function signature on Letta upgrades.
"""

import ipaddress
import socket
from urllib.parse import urlparse

# Cloud-metadata and orchestrator-internal names still get blocked.
_BLOCKED_HOSTNAMES = {
    "metadata.google.internal",
    "metadata.google.internal.",
}

_BLOCKED_SUFFIXES = (
    ".svc",
    ".cluster.local",
)


def _normalize_hostname(hostname: str) -> str:
    return hostname.rstrip(".").lower()


def _is_blocked_hostname(hostname: str) -> bool:
    normalized = _normalize_hostname(hostname)
    blocked_hostnames = {_normalize_hostname(value) for value in _BLOCKED_HOSTNAMES}
    return normalized in blocked_hostnames or any(
        normalized.endswith(suffix) for suffix in _BLOCKED_SUFFIXES
    )


def _ip_blocked(ip) -> bool:
    """Block only the genuine SSRF risks; allow loopback + private LAN."""
    return ip.is_link_local or ip.is_multicast or ip.is_unspecified or ip.is_reserved


def validate_mcp_server_url(url: str, *, resolve_hostname: bool = True) -> str:
    """Validate MCP HTTP(S) URLs. Permits loopback/private; blocks link-local/metadata."""
    if not url:
        raise ValueError("server_url cannot be empty")

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"server_url must start with 'http://' or 'https://', got: '{url}'")
    if not parsed.netloc:
        raise ValueError(f"server_url must have a valid host, got: '{url}'")
    if parsed.hostname is None:
        raise ValueError("Missing hostname")

    hostname = _normalize_hostname(parsed.hostname)
    if _is_blocked_hostname(hostname):
        raise ValueError(f"Blocked internal hostname: {parsed.hostname}")

    try:
        parsed_ip = ipaddress.ip_address(hostname)
    except ValueError:
        parsed_ip = None

    if parsed_ip is not None:
        if _ip_blocked(parsed_ip):
            raise ValueError(f"Blocked IP not allowed: {parsed.hostname}")
        return url

    if not resolve_hostname:
        return url

    try:
        infos = socket.getaddrinfo(
            hostname,
            parsed.port or (443 if parsed.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise ValueError(f"Cannot resolve hostname: {parsed.hostname}") from exc

    seen_ips = set()
    for _, _, _, _, sockaddr in infos:
        ip_text = sockaddr[0]
        if ip_text in seen_ips:
            continue
        seen_ips.add(ip_text)
        if _ip_blocked(ipaddress.ip_address(ip_text)):
            raise ValueError(f"Hostname resolves to blocked IP: {ip_text}")

    if not seen_ips:
        raise ValueError(f"Cannot resolve hostname: {parsed.hostname}")

    return url
