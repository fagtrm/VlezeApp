"""
Загрузка файлов из интернета и чтение локальных файлов.

Использование:
    from app.services.file_downloader import FileDownloader

    content = FileDownloader.download("https://example.com/config.txt")
    local   = FileDownloader.read_file("/path/to/local/file.txt")
"""
from __future__ import annotations

import logging
import urllib.request

from app.i18n import _

logger = logging.getLogger(__name__)


class FileDownloader:
    """Загрузка файлов из интернета и чтение локальных файлов."""

    @staticmethod
    def download(url: str) -> str:
        """
        Скачивает файл по URL и возвращает его содержимое.

        Args:
            url: URL файла для загрузки.

        Returns:
            Содержимое файла в виде строки, или пустая строка при ошибке.
        """
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.read().decode("utf-8", errors="ignore")
        except urllib.error.URLError as exc:
            logger.error(_("Ошибка загрузки файла: %s"), exc)
            return ""
        except Exception as exc:
            logger.error(_("Неизвестная ошибка при загрузке: %s"), exc)
            return ""

    @staticmethod
    def read_file(path: str) -> str:
        """
        Читает содержимое локального файла.

        Args:
            path: Путь к файлу на локальной файловой системе.

        Returns:
            Содержимое файла в виде строки, или пустая строка при ошибке.
        """
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except FileNotFoundError:
            logger.error(_("Файл не найден: %s"), path)
            return ""
        except PermissionError:
            logger.error(_("Нет прав на чтение файла: %s"), path)
            return ""
        except Exception as exc:
            logger.error(_("Ошибка чтения файла: %s"), exc)
            return ""
