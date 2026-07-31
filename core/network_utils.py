import subprocess
import sys
from typing import Optional


def get_physical_gateway() -> str:
    """Get the physical network gateway IP address for anti-lockout route."""
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-NetRoute -DestinationPrefix '0.0.0.0/0' "
                "| Select-Object -First 1 -ExpandProperty NextHop"
            ],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return result.stdout.strip()
    except Exception:
        return ""