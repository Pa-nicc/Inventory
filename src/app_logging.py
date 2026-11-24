"""Writes the audit log to %LOCALAPPDATA%\\EngInventory\\logs\\app.log."""
import logging

from src.db.db_manager import get_data_dir


def setup_logging() -> None:
    root = logging.getLogger()
    if any(isinstance(h, logging.FileHandler) for h in root.handlers):
        return                                       # already set up
    log_dir = get_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_dir / "app.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    root.addHandler(handler)
    root.setLevel(logging.INFO)