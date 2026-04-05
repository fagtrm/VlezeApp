"""
Модули сервисов VlezeApp.
"""
from __future__ import annotations

from app.services.tray import TrayService
from app.services.file_downloader import FileDownloader

__all__ = [
    "TrayService",
    "FileDownloader",
]
