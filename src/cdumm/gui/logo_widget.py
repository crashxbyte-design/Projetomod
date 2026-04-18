"""
gui/logo_widget.py
──────────────────────────────────────────────────────────────────
Standalone GemLogo widget — loads the application icon image.
──────────────────────────────────────────────────────────────────
"""

import sys
import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel


class GemLogo(QLabel):
    """
    Loads the custom application logo from cdumm.ico so that 
    changing the executable icon also updates the internal UI!
    """

    def __init__(self, size: int = 68, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # PyInstaller extracts to _MEIPASS in production;
        # in dev mode, the .ico lives at the project root (3 levels up from this file:
        #   src/cdumm/gui/logo_widget.py -> src/cdumm/gui -> src/cdumm -> src -> project root)
        if getattr(sys, 'frozen', False):
            base_path = Path(sys._MEIPASS)
        else:
            base_path = Path(__file__).resolve().parents[3]
        icon_path = base_path / "cdumm.ico"
        
        pixmap = QPixmap(str(icon_path))
        if not pixmap.isNull():
            self.setPixmap(pixmap.scaled(
                size, size, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            ))
