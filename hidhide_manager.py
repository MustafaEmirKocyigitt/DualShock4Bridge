"""
Dahili HidHide Yönetim Modülü (HidHide Manager)
==============================================
Nefarius HidHide sürücüsünü yönetir.
Fiziksel XInput (Xbox) kolunu oyunlardan tek tıkla gizleyerek
çift girdi (double input) ve Xbox tuş simgesi sorununu çözer.
"""

import os
import subprocess
import sys
from typing import List, Optional, Tuple


class HidHideManager:
    DEFAULT_CLI_PATHS = [
        r"C:\Program Files\Nefarius Software Solutions\HidHide\x64\HidHideCLI.exe",
        r"C:\Program Files\Nefarius Software Solutions\HidHide\HidHideCLI.exe",
    ]

    def __init__(self, cli_path: Optional[str] = None):
        self.cli_path = cli_path or self._find_cli_path()

    def _find_cli_path(self) -> Optional[str]:
        for path in self.DEFAULT_CLI_PATHS:
            if os.path.isfile(path):
                return path
        return None

    def is_installed(self) -> bool:
        """Sistemde HidHide kurulu mu kontrol eder."""
        return self.cli_path is not None and os.path.isfile(self.cli_path)

    def _run_cli(self, args: List[str], run_as_admin: bool = False) -> Tuple[int, str, str]:
        """HidHideCLI çalıştırır."""
        if not self.cli_path:
            return -1, "", "HidHideCLI.exe bulunamadı. Lütfen HidHide'ı kurun."

        cmd = [self.cli_path] + args

        if run_as_admin:
            # UAC ile yönetici olarak çalıştır
            args_str = " ".join([f'"{a}"' for a in args])
            ps_cmd = f"Start-Process -FilePath '{self.cli_path}' -ArgumentList '{args_str}' -Verb RunAs -WindowStyle Hidden -Wait"
            proc = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True)
            return proc.returncode, proc.stdout, proc.stderr
        else:
            proc = subprocess.run(cmd, capture_output=True, text=True)
            return proc.returncode, proc.stdout, proc.stderr

    def get_cloaking_status(self) -> Optional[bool]:
        """Gizleme (Cloaking) durumunu sorgular: True (Açık), False (Kapalı), None (Okunamadı)"""
        code, out, _ = self._run_cli(["--cloak-state"])
        if code == 0:
            if "Active" in out or "True" in out or "enabled" in out.lower():
                return True
            if "Inactive" in out or "False" in out or "disabled" in out.lower():
                return False
        return None

    def set_cloaking(self, enable: bool) -> bool:
        """Gizlemeyi açar veya kapatır (Yönetici yetkisiyle)."""
        arg = "--cloak-on" if enable else "--cloak-off"
        code, _, _ = self._run_cli([arg], run_as_admin=True)
        return code == 0

    def whitelist_application(self, app_path: str) -> bool:
        """Belirtilen uygulamanın gizlenmiş kolları görebilmesini sağlar (Whitelist ekler)."""
        if not os.path.exists(app_path):
            return False
        code, _, _ = self._run_cli(["--app-reg", app_path], run_as_admin=True)
        return code == 0

    def get_whitelist(self) -> List[str]:
        """Mevcut whitelist uygulamalarını listeler."""
        code, out, _ = self._run_cli(["--app-list"])
        if code == 0:
            lines = [line.strip() for line in out.strip().splitlines() if line.strip() and not line.startswith("---")]
            return lines
        return []
