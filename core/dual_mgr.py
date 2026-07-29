import os
import subprocess
import sys
import time
import logging
from pathlib import Path

from .config_builder import save_config_to_file, build_singbox_tun_config
from .amnezia_mgr import AmneziaManager

logger = logging.getLogger(__name__)


class DualManager:
    def __init__(self, sb_path: Path, xray_path: Path, config_dir: Path):
        self.sb_path = sb_path
        self.xray_path = xray_path
        self.config_dir = config_dir
        self.sb_config = config_dir / "sb_config.json"
        self.xray_config = config_dir / "xray_config.json"
        self._sb_proc: subprocess.Popen | None = None
        self._xray_proc: subprocess.Popen | None = None
        self._running = False
        self._amnezia_mgr: AmneziaManager | None = None
        self._amnezia_config: str = ""

    @property
    def is_running(self) -> bool:
        if self._amnezia_mgr and self._amnezia_mgr.is_connected:
            return True
        if self._sb_proc and self._sb_proc.poll() is None:
            return True
        if self._xray_proc and self._xray_proc.poll() is None:
            return True
        return False

    def _cleanup_tun(self):
        if sys.platform != "win32":
            return
        try:
            flags = subprocess.CREATE_NO_WINDOW
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "$adapters = Get-NetAdapter -ErrorAction SilentlyContinue "
                 "| Where-Object { $_.Name -like '*singbox*' -or "
                 "$_.Name -like '*myvpn*' -or $_.Name -like '*wintun*' "
                 "-or $_.Name -like '*MyAmnezia*' -or $_.Name -like '*Amnezia*' }; "
                 "if ($adapters) { "
                 "$adapters | ForEach-Object { "
                 "Write-Output \\\"DEL adapter $($_.Name)\\\"; "
                 "Get-NetIPAddress -InterfaceIndex $_.InterfaceIndex "
                 "-ErrorAction SilentlyContinue "
                 "| Remove-NetIPAddress -Confirm:$false -ErrorAction SilentlyContinue; "
                 "Remove-NetAdapter -Name $_.Name -Confirm:$false "
                 "-ErrorAction SilentlyContinue "
                 "} } else { Write-Output 'no stale adapters' }"],
                capture_output=True, timeout=15, text=True,
                creationflags=flags,
            )
            for line in r.stdout.splitlines():
                logger.info("TUN cleanup: %s", line.strip())
        except Exception as e:
            logger.debug("TUN cleanup: %s", e)

    def start(self,
        xray_cfg: dict, settings,
    ) -> tuple[bool, str]:
        if self.is_running:
            self.stop()

        self._cleanup_tun()

        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        env = os.environ.copy()
        env["ENABLE_DEPRECATED_LEGACY_DNS_SERVERS"] = "true"

        core_paths = [str(self.sb_path), str(self.xray_path)]

        sb_cfg = build_singbox_tun_config(settings, core_paths=core_paths)
        save_config_to_file(sb_cfg, self.sb_config)

        save_config_to_file(xray_cfg, self.xray_config)

        try:
            sb_log = open(self.config_dir / "singbox.log", "a", encoding="utf-8")
            self._sb_proc = subprocess.Popen(
                [str(self.sb_path), "run", "-c", str(self.sb_config),
                 "--disable-color"],
                stdout=sb_log, stderr=subprocess.STDOUT, env=env,
                creationflags=flags,
            )
            logger.info("sing-box PID: %s", self._sb_proc.pid)
            time.sleep(2.5)
            if self._sb_proc.poll() is not None:
                code = self._sb_proc.returncode
                self.stop()
                return False, f"sing-box exit {code}"

            xr_log = open(self.config_dir / "xray.log", "a", encoding="utf-8")
            self._xray_proc = subprocess.Popen(
                [str(self.xray_path), "run", "-config", str(self.xray_config)],
                stdout=xr_log, stderr=subprocess.STDOUT, creationflags=flags,
            )
            logger.info("Xray PID: %s", self._xray_proc.pid)
            time.sleep(1.0)
            if self._xray_proc.poll() is not None:
                code = self._xray_proc.returncode
                self.stop()
                return False, f"Xray failed (code {code})"

            self._running = True
            return True, "TUN"

        except Exception as e:
            logger.error("Start: %s", e, exc_info=True)
            self.stop()
            return False, str(e)

    def init_amnezia(self, bin_dir: Path):
        if self._amnezia_mgr is None:
            self._amnezia_mgr = AmneziaManager(bin_dir)

    def start_amnezia(self, config_path: str) -> tuple[bool, str]:
        logger.info("=== STARTING AMNEZIA WG ===")
        if self.is_running:
            self.stop()
        AmneziaManager.kill_stale_service()
        self._cleanup_tun()
        self._amnezia_config = config_path
        ok, msg = self._amnezia_mgr.connect(config_path)
        if ok:
            self._running = True
            return True, "AWG"
        return False, msg

    def stop(self):
        logger.info("Stopping...")
        if self._amnezia_mgr and self._amnezia_mgr.is_connected:
            self._amnezia_mgr.disconnect()
            AmneziaManager.kill_stale_service()
        for proc in [self._xray_proc, self._sb_proc]:
            if proc:
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=2)
                except Exception:
                    pass
        self._sb_proc = self._xray_proc = None
        self._running = False

        self._cleanup_tun()
        logger.info("Stopped")

    @staticmethod
    def tcp_ping(host: str, port: int, timeout: float = 2.0) -> int:
        import socket
        start = time.perf_counter()
        try:
            s = socket.create_connection((host, port), timeout=timeout)
            s.close()
            return int((time.perf_counter() - start) * 1000)
        except Exception:
            return -1

    @staticmethod
    def tcp_ping_servers(servers, timeout: float = 2.0) -> dict:
        import concurrent.futures
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
            futures = {
                ex.submit(DualManager.tcp_ping, s.server, s.port, timeout): s.tag
                for s in servers
            }
            for f in concurrent.futures.as_completed(futures):
                tag = futures[f]
                try:
                    results[tag] = f.result()
                except Exception:
                    results[tag] = -1
        return results
