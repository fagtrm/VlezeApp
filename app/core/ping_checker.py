"""
Ping checker for VlezeApp.

Verifies VPN connectivity by making HTTP requests through the
SOCKS proxy provided by xray.
"""

from __future__ import annotations

import subprocess
import time

from app.i18n import _


class PingChecker:
    """Performs latency checks through the xray SOCKS proxy.

    Attributes:
        last_ping_ms: The last measured round-trip time in milliseconds.
        is_ping_in_progress: Whether a ping operation is currently running.
    """

    def __init__(self) -> None:
        self.last_ping_ms: int | None = None
        self.is_ping_in_progress: bool = False

    def ping_via_socks(
        self,
        target_host: str = "1.1.1.1",
        socks_port: int = 1080,
    ) -> tuple[bool, str]:
        """Ping a target host through the SOCKS5 proxy.

        Uses curl with --socks5 to route the request through the
        local xray proxy and measures total elapsed time.

        Args:
            target_host: The hostname or IP to reach through the proxy.
            socks_port: The local SOCKS5 proxy port (default 1080).

        Returns:
            A tuple of (success: bool, message: str) where the message
            contains the measured latency or an error description.
        """
        if self.is_ping_in_progress:
            return False, _("Пинг уже выполняется")

        self.is_ping_in_progress = True
        try:
            start = time.monotonic()

            result = subprocess.run(
                [
                    "curl", "-s", "-o", "/dev/null",
                    "--socks5", f"127.0.0.1:{socks_port}",
                    "--connect-timeout", "5",
                    "--max-time", "10",
                    f"http://{target_host}/",
                ],
                capture_output=True,
                text=True,
                timeout=12,
            )

            elapsed_ms = int((time.monotonic() - start) * 1000)

            if result.returncode == 0:
                self.last_ping_ms = elapsed_ms
                return True, f"{elapsed_ms} {_('мс')}"
            else:
                error_info = result.stderr.strip() if result.stderr else _("неизвестная ошибка")
                return False, f"{_('Ошибка')} ({elapsed_ms} {_('мс')}): {error_info[:80]}"

        except subprocess.TimeoutExpired:
            return False, _("Таймаут (>10 с)")
        except FileNotFoundError:
            return False, _("curl не найден")
        except Exception as exc:
            return False, f"{_('Ошибка')}: {str(exc)[:80]}"
        finally:
            self.is_ping_in_progress = False
