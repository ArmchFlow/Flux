import ctypes
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class AmneziaStatus(ctypes.Structure):
    _fields_ = [
        ("state", ctypes.c_ulong),
        ("exitCode", ctypes.c_ulong),
        ("serviceState", ctypes.c_ulong),
    ]


class AmneziaManager:
    def __init__(self, bin_dir: Path):
        dll_path = bin_dir / "AmneziaLib.dll"
        if not dll_path.exists():
            raise FileNotFoundError(f"AmneziaLib.dll not found: {dll_path}")
        self._lib = ctypes.CDLL(str(dll_path))
        self._lib.amnezia_connect.argtypes = [ctypes.c_wchar_p]
        self._lib.amnezia_connect.restype = ctypes.c_int
        self._lib.amnezia_disconnect.argtypes = []
        self._lib.amnezia_disconnect.restype = ctypes.c_int
        self._lib.amnezia_get_status.argtypes = [ctypes.POINTER(AmneziaStatus)]
        self._lib.amnezia_get_status.restype = ctypes.c_int
        logger.info("AmneziaLib loaded from %s", dll_path)

    def connect(self, config_path: str) -> tuple[bool, str]:
        code = self._lib.amnezia_connect(config_path)
        if code == 0:
            logger.info("Amnezia connected")
            return True, ""
        msgs = {1: "tunnel_service.exe or tunnel.dll not found",
                2: "failed to write config",
                3: "failed to install Windows service",
                4: "service started but crashed (check logs)"}
        msg = msgs.get(code, f"unknown error code {code}")
        logger.error("Amnezia connect failed: %s", msg)
        return False, msg

    def disconnect(self) -> bool:
        code = self._lib.amnezia_disconnect()
        ok = code == 0
        logger.info("Amnezia disconnect: %s", "ok" if ok else f"code {code}")
        return ok

    def get_status(self) -> AmneziaStatus | None:
        st = AmneziaStatus()
        code = self._lib.amnezia_get_status(ctypes.byref(st))
        if code == 0:
            return st
        return None

    @property
    def is_connected(self) -> bool:
        st = self.get_status()
        if st and st.serviceState == 4:
            return True
        return False
