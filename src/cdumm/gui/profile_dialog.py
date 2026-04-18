from cdumm.gui.msg_box_br import _pergunta_br, _info_br, _warning_br, _critical_br, _input_text_br
"""Mod profile management dialog."""
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QVBoxLayout,
)
from cdumm.gui.premium_buttons import PremiumNeonButton

from cdumm.engine.profile_manager import ProfileManager
from cdumm.storage.database import Database
class ProfileDialog(QDialog):
    def __init__(self, db: Database, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("GERENCIADOR DE PERFIS ELITE BR")
        self.setMinimumSize(600, 450)
        self.setStyleSheet("""
            QDialog {
                background-color: #0E080C;
            }
            QLabel {
                font-family: 'Bahnschrift';
                font-size: 13px;
                color: #FF6E1A;
                font-weight: bold;
                letter-spacing: 0.5px;
            }
            QListWidget {
                background-color: rgba(14, 8, 12, 0.6);
                border: 1px solid #1A0F12;
                border-radius: 4px;
                color: #F4F4FC;
                padding: 4px;
                font-family: 'Segoe UI';
                font-size: 12px;
                outline: none;
            }
            QListWidget::item {
                padding: 6px;
                border-bottom: 1px solid #1A0F12;
            }
            QListWidget::item:selected {
                background-color: rgba(229, 20, 20, 0.25);
                border-left: 2px solid #FF6E1A;
            }
        """)
        self._db = db
        self._pm = ProfileManager(db)
        self._profile_loaded = False

        layout = QHBoxLayout(self)

        # Left: profile list
        left = QVBoxLayout()
        left.addWidget(QLabel("PERFIS MEMORIZADOS:"))
        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_selection_changed)
        left.addWidget(self._list)

        btn_row = QHBoxLayout()
        save_btn = PremiumNeonButton("Salvar")
        save_btn.setFixedHeight(28)
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)
        
        delete_btn = PremiumNeonButton("Deletar")
        delete_btn.setFixedHeight(28)
        delete_btn.clicked.connect(self._on_delete)
        btn_row.addWidget(delete_btn)
        
        rename_btn = PremiumNeonButton("Renomear")
        rename_btn.setFixedHeight(28)
        rename_btn.clicked.connect(self._on_rename)
        btn_row.addWidget(rename_btn)
        left.addLayout(btn_row)

        load_btn = PremiumNeonButton("▶ CARREGAR PERFIL SELECIONADO")
        load_btn.setFixedHeight(34)
        load_btn.clicked.connect(self._on_load)
        left.addWidget(load_btn)

        layout.addLayout(left, 2)

        # Right: preview
        right = QVBoxLayout()
        right.addWidget(QLabel("ESTRUTURA DE MÓDULOS (ATIVOS/INATIVOS):"))
        self._preview = QListWidget()
        right.addWidget(self._preview)
        layout.addLayout(right, 3)

        self._refresh()

    def _refresh(self) -> None:
        self._list.clear()
        for p in self._pm.list_profiles():
            item = QListWidgetItem(p["name"])
            item.setData(256, p["id"])  # Qt.UserRole
            self._list.addItem(item)

    def _on_selection_changed(self, row: int) -> None:
        self._preview.clear()
        item = self._list.item(row)
        if not item:
            return
        pid = item.data(256)
        for mod in self._pm.get_profile_mods(pid):
            status = "ON" if mod["enabled"] else "off"
            self._preview.addItem(f"[{status}] {mod['name']}")

    def _on_save(self) -> None:
        name, ok = _input_text_br(self, "Salvar Perfil Tático", "Insira o nome deste perfil:")
        if ok and name.strip():
            self._pm.save_profile(name.strip())
            self._refresh()

    def _on_load(self) -> None:
        item = self._list.currentItem()
        if not item:
            return
        pid = item.data(256)
        name = item.text()
        reply = _pergunta_br(
            self, "Carregar Perfil",
            f"Deseja carregar a estrutura do perfil '{name}'?\n\nIsso abortará o arranjo atual da sua lista de mods.",
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._pm.load_profile(pid)
            self._profile_loaded = True
            self.accept()

    def _on_delete(self) -> None:
        item = self._list.currentItem()
        if not item:
            return
        reply = _pergunta_br(
            self, "Deletar Perfil", f"Deletar o perfil '{item.text()}' definitivamente?")
        if reply == QMessageBox.StandardButton.Yes:
            self._pm.delete_profile(item.data(256))
            self._refresh()

    def _on_rename(self) -> None:
        item = self._list.currentItem()
        if not item:
            return
        name, ok = _input_text_br(self, "Renomear Perfil", "Novo designativo tático:", default=item.text())
        if ok and name.strip():
            self._pm.rename_profile(item.data(256), name.strip())
            self._refresh()

    @property
    def was_profile_loaded(self) -> bool:
        return self._profile_loaded
