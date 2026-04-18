import logging
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

logger = logging.getLogger(__name__)

DROP_DEFAULT = (
    "border: 1px dashed rgba(255, 110, 26, 0.30); border-radius: 6px; "
    "padding: 16px; color: #9A8A9E; background: rgba(255, 110, 26, 0.04); "
    "font-size: 11px; font-weight: 700; letter-spacing: 1.5px; font-family: 'Segoe UI';"
)

DROP_HOVER = (
    "border: 2px solid rgba(229, 20, 20, 0.70); border-radius: 6px; "
    "padding: 15px; color: #FFFFFF; background: rgba(229, 20, 20, 0.15); "
    "font-size: 11px; font-weight: 800; letter-spacing: 1.5px; font-family: 'Segoe UI';"
)


class ImportWidget(QWidget):
    """Drag-and-drop area for mod import."""

    file_dropped = Signal(Path)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(64)
        self.setMaximumHeight(96)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        self._label = QLabel(
            "<span style='color: #F3F6F4; font-size: 14px; font-weight: 700; "
            "letter-spacing: 0.8px;'>"
            "↓   SOLTE SEUS MODS AQUI  [ ZIP/ JSON / PAZ / PASTA ]<br></span>"
           # "<span style='color: #F3F6F4; font-size: 12px; font-weight: 700; "
           #"letter-spacing: 0.8px;'>"
            #"» PARA PACOTES ACIMA DE 1 GIGABYTE, EXTRAIA E SOLTE O DIRETÓRIO PARA VELOCIDADE MÁXIMA «</span><br>"
            "<span style='color: #F3F6F4; font-size: 14px; font-weight: 700; "
            "letter-spacing: 0.5px'>[ FORMATO COMPACTADO .RAR NÃO SUPORTADO ]</span>"
        )
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setWordWrap(True)
        self._label.setStyleSheet(DROP_DEFAULT)
        layout.addWidget(self._label)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._label.setStyleSheet(DROP_HOVER)

    def dragLeaveEvent(self, event) -> None:
        self._label.setStyleSheet(DROP_DEFAULT)

    def dropEvent(self, event) -> None:
        self._label.setStyleSheet(DROP_DEFAULT)
        urls = event.mimeData().urls()
        for url in urls:
            path = Path(url.toLocalFile())
            logger.info("File dropped for import: %s", path)
            self.file_dropped.emit(path)
