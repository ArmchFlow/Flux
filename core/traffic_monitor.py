import logging
import os
import subprocess
import threading
import time

logger = logging.getLogger(__name__)

_ADAPTER_PATTERN = (
    "*singbox*", "*myvpn*", "*wintun*", "*amnezia*", "*Amnezia*"
)


class TrafficMonitor:
    def __init__(self):
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self._speed_up = 0
        self._speed_down = 0
        self._total_up = 0
        self._total_down = 0
        self._session_start = 0.0
        self._first = True

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def start(self):
        with self._lock:
            if self._running:
                return
            self._running = True
            self._speed_up = 0
            self._speed_down = 0
            self._total_up = 0
            self._total_down = 0
            self._session_start = time.time()
            self._first = True
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
        logger.info("Traffic monitor started")

    def stop(self):
        with self._lock:
            self._running = False
        logger.info("Traffic monitor stopped")

    def _loop(self):
        if os.name != "nt":
            with self._lock:
                self._running = False
            return
        patterns = " -or ".join(
            "$_.Name -like '{}'".format(p) for p in _ADAPTER_PATTERN
        )
        ps = (
            "while ($true) { "
            "$t = Get-NetAdapter -ErrorAction SilentlyContinue "
            "| Where-Object { " + patterns + " }; "
            "$up=0; $down=0; "
            "foreach ($a in $t) { "
            "$s = Get-NetAdapterStatistics -Name $a.Name -ErrorAction SilentlyContinue; "
            "if ($s) { $down += $s.ReceivedBytes; $up += $s.SentBytes } }; "
            "Write-Output (\"$up $down\"); "
            "Start-Sleep -Seconds 1 }"
        )
        try:
            proc = subprocess.Popen(
                ["powershell", "-NoProfile", "-Command", ps],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, encoding="utf-8", errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except Exception as e:
            logger.debug("Traffic monitor start failed: %s", e)
            with self._lock:
                self._running = False
            return

        prev_up = prev_down = 0
        prev_time = 0.0
        first = True
        try:
            while True:
                line = proc.stdout.readline()
                if not line:
                    break
                parts = line.strip().split()
                if len(parts) != 2:
                    continue
                try:
                    up, down = int(parts[0]), int(parts[1])
                except ValueError:
                    continue
                now = time.monotonic()
                with self._lock:
                    if not self._running:
                        break
                    if not first and prev_time:
                        dt = now - prev_time
                        if dt > 0:
                            self._speed_up = int(max(0, up - prev_up) / dt)
                            self._speed_down = int(max(0, down - prev_down) / dt)
                            self._total_up += max(0, up - prev_up)
                            self._total_down += max(0, down - prev_down)
                    self._first = first
                    first = False
                prev_up, prev_down, prev_time = up, down, now
        finally:
            try:
                proc.terminate()
            except Exception:
                pass
            with self._lock:
                self._running = False
            logger.debug("Traffic monitor loop ended")

    def snapshot(self) -> tuple[int, int, int, int, int]:
        """Returns (up_bps, down_bps, total_up, total_down, session_secs)."""
        with self._lock:
            if not self._running or self._first:
                return 0, 0, self._total_up, self._total_down, 0
            secs = int(time.time() - self._session_start)
            return (
                self._speed_up, self._speed_down,
                self._total_up, self._total_down, secs,
            )
