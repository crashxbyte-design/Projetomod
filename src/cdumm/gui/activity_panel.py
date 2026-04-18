"""Activity Log panel — shows a persistent, color-coded history of all CDUMM actions."""

import logging
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser, QComboBox,
    QLineEdit, QPushButton, QLabel,
)
from cdumm.gui.premium_buttons import PremiumNeonButton

from cdumm.engine.activity_log import ActivityLog, CATEGORY_COLORS

logger = logging.getLogger(__name__)

# PT-BR display names for each category shown in the legend
CATEGORY_LABELS_PTBR = {
    "apply":    "Aplicar",
    "revert":   "Reverter",
    "import":   "Importar",
    "remove":   "Remover",
    "snapshot": "Backup",
    "verify":   "Verificar",
    "cleanup":  "Limpeza",
    "warning":  "Aviso",
    "error":    "Erro",
}


class ActivityPanel(QWidget):
    """Scrollable, color-coded activity log with session filtering and search."""

    def __init__(self, activity_log: ActivityLog, parent=None):
        super().__init__(parent)
        self._log = activity_log
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header
        header = QLabel("REGISTROS DE TELEMETRIA (LOGS)")
        header.setStyleSheet("font-family: 'Bahnschrift'; font-size: 16px; font-weight: bold; color: #FF6E1A; padding-left: 4px; letter-spacing: 1px;")
        layout.addWidget(header)
        layout.addSpacing(8)

        # Toolbar row: session filter + search
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        toolbar.addWidget(QLabel("Sessão:"))
        self._session_combo = QComboBox()
        self._session_combo.setMinimumWidth(200)
        self._session_combo.setStyleSheet("""
            QComboBox {
                background-color: rgba(14, 8, 12, 0.7);
                border: 1px solid #FF6E1A;
                border-radius: 4px;
                color: #F4F4FC;
                padding: 6px 12px;
                font-family: 'Segoe UI';
                font-size: 13px;
            }
            QComboBox::drop-down {
                border-left: 1px solid #FF6E1A;
                width: 30px;
            }
            QComboBox QAbstractItemView {
                background-color: #0E080C;
                color: #D6D6E0;
                selection-background-color: rgba(229, 20, 20, 0.4);
                selection-color: white;
                border: 1px solid #FF6E1A;
                outline: none;
            }
        """)
        self._session_combo.currentIndexChanged.connect(self._on_filter_changed)
        toolbar.addWidget(self._session_combo)

        toolbar.addSpacing(12)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Pesquisar nos logs (Ctrl+F)...")
        self._search_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(14, 8, 12, 0.7);
                border: 1px solid #1A0F12;
                border-radius: 4px;
                color: #F4F4FC;
                padding: 6px 12px;
                font-family: 'Segoe UI';
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #FF6E1A;
                background-color: rgba(229, 20, 20, 0.05);
            }
        """)
        self._search_input.returnPressed.connect(self._on_search)
        toolbar.addWidget(self._search_input)

        search_btn = PremiumNeonButton("🔍 Buscar")
        search_btn.setMinimumWidth(80)
        search_btn.clicked.connect(self._on_search)
        toolbar.addWidget(search_btn)

        clear_btn = PremiumNeonButton("✕ Limpar")
        clear_btn.setMinimumWidth(80)
        clear_btn.clicked.connect(self._on_clear_search)
        toolbar.addWidget(clear_btn)

        toolbar.addSpacing(12)

        export_btn = PremiumNeonButton("💾 Exportar Log")
        export_btn.setMinimumWidth(120)
        export_btn.clicked.connect(self._on_export)
        toolbar.addWidget(export_btn)

        toolbar.addSpacing(4)

        delete_btn = PremiumNeonButton("🗑️ Apagar Histórico")
        delete_btn.setMinimumWidth(140)
        delete_btn.clicked.connect(self._on_delete_history)
        toolbar.addWidget(delete_btn)

        layout.addLayout(toolbar)

        # Legend — uses PT-BR labels
        legend = QHBoxLayout()
        legend.setSpacing(12)
        for cat, color in CATEGORY_COLORS.items():
            label = CATEGORY_LABELS_PTBR.get(cat, cat.capitalize())
            dot = QLabel(f'<span style="color:{color};">●</span> {label}')
            dot.setStyleSheet("font-size: 11px; color: #565668;")
            legend.addWidget(dot)
        legend.addStretch()
        layout.addLayout(legend)

        # Log browser
        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(False)
        self._browser.setStyleSheet("""
            QTextBrowser {
                background-color: rgba(10, 6, 8, 0.65);
                border: 1px solid #180D10;
                border-radius: 6px;
                padding: 12px;
                font-family: 'Consolas', 'Cascadia Mono', monospace;
                font-size: 12px;
                color: #A09BA0;
            }
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 10px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 110, 26, 0.3);
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 110, 26, 0.65);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)
        layout.addWidget(self._browser)

    def refresh(self):
        """Reload session list and show latest session."""
        self._session_combo.blockSignals(True)
        self._session_combo.clear()
        self._session_combo.addItem("Todas as Sessões", None)

        sessions = self._log.get_sessions(limit=30)
        for s in sessions:
            label = f"Sessão {s['id']} — {s['started_at']} (v{s['version']}, {s['count']} entradas)"
            self._session_combo.addItem(label, s["id"])

        # Select latest session by default
        if len(sessions) > 0:
            self._session_combo.setCurrentIndex(1)
        self._session_combo.blockSignals(False)
        self._on_filter_changed()

    def _on_filter_changed(self):
        session_id = self._session_combo.currentData()
        entries = self._log.get_entries(session_id=session_id)
        self._render_entries(entries)

    def _on_search(self):
        query = self._search_input.text().strip()
        if not query:
            self._on_filter_changed()
            return
        entries = self._log.search(query)
        self._render_entries(entries)

    def _on_clear_search(self):
        self._search_input.clear()
        self._on_filter_changed()

    def _on_delete_history(self):
        """Apaga todo o histórico de atividades após confirmação do utilizador."""
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "Apagar Histórico",
            "Tem certeza que deseja apagar todo o histórico de atividades?\n\n"
            "Esta ação não pode ser desfeita.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        count = self._log.clear_all()
        self.refresh()
        logger.info("Histórico apagado pelo utilizador: %d entradas removidas", count)

    def _on_export(self):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar Log de Atividades", "cdumm_atividades.txt",
            "Arquivos de Texto (*.txt);;Todos os Arquivos (*)")
        if not path:
            return
        entries = self._log.get_entries()
        with open(path, "w", encoding="utf-8") as f:
            for e in entries:
                detail = f" — {e['detail']}" if e.get('detail') else ""
                cat_label = CATEGORY_LABELS_PTBR.get(e['category'], e['category'].upper())
                f.write(f"[{e['timestamp']}] [{cat_label}] {e['message']}{detail}\n")

    def _render_entries(self, entries: list[dict]):
        html_parts = ['<table cellspacing="0" cellpadding="2" style="width:100%;">']

        if not entries:
            html_parts.append(
                '<tr><td style="color:#788090; padding:20px; text-align:center;">'
                'Nenhum registro encontrado</td></tr>')
        else:
            for entry in entries:
                cat = entry["category"]
                color = CATEGORY_COLORS.get(cat, "#788090")
                cat_label = CATEGORY_LABELS_PTBR.get(cat, cat.upper())
                ts = entry["timestamp"]
                msg = entry["message"]
                detail = entry.get("detail") or ""

                html_parts.append(
                    f'<tr>'
                    f'<td style="color:#4C566A; white-space:nowrap; padding-right:8px; '
                    f'vertical-align:top;">{ts}</td>'
                    f'<td style="color:{color}; font-weight:bold; white-space:nowrap; '
                    f'padding-right:8px; vertical-align:top;">[{cat_label}]</td>'
                    f'<td style="color:#D8DEE9;">{msg}'
                )
                if detail:
                    html_parts.append(
                        f'<br><span style="color:#788090; font-size:11px;">{detail}</span>'
                    )
                html_parts.append('</td></tr>')

        html_parts.append('</table>')
        self._browser.setHtml("\n".join(html_parts))
