from __future__ import annotations

import socket
from ipaddress import ip_address

from .config import SAFETY_BOUNDARY
from .state_store import now_iso


def _is_phone_lan_candidate(address: str) -> bool:
    try:
        parsed = ip_address(address)
    except ValueError:
        return False
    return bool(parsed.version == 4 and parsed.is_private and not parsed.is_loopback and not parsed.is_link_local)


def _local_ipv4_candidates() -> list[str]:
    candidates: set[str] = set()
    hostnames = {socket.gethostname(), socket.getfqdn()}
    for hostname in hostnames:
        try:
            for info in socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM):
                address = info[4][0]
                if address and not address.startswith("127."):
                    candidates.add(address)
        except socket.gaierror:
            continue

    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))
        address = probe.getsockname()[0]
        if address and not address.startswith("127."):
            candidates.add(address)
    except OSError:
        pass
    finally:
        try:
            probe.close()
        except UnboundLocalError:
            pass

    return sorted(candidates)


def build_mobile_connection_info(host: str, port: int) -> dict:
    lan_addresses = _local_ipv4_candidates()
    recommended_addresses = [address for address in lan_addresses if _is_phone_lan_candidate(address)]
    fallback_addresses = [address for address in lan_addresses if address not in recommended_addresses]
    mobile_addresses = recommended_addresses or fallback_addresses
    mobile_urls = [f"http://{address}:{port}" for address in mobile_addresses]
    endpoint_urls = [f"{url}/api/mobile/status" for url in mobile_urls]
    local_url = f"http://127.0.0.1:{port}"
    server_lan_visible = host in {"0.0.0.0", "::"} or _is_phone_lan_candidate(host)
    recommended_url = endpoint_urls[0] if endpoint_urls and server_lan_visible else None
    notes = [
        "Use the LAN URL on a real phone; 127.0.0.1 points to the phone itself.",
        "Keep the phone and desktop on the same Wi-Fi or LAN.",
        "If the phone cannot connect, allow Python through Windows Firewall for this local port.",
        "This endpoint only exposes read-only status and cannot execute trades.",
    ]
    if not server_lan_visible:
        notes.insert(0, "The console is currently bound to localhost only. Restart with scripts/start_console.ps1 -Mobile for phone testing.")
    return {
        "version": "V13.6.3",
        "source": "alphapilot_control_console_v13_6_3",
        "generatedAt": now_iso(),
        "serverHost": host,
        "serverPort": port,
        "serverLanVisible": server_lan_visible,
        "localUrl": local_url,
        "localMobileStatusUrl": f"{local_url}/api/mobile/status",
        "lanAddresses": recommended_addresses,
        "allDetectedIpv4Addresses": lan_addresses,
        "mobileUrls": mobile_urls,
        "mobileStatusUrls": endpoint_urls,
        "recommendedMobileUrl": recommended_url,
        "sameWifiRequired": True,
        "firewallMayBlock": True,
        "safetyBoundary": SAFETY_BOUNDARY,
        "notes": notes,
    }
