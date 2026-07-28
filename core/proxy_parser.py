import base64
import json
import re
from dataclasses import dataclass, field
from urllib.parse import urlparse, parse_qs, unquote
from typing import Optional


SUPPORTED_PROTOCOLS = {"vless", "vmess", "ss", "trojan", "hysteria2", "hy2"}


@dataclass
class ProxyServer:
    protocol: str
    name: str = ""
    server: str = ""
    port: int = 443
    uuid: str = ""
    password: str = ""
    flow: str = ""
    encryption: str = ""
    network: str = "tcp"
    security: str = "none"

    sni: str = ""
    alpn: str = ""
    fingerprint: str = ""
    public_key: str = ""
    short_id: str = ""
    spider_x: str = ""

    ws_path: str = ""
    ws_host: str = ""

    grpc_service: str = ""

    hopath: str = ""
    hohost: str = ""

    cipher: str = ""
    ss_method: str = ""

    quic_security: str = ""
    quic_key: str = ""

    obfs: str = ""
    obfs_password: str = ""
    obfs_host: str = ""

    subscription_tag: str = ""

    @property
    def tag(self) -> str:
        if self.name:
            clean = re.sub(r'[^a-zA-Z0-9\-_.#\[\]]', '', self.name)
            return clean or f"{self.protocol}-{self.server or 'unknown'}"
        return f"{self.protocol}-{self.server or 'unknown'}"

    @property
    def display_name(self) -> str:
        return self.name or self.tag


def parse_proxy_uri(uri: str) -> Optional[ProxyServer]:
    uri = uri.strip()
    if not uri:
        return None

    if "://" not in uri:
        return None

    proto, rest = uri.split("://", 1)
    proto = proto.lower()

    if proto not in SUPPORTED_PROTOCOLS:
        return None

    try:
        if proto == "vmess":
            return _parse_vmess(rest)
        elif proto == "ss":
            return _parse_ss(rest)
        elif proto == "ssr":
            return _parse_ssr(rest)
        elif proto == "trojan":
            return _parse_trojan(rest)
        elif proto in ("hysteria2", "hy2"):
            return _parse_hysteria2(rest)
        else:
            return _parse_vless(uri, proto)
    except Exception:
        return None


def _parse_vless(uri: str, proto: str) -> ProxyServer:
    s = ProxyServer(protocol=proto)

    parsed = urlparse(uri)
    s.server = parsed.hostname or ""
    s.port = parsed.port or 443
    s.uuid = parsed.username or ""

    s.name = unquote(parsed.fragment or "")

    params = parse_qs(parsed.query)

    s.encryption = _first(params, "encryption", "none")
    s.security = _first(params, "security", "")
    s.flow = _first(params, "flow", "")
    s.network = _first(params, "type", "tcp")

    s.sni = _first(params, "sni", "") or s.server
    s.alpn = _first(params, "alpn", "")
    s.fingerprint = _first(params, "fp", "")
    s.public_key = _first(params, "pbk", "")
    s.short_id = _first(params, "sid", "")
    s.spider_x = _first(params, "spx", "")

    s.ws_path = _first(params, "path", "")
    s.ws_host = _first(params, "host", "")

    s.grpc_service = _first(params, "serviceName", "")

    s.quic_security = _first(params, "quicSecurity", "")
    s.quic_key = _first(params, "key", "")

    if s.network == "http":
        s.hopath = _first(params, "path", "")
        s.hohost = _first(params, "host", "")
    elif s.network == "httpupgrade":
        s.hopath = _first(params, "path", "")
        s.hohost = _first(params, "host", "")

    return s


def _parse_vmess(rest: str) -> ProxyServer:
    try:
        raw = base64.b64decode(rest + "===").decode("utf-8")
    except Exception:
        raw = rest

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        url_part = "vmess://" + rest
        return _parse_vless(url_part, "vmess")

    s = ProxyServer(protocol="vmess")
    s.name = data.get("ps", "")
    s.server = data.get("add", "")
    s.port = int(data.get("port", 443))
    s.uuid = data.get("id", "")
    s.encryption = data.get("scy", "auto")
    s.network = data.get("net", "tcp")
    s.security = data.get("tls", "none")
    s.sni = data.get("sni", data.get("host", "")) or s.server
    s.fingerprint = data.get("fp", "")
    s.alpn = data.get("alpn", "")
    s.ws_path = data.get("path", "")
    s.ws_host = data.get("host", "")
    s.grpc_service = data.get("path", "")

    if data.get("type") in ("http", "h2"):
        s.network = "http"
        s.hohost = ",".join(data.get("host", "")) if isinstance(data.get("host"), list) else data.get("host", "")

    return s


def _parse_ss(rest: str) -> ProxyServer:
    s = ProxyServer(protocol="ss", port=8388)

    if "@" not in rest:
        try:
            decoded = base64.b64decode(rest + "===").decode("utf-8")
        except Exception:
            return s
        rest = decoded

    if "#" in rest:
        rest, name = rest.rsplit("#", 1)
        s.name = unquote(name)

    if "@" in rest:
        userinfo, hostpart = rest.rsplit("@", 1)
    else:
        userinfo = rest
        hostpart = ""

    if hostpart:
        if ":" in hostpart:
            host, port = hostpart.rsplit(":", 1)
            s.server = host.strip("[]")
            try:
                s.port = int(port)
            except ValueError:
                pass
        else:
            s.server = hostpart.strip("[]")

    if ":" in userinfo:
        try:
            decoded = base64.b64decode(userinfo + "===").decode("utf-8")
        except Exception:
            decoded = userinfo
        if ":" in decoded:
            s.ss_method, s.password = decoded.split(":", 1)

    return s


def _parse_ssr(rest: str) -> ProxyServer:
    try:
        decoded = base64.b64decode(rest + "===").decode("utf-8")
    except Exception:
        return ProxyServer(protocol="ssr")

    parts = decoded.split(":", 5)
    if len(parts) < 6:
        return ProxyServer(protocol="ssr")

    s = ProxyServer(protocol="ssr")
    s.server = parts[0]
    try:
        s.port = int(parts[1])
    except ValueError:
        s.port = 1080
    s.protocol = parts[2]
    s.ss_method = parts[3]
    s.obfs = parts[4]

    param_part = parts[5]
    if "/?" in param_part:
        base_pw, params_str = param_part.split("/?", 1)
        try:
            s.password = base64.b64decode(base_pw + "===").decode("utf-8")
        except Exception:
            s.password = base_pw

        params = parse_qs(params_str)
        s.obfs_password = _first(params, "obfsparam", "")
        try:
            s.obfs_password = base64.b64decode(s.obfs_password + "===").decode("utf-8")
        except Exception:
            pass
        s.name = _first(params, "remarks", "")
        try:
            s.name = base64.b64decode(s.name + "===").decode("utf-8")
        except Exception:
            pass
    else:
        try:
            s.password = base64.b64decode(param_part + "===").decode("utf-8")
        except Exception:
            s.password = param_part

    return s


def _parse_trojan(rest: str) -> ProxyServer:
    s = ProxyServer(protocol="trojan")

    if "#" in rest:
        rest, name = rest.rsplit("#", 1)
        s.name = unquote(name)

    if "?" in rest:
        hostport, query = rest.split("?", 1)
        params = parse_qs(query)
        s.security = _first(params, "security", "")
        s.sni = _first(params, "sni", "") or s.server
        s.alpn = _first(params, "alpn", "")
        s.fingerprint = _first(params, "fp", "")
        s.network = _first(params, "type", "tcp")
        s.ws_path = _first(params, "path", "")
        s.ws_host = _first(params, "host", "")
        s.grpc_service = _first(params, "serviceName", "")
        if s.network in ("http", "httpupgrade"):
            s.hopath = _first(params, "path", "")
            s.hohost = _first(params, "host", "")
    else:
        hostport = rest

    if "@" in hostport:
        password, hostport = hostport.rsplit("@", 1)
    else:
        password = hostport
        hostport = ""

    s.password = password

    if hostport:
        if ":" in hostport:
            host, port = hostport.rsplit(":", 1)
            s.server = host.strip("[]")
            try:
                s.port = int(port)
            except ValueError:
                pass
        else:
            s.server = hostport.strip("[]")

    if not s.sni:
        s.sni = s.server

    return s


def _parse_hysteria2(rest: str) -> ProxyServer:
    s = ProxyServer(protocol="hysteria2")

    if "#" in rest:
        rest, name = rest.rsplit("#", 1)
        s.name = unquote(name)

    if "?" in rest:
        hostport, query = rest.split("?", 1)
        params = parse_qs(query)
        s.sni = _first(params, "sni", "") or s.server
        s.alpn = _first(params, "alpn", "")
        s.fingerprint = _first(params, "fp", "")
        s.obfs = _first(params, "obfs", "")
        s.obfs_password = _first(params, "obfs-password", "")
        s.security = "tls" if _first(params, "insecure", "0") == "0" else ""
    else:
        hostport = rest

    if "@" in hostport:
        password, hostport = hostport.rsplit("@", 1)
    else:
        password = hostport
        hostport = ""

    s.password = password

    if hostport:
        if ":" in hostport:
            host, port = hostport.rsplit(":", 1)
            s.server = host.strip("[]")
            try:
                s.port = int(port)
            except ValueError:
                pass
        else:
            s.server = hostport.strip("[]")

    if not s.sni:
        s.sni = s.server

    return s


def _first(params: dict, key: str, default: str = "") -> str:
    vals = params.get(key, [])
    return unquote(vals[0]) if vals else default


def parse_subscription_data(data: str) -> list[ProxyServer]:
    if data.startswith("proxies:"):
        return _parse_clash_yaml(data)

    try:
        decoded = base64.b64decode(data + "===").decode("utf-8", errors="replace")
    except Exception:
        decoded = data

    servers = []
    for line in decoded.splitlines():
        line = line.strip()
        if not line or "://" not in line:
            continue
        srv = parse_proxy_uri(line)
        if srv:
            servers.append(srv)

    return servers


def _parse_clash_yaml(data: str) -> list[ProxyServer]:
    try:
        import yaml
    except ImportError:
        return []

    try:
        config = yaml.safe_load(data)
    except Exception:
        return []

    servers = []
    proxies = config.get("proxies", [])

    for p in proxies:
        ptype = p.get("type", "").lower()

        s = ProxyServer(protocol=ptype)
        s.name = p.get("name", "")
        s.server = p.get("server", "")
        try:
            s.port = int(p.get("port", 443))
        except (ValueError, TypeError):
            s.port = 443

        if ptype == "vmess":
            s.uuid = p.get("uuid", "")
            s.encryption = p.get("cipher", "auto")
            s.network = p.get("network", "tcp")
            s.security = p.get("tls", False)
            if isinstance(s.security, bool):
                s.security = "tls" if s.security else "none"
            s.sni = p.get("servername", "") or s.server
            s.fingerprint = p.get("client-fingerprint", "")
            s.alpn = ",".join(p.get("alpn", [])) if isinstance(p.get("alpn"), list) else p.get("alpn", "")
            s.ws_path = p.get("ws-opts", {}).get("path", "") if isinstance(p.get("ws-opts"), dict) else ""
            s.ws_host = p.get("ws-opts", {}).get("headers", {}).get("Host", "") if isinstance(p.get("ws-opts"), dict) else ""
            s.grpc_service = p.get("grpc-opts", {}).get("grpc-service-name", "") if isinstance(p.get("grpc-opts"), dict) else ""

            reality = p.get("reality-opts", {})
            if isinstance(reality, dict):
                s.public_key = reality.get("public-key", "")
                s.short_id = reality.get("short-id", "")

        elif ptype == "ss":
            s.ss_method = p.get("cipher", "")
            s.password = p.get("password", "")

        elif ptype == "trojan":
            s.password = p.get("password", "")
            s.sni = p.get("sni", "") or s.server
            s.network = p.get("network", "tcp")

        elif ptype in ("hysteria2", "hy2"):
            s.password = p.get("password", "")
            s.sni = p.get("sni", "") or s.server
            s.obfs = p.get("obfs", "")

        elif ptype == "vless":
            s.uuid = p.get("uuid", "")
            s.flow = p.get("flow", "")
            s.network = p.get("network", "tcp")
            s.security = p.get("tls", False)
            if isinstance(s.security, bool):
                s.security = "tls" if s.security else "none"
            s.sni = p.get("servername", "") or s.server

        servers.append(s)

    return servers
