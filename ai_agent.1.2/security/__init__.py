# security paketi
"""
Komut yurutme guvenlik modeli (openclaw exec-approvals portu).

Kullanim:
    from security import ExecApprovals

    approvals = ExecApprovals(security="allowlist", ask="on-miss")
    if approvals.is_allowed(cmd):
        run(cmd)
    else:
        decision = approvals.evaluate(cmd)
        if decision["requires_approval"] and confirm_callback(cmd):
            run(approvals sanitize_env icin ...)
"""

from .exec_approvals import (
    ExecApprovals,
    DEFAULT_SAFE_BINS,
    DANGEROUS_HOST_ENV_VARS,
    DANGEROUS_HOST_ENV_PREFIXES,
    APPROVALS_PATH,
)

__all__ = [
    "ExecApprovals",
    "DEFAULT_SAFE_BINS",
    "DANGEROUS_HOST_ENV_VARS",
    "DANGEROUS_HOST_ENV_PREFIXES",
    "APPROVALS_PATH",
]
