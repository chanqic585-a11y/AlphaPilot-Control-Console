"""Open the fixed OKX Demo launcher from the local console only."""

from __future__ import annotations

import ipaddress
import subprocess
import threading
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCHER_SCRIPT = REPO_ROOT / "scripts" / "start_okx_demo_console.ps1"


def _is_loopback_host(value: str) -> bool:
    try:
        return ipaddress.ip_address(value.split("%", 1)[0]).is_loopback
    except ValueError:
        return False


class LocalDemoLauncher:
    """Launch one visible, fixed PowerShell process without browser credentials."""

    def __init__(
        self,
        *,
        repo_root: Path = REPO_ROOT,
        popen_factory: Callable[..., Any] = subprocess.Popen,
    ) -> None:
        self._repo_root = Path(repo_root).resolve()
        self._script_path = self._repo_root / "scripts" / "start_okx_demo_console.ps1"
        self._popen_factory = popen_factory
        self._process: Any | None = None
        self._lock = threading.Lock()

    def open(
        self,
        client_host: str,
        *,
        current_pid: int,
        port: int,
        mobile: bool = False,
    ) -> dict[str, object]:
        if not _is_loopback_host(str(client_host or "")):
            return {
                "ok": False,
                "error": "local_host_required",
                "message": "OKX Demo 启动器只能从运行控制台的本机打开。",
            }
        if current_pid <= 0 or not 1 <= port <= 65535:
            return {
                "ok": False,
                "error": "invalid_launcher_context",
                "message": "本机启动上下文无效。",
            }
        if not self._script_path.is_file():
            return {
                "ok": False,
                "error": "launcher_script_missing",
                "message": "找不到仓库内固定的 OKX Demo 启动脚本。",
            }

        with self._lock:
            if self._process is not None and self._process.poll() is None:
                return {
                    "ok": False,
                    "error": "launcher_already_open",
                    "message": "OKX Demo 启动器已经打开，请在现有 PowerShell 窗口继续。",
                }

            command = [
                "powershell.exe",
                "-NoExit",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(self._script_path),
                "-HostName",
                "127.0.0.1",
                "-Port",
                str(port),
                "-EnableOrder",
                "-EnableAutomation",
                "-ReplaceExistingConsole",
                "-ExpectedConsoleProcessId",
                str(current_pid),
            ]
            if mobile:
                command.append("-Mobile")
            try:
                self._process = self._popen_factory(
                    command,
                    cwd=str(self._repo_root),
                    creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
                    close_fds=True,
                )
            except OSError:
                self._process = None
                return {
                    "ok": False,
                    "error": "launcher_start_failed",
                    "message": "无法打开本机 PowerShell 启动器。",
                }

        return {
            "ok": True,
            "status": "launcher_opened",
            "message": "启动器已打开，请在 PowerShell 窗口输入三项 Demo 凭据。",
            "credentialPolicy": "process_only",
        }


LOCAL_DEMO_LAUNCHER = LocalDemoLauncher()
