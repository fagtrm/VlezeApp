"""
Xray process manager for VlezeApp.

Starts, stops, and monitors the xray-core subprocess, including
non-blocking log capture via a background thread.
"""

from __future__ import annotations

import signal
import subprocess
import threading
from datetime import datetime
from pathlib import Path

from app.i18n import _


class XrayManager:
    """Manages the xray-core subprocess lifecycle.

    Attributes:
        process: The running subprocess, or None.
        is_running: Whether xray is currently considered running.
        log_lines: Rolling buffer of log output lines.
    """

    def __init__(self) -> None:
        self.process: subprocess.Popen[str] | None = None
        self.is_running: bool = False
        self.log_lines: list[str] = []
        self.max_log_lines: int = 500
        self._log_thread: threading.Thread | None = None
        self._stop_thread: bool = False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _log_reader_thread(self) -> None:
        """Background thread that reads stdout from the xray process."""
        try:
            while not self._stop_thread and self.process and self.process.stdout:
                line = self.process.stdout.readline()
                if line:
                    line = line.strip()
                    self.log_lines.append(f"[{self._now()}] {line}")
                    if len(self.log_lines) > self.max_log_lines:
                        self.log_lines = self.log_lines[-self.max_log_lines:]
                else:
                    break
        except (ValueError, IOError):
            pass
        finally:
            if self.process:
                code = self.process.poll()
                if code is not None:
                    self.is_running = False
                    self.log_lines.append(
                        f"[{self._now()}] {_('xray завершился с кодом')} {code}"
                    )
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
            self.log_lines = [
                f"[{self._now()}] {_('xray запущен с PID')} {self.process.pid}"
            ]

            self._log_thread = threading.Thread(
                target=self._log_reader_thread, daemon=True
            )
            self._log_thread.start()

            return True, _("xray запущен")

        except FileNotFoundError:
            msg = _("xray не найден в /usr/bin/xray")
            self.log_lines.append(f"[{self._now()}] {msg}")
            return False, msg

        except Exception as exc:
            msg = _("Ошибка запуска xray: {}").format(exc)
            self.log_lines.append(f"[{self._now()}] {msg}")
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
                self.log_lines.append(f"[{self._now()}] {_('xray остановлен')}")
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
                self.log_lines.append(
                    f"[{self._now()}] {_('xray завершился с кодом')} {poll}"
                )
                self.process = None
        return self.is_running
