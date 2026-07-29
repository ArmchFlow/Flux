import sys
import os
import logging
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon

from core.log_utils import setup_logging
from core.crypto import get_or_create_vault
from core.subscription import SubscriptionManager
from core.settings_manager import SettingsManager
from core.dual_mgr import DualManager
from core.translations import set_language
from ui.main_window import MainWindow


def get_data_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path.home() / ".config"
    return base / "my_vpn"


def find_binary(name: str) -> Path:
    try:
        base = Path(sys._MEIPASS)
    except AttributeError:
        base = Path(__file__).parent
    bundled = base / "bin" / name
    if bundled.exists():
        return bundled
    import shutil
    system_bin = shutil.which(name)
    return Path(system_bin) if system_bin else bundled


def find_icon(name: str) -> str:
    try:
        base = Path(sys._MEIPASS)
    except AttributeError:
        base = Path(__file__).parent
    for path in [base / "bin" / name, base / name, base / "Flux mini.png"]:
        p = path.resolve()
        if p.exists():
            return str(p)
    return ""


def main():
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.kernel32.SetConsoleCP(65001)
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)

    data_dir = get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)

    setup_logging(data_dir, level=logging.DEBUG)
    logger = logging.getLogger("main")

    def _crash_handler(exc_type, exc_val, exc_tb):
        logger.critical("UNHANDLED CRASH: %s: %s", exc_type.__name__, exc_val, exc_info=(exc_type, exc_val, exc_tb))
        from core.log_utils import get_signal_handler
        handler = get_signal_handler()
        if handler:
            crash_log = data_dir / "crash.log"
            crash_log.write_text("\n".join(handler.buffer), encoding="utf-8")
    import sys as _sys
    _sys.excepthook = _crash_handler

    logger.info("=" * 60)
    logger.info("  MyVPN STARTING  PID=%s", os.getpid())
    logger.info("=" * 60)

    app = QApplication(sys.argv)
    app.setApplicationName("Flux")
    app.setOrganizationName("Flux")
    app.setQuitOnLastWindowClosed(False)

    icon_path = find_icon("flux.ico")
    if icon_path:
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)

    vault = get_or_create_vault()
    settings_mgr = SettingsManager(data_dir)
    set_language(settings_mgr.settings.language)
    sub_manager = SubscriptionManager(data_dir, vault)

    sb_path = find_binary("sing-box.exe")
    xr_path = find_binary("xray.exe")

    missing = []
    for name, path in [("sing-box", sb_path), ("xray", xr_path)]:
        if not path.exists():
            missing.append(name)
    if missing:
        QMessageBox.warning(None, "Missing binaries",
                           "Not found: " + ", ".join(missing))

    dual_mgr = DualManager(sb_path, xr_path, data_dir)

    logger.info("Subs: %d, servers: %d", len(sub_manager.subscriptions), len(sub_manager.get_all_servers()))
    logger.info("sing-box: %s, xray: %s", sb_path.exists(), xr_path.exists())

    window = MainWindow(sub_manager, settings_mgr, dual_mgr, vault, data_dir)

    logger.info("Entering Qt event loop...")
    exit_code = app.exec()
    dual_mgr.stop()
    logger.info("MyVPN stopped")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
