import json
import re
import time
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import requests
from cryptography.fernet import Fernet

from .proxy_parser import parse_subscription_data, parse_proxy_uri, parse_awg_conf, ProxyServer
from .crypto import encrypt_dict, decrypt_dict
from .log_utils import log_call, log_api_call, log_api_response, log_servers

logger = logging.getLogger(__name__)

USER_AGENT = "MyVPN/1.0 (VPN Client)"


@dataclass
class Subscription:
    url: str
    name: str = ""
    last_updated: float = 0.0
    auto_update_hours: int = 0
    enabled: bool = True
    _servers: list[ProxyServer] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        return self.name or self.url

    @property
    def servers(self) -> list[ProxyServer]:
        return self._servers

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "name": self.name,
            "last_updated": self.last_updated,
            "auto_update_hours": self.auto_update_hours,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Subscription":
        return cls(
            url=data.get("url", ""),
            name=data.get("name", ""),
            last_updated=data.get("last_updated", 0.0),
            auto_update_hours=data.get("auto_update_hours", 0),
            enabled=data.get("enabled", True),
        )


class SubscriptionManager:
    def __init__(self, data_dir: Path, vault: Fernet):
        self.data_dir = data_dir
        self.vault = vault
        self.subscriptions: list[Subscription] = []
        self._servers_cache: dict[str, list[ProxyServer]] = {}
        self._subs_file = data_dir / "subscriptions.json"
        self._servers_file = data_dir / "servers.json"
        data_dir.mkdir(parents=True, exist_ok=True)
        self._load()

    @log_call()
    def _load(self):
        if self._subs_file.exists():
            logger.debug("Loading subscriptions from %s", self._subs_file)
            try:
                content = self._subs_file.read_text(encoding="utf-8")
                data = json.loads(content)
                self.subscriptions = [Subscription.from_dict(s) for s in data]
                logger.info(
                    "Loaded %d subscriptions from %s",
                    len(self.subscriptions), self._subs_file,
                )
            except json.JSONDecodeError as e:
                logger.warning("Corrupt subscriptions file: %s, starting fresh", e)
                self.subscriptions = []
            except KeyError as e:
                logger.warning("Bad subscription entry (%s), starting fresh", e)
                self.subscriptions = []
        else:
            logger.debug("No subscriptions file found at %s", self._subs_file)
            self.subscriptions = []

        if self._servers_file.exists():
            logger.debug("Loading encrypted servers from %s", self._servers_file)
            try:
                with open(self._servers_file, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                if isinstance(raw_data, dict) and "v" in raw_data:
                    for url, enc in raw_data["v"].items():
                        servers_dicts = decrypt_dict(enc, self.vault)
                        self._servers_cache[url] = [
                            ProxyServer(**s) for s in servers_dicts
                        ]
                    total = sum(len(v) for v in self._servers_cache.values())
                    logger.info(
                        "Loaded %d cached servers from %d subscriptions",
                        total, len(self._servers_cache),
                    )
                else:
                    logger.warning("Servers file has unexpected structure")
            except Exception as e:
                logger.warning("Failed to load servers cache: %s, starting fresh", e)
                self._servers_cache = {}
        else:
            logger.debug("No servers file found at %s", self._servers_file)
            self._servers_cache = {}

    @log_call()
    def _save(self):
        logger.debug("Saving %d subscriptions...", len(self.subscriptions))
        self._subs_file.write_text(
            json.dumps(
                [s.to_dict() for s in self.subscriptions],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        payload = {}
        for url, servers in self._servers_cache.items():
            payload[url] = encrypt_dict(
                [{k: v for k, v in s.__dict__.items() if not k.startswith("_")} for s in servers],
                self.vault,
            )

        raw_data = {"v": payload}
        with open(self._servers_file, "w", encoding="utf-8") as f:
            json.dump(raw_data, f, ensure_ascii=False, indent=2)
        logger.debug(
            "Saved: %d subs + %d encrypted server entries",
            len(self.subscriptions), len(self._servers_cache),
        )

    @log_call()
    def add_subscription(self, url: str, name: str = "") -> Subscription:
        logger.info("Adding subscription: url=%s, name=%s", url, name or "(auto)")
        for sub in self.subscriptions:
            if sub.url == url:
                logger.info("Subscription already exists (url=%s), returning existing", url)
                return sub

        sub = Subscription(url=url, name=name)
        self.subscriptions.append(sub)
        self._save()
        logger.info("Added subscription #%d: %s", len(self.subscriptions), sub.display_name)
        return sub

    @log_call()
    def import_conf_file(self, filepath: str) -> Optional[ProxyServer]:
        srv = parse_awg_conf(filepath)
        if not srv:
            return None
        srv.subscription_tag = "Amnezia"
        self._all_servers_cache = None
        logger.info("Imported AWG config: %s (%s:%d)", srv.name, srv.server, srv.port)
        return srv

    @log_call()
    def remove_subscription(self, url: str):
        logger.info("Removing subscription: url=%s", url)
        before = len(self.subscriptions)
        self.subscriptions = [s for s in self.subscriptions if s.url != url]
        self._servers_cache.pop(url, None)
        self._save()
        logger.info("Removed subscription: %d → %d subs", before, len(self.subscriptions))

    @log_call()
    def update_subscription(self, url: str) -> list[ProxyServer]:
        sub = next((s for s in self.subscriptions if s.url == url), None)
        if not sub:
            logger.warning("Update requested for unknown subscription: %s", url)
            return []

        logger.info("Fetching subscription: %s", url[:100])

        if any(url.startswith(p) for p in ["vless://", "vmess://", "ss://", "trojan://", "hysteria2://", "hy2://"]):
            logger.info("Detected direct proxy URI, parsing locally")
            srv = parse_proxy_uri(url)
            servers = [srv] if srv else []
            for s in servers:
                s.subscription_tag = sub.display_name
            self._servers_cache[url] = servers
            sub.last_updated = time.time()
            if not sub.name and servers:
                sub.name = servers[0].display_name
            self._save()
            logger.info("Parsed %d servers from direct URI", len(servers))
            return servers

        try:
            log_api_call(logger, "GET", url)
            resp = requests.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=30,
                allow_redirects=True,
            )
            log_api_response(logger, "GET", url, resp.status_code,
                             f"Content-Type: {resp.headers.get('content-type', '?')}, Size: {len(resp.text)}")

            resp.raise_for_status()

            content_type = resp.headers.get("content-type", "").lower()
            logger.debug("Response Content-Type: %s", content_type)

            if "text/html" in content_type:
                raise ValueError(
                    f"Subscription URL returned HTML page, not proxy data: {url[:100]}"
                )

            data = resp.text
            logger.debug("Response body length: %d bytes, first 200 chars: %s...",
                        len(data), data[:200].replace("\n", "\\n"))

            if not sub.name:
                sub.name = _extract_name_from_url(url)
                logger.debug("Auto-extracted name: %s", sub.name)

            servers = parse_subscription_data(data)
            logger.info(
                "Parsed %d servers from subscription '%s'",
                len(servers), sub.display_name,
            )
            log_servers(logger, servers, f"from {sub.display_name}")

            for srv in servers:
                srv.subscription_tag = sub.display_name

            self._servers_cache[url] = servers
            sub.last_updated = time.time()
            self._save()
            logger.info("Subscription '%s' updated at %s", sub.display_name,
                       time.strftime("%H:%M:%S", time.localtime(sub.last_updated)))
            return servers

        except requests.RequestException as e:
            logger.error("HTTP error fetching subscription %s: %s", url[:80], e)
            raise RuntimeError(f"Failed to fetch subscription: {e}") from e
        except ValueError as e:
            logger.error("Parse error on subscription %s: %s", url[:80], e)
            raise

    @log_call()
    def update_all_subscriptions(self) -> dict[str, list[ProxyServer]]:
        logger.info("Updating all %d subscriptions...", len(self.subscriptions))
        results = {}
        for sub in self.subscriptions:
            if not sub.enabled:
                logger.debug("Skipping disabled subscription: %s", sub.display_name)
                continue
            try:
                servers = self.update_subscription(sub.url)
                results[sub.url] = servers
            except Exception as e:
                logger.error("Failed to update '%s': %s", sub.display_name, e, exc_info=True)
                results[sub.url] = []
        total = sum(len(v) for v in results.values())
        logger.info("All subscriptions updated: %d total servers", total)
        return results

    @log_call()
    def get_all_servers(self) -> list[ProxyServer]:
        all_servers = []
        seen_tags = set()
        for sub in self.subscriptions:
            if not sub.enabled:
                continue
            servers = self._servers_cache.get(sub.url, [])
            logger.debug("Subscription '%s': %d cached servers", sub.display_name, len(servers))
            for srv in servers:
                if srv.tag not in seen_tags:
                    seen_tags.add(srv.tag)
                    all_servers.append(srv)
        logger.debug("Total unique servers: %d", len(all_servers))
        return all_servers

    @log_call()
    def get_cached_servers(self, url: str) -> list[ProxyServer]:
        servers = self._servers_cache.get(url, [])
        logger.debug("Cached servers for %s: %d", url[:60], len(servers))
        return servers

    def needs_update(self, url: str) -> bool:
        sub = next((s for s in self.subscriptions if s.url == url), None)
        if not sub:
            return True
        if not self._servers_cache.get(url):
            return True
        if sub.auto_update_hours <= 0:
            return False
        elapsed = time.time() - sub.last_updated
        should_update = elapsed > sub.auto_update_hours * 3600
        logger.debug(
            "needs_update(%s): last=%s, hours=%d, elapsed=%.1fh, needs=%s",
            url[:50], sub.last_updated, sub.auto_update_hours,
            elapsed / 3600, should_update,
        )
        return should_update


def _extract_name_from_url(url: str) -> str:
    from urllib.parse import urlparse, parse_qs

    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        name = params.get("name", [None])[0]
        if name:
            return name
        path = parsed.path.strip("/")
        if path:
            name_match = re.search(r"token[=/](\d+)", url)
            if name_match:
                return f"Sub {name_match.group(1)}"
        host = parsed.hostname or ""
        if host:
            return host.split(".")[-2] if len(host.split(".")) > 1 else host
    except Exception:
        pass
    return "Subscription"
