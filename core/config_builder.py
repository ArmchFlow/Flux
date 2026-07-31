import json
import logging
from pathlib import Path

from .proxy_parser import ProxyServer
from .settings_manager import AppSettings

logger = logging.getLogger(__name__)


def _is_ip(host: str) -> bool:
    parts = host.split(".")
    if len(parts) != 4:
        return False
    return all(p.isdigit() for p in parts)


def _parse_dns_url(raw: str) -> tuple[str, str]:
    proto = "https"
    host = raw
    if "://" in raw:
        proto = raw.split("://", 1)[0]
        host = raw.split("://", 1)[1].split("/")[0]
    proto_map = {
        "https": "https", "tls": "tls", "tcp": "tcp",
        "udp": "udp", "quic": "quic", "h3": "h3",
    }
    return proto_map.get(proto, "https"), host


def build_singbox_tun_config(
    settings: AppSettings,
    core_paths: list[str] | None = None,
) -> dict:
    dns_type, dns_host = _parse_dns_url(settings.dns.remote_dns)

    dns_remote = {"tag": "dns-remote", "type": dns_type, "server": dns_host}
    if not _is_ip(dns_host):
        dns_remote["domain_resolver"] = "dns-direct"

    rules = []

    if core_paths:
        rules.append({
            "port": [53],
            "action": "hijack-dns",
            "process_path": core_paths,
        })
        rules.append({
            "outbound": "direct",
            "process_path": core_paths,
        })

    rules.extend([
        {"domain_suffix": ["msftncsi.com", "msftconnecttest.com"], "outbound": "direct"},
        {"action": "sniff"},
        {
            "type": "logical",
            "mode": "or",
            "action": "hijack-dns",
            "rules": [
                {"port": [53]},
                {"protocol": ["dns"]},
            ],
        },
        {"ip_is_private": True, "outbound": "direct"},
        {"inbound": "tun-in", "outbound": "proxy"},
    ])

    return {
        "log": {"level": "debug"},
        "dns": {
            "servers": [
                dns_remote,
                {"tag": "dns-direct", "type": "udp", "server": "8.8.8.8"},
            ],
            "final": "dns-remote",
            "strategy": "ipv4_only",
            "reverse_mapping": True,
        },
        "inbounds": [{
            "type": "tun",
            "tag": "tun-in",
            "interface_name": settings.tun.interface_name or "",
            "address": [settings.tun.address],
            "mtu": settings.tun.mtu,
            "auto_route": settings.tun.auto_route,
            "strict_route": settings.tun.strict_route,
            "stack": settings.tun.stack,
        }],
        "outbounds": [
            {"type": "direct", "tag": "direct"},
            {
                "type": "socks", "tag": "proxy",
                "server": "127.0.0.1", "server_port": 10808,
            },
        ],
        "route": {
            "auto_detect_interface": True,
            "default_domain_resolver": "dns-remote",
            "rules": rules,
            "final": "proxy",
        },
    }


def build_xray_proxy_config(servers, selected_tag):
    srv = next((s for s in servers if s.tag == selected_tag), None)
    if not srv and servers:
        srv = servers[0]
    if not srv:
        raise ValueError("No servers available")

    ob = {"protocol": srv.protocol, "tag": srv.tag}

    if srv.protocol == "vless":
        ob["settings"] = {"vnext": [{
            "address": srv.server, "port": srv.port,
            "users": [{
                "id": srv.uuid,
                "encryption": srv.encryption or "none",
            }],
        }]}
        if srv.flow:
            ob["settings"]["vnext"][0]["users"][0]["flow"] = srv.flow
    elif srv.protocol == "vmess":
        ob["settings"] = {"vnext": [{
            "address": srv.server, "port": srv.port,
            "users": [{"id": srv.uuid, "security": srv.encryption or "auto"}],
        }]}
    elif srv.protocol == "trojan":
        ob["settings"] = {"servers": [{
            "address": srv.server, "port": srv.port, "password": srv.password,
        }]}
    elif srv.protocol == "ss":
        ob["settings"] = {"servers": [{
            "address": srv.server, "port": srv.port,
            "method": srv.ss_method or "aes-256-gcm", "password": srv.password,
        }]}
    else:
        raise ValueError(f"Unsupported protocol: {srv.protocol}")

    _add_xray_stream(ob, srv)

    config = {
        "log": {"loglevel": "info"},
        "inbounds": [{
            "tag": "socks-in", "protocol": "socks",
            "listen": "127.0.0.1", "port": 10808,
            "settings": {"auth": "noauth", "udp": True},
            "sniffing": {"enabled": True, "destOverride": ["http", "tls"]},
        }],
        "outbounds": [
            {"protocol": "freedom", "tag": "direct"},
            ob,
        ],
        "routing": {
            "rules": [{
                "type": "field",
                "inboundTag": ["socks-in"],
                "outboundTag": srv.tag,
            }],
        },
    }

    logger.info("Xray config: %s://%s:%d", srv.protocol, srv.server, srv.port)
    return config


def _add_xray_stream(ob: dict, srv: ProxyServer):
    ss: dict = {}
    network = (srv.network or "tcp").lower()

    if network in ("ws", "websocket"):
        ss["network"] = "ws"
        ws = {}
        if srv.ws_path:
            ws["path"] = srv.ws_path
        if srv.ws_host:
            ws["headers"] = {"Host": srv.ws_host}
        if ws:
            ss["wsSettings"] = ws
    elif network == "grpc":
        ss["network"] = "grpc"
        if srv.grpc_service:
            ss["grpcSettings"] = {"serviceName": srv.grpc_service}
    elif network in ("httpupgrade", "xhttp"):
        ss["network"] = "xhttp"
        xh = {}
        path = srv.hopath or srv.ws_path
        if path:
            xh["path"] = path
        host = srv.hohost or srv.ws_host or srv.sni
        if host:
            xh["host"] = host
        if xh:
            ss["xhttpSettings"] = xh

    if srv.security == "reality":
        ss["security"] = "reality"
        rs = {
            "serverName": srv.sni or srv.server,
            "fingerprint": srv.fingerprint or "chrome",
        }
        if srv.public_key:
            rs["publicKey"] = srv.public_key
        if srv.short_id:
            rs["shortId"] = srv.short_id
        if srv.spider_x:
            rs["spiderX"] = srv.spider_x
        ss["realitySettings"] = rs
    elif srv.security == "tls":
        ss["security"] = "tls"
        ts = {"serverName": srv.sni or srv.server}
        if srv.fingerprint:
            ts["fingerprint"] = srv.fingerprint
        if srv.alpn:
            ts["alpn"] = [a.strip() for a in srv.alpn.split(",") if a.strip()]
        ss["tlsSettings"] = ts

    if ss:
        ob["streamSettings"] = ss


def save_config_to_file(config: dict, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
