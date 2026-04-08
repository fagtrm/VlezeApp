"""
Xray process manager for VlezeApp.

Starts, stops, and monitors the xray-core subprocess, including
non-blocking log capture via a background thread.
"""

from __future__ import annotations

import os
import signal
import subprocess
import threading
from datetime import datetime
from pathlib import Path

from app.i18n import _

# Максимальный размер лог-файла перед ротацией (5 МБ)
_MAX_LOG_FILE_SIZE = 5 * 1024 * 1024


class XrayManager:
    """Manages the xray-core subprocess lifecycle.

    Attributes:
        process: The running subprocess, or None.
        is_running: Whether xray is currently considered running.
        log_lines: Rolling buffer of log output lines.
        log_file: Path to the persistent log file.
        max_log_lines: Maximum number of lines to keep in memory.
    """

    def __init__(
        self,
        log_file: Path | None = None,
        max_log_lines: int = 500,
        enable_logging: bool = True,
    ) -> None:
        self.process: subprocess.Popen[str] | None = None
        self.is_running: bool = False
        self.log_lines: list[str] = []
        self.max_log_lines: int = max_log_lines
        self.enable_logging: bool = enable_logging
        self.log_file: Path = log_file or Path.home() / ".config" / "VlezeApp" / "xray.log"
        self._log_thread: threading.Thread | None = None
        self._stop_thread: bool = False

        # Создаём директорию для лог-файла если нужно
        if self.enable_logging:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _rotate_log_file(self) -> None:
        """Ротировать лог-файл если он превысил размер."""
        if not self.log_file.exists():
            return
        try:
            size = os.path.getsize(self.log_file)
            if size > _MAX_LOG_FILE_SIZE:
                old_log = self.log_file.with_suffix(".log.1")
                if old_log.exists():
                    old_log.unlink()
                self.log_file.rename(old_log)
        except OSError:
            pass

    def _append_to_log_file(self, line: str) -> None:
        """Добавить строку в лог-файл с ротацией."""
        if not self.enable_logging:
            return
        self._rotate_log_file()
        try:
            with open(self.log_file, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError:
            pass

    def _load_recent_logs(self, count: int) -> list[str]:
        """Загрузить последние N строк из лог-файла."""
        if not self.log_file.exists():
            return []
        try:
            with open(self.log_file, "r", encoding="utf-8") as fh:
                lines = fh.readlines()
            # Берём последние count строк, убираем пустые
            stripped = [l.rstrip("\n") for l in lines if l.strip()]
            return stripped[-count:] if len(stripped) > count else stripped
        except OSError:
            return []

    def _log_reader_thread(self) -> None:
        """Background thread that reads stdout from the xray process."""
        try:
            while not self._stop_thread and self.process and self.process.stdout:
                line = self.process.stdout.readline()
                if line:
                    line = line.strip()
                    formatted = f"[{self._now()}] {line}"
                    self.log_lines.append(formatted)
                    if len(self.log_lines) > self.max_log_lines:
                        self.log_lines = self.log_lines[-self.max_log_lines:]
                    # Пишем в файл
                    self._append_to_log_file(formatted)
                else:
                    break
        except (ValueError, IOError):
            pass
        finally:
            if self.process:
                code = self.process.poll()
                if code is not None:
                    self.is_running = False
                    msg = f"[{self._now()}] {_('xray завершился с кодом')} {code}"
                    self.log_lines.append(msg)
                    self._append_to_log_file(msg)
                    self.process = None

    @staticmethod
    def _now() -> str:
        """Return the current time as HH:MM:SS."""
        return datetime.now().strftime("%H:%M:%S")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self, config_path: Path) -> tuple[bool, str]:
        """Start xray with the given configuration file.

        Args:
            config_path: Path to the xray JSON config file.

        Returns:
            A tuple of (success: bool, message: str).
        """
        if self.is_running:
            self.stop()

        try:
            self.process = subprocess.Popen(
                ["/usr/bin/xray", "-config", str(config_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )
            self.is_running = True
            self._stop_thread = False
            start_msg = f"[{self._now()}] {_('xray запущен с PID')} {self.process.pid}"
            self.log_lines = [start_msg]
            self._append_to_log_file(start_msg)

            self._log_thread = threading.Thread(
                target=self._log_reader_thread, daemon=True
            )
            self._log_thread.start()

            return True, _("xray запущен")

        except FileNotFoundError:
            msg = _("xray не найден в /usr/bin/xray")
            formatted = f"[{self._now()}] {msg}"
            self.log_lines.append(formatted)
            self._append_to_log_file(formatted)
            return False, msg

        except Exception as exc:
            msg = _("Ошибка запуска xray: {}").format(exc)
            formatted = f"[{self._now()}] {msg}"
            self.log_lines.append(formatted)
            self._append_to_log_file(formatted)
            return False, msg

    def stop(self) -> None:
        """Stop the running xray process gracefully, then forcefully if needed."""
        self._stop_thread = True
        if self.process and self.is_running:
            try:
                self.process.send_signal(signal.SIGTERM)
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
            except Exception:
                pass
            finally:
                msg = f"[{self._now()}] {_('xray остановлен')}"
                self.log_lines.append(msg)
                self._append_to_log_file(msg)
                self.is_running = False
                self.process = None

    def read_logs(self) -> list[str]:
        """Return the current rolling log buffer."""
        return self.log_lines

    def check_status(self) -> bool:
        """Poll the xray process and update internal state.

        Returns:
            True if xray is still running, False otherwise.
        """
        if self.process and self.is_running:
            poll = self.process.poll()
            if poll is not None:
                self.is_running = False
                msg = f"[{self._now()}] {_('xray завершился с кодом')} {poll}"
                self.log_lines.append(msg)
                self._append_to_log_file(msg)
                self.process = None
        return self.is_running
