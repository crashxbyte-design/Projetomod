"""panel_analise_critica.py - Análise crítica por indicador."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QComboBox, QTextEdit, QLineEdit, QPushButton,
    QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import database as db
from styles import VERMELHO, VERMELHO_ESC, BRANCO, CINZA_BG, CINZA_BORDA, CINZA_SUAVE, PRETO_TITULO, VERDE, LARANJA

NIVEIS = ["ATENÇÃO", "CRÍTICO", "OK", "MONITORAMENTO"]


def _lbl(txt, bold=False):
    l = QLabel(txt)
    l.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold if bold else QFont.Weight.Normal))
    l.setStyleSheet(f"color:{PRETO_TITULO};background:transparent;border:none;")
    return l


def _field():
    w = QLineEdit()
    w.setFixedHeight(34)
    w.setFont(QFont("Segoe UI", 9))
    w.setStyleSheet(f"QLineEdit{{background:{BRANCO};border:1px solid {CINZA_BORDA};border-radius:4px;padding:4px 10px;}}QLineEdit:focus{{border-color:{VERMELHO};}}")
    return w


def _textarea(rows=4):
    w = QTextEdit()
    w.setFixedHeight(rows * 28)
    w.setFont(QFont("Segoe UI", 9))
    w.setStyleSheet(f"QTextEdit{{background:{BRANCO};border:1px solid {CINZA_BORDA};border-radius:4px;padding:6px;}}QTextEdit:focus{{border-color:{VERMELHO};}}")
    return w


class AnaliseCriticaPanel(QWidget):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self._build_ui()
        self._populate_selector()

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        root.addWidget(scroll)
        container = QWidget(); container.setStyleSheet(f"background:{CINZA_BG};")
        scroll.setWidget(container)
        ly = QVBoxLayout(container); ly.setContentsMargins(28, 24, 28, 28); ly.setSpacing(20)

        # Título
        t = QLabel("ANÁLISE CRÍTICA DOS INDICADORES")
        t.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        t.setStyleSheet(f"color:{PRETO_TITULO};background:transparent;border:none;")
        ly.addWidget(t)
        s = QLabel("Registre análise, causa, ação, responsável e prazo para cada indicador.")
        s.setFont(QFont("Segoe UI", 9))
        s.setStyleSheet(f"color:{CINZA_SUAVE};background:transparent;border:none;")
        ly.addWidget(s)

        # Seletor
        sel_frame = QFrame()
        sel_frame.setStyleSheet(f"QFrame{{background:{BRANCO};border:1px solid {CINZA_BORDA};border-radius:6px;}}")
        sel_ly = QHBoxLayout(sel_frame); sel_ly.setContentsMargins(20, 14, 20, 14); sel_ly.setSpacing(14)
        sel_ly.addWidget(_lbl("Indicador:", True))
        self.sel_ind = QComboBox()
        self.sel_ind.setMinimumWidth(380); self.sel_ind.setFixedHeight(34)
        self.sel_ind.setFont(QFont("Segoe UI", 9))
        self.sel_ind.setStyleSheet(f"QComboBox{{background:{BRANCO};border:1px solid {CINZA_BORDA};border-radius:4px;padding:4px 10px;}}QComboBox::drop-down{{border:none;}}")
        sel_ly.addWidget(self.sel_ind)
        sel_ly.addWidget(_lbl("Período:", True))
        self.f_periodo = _field(); self.f_periodo.setFixedWidth(140); self.f_periodo.setPlaceholderText("Jan a Fev/2026")
        sel_ly.addWidget(self.f_periodo)
        sel_ly.addStretch()
        ly.addWidget(sel_frame)

        # Form
        form = QFrame()
        form.setStyleSheet(f"QFrame{{background:{BRANCO};border:1px solid {CINZA_BORDA};border-radius:6px;}}")
        form_ly = QVBoxLayout(form); form_ly.setContentsMargins(24, 20, 24, 20); form_ly.setSpacing(14)

        form_ly.addWidget(_lbl("Análise Crítica", True))
        self.f_analise = _textarea(5)
        form_ly.addWidget(self.f_analise)

        row2 = QHBoxLayout(); row2.setSpacing(20)
        col_c = QVBoxLayout(); col_c.addWidget(_lbl("Causa", True)); self.f_causa = _textarea(3); col_c.addWidget(self.f_causa)
        col_a = QVBoxLayout(); col_a.addWidget(_lbl("Ação", True)); self.f_acao = _textarea(3); col_a.addWidget(self.f_acao)
        row2.addLayout(col_c); row2.addLayout(col_a)
        form_ly.addLayout(row2)

        row3 = QHBoxLayout(); row3.setSpacing(20)
        col_r = QVBoxLayout(); col_r.addWidget(_lbl("Responsável", True)); self.f_resp = _field(); col_r.addWidget(self.f_resp)
        col_p = QVBoxLayout(); col_p.addWidget(_lbl("Prazo", True)); self.f_prazo = _field(); self.f_prazo.setPlaceholderText("DD/MM/AAAA"); col_p.addWidget(self.f_prazo)
        col_n = QVBoxLayout(); col_n.addWidget(_lbl("Nível", True))
        self.f_nivel = QComboBox(); self.f_nivel.addItems(NIVEIS); self.f_nivel.setFixedHeight(34)
        self.f_nivel.setStyleSheet(f"QComboBox{{background:{BRANCO};border:1px solid {CINZA_BORDA};border-radius:4px;padding:4px 10px;}}QComboBox::drop-down{{border:none;}}")
        col_n.addWidget(self.f_nivel)
        row3.addLayout(col_r, 2); row3.addLayout(col_p, 1); row3.addLayout(col_n, 1)
        form_ly.addLayout(row3)

        # Botões
        btn_ly = QHBoxLayout(); btn_ly.setSpacing(10)
        self.lbl_status = QLabel("")
        self.lbl_status.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.lbl_status.setStyleSheet("background:transparent;border:none;")
        btn_ly.addWidget(self.lbl_status); btn_ly.addStretch()
        btn_limpar = QPushButton("Limpar")
        btn_limpar.setFixedHeight(34)
        btn_limpar.setStyleSheet(f"QPushButton{{background:{BRANCO};border:1px solid {CINZA_BORDA};border-radius:5px;padding:0 16px;}}QPushButton:hover{{background:#F5F5F5;}}")
        btn_save = QPushButton("💾  Salvar Análise")
        btn_save.setFixedHeight(34)
        btn_save.setStyleSheet(f"QPushButton{{background:{VERMELHO_ESC};color:{BRANCO};border:none;border-radius:5px;padding:0 20px;font-weight:bold;}}QPushButton:hover{{background:{VERMELHO};}}")
        btn_ly.addWidget(btn_limpar); btn_ly.addWidget(btn_save)
        form_ly.addLayout(btn_ly)
        ly.addWidget(form, 1)

        # Signals
        self.sel_ind.currentIndexChanged.connect(self._load_analise)
        btn_save.clicked.connect(self._save)
        btn_limpar.clicked.connect(self._clear)

    def _populate_selector(self):
        self.sel_ind.clear()
        for i in db.get_indicadores_ativos():
            self.sel_ind.addItem(f"{i['codigo_indicador']}  —  {i['nome_indicador']}", i['codigo_indicador'])

    def _load_analise(self):
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
            self.f_nivel.setCurrentIndex(idx if idx >= 0 else 0)
        else:
            self._clear()

    def _save(self):
        cod = self.sel_ind.currentData()
        if not cod:
            self.lbl_status.setText("⚠️ Selecione um indicador.")
            self.lbl_status.setStyleSheet(f"color:{LARANJA};background:transparent;border:none;")
            return
        ok = db.upsert_analise_critica({
            "codigo_indicador": cod,
            "periodo":    self.f_periodo.text().strip(),
            "analise":    self.f_analise.toPlainText().strip(),
            "causa":      self.f_causa.toPlainText().strip(),
            "acao":       self.f_acao.toPlainText().strip(),
            "responsavel":self.f_resp.text().strip(),
            "prazo":      self.f_prazo.text().strip(),
            "nivel":      self.f_nivel.currentText(),
        })
        if ok:
            self.lbl_status.setText("✅ Análise salva com sucesso!")
            self.lbl_status.setStyleSheet(f"color:{VERDE};background:transparent;border:none;")
        else:
            self.lbl_status.setText("❌ Erro ao salvar.")
            self.lbl_status.setStyleSheet(f"color:{VERMELHO};background:transparent;border:none;")

    def _clear(self):
        for w in [self.f_periodo, self.f_resp, self.f_prazo]:
            w.clear()
        for w in [self.f_analise, self.f_causa, self.f_acao]:
            w.clear()
        self.f_nivel.setCurrentIndex(0)
        self.lbl_status.setText("")
