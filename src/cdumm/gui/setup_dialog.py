import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)
from cdumm.gui.premium_buttons import PremiumNeonButton

from cdumm.storage.game_finder import find_game_directories, validate_game_directory

logger = logging.getLogger(__name__)


class SetupDialog(QDialog):
    """First-run dialog for selecting the Crimson Desert game directory."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configuração Inicial do Crimson Desert")
        self.setMinimumWidth(500)
        self.setStyleSheet("""
            QDialog { background-color: #0E080C; border: 1px solid #FF6E1A; }
            QLabel { color: #D6D6E0; font-family: 'Segoe UI'; font-size: 13px; font-weight: 500; }
            QLineEdit { background: rgba(14, 8, 12, 0.8); border: 1px solid #26181A; border-radius: 4px; color: #F4F4FC; padding: 6px; font-size: 13px; }
            QLineEdit:focus { border: 1px solid #FF6E1A; }
        """)
        self._selected_path: Path | None = None

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Não detectei automaticamente a pasta de instalação...\nSelecione manualmente a pasta onde Crimson Desert está instalado no seu PC:"))

        path_row = QHBoxLayout()
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("C:/SteamLibrary/steamapps/common/Crimson Desert...")
        self._path_edit.textChanged.connect(self._on_path_changed)
        path_row.addWidget(self._path_edit)

        browse_btn = PremiumNeonButton("Navegar...")
        browse_btn.clicked.connect(self._on_browse)
        path_row.addWidget(browse_btn)
        layout.addLayout(path_row)

        self._status_label = QLabel("")
        layout.addWidget(self._status_label)

        btn_row = QHBoxLayout()
        self._ok_btn = PremiumNeonButton("Confirmar Instalação")
        self._ok_btn.setEnabled(False)
        self._ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(self._ok_btn)

        cancel_btn = PremiumNeonButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        # Try auto-detection
        self._try_auto_detect()

    def _try_auto_detect(self) -> None:
        candidates = find_game_directories()
        if candidates:
            self._path_edit.setText(str(candidates[0]))
            self._status_label.setText(f"Aguarde, sistema achou aqui: {candidates[0]}")
            logger.info("Auto-detected game directory: %s", candidates[0])

    def _on_browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Crimson Desert Folder")
        if folder:
            self._path_edit.setText(folder)

    def _on_path_changed(self, text: str) -> None:
        path = Path(text)
        if validate_game_directory(path):
            self._selected_path = path
            self._ok_btn.setEnabled(True)
            self._status_label.setText("Válido! Configuração Tática Inicializada.")
            self._status_label.setStyleSheet("color: #FF6E1A; font-weight: bold;")
        else:
            self._selected_path = None
            self._ok_btn.setEnabled(False)
            if text:
                self._status_label.setText("[X] Binários não encontrados... Esta não é a pasta base do jogo.")
                self._status_label.setStyleSheet("color: #E51414; font-weight: bold;")
            else:
                self._status_label.setText("")

    @property
    def game_directory(self) -> Path | None:
        return self._selected_path
