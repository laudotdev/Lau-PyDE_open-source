from pathlib import Path

from PySide6.QtCore import QFileInfo
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFileIconProvider


ICON_FILES = {
    ".py": "file-python.svg",
    ".html": "file-html.svg",
    ".htm": "file-html.svg",
    ".css": "file-css.svg",
    ".js": "file-js.svg",
    ".mjs": "file-js.svg",
    ".cjs": "file-js.svg",
    ".md": "file-md.svg",
    ".json": "file-json.svg",
    ".yaml": "file-yaml.svg",
    ".yml": "file-yaml.svg",
    ".toml": "file-toml.svg",
    ".c": "file-code.svg",
    ".h": "file-code.svg",
    ".cc": "file-code.svg",
    ".cpp": "file-code.svg",
    ".cxx": "file-code.svg",
    ".hpp": "file-code.svg",
    ".hh": "file-code.svg",
    ".java": "file-java.svg",
    ".go": "file-go.svg",
    ".rs": "file-rust.svg",
}

_ICON_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons"


class LauPydeFileIconProvider(QFileIconProvider):
    def icon_from_path(self, path: str) -> QIcon:
        return self.icon(QFileInfo(path))

    def icon(self, file_info):
        if isinstance(file_info, QFileInfo) and file_info.isFile():
            suffix = file_info.suffix().lower()
            icon_name = ICON_FILES.get(f".{suffix}") if suffix else None
            if icon_name:
                icon = QIcon(str(_ICON_DIR / icon_name))
                if not icon.isNull():
                    return icon
        return super().icon(file_info)


def file_icon(path: str) -> QIcon:
    return LauPydeFileIconProvider().icon(QFileInfo(path))