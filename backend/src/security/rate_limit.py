from __future__ import annotations

import ipaddress
import os

from fastapi import Request
from slowapi import Limiter


def _trusted_proxy_networks() -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    configured = os.getenv("TRUSTED_PROXY_CIDRS", "127.0.0.1,::1")
    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for raw_cidr in configured.split(","):
        cidr = raw_cidr.strip()
        if not cidr:
            continue
        try:
            networks.append(ipaddress.ip_network(cidr, strict=False))
        except ValueError:
            continue
    return tuple(networks)


def _is_trusted_proxy_ip(remote_ip: str) -> bool:
    try:
        remote = ipaddress.ip_address(remote_ip)
    except ValueError:
        return False
    return any(remote in network for network in _trusted_proxy_networks())


def get_rate_limit_key(request: Request) -> str:
    remote_ip = request.client.host if request.client and request.client.host else "127.0.0.1"
    forwarded_for = request.headers.get("x-forwarded-for")

    if not forwarded_for or not _is_trusted_proxy_ip(remote_ip):
        return remote_ip

    for candidate in (piece.strip() for piece in forwarded_for.split(",")):
        if not candidate:
            continue
        try:
            ipaddress.ip_address(candidate)
            return candidate
        except ValueError:
            continue

    return remote_ip


limiter = Limiter(key_func=get_rate_limit_key)
