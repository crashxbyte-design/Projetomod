"""panel_config.py - Configurações globais do sistema."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QLineEdit, QPushButton
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import database as db
from styles import VERMELHO, VERMELHO_ESC, BRANCO, CINZA_BG, CINZA_BORDA, CINZA_SUAVE, PRETO_TITULO, VERDE, LARANJA


def _field(placeholder=""):
    w = QLineEdit()
    w.setPlaceholderText(placeholder)
    w.setFixedHeight(36)
    w.setFont(QFont("Segoe UI", 10))
    w.setStyleSheet(f"QLineEdit{{background:{BRANCO};border:1px solid {CINZA_BORDA};border-radius:4px;padding:4px 12px;}}QLineEdit:focus{{border-color:{VERMELHO};}}")
    return w


def _row(label, widget):
    ly = QHBoxLayout(); ly.setSpacing(12)
    lbl = QLabel(label)
    lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
    lbl.setFixedWidth(180)
    lbl.setStyleSheet(f"color:{PRETO_TITULO};background:transparent;border:none;")
    ly.addWidget(lbl); ly.addWidget(widget, 1)
    w = QWidget(); w.setLayout(ly); w.setStyleSheet("background:transparent;border:none;")
    return w


class ConfigPanel(QWidget):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self._build_ui()
        self._load()

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        root.addWidget(scroll)
        container = QWidget(); container.setStyleSheet(f"background:{CINZA_BG};")
        scroll.setWidget(container)
        ly = QVBoxLayout(container); ly.setContentsMargins(28, 24, 28, 28); ly.setSpacing(20)

        # Título
        t = QLabel("CONFIGURAÇÕES DO SISTEMA")
        t.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        t.setStyleSheet(f"color:{PRETO_TITULO};background:transparent;border:none;")
        ly.addWidget(t)
        s = QLabel("Defina as informações globais exibidas no book de indicadores.")
        s.setFont(QFont("Segoe UI", 9))
        s.setStyleSheet(f"color:{CINZA_SUAVE};background:transparent;border:none;")
        ly.addWidget(s)

        # Card principal
        card = QFrame()
        card.setStyleSheet(f"QFrame{{background:{BRANCO};border:1px solid {CINZA_BORDA};border-radius:6px;}}")
        card_ly = QVBoxLayout(card); card_ly.setContentsMargins(28, 24, 28, 28); card_ly.setSpacing(16)

        sec = QLabel("IDENTIFICAÇÃO")
        sec.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        sec.setStyleSheet(f"color:{CINZA_SUAVE};background:transparent;border:none;letter-spacing:2px;")
        card_ly.addWidget(sec)

        self.f_book        = _field("Ex: Indicadores de Segurança Patrimonial")
        self.f_instituicao = _field("Ex: Hospital Universitário Evangélico Mackenzie")
        self.f_responsavel = _field("Ex: Segurança Patrimonial")
        card_ly.addWidget(_row("Nome do Book",    self.f_book))
        card_ly.addWidget(_row("Instituição",     self.f_instituicao))
        card_ly.addWidget(_row("Responsável",     self.f_responsavel))

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background:{CINZA_BORDA};border:none;"); sep.setFixedHeight(1)
        card_ly.addWidget(sep)

        sec2 = QLabel("PERÍODO E DATA")
        sec2.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        sec2.setStyleSheet(f"color:{CINZA_SUAVE};background:transparent;border:none;letter-spacing:2px;")
        card_ly.addWidget(sec2)

        self.f_periodo     = _field("Ex: Jan a Fev/2026")
        self.f_atualizacao = _field("Ex: 05/02/2026")
        card_ly.addWidget(_row("Período Atual",       self.f_periodo))
        card_ly.addWidget(_row("Data de Atualização", self.f_atualizacao))

        # Botões
        btn_ly = QHBoxLayout(); btn_ly.setSpacing(10)
        self.lbl_status = QLabel("")
        self.lbl_status.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.lbl_status.setStyleSheet("background:transparent;border:none;")
        btn_ly.addWidget(self.lbl_status); btn_ly.addStretch()
        btn_save = QPushButton("💾  Salvar Configurações")
        btn_save.setFixedHeight(36)
        btn_save.setStyleSheet(f"QPushButton{{background:{VERMELHO_ESC};color:{BRANCO};border:none;border-radius:5px;padding:0 24px;font-weight:bold;font-size:10pt;}}QPushButton:hover{{background:{VERMELHO};}}")
        btn_ly.addWidget(btn_save)
        card_ly.addLayout(btn_ly)

        ly.addWidget(card)
        ly.addStretch()

        btn_save.clicked.connect(self._save)

    def _load(self):
        cfg = db.get_all_config()
        self.f_book.setText(cfg.get("nome_book", ""))
        self.f_instituicao.setText(cfg.get("nome_instituicao", ""))
        self.f_responsavel.setText(cfg.get("responsavel", ""))
        self.f_periodo.setText(cfg.get("periodo_atual", ""))
        self.f_atualizacao.setText(cfg.get("data_atualizacao", ""))

    def _save(self):
        db.set_config("nome_book",        self.f_book.text().strip())
        db.set_config("nome_instituicao", self.f_instituicao.text().strip())
        db.set_config("responsavel",      self.f_responsavel.text().strip())
        db.set_config("periodo_atual",    self.f_periodo.text().strip())
        db.set_config("data_atualizacao", self.f_atualizacao.text().strip())
        self.lbl_status.setText("✅ Configurações salvas!")
        self.lbl_status.setStyleSheet(f"color:{VERDE};background:transparent;border:none;")
