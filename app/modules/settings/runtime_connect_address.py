from __future__ import annotations

import ipaddress
import os
import socket

from fastapi import Request

LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1", "[::1]"}


def _is_non_loopback_ipv4(value: str | None) -> bool:
    if not value:
        return False
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return isinstance(address, ipaddress.IPv4Address) and not address.is_loopback and not address.is_unspecified


def _resolve_hostname_ipv4(hostname: str) -> str | None:
    try:
        infos = socket.getaddrinfo(hostname, None, family=socket.AF_INET, type=socket.SOCK_STREAM)
    except OSError:
        return None
    for info in infos:
        candidate = info[4][0]
        if not isinstance(candidate, str):
            continue
        if _is_non_loopback_ipv4(candidate):
            return candidate
    return None


def resolve_runtime_connect_address(request: Request) -> str:
    override = os.getenv("CODEX_LB_CONNECT_ADDRESS", "").strip()
    if override:
        return override

    request_host = request.url.hostname or ""
    if _is_non_loopback_ipv4(request_host):
        return request_host

    normalized_host = request_host.strip().lower()
    if normalized_host and normalized_host not in LOOPBACK_HOSTS:
        resolved_host = _resolve_hostname_ipv4(request_host)
        if resolved_host:
            return resolved_host
        return request_host
    return "<codex-lb-ip-or-dns>"
