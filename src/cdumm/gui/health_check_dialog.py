"""Health check results dialog — shows mod validation issues."""
import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QScrollArea,
    QTextEdit, QVBoxLayout, QWidget,
)
from cdumm.gui.premium_buttons import SolidCrimsonButton

from cdumm.engine.mod_health_check import HealthIssue, generate_bug_report

logger = logging.getLogger(__name__)

SEVERITY_COLORS = {
    "critical": "#FF4444",
    "warning": "#FFAA00",
    "info": "#4488FF",
}

SEVERITY_LABELS = {
    "critical": "CRÍTICO",
    "warning": "AVISO",
    "info": "INFO",
}


class HealthCheckDialog(QDialog):
    """Dialog showing mod health check results with bug report export."""

    def __init__(self, issues: list[HealthIssue], mod_name: str,
                 mod_files: dict, parent=None):
        super().__init__(parent)
        self._issues = issues
        self._mod_name = mod_name
        self._mod_files = mod_files
        self._user_choice = "cancel"  # "apply", "cancel"

        self.setWindowTitle(f"Check-up de Integridade do Mod: {mod_name}")
        self.setMinimumSize(700, 500)
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet("""
            QDialog { background: #0F0A0A; color: #E8E0D8; }
            QLabel  { color: #E8E0D8; }
            QScrollArea { background: transparent; border: none; }
            QScrollArea > QWidget > QWidget { background: transparent; }
            QPushButton { border-radius: 6px; padding: 8px 22px; font-weight: bold; font-size: 13px; }
            #tech_btn {
                color: #888888; font-size: 13px; font-weight: bold;
                background: transparent; border: none; text-align: left;
                margin-top: 12px; margin-bottom: 4px; padding: 0px;
            }
            #tech_btn:hover { color: #AAAAAA; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Summary
        critical = sum(1 for i in self._issues if i.severity == "critical")
        warnings = sum(1 for i in self._issues if i.severity == "warning")
        info = sum(1 for i in self._issues if i.severity == "info")

        if critical or warnings:
            summary = QLabel(
                "<span style='font-size: 15px;'><b>Encontramos alguns problemas e avisos neste mod.</b><br>"
                "Você ainda pode continuar clicando em <b style='color:#FF6E1A;'>Continuar e Aplicar</b>. O gerenciador vai corrigir automaticamente o que for possível.<br>"
                "<span style='color: #DDCCAA;'>Se o jogo fechar, travar ou o mod não funcionar como esperado, desative ou remova o mod e tente outra versão.</span></span>"
            )
        else:
            summary = QLabel(
                f"<b style='color:#44FF44'>Nenhum problema estrutural encontrado!</b>"
                f"{f' ({info} nota(s) informativa(s))' if info else ''}"
            )
        summary.setWordWrap(True)
        summary.setStyleSheet("color: #E8E0D8; margin-bottom: 6px; line-height: 1.4;")
        layout.addWidget(summary)

        if critical or warnings or info:
            from PySide6.QtWidgets import QPushButton
            self.tech_btn = QPushButton("Mostrar detalhes técnicos ▼")
            self.tech_btn.setObjectName("tech_btn")
            self.tech_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.tech_btn.clicked.connect(self._toggle_details)
            layout.addWidget(self.tech_btn)

        # Issue list
        self._scroll = QScrollArea()
        self._scroll.setVisible(not (critical or warnings or info))
        self._scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        for issue in self._issues:
            issue_widget = self._create_issue_widget(issue)
            scroll_layout.addWidget(issue_widget)

        scroll_layout.addStretch()
        self._scroll.setWidget(scroll_widget)
        layout.addWidget(self._scroll)

        # Buttons
        btn_layout = QHBoxLayout()

        from PySide6.QtWidgets import QPushButton

        copy_btn = QPushButton("📋 Copiar Relatório Técnico")
        copy_btn.setStyleSheet("background: #2A1A1A; color: #E8E0D8; border: 1px solid #444;")
        copy_btn.clicked.connect(self._copy_report)
        btn_layout.addWidget(copy_btn)

        btn_layout.addStretch()

        cancel_btn = QPushButton("✕ Cancelar")
        cancel_btn.setStyleSheet("background: #2A1A1A; color: #FF6E1A; border: 1px solid #FF6E1A;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        apply_btn = QPushButton("▶ Continuar e Aplicar")
        apply_btn.setStyleSheet("background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #C0392B,stop:1 #8B0000); color: #FFF; border: none;")
        apply_btn.clicked.connect(self._on_apply)
        btn_layout.addWidget(apply_btn)

        layout.addLayout(btn_layout)

    def _create_issue_widget(self, issue: HealthIssue) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 4, 8, 4)

        color = SEVERITY_COLORS.get(issue.severity, "#FFFFFF")
        label_text = SEVERITY_LABELS.get(issue.severity, "")

        header = QLabel(
            f"<span style='color:{color};'>[{label_text}]</span> "
            f"<span style='color:#AAAAAA;'>{issue.code}: {issue.check_name}</span>"
            f"<br><span style='color:#777777; font-size: 12px;'>Arquivo: {issue.file_path}</span>"
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        desc = QLabel(issue.description)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #888888; margin-left: 16px; font-size: 12px;")
        layout.addWidget(desc)

        if issue.fix_description:
            fix = QLabel(f"<i>Auto-correção: {issue.fix_description}</i>")
            fix.setWordWrap(True)
            fix.setStyleSheet("color: #66AA66; margin-left: 16px; font-size: 12px;")
            layout.addWidget(fix)

        widget.setStyleSheet(
            f"QWidget {{ border-left: 2px solid {color}; "
            f"background: rgba(20, 20, 20, 0.4); margin-bottom: 4px; padding: 4px; border-radius: 4px; }}"
        )
        return widget

    def _toggle_details(self):
        is_visible = not self._scroll.isVisible()
        self._scroll.setVisible(is_visible)
        self.tech_btn.setText("Ocultar detalhes técnicos ▲" if is_visible else "Mostrar detalhes técnicos ▼")

    def _copy_report(self):
        from PySide6.QtWidgets import QApplication
        report = generate_bug_report(self._issues, self._mod_name, self._mod_files)
        QApplication.clipboard().setText(report)
        self.parent().statusBar().showMessage("Relatório copiado para a área de transferência!", 5000)

    def _on_apply(self):
        self._user_choice = "apply"
        self.accept()

    @property
    def user_choice(self) -> str:
        return self._user_choice
