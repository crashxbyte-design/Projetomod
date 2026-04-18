from cdumm.gui.msg_box_br import _pergunta_br, _info_br, _warning_br, _critical_br
"""Test Mod dialog — read-only conflict analysis with export."""
import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QLabel,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
)
from cdumm.gui.premium_buttons import SolidCrimsonButton

from cdumm.engine.test_mod_checker import ModTestResult, generate_compatibility_report
logger = logging.getLogger(__name__)


class TestModDialog(QDialog):
    """Dialog showing Test Mod analysis results with export option."""

    def __init__(self, result: ModTestResult, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Teste de Compatibilidade: {result.mod_name}")
        self.setMinimumSize(600, 400)
        self._result = result

        layout = QVBoxLayout(self)

        # Summary
        if result.error:
            layout.addWidget(QLabel(f"Erro: {result.error}"))
        else:
            summary = (
                f"Arquivos modificados: {len(result.changed_files)}\n"
                f"Mods compatíveis: {len(result.compatible_mods)}\n"
                f"Conflitos: {len(result.conflicts)}"
            )
            layout.addWidget(QLabel(summary))

        # Report preview
        report_text = generate_compatibility_report(result)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(report_text)
        layout.addWidget(text_edit)

        # Buttons
        if not result.error:
            export_btn = SolidCrimsonButton("Exportar Relatório...")
            export_btn.clicked.connect(lambda: self._export(report_text))
            layout.addWidget(export_btn)

        close_btn = SolidCrimsonButton("Fechar")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _export(self, report_text: str) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar Relatório de Compatibilidade",
            f"{self._result.mod_name}_compatibilidade.md",
            "Markdown (*.md)",
        )
        if path:
            Path(path).write_text(report_text, encoding="utf-8")
            _info_br(self, "Exportado", f"Relatório salvo em {path}")
