"""Non-destructive GitHub Releases update checking for Lau-PyDE."""

from dataclasses import dataclass
import json
import re
import sys
from typing import Callable, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PySide6.QtCore import QObject, QThread, Signal

REPOSITORY = "laudotdev/Lau-PyDE_open-source"
RELEASES_URL = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
RELEASE_PAGE = f"https://github.com/{REPOSITORY}/releases/latest"
VERSION_PATTERN = re.compile(r"^(?:Lau-PyDE_)?v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:[-+].*)?$", re.IGNORECASE)


class UpdateCheckError(Exception):
    """A safe, user-facing update-check failure."""


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    name: str
    notes: str
    page_url: str
    assets: tuple[tuple[str, str], ...]


def _version(value: object) -> Optional[tuple[int, int, int]]:
    if not isinstance(value, str):
        return None
    match = VERSION_PATTERN.fullmatch(value.strip())
    if not match:
        return None
    return tuple(int(part or 0) for part in match.groups())


def compare_versions(left: object, right: object) -> Optional[int]:
    """Compare versions numerically; return None when either is unknown."""
    parsed_left, parsed_right = _version(left), _version(right)
    if parsed_left is None or parsed_right is None:
        return None
    return (parsed_left > parsed_right) - (parsed_left < parsed_right)


def parse_release(payload: object) -> ReleaseInfo:
    if not isinstance(payload, dict) or payload.get("draft") or payload.get("prerelease"):
        raise UpdateCheckError("The latest release is not a stable release.")
    version = _version(payload.get("tag_name"))
    page_url = payload.get("html_url")
    if version is None or not isinstance(page_url, str) or not page_url.startswith("https://"):
        raise UpdateCheckError("The release metadata is incomplete.")
    assets = []
    for asset in payload.get("assets", []):
        if isinstance(asset, dict) and isinstance(asset.get("name"), str) and isinstance(asset.get("browser_download_url"), str):
            assets.append((asset["name"], asset["browser_download_url"]))
    return ReleaseInfo(
        ".".join(map(str, version)),
        str(payload.get("name") or payload.get("tag_name")),
        str(payload.get("body") or "").strip(),
        page_url,
        tuple(assets),
    )


def select_download_url(release: ReleaseInfo, platform: str) -> str:
    platform = platform.lower()
    suffixes = (".exe",) if platform == "windows" else (".pkg.tar.zst",) if platform == "arch" else ()
    if suffixes:
        for name, url in release.assets:
            if name.lower().endswith(suffixes):
                return url
    return release.page_url


def fetch_latest_release(opener: Callable = urlopen, timeout: float = 8.0) -> ReleaseInfo:
    request = Request(RELEASES_URL, headers={"Accept": "application/vnd.github+json", "User-Agent": "Lau-PyDE-update-checker"})
    try:
        with opener(request, timeout=timeout) as response:
            return parse_release(json.loads(response.read().decode("utf-8")))
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, UnicodeError) as error:
        raise UpdateCheckError("Unable to check for updates.") from error


class UpdateWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def run(self) -> None:
        try:
            self.finished.emit(fetch_latest_release())
        except UpdateCheckError as error:
            self.failed.emit(str(error))


def current_platform() -> str:
    if sys.platform == "win32":
        return "windows"
    if sys.platform.startswith("linux"):
        try:
            import platform
            if platform.freedesktop_os_release().get("ID") == "arch":
                return "arch"
        except (AttributeError, OSError):
            pass
        return "linux"
    return "linux"
