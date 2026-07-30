import sys
import os
import logging
import traceback
import functools
import inspect
import threading
from pathlib import Path
from collections import deque
from datetime import datetime


class SignalEmitter:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        from PyQt6.QtCore import QObject, pyqtSignal
        class _Emitter(QObject):
            log_line = pyqtSignal(str)
        self.emitter = _Emitter()

    @classmethod
    def get(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def emit(self, line: str):
        self.emitter.log_line.emit(line)


class SignalHandler(logging.Handler):
    def __init__(self, max_lines=2000):
        super().__init__()
        self.buffer = deque(maxlen=max_lines)
        self.emitter = SignalEmitter.get()

    def emit(self, record):
        msg = self.format(record)
        self.buffer.append(msg)
        self.emitter.emit(msg)


LOG_FORMAT = (
    "%(asctime)s.%(msecs)03d | %(levelname)-7s | "
    "%(name)s.%(funcName)s:%(lineno)d | "
    "%(message)s"
)
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

_log_initialized = False
_handler: SignalHandler | None = None


def setup_logging(data_dir: Path, level=logging.DEBUG):
    global _log_initialized, _handler

    data_dir.mkdir(parents=True, exist_ok=True)
    log_file = data_dir / "flux.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)

    file_handler = logging.FileHandler(log_file, encoding="utf-8", mode="a")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, TIME_FORMAT))
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, TIME_FORMAT))
    root_logger.addHandler(console_handler)

    _handler = SignalHandler(max_lines=5000)
    _handler.setLevel(logging.DEBUG)
    _handler.setFormatter(logging.Formatter(LOG_FORMAT, TIME_FORMAT))
    root_logger.addHandler(_handler)

    _log_initialized = True

    logging.getLogger(__name__).info(
        "Logging initialized: file=%s, level=%s",
        log_file, logging.getLevelName(level),
    )


def get_signal_handler() -> SignalHandler | None:
    return _handler


def log_call(logger=None):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            _log = logger or logging.getLogger(func.__module__)
            cls_name = ""
            if args and hasattr(args[0], "__class__"):
                cls_name = args[0].__class__.__name__ + "."

            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()

            arg_strs = []
            for p_name, p_val in bound.arguments.items():
                if p_name == "self":
                    continue
                if isinstance(p_val, str) and len(p_val) > 80:
                    arg_strs.append(f"{p_name}={p_val[:77]}...")
                elif isinstance(p_val, (list, dict)) and len(str(p_val)) > 100:
                    arg_strs.append(f"{p_name}=<{type(p_val).__name__}({len(p_val)})>")
                else:
                    arg_strs.append(f"{p_name}={p_val!r}")

            _log.debug("→ %s%s(%s)", cls_name, func.__name__, ", ".join(arg_strs))

            try:
                result = func(*args, **kwargs)
                _log.debug("← %s%s → %s", cls_name, func.__name__, _truncate(repr(result), 200))
                return result
            except Exception as e:
                _log.error(
                    "✗ %s%s raised %s: %s\n%s",
                    cls_name, func.__name__,
                    type(e).__name__, e,
                    "".join(traceback.format_tb(e.__traceback__)),
                )
                raise
        return wrapper
    return decorator


def _truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 3] + "..."


def log_exception(logger: logging.Logger, context: str = ""):
    logger.error(
        "Exception [%s]: %s\n%s",
        context,
        traceback.format_exc().replace("\n", " | "),
    )


def log_api_call(logger: logging.Logger, method: str, url: str, **kwargs):
    safe_url = url.replace("://", "://") if "password" not in url else url
    logger.debug("HTTP %s %s | kwargs=%s", method, safe_url, _truncate(repr(kwargs), 300))


def log_api_response(logger: logging.Logger, method: str, url: str, status: int, body=None):
    body_str = _truncate(repr(body), 300) if body else ""
    logger.debug("HTTP %s %s → %s | body=%s", method, url, status, body_str)


def log_config(logger: logging.Logger, config: dict, label: str = ""):
    import json
    try:
        pretty = json.dumps(config, ensure_ascii=False, indent=2)
    except Exception:
        pretty = repr(config)
    lines = pretty.split("\n")
    logger.debug("Config %s (%d lines):\n%s", label, len(lines), pretty)


def log_servers(logger: logging.Logger, servers: list, label: str = ""):
    logger.debug(
        "Servers %s: count=%d\n%s",
        label,
        len(servers),
        "\n".join(
            f"  [{i}] {s.tag} ({s.protocol}://{s.server}:{s.port})"
            for i, s in enumerate(servers)
        ) if servers else "  (empty)",
    )
