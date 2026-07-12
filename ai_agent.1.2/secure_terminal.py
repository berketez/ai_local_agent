# secure_terminal.py

"""
Secure Terminal Module - shell komutlarını exec-approvals politikasıyla çalıştırır.

openclaw'un exec-approvals modeli (security/exec_approvals.py) ile entegre:
- deny / allowlist / full güvenlik modları
- safe-bins + kalıcı allowlist (allow-always)
- tehlikeli ortam değişkeni (DYLD_*/LD_*/NODE_OPTIONS/PYTHONPATH) temizliği

exec_approvals verilmezse eski string-blocklist davranışına düşer (geriye dönük uyumluluk).
"""

import os
import subprocess
import shlex
from typing import Dict, Any, Optional

TIMEOUT_SEC = 60
SHELL_OPERATORS = [">", "<", "|", "&&", "||", ";", "$(", "`", "&"]

# exec_approvals yoksa kullanılan eski (zayıf) blocklist — sadece fallback.
_LEGACY_DANGEROUS = [
    "rm -rf /", "mkfs", "dd if=", ":(){ :|:& };:", ":(){:|:&};:",
    "chmod -R 777 /", "curl | sh", "curl|sh", "wget | sh", "wget|sh",
    "curl | bash", "curl|bash", "wget | bash", "wget|bash",
]


def request_confirmation_basic(command: str) -> bool:
    response = input(f"PERMISSION REQUEST: Execute command \"{command}\"? (y/n): ")
    return response.lower() in ("y", "yes")


class SecureTerminalExecutor:
    """Shell komutlarını exec-approvals politikasıyla güvenli çalıştırır."""

    def __init__(self, confirmation_callback=request_confirmation_basic,
                 exec_approvals=None, auto_confirm: bool = False):
        self.confirmation_callback = confirmation_callback
        self.exec_approvals = exec_approvals
        self.auto_confirm = auto_confirm

    # ------------------------------------------------------------------ #
    def _approve(self, command: str) -> Dict[str, Any]:
        """
        Komutu politikaya göre değerlendir.
        Dönüş: {"run": bool, "error": str|None}
        """
        if self.auto_confirm:
            return {"run": True, "error": None}

        # --- exec-approvals modeli (tercih edilen) ---
        if self.exec_approvals is not None:
            ev = self.exec_approvals.evaluate(command)
            # Politika izin verdi ve ek onay gerekmiyorsa: doğrudan çalıştır.
            if ev.get("allowed") and not ev.get("requires_approval"):
                return {"run": True, "error": None}
            # Onay gerekiyorsa kullanıcıya sor.
            if ev.get("requires_approval") or not ev.get("allowed"):
                approved = self.confirmation_callback(command)
                if not approved:
                    return {"run": False, "error": "User denied permission."}
                # "allow-always": onaylanan komutun binary'sini kalıcı allowlist'e ekle.
                binary = ev.get("binary")
                if binary:
                    try:
                        self.exec_approvals.add_allowlist_entry(binary)
                    except Exception:
                        pass
                return {"run": True, "error": None}
            return {"run": True, "error": None}

        # --- Fallback: eski blocklist + basit onay ---
        if any(p in command for p in _LEGACY_DANGEROUS):
            return {"run": False, "error": "Command blocked due to potential security risk."}
        if not self.confirmation_callback(command):
            return {"run": False, "error": "User denied permission."}
        return {"run": True, "error": None}

    def _safe_env(self) -> Optional[Dict[str, str]]:
        """Tehlikeli env değişkenlerini temizlenmiş bir kopya döndürür."""
        if self.exec_approvals is None:
            return None  # subprocess mevcut env'i kullanır
        try:
            return self.exec_approvals.sanitize_env(dict(os.environ))
        except Exception:
            return None

    # ------------------------------------------------------------------ #
    def execute_command(self, command: str, require_confirmation: bool = True) -> Dict[str, Any]:
        if require_confirmation:
            decision = self._approve(command)
            if not decision["run"]:
                return {
                    "success": False,
                    "error": decision["error"],
                    "stdout": "",
                    "stderr": decision["error"],
                    "return_code": -1,
                }

        env = self._safe_env()

        try:
            needs_shell = any(op in command for op in SHELL_OPERATORS)
            if needs_shell:
                process = subprocess.run(
                    command, shell=True, capture_output=True, text=True,
                    check=False, timeout=TIMEOUT_SEC, env=env,
                )
            else:
                args = shlex.split(command)
                process = subprocess.run(
                    args, capture_output=True, text=True,
                    check=False, timeout=TIMEOUT_SEC, env=env,
                )
            return {
                "success": process.returncode == 0,
                "stdout": process.stdout.strip(),
                "stderr": process.stderr.strip(),
                "return_code": process.returncode,
            }
        except FileNotFoundError:
            first = shlex.split(command)[0] if command.strip() else command
            return {"success": False, "error": f"Command not found: {first}",
                    "stdout": "", "stderr": f"Command not found: {first}", "return_code": -1}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Command timed out after {TIMEOUT_SEC} seconds.",
                    "stdout": "", "stderr": "Timeout expired.", "return_code": -1}
        except Exception as e:
            return {"success": False, "error": f"Error executing command: {e}",
                    "stdout": "", "stderr": str(e), "return_code": -1}


if __name__ == "__main__":
    print("Testing SecureTerminalExecutor (auto_confirm)...")
    ex = SecureTerminalExecutor(auto_confirm=True)
    r = ex.execute_command("echo Hello World", require_confirmation=False)
    print(r)
