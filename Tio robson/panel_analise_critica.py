"""panel_analise_critica.py — Análise crítica refinada."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QComboBox, QTextEdit, QLineEdit, QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import database as db
from styles import VERMELHO, VERMELHO_ESC, BRANCO, CINZA_BG, CINZA_BORDA, CINZA_SUAVE, PRETO_TITULO, VERDE, LARANJA
from widgets import shadow

NIVEIS = ["ATENÇÃO", "CRÍTICO", "OK", "MONITORAMENTO"]
NIVEL_CORES = {"ATENÇÃO": "#F59E0B", "CRÍTICO": "#EF4444", "OK": "#10B981", "MONITORAMENTO": "#6366F1"}

CSS_FIELD = "background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:8px 12px;color:#0F172A;font-family:'Segoe UI';font-size:10pt;"
CSS_FIELD_FOCUS = "background:#FFFFFF;border:1.5px solid #BE123C;border-radius:6px;padding:8px 12px;color:#0F172A;box-shadow: 0 0 0 2px rgba(185,28,28,0.2);"

def _lbl(t, bold=False, size=9, color="#475569"):
    l = QLabel(t)
    l.setFont(QFont("Segoe UI", size, QFont.Weight.Bold if bold else QFont.Weight.Normal))
    l.setStyleSheet(f"color:{color};background:transparent;border:none;")
    return l

def _sec(t):
    f = QFrame()
    f.setStyleSheet("background:transparent;border:none;")
    ly = QHBoxLayout(f); ly.setContentsMargins(0,12,0,6); ly.setSpacing(10)
    bar = QFrame(); bar.setFixedSize(4,16)
    bar.setStyleSheet(f"background:{VERMELHO_ESC};border-radius:2px;border:none;")
    ly.addWidget(bar)
    lbl = QLabel(t.upper())
    lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
    lbl.setStyleSheet(f"color:#475569;letter-spacing:1px;background:transparent;border:none;")
    ly.addWidget(lbl); ly.addStretch()
    return f

def _fld(ph=""):
    w = QLineEdit(); w.setPlaceholderText(ph); w.setFixedHeight(40)
    w.setStyleSheet(f"QLineEdit{{{CSS_FIELD}}}QLineEdit:focus{{{CSS_FIELD_FOCUS}}}")
    return w

def _txt(rows=4):
    w = QTextEdit(); w.setFixedHeight(rows*28)
    w.setStyleSheet(f"QTextEdit{{{CSS_FIELD}}}QTextEdit:focus{{{CSS_FIELD_FOCUS}}}")
    return w

def _cbx(items=None, editable=False):
    w = QComboBox(); w.setFixedHeight(40); w.setEditable(editable)
    if items: w.addItems(items)
    w.setStyleSheet(f"QComboBox{{{CSS_FIELD}}}QComboBox::drop-down{{border:none;padding-right:8px;}}QComboBox:focus{{border:1.5px solid {VERMELHO_ESC};background:#FFFFFF;}}")
    return w

def _row(lbl, widget, stretch=False):
    f = QFrame(); f.setStyleSheet("background:transparent;border:none;")
    ly = QVBoxLayout(f); ly.setContentsMargins(0,0,0,0); ly.setSpacing(6)
    l = _lbl(lbl, color="#334155", size=9)
    l.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
    ly.addWidget(l); ly.addWidget(widget)
    if stretch: widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    return f

def _hrow(*pairs):
    f = QFrame(); f.setStyleSheet("background:transparent;border:none;")
    ly = QHBoxLayout(f); ly.setContentsMargins(0,0,0,0); ly.setSpacing(20)
    for lbl, widget, weight in pairs:
        ly.addWidget(_row(lbl, widget), weight)
    return f


class AnaliseCriticaPanel(QWidget):
    def __init__(self, data, parent=None):
        super().__init__(parent); self.data = data
        self._build_ui(); self._populate_selector()

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        root.addWidget(scroll)
        ctr = QWidget(); ctr.setStyleSheet(f"background:transparent;")
        scroll.setWidget(ctr)
        ly = QVBoxLayout(ctr); ly.setContentsMargins(32,32,32,32); ly.setSpacing(24)

        # Header bar
        hdr = QFrame()
        hdr.setStyleSheet(f"QFrame{{background:{BRANCO};border:1px solid #E2E8F0;border-radius:12px;}}")
        hdr.setGraphicsEffect(shadow(12,(0,4),(0,0,0,10)))
        hdr_ly = QHBoxLayout(hdr); hdr_ly.setContentsMargins(32,24,32,24); hdr_ly.setSpacing(24)
        
        ttl_ly = QVBoxLayout(); ttl_ly.setSpacing(6)
        ttl_ly.addWidget(_lbl("Análise Crítica", bold=True, size=16, color="#0F172A"))
        ttl_ly.addWidget(_lbl("Registre a análise completa, causas, plano de ação e respostas.", color="#64748B", size=10))
        hdr_ly.addLayout(ttl_ly, 1)

        sep1 = QFrame(); sep1.setFrameShape(QFrame.Shape.VLine); sep1.setStyleSheet("background:#E2E8F0;border:none;"); sep1.setFixedWidth(1)
        hdr_ly.addWidget(sep1)

        ind_col = QVBoxLayout(); ind_col.setSpacing(6)
        ind_col.addWidget(_lbl("Indicador Alvo", bold=True, size=9, color="#475569"))
        self.sel_ind = _cbx(); self.sel_ind.setMinimumWidth(360)
        ind_col.addWidget(self.sel_ind)
        hdr_ly.addLayout(ind_col)

        per_col = QVBoxLayout(); per_col.setSpacing(6)
        per_col.addWidget(_lbl("Período Relativo", bold=True, size=9, color="#475569"))
        self.f_periodo = _fld("Jan–Fev/2026"); self.f_periodo.setFixedWidth(140)
        per_col.addWidget(self.f_periodo)
        hdr_ly.addLayout(per_col)
        
        ly.addWidget(hdr)

        # Main card
        card = QFrame()
        card.setStyleSheet(f"QFrame{{background:{BRANCO};border:1px solid #E2E8F0;border-radius:12px;}}")
        card.setGraphicsEffect(shadow(12,(0,4),(0,0,0,10)))
        c_ly = QVBoxLayout(card); c_ly.setContentsMargins(32,32,32,32); c_ly.setSpacing(24)

        # Análise crítica
        c_ly.addWidget(_sec("Diagnóstico e Desempenho"))
        self.f_analise = _txt(4)
        c_ly.addWidget(_row("Análise Crítica — descreva o desempenho observado no período", self.f_analise))

        sep_c1 = QFrame(); sep_c1.setFrameShape(QFrame.Shape.HLine); sep_c1.setStyleSheet("background:#E2E8F0;border:none;")
        c_ly.addWidget(sep_c1)

        # Causa + Ação
        self.f_causa = _txt(3); self.f_acao = _txt(3)
        c_ly.addWidget(_sec("Plano de Intervenção"))
        c_ly.addWidget(_hrow(("Identificação da Causa Raiz", self.f_causa, 1), ("Ação Proposta / Plano", self.f_acao, 1)))

        sep_c2 = QFrame(); sep_c2.setFrameShape(QFrame.Shape.HLine); sep_c2.setStyleSheet("background:#E2E8F0;border:none;")
        c_ly.addWidget(sep_c2)

        # Resp + Prazo + Nível
        self.f_resp = _fld("Ex: Diretor de Operações")
        self.f_prazo = _fld("DD/MM/AAAA")
        self.f_nivel = _cbx(NIVEIS)
        c_ly.addWidget(_sec("Responsabilidade e Prazos"))
        c_ly.addWidget(_hrow(
            ("Responsável pela Ação", self.f_resp, 2),
            ("Prazo Alvo", self.f_prazo, 1),
            ("Nível de Criticidade", self.f_nivel, 1)
        ))

        sep_c3 = QFrame(); sep_c3.setFrameShape(QFrame.Shape.HLine); sep_c3.setStyleSheet("background:#E2E8F0;border:none;")
        c_ly.addWidget(sep_c3)

        # Barra de ações
        act = QHBoxLayout(); act.setSpacing(12)
        self.lbl_st = _lbl("", bold=True, size=10, color=VERDE)
        act.addWidget(self.lbl_st); act.addStretch()
        
        self._btn_limpar = QPushButton("Limpar Formulário")
        self._btn_limpar.setFixedHeight(42); self._btn_limpar.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_limpar.setStyleSheet(f"QPushButton{{background:transparent;color:#475569;border:1px solid #CBD5E1;border-radius:8px;padding:0 24px;font-weight:bold;font-size:10pt;}}QPushButton:hover{{background:#F1F5F9;}}")
        
        self._btn_save = QPushButton("Salvar Análise Crítica")
        self._btn_save.setFixedHeight(42); self._btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_save.setStyleSheet(f"QPushButton{{background:{VERMELHO_ESC};color:#fff;border:none;border-radius:8px;padding:0 32px;font-weight:bold;font-size:10pt;}}QPushButton:hover{{background:{VERMELHO};}}")
        
        act.addWidget(self._btn_limpar); act.addWidget(self._btn_save)
        c_ly.addSpacing(8)
        c_ly.addLayout(act)

        ly.addWidget(card, 1)

        self.sel_ind.currentIndexChanged.connect(self._load)
        self._btn_save.clicked.connect(self._save)
        self._btn_limpar.clicked.connect(self._clear)

    def _populate_selector(self):
        self.sel_ind.clear()
        for i in db.get_indicadores_ativos():
            self.sel_ind.addItem(f"{i['codigo_indicador']}  —  {i['nome_indicador']}", i['codigo_indicador'])

    def _load(self):
        cod = self.sel_ind.currentData()
        if not cod: return
        acs = db.get_analise_critica(cod)
        if acs:
            ac = acs[0]
            self.f_periodo.setText(ac.get("periodo") or "")
            self.f_analise.setPlainText(ac.get("analise") or "")
            self.f_causa.setPlainText(ac.get("causa") or "")
            self.f_acao.setPlainText(ac.get("acao") or "")
            self.f_resp.setText(ac.get("responsavel") or "")
            self.f_prazo.setText(ac.get("prazo") or "")
            idx = self.f_nivel.findText(ac.get("nivel") or "ATENÇÃO")
            self.f_nivel.setCurrentIndex(max(idx, 0))
        else:
            self._clear()

    def _save(self):
        cod = self.sel_ind.currentData()
        if not cod:
            self.lbl_st.setText("⚠️ Selecione um indicador.")
            self.lbl_st.setStyleSheet(f"color:{LARANJA};background:transparent;border:none;")
            return
        ok = db.upsert_analise_critica({
            "codigo_indicador": cod,
            "periodo":     self.f_periodo.text().strip(),
            "analise":     self.f_analise.toPlainText().strip(),
            "causa":       self.f_causa.toPlainText().strip(),
            "acao":        self.f_acao.toPlainText().strip(),
            "responsavel": self.f_resp.text().strip(),
            "prazo":       self.f_prazo.text().strip(),
            "nivel":       self.f_nivel.currentText(),
        })
        cor = VERDE if ok else VERMELHO
        msg = "✅ Análise salva!" if ok else "❌ Erro ao salvar."
        self.lbl_st.setText(msg)
        self.lbl_st.setStyleSheet(f"color:{cor};background:transparent;border:none;font-weight:bold;font-family:'Segoe UI';")

    def _clear(self):
        for w in [self.f_periodo, self.f_resp, self.f_prazo]: w.clear()
        for w in [self.f_analise, self.f_causa, self.f_acao]: w.clear()
        self.f_nivel.setCurrentIndex(0); self.lbl_st.setText("")
