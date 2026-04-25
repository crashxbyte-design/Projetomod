"""panel_config.py — Configurações globais refinadas."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QLineEdit, QPushButton
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import database as db
from styles import VERMELHO, VERMELHO_ESC, BRANCO, PRETO_TITULO, VERDE, LARANJA
from widgets import shadow

CSS_F = "background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:8px 12px;color:#0F172A;font-family:'Segoe UI';font-size:10pt;"

def _lbl(t, bold=False, size=9, color="#475569"):
    l = QLabel(t)
    l.setFont(QFont("Segoe UI", size, QFont.Weight.Bold if bold else QFont.Weight.Medium))
    l.setStyleSheet(f"color:{color};background:transparent;border:none;")
    return l

def _fld(ph=""):
    w = QLineEdit(); w.setPlaceholderText(ph); w.setFixedHeight(40)
    w.setStyleSheet(f"QLineEdit{{{CSS_F}}}QLineEdit:focus{{border:1.5px solid {VERMELHO_ESC};background:#FFFFFF;box-shadow: 0 0 0 2px rgba(185,28,28,0.2);}}")
    return w

def _sec(title, subtitle=""):
    f = QFrame(); f.setStyleSheet("background:transparent;border:none;")
    ly = QVBoxLayout(f); ly.setContentsMargins(0,0,0,0); ly.setSpacing(4)
    hly = QHBoxLayout(); hly.setContentsMargins(0,0,0,0); hly.setSpacing(10)
    bar = QFrame(); bar.setFixedSize(4, 16)
    bar.setStyleSheet(f"background:{VERMELHO_ESC};border-radius:2px;border:none;")
    hly.addWidget(bar)
    t = _lbl(title.upper(), bold=True, size=8, color="#334155")
    t.setStyleSheet(f"color:#334155;letter-spacing:1px;background:transparent;border:none;font-weight:bold;")
    hly.addWidget(t); hly.addStretch(); ly.addLayout(hly)
    if subtitle: ly.addWidget(_lbl(subtitle, size=9, color="#64748B"))
    sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
    sep.setStyleSheet("background:#E2E8F0;border:none;"); sep.setFixedHeight(1)
    ly.addSpacing(6); ly.addWidget(sep)
    return f

def _row_field(label, widget):
    f = QFrame(); f.setStyleSheet("background:transparent;border:none;")
    ly = QVBoxLayout(f); ly.setContentsMargins(0,0,0,0); ly.setSpacing(6)
    l = _lbl(label, size=9, color="#334155")
    l.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
    ly.addWidget(l); ly.addWidget(widget)
    return f

def _h2(w1, w2):
    f = QFrame(); f.setStyleSheet("background:transparent;border:none;")
    ly = QHBoxLayout(f); ly.setContentsMargins(0,0,0,0); ly.setSpacing(16)
    ly.addWidget(w1, 1); ly.addWidget(w2, 1)
    return f

class ConfigPanel(QWidget):
    def __init__(self, data, parent=None):
        super().__init__(parent); self.data = data
        self._build_ui(); self._load()

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        root.addWidget(scroll)
        ctr = QWidget(); ctr.setStyleSheet("background:transparent;")
        scroll.setWidget(ctr)
        ly = QVBoxLayout(ctr); ly.setContentsMargins(32,32,32,32); ly.setSpacing(24)

        # Page header
        ph = QFrame()
        ph.setStyleSheet(f"QFrame{{background:{BRANCO};border:1px solid #E2E8F0;border-radius:12px;}}")
        ph.setGraphicsEffect(shadow(12,(0,4),(0,0,0,10)))
        ph_ly = QHBoxLayout(ph); ph_ly.setContentsMargins(32,24,32,24)
        vly = QVBoxLayout(); vly.setSpacing(6)
        vly.addWidget(_lbl("Configurações do Sistema", bold=True, size=16, color="#0F172A"))
        vly.addWidget(_lbl("Defina os dados institucionais que serão exibidos nos relatórios e books gerados.", size=10, color="#64748B"))
        ph_ly.addLayout(vly, 1)
        ly.addWidget(ph)

        # Center container
        center = QWidget()
        center.setMaximumWidth(840)
        c_ly = QVBoxLayout(center); c_ly.setContentsMargins(0,0,0,0); c_ly.setSpacing(24)
        
        # Card 1 — Identificação
        card1 = QFrame()
        card1.setStyleSheet(f"QFrame{{background:{BRANCO};border:1px solid #E2E8F0;border-radius:12px;}}")
        card1.setGraphicsEffect(shadow(12,(0,4),(0,0,0,10)))
        c1 = QVBoxLayout(card1); c1.setContentsMargins(32,32,32,32); c1.setSpacing(20)
        c1.addWidget(_sec("Identificação Institucional", "Dados que aparecem na capa e cabeçalhos dos documentos exportados"))
        
        self.f_book = _fld("Ex: Indicadores de Segurança Patrimonial")
        self.f_inst = _fld("Ex: Hospital Universitário Evangélico Mackenzie")
        self.f_resp = _fld("Ex: Gerência de Segurança Patrimonial")
        c1.addWidget(_row_field("Nome do Book / Relatório", self.f_book))
        c1.addWidget(_row_field("Nome da Instituição", self.f_inst))
        c1.addWidget(_row_field("Departamento / Responsável", self.f_resp))
        c_ly.addWidget(card1)
        
        # Card 2 — Período
        card2 = QFrame()
        card2.setStyleSheet(f"QFrame{{background:{BRANCO};border:1px solid #E2E8F0;border-radius:12px;}}")
        card2.setGraphicsEffect(shadow(12,(0,4),(0,0,0,10)))
        c2 = QVBoxLayout(card2); c2.setContentsMargins(32,32,32,32); c2.setSpacing(20)
        c2.addWidget(_sec("Período e Atualização", "Dados de referência temporal do relatório global"))
        
        self.f_per = _fld("Ex: Janeiro a Fevereiro/2026")
        self.f_dat = _fld("Ex: 05/02/2026")
        c2.addWidget(_h2(_row_field("Período de Referência", self.f_per),
                         _row_field("Data de Atualização", self.f_dat)))
        c_ly.addWidget(card2)

        # Actions
        act = QHBoxLayout(); act.setSpacing(12)
        self.lbl_st = _lbl("", bold=True, size=10, color=VERDE)
        act.addWidget(self.lbl_st); act.addStretch()
        btn = QPushButton("Salvar Configurações")
        btn.setFixedHeight(42); btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"QPushButton{{background:{VERMELHO_ESC};color:#fff;border:none;border-radius:8px;padding:0 32px;font-family:'Segoe UI';font-weight:bold;font-size:10pt;}}QPushButton:hover{{background:{VERMELHO};}}")
        act.addWidget(btn)
        c_ly.addLayout(act)
        
        wrapper = QHBoxLayout(); wrapper.addWidget(center); wrapper.addStretch()
        ly.addLayout(wrapper)
        ly.addStretch()
        btn.clicked.connect(self._save)

    def _load(self):
        cfg = db.get_all_config()
        self.f_book.setText(cfg.get("nome_book", ""))
        self.f_inst.setText(cfg.get("nome_instituicao", ""))
        self.f_resp.setText(cfg.get("responsavel", ""))
        self.f_per.setText(cfg.get("periodo_atual", ""))
        self.f_dat.setText(cfg.get("data_atualizacao", ""))

    def _save(self):
        db.set_config("nome_book", self.f_book.text().strip())
        db.set_config("nome_instituicao", self.f_inst.text().strip())
        db.set_config("responsavel", self.f_resp.text().strip())
        db.set_config("periodo_atual", self.f_per.text().strip())
        db.set_config("data_atualizacao", self.f_dat.text().strip())
        self.lbl_st.setText("✅ Configurações salvas!")
        self.lbl_st.setStyleSheet(f"color:{VERDE};background:transparent;border:none;font-weight:bold;")
