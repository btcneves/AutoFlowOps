"""SSRF protection: block requests to private/internal network ranges."""

import ipaddress
import socket
from urllib.parse import urlparse

from fastapi import HTTPException

_PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),   # link-local
    ipaddress.ip_network("100.64.0.0/10"),    # shared address space
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),          # IPv6 ULA
    ipaddress.ip_network("fe80::/10"),         # IPv6 link-local
]


def _is_private(addr: str) -> bool:
    try:
        ip = ipaddress.ip_address(addr)
        return any(ip in net for net in _PRIVATE_NETWORKS)
    except ValueError:
        return False


def _resolve_host(host: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, None)
        return [info[4][0] for info in infos]
    except socket.gaierror:
        return []


def check_url(url: str) -> None:
    """Raise HTTP 403 if the URL targets a private/internal address."""
    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid job URL")

    host = parsed.hostname
    if not host:
        raise HTTPException(status_code=422, detail="Job URL has no host")

    if _is_private(host):
        raise HTTPException(
            status_code=403,
            detail="Job URL targets a private or reserved address (SSRF protection)",
        )

    for resolved in _resolve_host(host):
        if _is_private(resolved):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Job URL resolves to a private or reserved address"
                    " (SSRF protection)"
                ),
            )
