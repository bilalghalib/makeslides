"""
Shared helpers: logging, retries, subprocess, simple upload wrapper.

Usage:
    from makeslides.utils import log, retry, run, litterbox_upload
"""

import json
import logging
import os
import subprocess
import sys
import time
from functools import wraps
from pathlib import Path
from typing import Callable, TypeVar

T = TypeVar("T")

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
LOGLEVEL = os.getenv("MAKESLIDES_LOGLEVEL", "INFO").upper()

logging.basicConfig(
    level=LOGLEVEL,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("makeslides")


# --------------------------------------------------------------------------- #
# Retry decorator with exponential backoff
# --------------------------------------------------------------------------- #
def retry(
    attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    allowed: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry a function up to *attempts* times on *allowed* exceptions."""

    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @wraps(fn)
        def wrapper(*args, **kwargs) -> T:
            _delay = delay
            for i in range(attempts):
                try:
                    return fn(*args, **kwargs)
                except allowed as exc:
                    if i == attempts - 1:
                        log.error("All retries failed for %s: %s", fn.__name__, exc)
                        raise
                    log.warning(
                        "%s failed (%s). Retry %d/%d in %.1fs…",
                        fn.__name__,
                        exc,
                        i + 1,
                        attempts - 1,
                        _delay,
                    )
                    time.sleep(_delay)
                    _delay *= backoff

        return wrapper

    return decorator


# --------------------------------------------------------------------------- #
# Sub-process runner
# --------------------------------------------------------------------------- #
def run(cmd: list[str] | str, check: bool = True, capture: bool = True) -> str:
    """Run *cmd* and return stdout (str)."""
    if isinstance(cmd, str):
        cmd = cmd.split()
    log.debug("Running: %s", " ".join(cmd))
    res = subprocess.run(
        cmd,
        check=check,
        capture_output=capture,
        text=True,
    )
    if capture:
        return res.stdout.strip()
    return ""


# --------------------------------------------------------------------------- #
# Quick litterbox uploader (used by diagrams.renderer + assets.manager)
# --------------------------------------------------------------------------- #
@retry()
def litterbox_upload(path: str | Path, expiry: str = "24h") -> str:
    import requests

    path = Path(path)
    with path.open("rb") as fh:
        resp = requests.post(
            "https://litterbox.catbox.moe/resources/internals/api.php",
            data={"reqtype": "fileupload", "time": expiry},
            files={"fileToUpload": fh},
            timeout=20,
        )
    resp.raise_for_status()
    url = resp.text.strip()
    if not url.startswith("https://litter.catbox.moe"):
        raise ValueError(f"Unexpected response: {url}")
    log.info("Uploaded %s ➜ %s", path.name, url)
    return url
y
