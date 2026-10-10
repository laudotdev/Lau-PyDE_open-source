from pathlib import Path

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon

_ICON_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons"
ICON_SIZE = QSize(14, 14)

def panel_icon(name: str) -> QIcon:
    return QIcon(str(_ICON_DIR / f"{name}.svg"))
