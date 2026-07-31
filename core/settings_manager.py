import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from .log_utils import log_call

logger = logging.getLogger(__name__)


@dataclass
class TunSettings:
    enabled: bool = True
    interface_name: str = ""
    address: str = "172.19.0.1/30"
    mtu: int = 9000
    auto_route: bool = True
    strict_route: bool = False
    stack: str = "gvisor"


@dataclass
class SplitTunnelSettings:
    enabled: bool = False
    bypass_china: bool = True
    proxy_lan: bool = False
    custom_routes: list[str] = field(default_factory=list)
    custom_rule_sets: list[str] = field(default_factory=list)


@dataclass
class DnsSettings:
    local_dns: str = "https://dns.quad9.net/dns-query"
    remote_dns: str = "https://1.1.1.1/dns-query"
    fakeip_enabled: bool = True
    fakeip_range: str = "198.18.0.0/15"
    use_system_dns: bool = False


@dataclass
class ProxySettings:
    selected_tag: str = ""
    auto_select: bool = True


@dataclass
class LogSettings:
    level: str = "info"
    timestamp: bool = True
    max_lines: int = 500


@dataclass
class AppSettings:
    tun: TunSettings = field(default_factory=TunSettings)
    split_tunnel: SplitTunnelSettings = field(default_factory=SplitTunnelSettings)
    dns: DnsSettings = field(default_factory=DnsSettings)
    proxy: ProxySettings = field(default_factory=ProxySettings)
    log: LogSettings = field(default_factory=LogSettings)
    dark_theme: bool = True
    minimize_to_tray: bool = True
    start_minimized: bool = False
    auto_connect: bool = False
    auto_reconnect: bool = True
    advanced_open: bool = False
    language: str = "ru"


class SettingsManager:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.settings_file = data_dir / "settings.json"
        self.settings = AppSettings()
        data_dir.mkdir(parents=True, exist_ok=True)
        self._load()

    @log_call()
    def _load(self):
        if not self.settings_file.exists():
            logger.info("Settings file not found, creating defaults at %s", self.settings_file)
            self._save()
            return

        try:
            data = json.loads(self.settings_file.read_text(encoding="utf-8"))
            logger.debug("Settings loaded from %s: %d top-level keys", self.settings_file, len(data))
        except json.JSONDecodeError as e:
            logger.warning("Corrupt settings file: %s, resetting to defaults", e)
            self._save()
            return
        except OSError as e:
            logger.warning("Cannot read settings file: %s, using defaults", e)
            self._save()
            return

        if "tun" in data:
            self.settings.tun = TunSettings(**data["tun"])
            logger.debug("TUN settings: %s", data["tun"])
        if "split_tunnel" in data:
            self.settings.split_tunnel = SplitTunnelSettings(**data["split_tunnel"])
            logger.debug("Split tunnel settings: %s", data["split_tunnel"])
        if "dns" in data:
            self.settings.dns = DnsSettings(**data["dns"])
            logger.debug("DNS settings: %s", data["dns"])
        if "proxy" in data:
            self.settings.proxy = ProxySettings(**data["proxy"])
            logger.debug("Proxy settings selected=%s auto=%s",
                        self.settings.proxy.selected_tag, self.settings.proxy.auto_select)
        if "log" in data:
            self.settings.log = LogSettings(**data["log"])

        for key in ["dark_theme", "minimize_to_tray", "start_minimized", "auto_connect", "auto_reconnect", "advanced_open", "language"]:
            if key in data:
                setattr(self.settings, key, data[key])
                logger.debug("Setting %s = %s", key, data[key])

        logger.info("Settings loaded: TUN=%s, split=%s, auto_connect=%s",
                    self.settings.tun.enabled, self.settings.split_tunnel.enabled,
                    self.settings.auto_connect)

    @log_call()
    def _save(self):
        data = {
            "tun": asdict(self.settings.tun),
            "split_tunnel": asdict(self.settings.split_tunnel),
            "dns": asdict(self.settings.dns),
            "proxy": asdict(self.settings.proxy),
            "log": asdict(self.settings.log),
            "dark_theme": self.settings.dark_theme,
            "minimize_to_tray": self.settings.minimize_to_tray,
            "start_minimized": self.settings.start_minimized,
            "auto_connect": self.settings.auto_connect,
            "auto_reconnect": self.settings.auto_reconnect,
            "advanced_open": self.settings.advanced_open,
            "language": self.settings.language,
        }
        self.settings_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.debug("Settings saved to %s", self.settings_file)

    def save(self):
        self._save()
