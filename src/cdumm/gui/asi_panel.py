from cdumm.gui.msg_box_br import _pergunta_br, _info_br, _warning_br, _critical_br
"""ASI plugin management panel widget."""
import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from cdumm.gui.premium_buttons import PremiumNeonButton

from cdumm.asi.asi_manager import AsiManager

logger = logging.getLogger(__name__)


class AsiPanel(QWidget):
    """Panel for viewing and managing ASI plugins."""

    def __init__(self, bin64_dir: Path, parent=None) -> None:
        super().__init__(parent)
        self._asi_mgr = AsiManager(bin64_dir)
        self._plugins = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 8)

        # Header Otimizado
        header = QHBoxLayout()
        title = QLabel("MODULOS CORE (ASI)")
        title.setStyleSheet("font-family: 'Bahnschrift'; font-size: 16px; font-weight: bold; color: #FF6E1A; padding-left: 8px; letter-spacing: 1px;")
        header.addWidget(title)
        self._loader_label = QLabel()
        header.addWidget(self._loader_label)
        header.addStretch()
        refresh_btn = PremiumNeonButton("Atualizar")
        refresh_btn.clicked.connect(self.refresh)
        header.addWidget(refresh_btn)
        layout.addLayout(header)

        # Table — 3 columns, no inline buttons
        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels(["PLUGIN/DLL", "STATUS DO MÓDULO", "CONFLITOS LOGICOS"])
        from PySide6.QtWidgets import QHeaderView
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setSortingEnabled(True)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)
        self._table.setShowGrid(False)
        self._table.setStyleSheet("""
            QTableWidget {
                background-color: rgba(14, 8, 12, 0.6);
                color: #D6D6E0;
                border: 1px solid #1A0F12;
                border-radius: 4px;
                outline: none;
            }
            QTableWidget::item {
                padding: 6px 12px;
                border-bottom: 1px solid #1A0F12;
            }
            QTableWidget::item:hover {
                background-color: rgba(229, 20, 20, 0.08);
            }
            QTableWidget::item:selected {
                background-color: rgba(229, 20, 20, 0.25);
                color: #FFFFFF;
                border-left: 2px solid #FF6E1A;
            }
            QHeaderView::section {
                background-color: #120A0D;
                color: #F4F4FC;
                border: none;
                border-bottom: 2px solid #E51414;
                padding: 10px;
                font-family: 'Bahnschrift', 'Segoe UI';
                font-size: 11px;
                font-weight: bold;
                letter-spacing: 0.5px;
            }
        """)
        layout.addWidget(self._table)

        # Hint
        hint = QLabel("Clique com botão direito num plugin para ver as ações")
        hint.setStyleSheet("color: #303240; font-size: 11px; padding: 4px 8px;")
        layout.addWidget(hint)

        self.refresh()

    def refresh(self) -> None:
        if self._asi_mgr.has_loader():
            self._loader_label.setText("[ ASI LOADER: ATIVO ]")
            self._loader_label.setStyleSheet("color: #FF6E1A; font-family: 'Bahnschrift'; font-weight: bold; letter-spacing: 1px;")
        else:
            # Try to auto-install bundled ASI loader
            self._install_bundled_loader()
            if self._asi_mgr.has_loader():
                self._loader_label.setText("[ ASI LOADER: ATIVO (AUTO-INJETADO) ]")
                self._loader_label.setStyleSheet("color: #FF6E1A; font-family: 'Bahnschrift'; font-weight: bold; letter-spacing: 1px;")
            else:
                self._loader_label.setText("[ ASI LOADER: FALHA/AUSENTE ]")
                self._loader_label.setStyleSheet("color: #E51414; font-family: 'Bahnschrift'; font-weight: bold; letter-spacing: 1px;")

        self._plugins = self._asi_mgr.scan()
        conflicts = self._asi_mgr.detect_conflicts(self._plugins)

        # Populate table

        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(self._plugins))

        for row, plugin in enumerate(self._plugins):
            # Name
            name_item = QTableWidgetItem(plugin.name)
            name_item.setData(Qt.ItemDataRole.UserRole, row)  # store index
            self._table.setItem(row, 0, name_item)

            # Status with color
            status = "Ativado" if plugin.enabled else "Desativado"
            status_item = QTableWidgetItem(status)
            if plugin.enabled:
                status_item.setForeground(QColor("#2ECC71"))
            else:
                status_item.setForeground(QColor("#565668"))
            self._table.setItem(row, 1, status_item)

            # Conflicts
            plugin_conflicts = [c for c in conflicts
                                if c.plugin_a == plugin.name or c.plugin_b == plugin.name]
            if plugin_conflicts:
                text = "; ".join(c.reason for c in plugin_conflicts)
                item = QTableWidgetItem(text)
                item.setForeground(QColor("#E53935"))
            else:
                item = QTableWidgetItem("Nenhum")
                item.setForeground(QColor("#565668"))
            self._table.setItem(row, 2, item)

        self._table.setSortingEnabled(True)
        self._table.resizeColumnsToContents()

    def _install_bundled_loader(self) -> None:
        """Install the bundled ASI loader (winmm.dll) to bin64."""
        import sys, shutil
        if getattr(sys, 'frozen', False):
            bundled = Path(sys._MEIPASS) / "asi_loader" / "winmm.dll"
        else:
            bundled = Path(__file__).resolve().parents[3] / "asi_loader" / "winmm.dll"
        if not bundled.exists():
            return
        dst = self._asi_mgr._bin64 / "winmm.dll"
        if dst.exists():
            return
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(bundled, dst)
            logger.info("Auto-installed bundled ASI loader: %s", dst)
        except Exception as e:
            logger.warning("Failed to install ASI loader: %s", e)

    def _get_plugin_at_row(self, row: int):
        item = self._table.item(row, 0)
        if item is None:
            return None
        idx = item.data(Qt.ItemDataRole.UserRole)
        if idx is not None and idx < len(self._plugins):
            return self._plugins[idx]
        return None

    def _show_context_menu(self, pos) -> None:
        index = self._table.indexAt(pos)
        if not index.isValid():
            return
        plugin = self._get_plugin_at_row(index.row())
        if not plugin:
            return

        menu = QMenu(self)
        menu.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(14, 8, 12, 0.85);
                border: 1px solid #FF6E1A;
                border-radius: 4px;
                padding: 4px 0px;
                color: #D6D6E0;
                font-family: 'Bahnschrift', 'Segoe UI';
                font-size: 13px;
                font-weight: 500;
                letter-spacing: 0.5px;
            }
            QMenu::item {
                padding: 6px 24px 6px 16px;
                border-left: 2px solid transparent;
            }
            QMenu::item:selected {
                background-color: rgba(229, 20, 20, 0.4);
                border-left: 2px solid #FF6E1A;
                color: #FFFFFF;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 110, 26, 0.2);
                margin: 4px 8px;
            }
        """)

        # Enable/Disable
        if plugin.enabled:
            toggle = QAction("Desativar", self)
        else:
            toggle = QAction("Ativar", self)
        toggle.triggered.connect(lambda: self._toggle_plugin(plugin))
        menu.addAction(toggle)

        # Config (if .ini exists)
        if plugin.ini_path:
            config = QAction("Editar Config", self)
            config.triggered.connect(lambda: self._asi_mgr.open_config(plugin))
            menu.addAction(config)

        menu.addSeparator()

        # Update
        update = QAction("Atualizar Plugin", self)
        update.triggered.connect(lambda: self._update_plugin(plugin))
        menu.addAction(update)

        # Uninstall
        uninstall = QAction("Desinstalar", self)
        uninstall.triggered.connect(lambda: self._uninstall_plugin(plugin))
        menu.addAction(uninstall)

        menu.exec(self._table.viewport().mapToGlobal(pos))

    def _toggle_plugin(self, plugin) -> None:
        if plugin.enabled:
            self._asi_mgr.disable(plugin)
        else:
            self._asi_mgr.enable(plugin)
        self.refresh()

    def _update_plugin(self, plugin) -> None:
        path_str = QFileDialog.getExistingDirectory(
            self, f"Atualizar {plugin.name} — Selecione a pasta com o novo .asi")
        if not path_str:
            return
        folder = Path(path_str)
        asi_files = list(folder.glob("*.asi"))
        if not asi_files:
            asi_files = list(folder.rglob("*.asi"))
        if not asi_files:
            _warning_br(self, "Nenhum ASI Encontrado", "Nenhum arquivo .asi encontrado nessa pasta.")
            return
        match = next((f for f in asi_files if plugin.name.lower() in f.stem.lower()), asi_files[0])
        updated = self._asi_mgr.update(plugin, match)
        if updated:
            _info_br(
                self, "Atualizado",
                f"Plugin {plugin.name} atualizado:\n" + "\n".join(f"  {f}" for f in updated))
            self.refresh()

    def _uninstall_plugin(self, plugin) -> None:
        reply = _pergunta_br(
            self, "Desinstalar Plugin ASI",
            f"Excluir {plugin.name} da pasta bin64?\n\n"
            f"Arquivos: {plugin.path.name}"
            f"{', ' + plugin.ini_path.name if plugin.ini_path else ''}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            deleted = self._asi_mgr.uninstall(plugin)
            if deleted:
                self.refresh()
