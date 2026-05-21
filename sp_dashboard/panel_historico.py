"""
panel_historico.py — Lançamento e edição de histórico mensal.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QPushButton, QComboBox, QLineEdit,
    QGridLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox, QInputDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIntValidator, QDoubleValidator, QRegularExpressionValidator
from PySide6.QtCore import QRegularExpression

import database as db
from styles import (
    VERMELHO, VERMELHO_ESC, BRANCO, CINZA_BG, CINZA_BORDA,
    CINZA_SUAVE, PRETO_TITULO, VERDE, LARANJA, COMBO_DROPDOWN_CSS
)
from widgets import shadow, SectionTitle

MESES = [
    "Janeiro","Fevereiro","Março","Abril","Maio","Junho",
    "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"
]

TRIM_LABELS = [
    "T1 — JAN / FEV / MAR", "T2 — ABR / MAI / JUN",
    "T3 — JUL / AGO / SET", "T4 — OUT / NOV / DEZ"
]

def _lbl(t, bold=False, size=9, color=PRETO_TITULO):
    label = QLabel(t)
    label.setFont(QFont("Segoe UI", size, QFont.Weight.Bold if bold else QFont.Weight.Normal))
    label.setStyleSheet(f"color:{color}; background:transparent; border:none;")
    return label

def _cbx():
    w = QComboBox()
    w.setFixedHeight(38)
    w.setStyleSheet(f"""
        QComboBox {{
            background: #F9FAFB; border: 1.5px solid #E2E8F0; border-radius: 6px;
            padding: 4px 12px; color: {PRETO_TITULO}; font-size: 10pt;
        }}
        {COMBO_DROPDOWN_CSS}
        QComboBox:focus {{ border: 1.5px solid {VERMELHO_ESC}; background: #FFFFFF; }}
        QComboBox QLineEdit {{ background: transparent; border: none; color: {PRETO_TITULO}; }}
    """)
    return w

class HistoricoPanel(QWidget):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self._inputs = {}
        self._build_ui()
        self._populate_selector()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        root.addWidget(scroll)
        
        ctr = QWidget()
        ctr.setStyleSheet(f"background: {CINZA_BG};")
        scroll.setWidget(ctr)
        
        main = QVBoxLayout(ctr)
        main.setContentsMargins(32, 28, 32, 32)
        main.setSpacing(24)

        # ── Título da Página ───────────────────────────────────────────────
        title = SectionTitle("LANÇAMENTO DE HISTÓRICO MENSAL")
        main.addWidget(title)

        # ── Filtros (Header) ───────────────────────────────────────────────
        hdr = QFrame()
        hdr.setStyleSheet(f"""
            QFrame {{
                background: {BRANCO}; border: 1px solid {CINZA_BORDA}; border-radius: 12px;
            }}
        """)
        hdr.setGraphicsEffect(shadow(12, (0, 4), (0, 0, 0, 10)))
        hdr_ly = QHBoxLayout(hdr)
        hdr_ly.setContentsMargins(24, 24, 24, 24)
        hdr_ly.setSpacing(24)

        params_ly = QHBoxLayout()
        params_ly.setSpacing(16)
        
        def _lbl_hdr(t): return _lbl(t, bold=True, size=8, color="#475569")
        
        ind_col = QVBoxLayout()
        ind_col.setSpacing(6)
        ind_col.addWidget(_lbl_hdr("INDICADOR PAI"))
        self.sel_ind = _cbx()
        self.sel_ind.setMinimumWidth(280)
        ind_col.addWidget(self.sel_ind)
        params_ly.addLayout(ind_col)

        sub_col = QVBoxLayout()
        sub_col.setSpacing(6)
        sub_col.addWidget(_lbl_hdr("SUBINDICADOR ALVO"))
        self.sel_sub = _cbx()
        self.sel_sub.setMinimumWidth(260)
        sub_col.addWidget(self.sel_sub)
        params_ly.addLayout(sub_col)

        ano_col = QVBoxLayout()
        ano_col.setSpacing(6)
        ano_col.addWidget(_lbl_hdr("ANO"))

        self.sel_ano = _cbx()
        self.sel_ano.setEditable(True)
        self.sel_ano.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.sel_ano.lineEdit().setValidator(
            QRegularExpressionValidator(QRegularExpression(r"\d{0,4}"), self.sel_ano)
        )
        self._refresh_year_selector(db.DEFAULT_YEAR)
        self.sel_ano.setFixedWidth(100)

        self.btn_new_year = QPushButton("+")
        self.btn_new_year.setFixedSize(38, 38)
        self.btn_new_year.setToolTip("Adicionar ou selecionar outro ano")
        self.btn_new_year.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new_year.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.btn_new_year.setStyleSheet(f"""
            QPushButton {{
                background: #FFFFFF; color: {PRETO_TITULO}; border: 1.5px solid #E2E8F0;
                border-radius: 6px;
            }}
            QPushButton:hover {{ background: #F8FAFC; border-color: {VERMELHO_ESC}; }}
        """)

        year_row = QHBoxLayout()
        year_row.setSpacing(6)
        year_row.addWidget(self.sel_ano)
        year_row.addWidget(self.btn_new_year)
        ano_col.addLayout(year_row)
        params_ly.addLayout(ano_col)
        
        hdr_ly.addLayout(params_ly)
        hdr_ly.addStretch()

        self.btn_load = QPushButton("Carregar Formulário")
        self.btn_load.setFixedHeight(38)
        self.btn_load.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_load.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.btn_load.setStyleSheet(f"""
            QPushButton {{
                background: {PRETO_TITULO}; color: #FFFFFF; border: none;
                border-radius: 6px; padding: 0 20px;
            }}
            QPushButton:hover {{ background: #334155; }}
        """)

        self.btn_delete_year = QPushButton("Excluir ano")
        self.btn_delete_year.setFixedHeight(38)
        self.btn_delete_year.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete_year.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.btn_delete_year.setStyleSheet(f"""
            QPushButton {{
                background: #FFFFFF; color: {VERMELHO_ESC}; border: 1px solid #FCA5A5;
                border-radius: 6px; padding: 0 16px; font-weight: bold;
            }}
            QPushButton:hover {{ background: #FEF2F2; border-color: {VERMELHO_ESC}; }}
        """)

        load_col = QVBoxLayout()
        load_col.setSpacing(8)
        load_col.addStretch()
        load_col.addWidget(self.btn_load)
        load_col.addWidget(self.btn_delete_year)
        hdr_ly.addLayout(load_col)
        
        main.addWidget(hdr)

        # ── Grade Mensal (Formulário) ──────────────────────────────────────
        self.grade_frame = QFrame()
        self.grade_frame.setStyleSheet(f"""
            QFrame {{
                background: {BRANCO}; border: 1px solid {CINZA_BORDA}; border-radius: 12px;
            }}
        """)
        self.grade_frame.setGraphicsEffect(shadow(12, (0, 4), (0, 0, 0, 10)))
        g_ly = QVBoxLayout(self.grade_frame)
        g_ly.setContentsMargins(32, 28, 32, 28)
        g_ly.setSpacing(24)

        # Cabeçalho da Grade (Título e KPIs)
        title_row = QHBoxLayout()
        title_row.setSpacing(16)
        self.grade_title = _lbl("Nenhum formulário carregado", bold=True, size=14, color=PRETO_TITULO)
        title_row.addWidget(self.grade_title, 1)

        # Mini KPIs úteis
        kpi_defs = [
            ("kpi_preenchidos", "MESES", "#3B82F6"),
            ("kpi_total", "ACUMULADO", "#10B981"),
            ("kpi_media", "MÉDIA", "#F59E0B")
        ]
        
        for attr, label, color in kpi_defs:
            kpi = QFrame()
            kpi.setStyleSheet(f"""
                QFrame {{
                    background: {color}0A; border: 1px solid {color}30; border-radius: 8px;
                }}
            """)
            kpi.setMinimumWidth(100)
            kpi_ly = QVBoxLayout(kpi)
            kpi_ly.setContentsMargins(12, 8, 12, 8)
            kpi_ly.setSpacing(0)
            
            val_lbl = _lbl("—", bold=True, size=15, color=color)
            val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_lbl = _lbl(label, size=7, color="#64748B")
            lbl_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_lbl.setStyleSheet("letter-spacing: 1px; font-weight: bold;")
            
            kpi_ly.addWidget(val_lbl)
            kpi_ly.addWidget(lbl_lbl)
            setattr(self, attr, val_lbl)
            title_row.addWidget(kpi)
            
        g_ly.addLayout(title_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background: {CINZA_BORDA}; border: none; max-height: 1px;")
        g_ly.addWidget(sep)

        # Grid 4 Trimestres x 3 Meses
        grid = QGridLayout()
        grid.setSpacing(16)
        
        # Alternância sutil de contraste para leitura
        TRIM_STYLES = [
            ("#F8FAFC", "#E2E8F0"), # T1
            ("#F1F5F9", "#CBD5E1"), # T2
            ("#F8FAFC", "#E2E8F0"), # T3
            ("#F1F5F9", "#CBD5E1")  # T4
        ]

        for ti, trim in enumerate(TRIM_LABELS):
            bg_c, b_c = TRIM_STYLES[ti]
            
            th = QLabel(trim)
            th.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            th.setStyleSheet(f"""
                color: {CINZA_SUAVE}; background: {bg_c};
                border: 1px solid {b_c}; border-radius: 6px;
                padding: 8px 0; letter-spacing: 1px;
            """)
            th.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(th, ti * 2, 0, 1, 3)
            
            for mi in range(3):
                mes_idx = ti * 3 + mi
                mes = MESES[mes_idx]
                
                cell = QFrame()
                cell.setStyleSheet(f"background: #FFFFFF; border: 1px solid {CINZA_BORDA}; border-radius: 6px;")
                c_ly = QVBoxLayout(cell)
                c_ly.setContentsMargins(8, 12, 8, 12)
                c_ly.setSpacing(8)
                
                mlbl = _lbl(mes[:3].upper(), bold=True, size=7, color="#64748B")
                mlbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                mlbl.setStyleSheet("letter-spacing: 1.5px;")
                
                inp = QLineEdit()
                inp.setFixedHeight(38)
                inp.setAlignment(Qt.AlignmentFlag.AlignCenter)
                inp.setPlaceholderText("—")
                inp.setStyleSheet(f"""
                    QLineEdit {{
                        background: #F9FAFB; border: 1px solid #E2E8F0; border-radius: 4px;
                        padding: 4px 8px; color: {PRETO_TITULO}; font-size: 11pt; font-weight: bold;
                    }}
                    QLineEdit:focus {{
                        border: 1.5px solid {VERMELHO_ESC}; background: #FFFFFF;
                        box-shadow: 0 0 0 3px rgba(185, 28, 28, 0.1);
                    }}
                """)
                self._inputs[mes] = inp
                
                c_ly.addWidget(mlbl)
                c_ly.addWidget(inp)
                grid.addWidget(cell, ti * 2 + 1, mi)
                
        g_ly.addLayout(grid)

        # Botões de Ação
        act = QHBoxLayout()
        act.setSpacing(16)
        
        self.lbl_info = _lbl("", bold=True, size=10, color=VERDE)
        act.addWidget(self.lbl_info)
        act.addStretch()
        
        self.btn_clear = QPushButton("Limpar Campos")
        self.btn_clear.setFixedHeight(38)
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {CINZA_SUAVE}; border: 1px solid {CINZA_BORDA};
                border-radius: 6px; padding: 0 20px; font-weight: bold; font-size: 9pt;
            }}
            QPushButton:hover {{ background: #F1F5F9; color: {PRETO_TITULO}; }}
        """)
        
        self.btn_save = QPushButton("Salvar Alterações")
        self.btn_save.setFixedHeight(38)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setStyleSheet(f"""
            QPushButton {{
                background: {VERMELHO_ESC}; color: #FFFFFF; border: none;
                border-radius: 6px; padding: 0 28px; font-weight: bold; font-size: 9pt;
            }}
            QPushButton:hover {{ background: {VERMELHO}; }}
        """)
        
        act.addWidget(self.btn_clear)
        act.addWidget(self.btn_save)
        g_ly.addSpacing(8)
        g_ly.addLayout(act)
        
        main.addWidget(self.grade_frame)

        # ── Vista: Por Horário ────────────────────────────────────────────
        self.horario_frame = QFrame()
        self.horario_frame.setStyleSheet(f"""
            QFrame {{
                background: {BRANCO}; border: 1px solid {CINZA_BORDA}; border-radius: 12px;
            }}
        """)
        self.horario_frame.setGraphicsEffect(shadow(12, (0, 4), (0, 0, 0, 10)))
        self.horario_frame.setVisible(False)
        h_ly = QVBoxLayout(self.horario_frame)
        h_ly.setContentsMargins(32, 28, 32, 28)
        h_ly.setSpacing(16)

        # Cabeçalho
        h_title_row = QHBoxLayout()
        self.h_title = _lbl("", bold=True, size=14, color=PRETO_TITULO)
        h_title_row.addWidget(self.h_title, 1)

        # Seletor de mês exclusivo da vista horária
        mes_col = QVBoxLayout()
        mes_col.setSpacing(4)
        mes_col.addWidget(_lbl("MÊS", bold=True, size=7, color="#475569"))
        self.sel_mes_h = _cbx()
        self.sel_mes_h.addItems(MESES)
        self.sel_mes_h.setFixedWidth(160)
        mes_col.addWidget(self.sel_mes_h)
        h_title_row.addLayout(mes_col)

        # Badge modo
        badge = QLabel("⏱  Por Horário")
        badge.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        badge.setStyleSheet(
            "background:#FFF7ED;border:1px solid #FED7AA;"
            "border-radius:6px;padding:4px 10px;color:#B45309;"
        )
        h_title_row.addWidget(badge)
        h_ly.addLayout(h_title_row)

        sep_h = QFrame()
        sep_h.setFrameShape(QFrame.Shape.HLine)
        sep_h.setStyleSheet(f"background:{CINZA_BORDA};border:none;max-height:1px;")
        h_ly.addWidget(sep_h)

        # Formulário de novo lançamento
        add_card = QFrame()
        add_card.setStyleSheet(
            "QFrame{background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;}"
        )
        add_form = QHBoxLayout(add_card)
        add_form.setContentsMargins(16, 14, 16, 14)
        add_form.setSpacing(12)

        def _mini_lbl(t):
            label = QLabel(t)
            label.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            label.setStyleSheet("color:#475569;background:transparent;border:none;letter-spacing:0.3px;")
            return label

        def _mini_inp(ph, w=None):
            e = QLineEdit()
            e.setFixedHeight(36)
            e.setPlaceholderText(ph)
            if w:
                e.setFixedWidth(w)
            e.setStyleSheet(f"""
                QLineEdit{{background:#FFFFFF;border:1.5px solid #E2E8F0;border-radius:6px;
                           padding:4px 10px;color:{PRETO_TITULO};font-size:10pt;}}
                QLineEdit:focus{{border:1.5px solid {VERMELHO_ESC};background:#FFFFFF;}}
            """)
            return e

        dia_col = QVBoxLayout()
        dia_col.setSpacing(4)
        dia_col.addWidget(_mini_lbl("DIA"))
        self.h_inp_dia = _mini_inp("1–31", w=70)
        self.h_inp_dia.setValidator(QIntValidator(1, 31))
        dia_col.addWidget(self.h_inp_dia)
        add_form.addLayout(dia_col)

        # ── Campo HH:MM ────────────────────────────────────────────
        hora_col = QVBoxLayout()
        hora_col.setSpacing(4)
        hora_col.addWidget(_mini_lbl("HORÁRIO (HH:MM)"))
        self.h_inp_hora = _mini_inp("08:00", w=110)
        self.h_inp_hora.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.h_inp_hora.setInputMask("99:99")  # digitar 1230 → 12:30 automaticamente
        # Sem validator separado — validação HH/MM feita ao salvar via regex
        hora_col.addWidget(self.h_inp_hora)
        add_form.addLayout(hora_col)

        # ── Combo Período ──────────────────────────────────────────
        per_col = QVBoxLayout()
        per_col.setSpacing(4)
        per_col.addWidget(_mini_lbl("PERÍODO"))
        self.h_sel_periodo = QComboBox()
        self.h_sel_periodo.setFixedHeight(36)
        self.h_sel_periodo.setFixedWidth(120)
        self.h_sel_periodo.addItems(["Manhã", "Tarde", "Noite"])
        self.h_sel_periodo.setStyleSheet(
            f"QComboBox{{background:#FFFFFF;border:1.5px solid #E2E8F0;border-radius:6px;"
            f"padding:4px 10px;color:{PRETO_TITULO};font-size:10pt;}}"
            f"{COMBO_DROPDOWN_CSS}"
            f"QComboBox:focus{{border:1.5px solid {VERMELHO_ESC};}}"
        )
        per_col.addWidget(self.h_sel_periodo)
        add_form.addLayout(per_col)

        val_col = QVBoxLayout()
        val_col.setSpacing(4)
        val_col.addWidget(_mini_lbl("VALOR"))
        self.h_inp_val = _mini_inp("0", w=100)
        self.h_inp_val.setValidator(QDoubleValidator())
        val_col.addWidget(self.h_inp_val)
        add_form.addLayout(val_col)

        obs_col = QVBoxLayout()
        obs_col.setSpacing(4)
        obs_col.addWidget(_mini_lbl("OBS. (opcional)"))
        self.h_inp_obs = _mini_inp("", w=150)
        obs_col.addWidget(self.h_inp_obs)
        add_form.addLayout(obs_col)

        self.btn_h_add = QPushButton("+  Adicionar")
        self.btn_h_add.setFixedHeight(36)
        self.btn_h_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_h_add.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.btn_h_add.setStyleSheet(f"""
            QPushButton{{background:{VERMELHO_ESC};color:#fff;border:none;
                        border-radius:6px;padding:0 20px;}}
            QPushButton:hover{{background:{VERMELHO};}}
        """)
        add_col = QVBoxLayout()
        add_col.setSpacing(4)
        add_col.addWidget(_mini_lbl(" "))
        add_col.addWidget(self.btn_h_add)
        add_form.addLayout(add_col)
        h_ly.addWidget(add_card)

        # Tabela de lançamentos existentes — 6 colunas (acões agrupadas)
        self.h_tbl = QTableWidget(0, 6)
        self.h_tbl.setHorizontalHeaderLabels(["Dia", "Tipo", "Referência", "Valor", "Obs.", "Ações"])
        self.h_tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.h_tbl.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.h_tbl.verticalHeader().setVisible(False)
        self.h_tbl.setShowGrid(False)
        self.h_tbl.setAlternatingRowColors(False)
        self.h_tbl.setStyleSheet(f"""
            QTableWidget{{
                border:none;font-size:10pt;font-family:'Segoe UI';
                background:{BRANCO};border-radius:8px;outline:none;
            }}
            QTableWidget::item{{
                padding:0px 12px;color:#1E293B;
                border-bottom:1px solid #F1F5F9;
            }}
            QTableWidget::item:hover{{background:#F8FAFC;}}
            QHeaderView::section{{
                background:#F8FAFC;color:#64748B;font-weight:bold;
                font-size:8pt;font-family:'Segoe UI';
                padding:12px 12px;border:none;
                border-bottom:2px solid #E2E8F0;
                letter-spacing:1px;
            }}
        """)
        hdr_h = self.h_tbl.horizontalHeader()
        hdr_h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr_h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr_h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr_h.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr_h.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        hdr_h.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.h_tbl.setColumnWidth(5, 90)
        self.h_tbl.verticalHeader().setDefaultSectionSize(44)
        h_ly.addWidget(self.h_tbl)

        # Rodapé: totais + consolidar
        h_foot = QHBoxLayout()
        self.h_lbl_total = _lbl("", bold=True, size=10, color=PRETO_TITULO)
        h_foot.addWidget(self.h_lbl_total)
        h_foot.addStretch()
        self.h_lbl_info = _lbl("", bold=True, size=9, color=VERDE)
        h_foot.addWidget(self.h_lbl_info)
        self.btn_h_consolidar = QPushButton("↻  Consolidar Resultado do Mês")
        self.btn_h_consolidar.setFixedHeight(36)
        self.btn_h_consolidar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_h_consolidar.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.btn_h_consolidar.setStyleSheet("""
            QPushButton{background:#1E293B;color:#fff;border:none;
                        border-radius:6px;padding:0 20px;}
            QPushButton:hover{background:#334155;}
        """)
        h_foot.addWidget(self.btn_h_consolidar)
        h_ly.addLayout(h_foot)

        main.addWidget(self.horario_frame)

        # ── Tabela de Conferência (Compacta e Limpa) ─────────────────────────
        sv = QFrame()
        sv.setStyleSheet(f"""
            QFrame {{
                background: {BRANCO}; border: 1px solid {CINZA_BORDA}; border-radius: 12px;
            }}
        """)
        sv.setGraphicsEffect(shadow(12, (0, 4), (0, 0, 0, 10)))
        sv_ly = QVBoxLayout(sv)
        sv_ly.setContentsMargins(24, 20, 24, 20)
        sv_ly.setSpacing(12)

        sh_row = QHBoxLayout()
        sh_row.addWidget(_lbl("CONFERÊNCIA RÁPIDA (VALORES SALVOS)", bold=True, size=8, color="#64748B"))
        sh_row.addStretch()
        sv_ly.addLayout(sh_row)
        
        sep_sv = QFrame()
        sep_sv.setFrameShape(QFrame.Shape.HLine)
        sep_sv.setStyleSheet(f"background: {CINZA_BORDA}; border: none; max-height: 1px;")
        sv_ly.addWidget(sep_sv)

        self.saved_grid = QGridLayout()
        self.saved_grid.setSpacing(4)
        sv_ly.addLayout(self.saved_grid)
        
        main.addWidget(sv)
        main.addStretch()

        # Signals
        self.btn_load.clicked.connect(self._load_historico)
        self.btn_save.clicked.connect(self._save_historico)
        self.btn_clear.clicked.connect(self._clear_inputs)
        self.btn_new_year.clicked.connect(self._select_new_year)
        self.btn_delete_year.clicked.connect(self._delete_year)
        self.sel_ind.currentIndexChanged.connect(self._on_indicador_changed)
        self.sel_sub.currentIndexChanged.connect(self._on_subindicador_changed)
        self.sel_ano.currentIndexChanged.connect(self._load_historico)
        self.sel_ano.lineEdit().editingFinished.connect(self._load_historico)
        self.btn_h_add.clicked.connect(self._add_lancamento_horario)
        self.btn_h_consolidar.clicked.connect(self._consolidar_mes)
        self.sel_mes_h.currentIndexChanged.connect(
            lambda: self._rebuild_horario_table(
                getattr(self, "_h_sub_id", None),
                getattr(self, "_h_ano", None)
            ) if getattr(self, "_h_sub_id", None) else None
        )

    # ── Lógica ──────────────────────────────────────────────────────────────
    @staticmethod
    def _parse_valid_year(text: str) -> int | None:
        return db.parse_valid_year(text)

    def _refresh_year_selector(self, preferred_year: int | None = None):
        current_text = self.sel_ano.currentText().strip()
        years = {db.DEFAULT_YEAR}
        sub_id = self._current_sub_id()
        if sub_id:
            years.update(db.get_anos_historico_subindicador(sub_id))
            years.update(db.get_anos_horario(sub_id))
        if preferred_year is not None:
            years.add(preferred_year)

        years = sorted(years, reverse=True)
        year_texts = [str(year) for year in years]
        selected_text = str(preferred_year) if preferred_year is not None else current_text

        previous_state = self.sel_ano.blockSignals(True)
        self.sel_ano.clear()
        self.sel_ano.addItems(year_texts)
        if selected_text in year_texts:
            self.sel_ano.setCurrentText(selected_text)
        else:
            self.sel_ano.setCurrentText(str(db.DEFAULT_YEAR))
        self.sel_ano.blockSignals(previous_state)

    def _populate_selector(self):
        self.sel_ind.blockSignals(True)
        self.sel_ind.clear()
        for i in db.get_indicadores_ativos():
            self.sel_ind.addItem(f"{i['codigo_indicador']}  —  {i['nome_indicador']}", i['codigo_indicador'])
        self.sel_ind.blockSignals(False)
        self._on_indicador_changed()

    def _on_indicador_changed(self):
        cod = self.sel_ind.currentData()
        previous_state = self.sel_sub.blockSignals(True)
        self.sel_sub.clear()
        if cod:
            for s in db.get_subindicadores(cod):
                self.sel_sub.addItem(s['nome_subindicador'], s['id'])
        self.sel_sub.blockSignals(previous_state)
        self._on_subindicador_changed()

    def _on_subindicador_changed(self):
        self._refresh_year_selector()
        self._load_historico()

    def _current_sub_id(self): 
        return self.sel_sub.currentData()
        
    def _current_ano(self):
        return self._parse_valid_year(self.sel_ano.currentText())

    def _current_ano_raw(self):
        value = self.sel_ano.currentText().strip()
        if value.isdecimal():
            return int(value)
        return None

    def _select_new_year(self):
        current_year = self._current_ano() or db.DEFAULT_YEAR
        dialog = QInputDialog(self)
        dialog.setWindowTitle("Selecionar ano")
        dialog.setLabelText("Informe o ano para lançamento:")
        dialog.setInputMode(QInputDialog.InputMode.IntInput)
        dialog.setIntRange(db.YEAR_MIN, db.YEAR_MAX)
        dialog.setIntValue(current_year)
        dialog.setOkButtonText("Selecionar")
        dialog.setCancelButtonText("Cancelar")

        if not dialog.exec():
            return

        selected_year = dialog.intValue()
        self._refresh_year_selector(selected_year)
        self._load_historico()

    def _load_historico(self):
        sub_id = self._current_sub_id()
        ano    = self._current_ano()
        if not sub_id:
            return
        if ano is None:
            if self.sel_ano.currentText().strip():
                self._set_historico_status(
                    f"⚠️ Ano inválido. Use 4 dígitos entre {db.YEAR_MIN} e {db.YEAR_MAX}.",
                    LARANJA,
                )
            return

        sub  = db.get_subindicador(sub_id)
        nome = sub['nome_subindicador'] if sub else f"ID:{sub_id}"
        modo = (sub or {}).get("modo_lancamento", "mensal")

        if modo == "por_horario":
            # Oculta grade mensal, exibe vista horário
            self.grade_frame.setVisible(False)
            self.horario_frame.setVisible(True)
            self.h_title.setText(f"{nome}  |  {ano}")
            self._load_horario(sub_id, ano)
        else:
            # Fluxo mensal original — sem alteração
            self.grade_frame.setVisible(True)
            self.horario_frame.setVisible(False)
            self.grade_title.setText(f"{nome}  |  {ano}")
            self._load_mensal(sub_id, ano)

    def _load_mensal(self, sub_id: int, ano: int):
        """Preenche a grade mensal original (fluxo inalterado)."""
        hist  = db.get_historico_subindicador(sub_id, [ano])
        dados = hist.get(ano, {})
        vals  = []
        for mes in MESES:
            val = dados.get(mes)
            inp = self._inputs[mes]
            txt = str(int(val)) if isinstance(val, float) and val == int(val) else str(val) if val is not None else ""
            inp.setText(txt)
            if val is not None:
                inp.setStyleSheet(f"""
                    QLineEdit{{
                        background:#F0FDF4;border:1px solid #86EFAC;border-radius:4px;
                        padding:4px 8px;color:#065F46;font-size:11pt;font-weight:bold;
                    }}
                    QLineEdit:focus{{border:1.5px solid {VERMELHO_ESC};background:#FFFFFF;}}
                """)
                vals.append(val)
            else:
                inp.setStyleSheet(f"""
                    QLineEdit{{
                        background:#F9FAFB;border:1px solid #E2E8F0;border-radius:4px;
                        padding:4px 8px;color:{PRETO_TITULO};font-size:11pt;font-weight:bold;
                    }}
                    QLineEdit:focus{{border:1.5px solid {VERMELHO_ESC};background:#FFFFFF;}}
                """)
        self.kpi_preenchidos.setText(f"{len(vals)}/12")
        self.kpi_total.setText(f"{sum(vals):g}" if vals else "—")
        med = sum(vals) / len(vals) if vals else None
        self.kpi_media.setText(f"{med:.1f}" if med is not None else "—")
        self.lbl_info.setText("")
        self._rebuild_saved_table(sub_id)

    def _load_horario(self, sub_id: int, ano: int):
        """Carrega o painel horário para o subindicador/ano selecionado."""
        self._h_sub_id = sub_id
        self._h_ano    = ano
        self._rebuild_horario_table(sub_id, ano)
        self._rebuild_saved_table(sub_id)  # Conferência Rápida sempre atualizada
        self.h_lbl_info.setText("")

    def _get_h_mes(self) -> str:
        """Retorna o mês selecionado para o painel horário.
        Usa o QComboBox de mês se existir, caso contrário retorna Janeiro."""
        if hasattr(self, "sel_mes_h"):
            return self.sel_mes_h.currentText()
        return "Janeiro"


    def _rebuild_horario_table(self, sub_id: int, ano: int):
        """Reconstrói a tabela de lançamentos horários do mês selecionado."""
        import re as _re
        from PySide6.QtGui import QColor
        if not sub_id or not ano:
            return
        _re_hora_pat = _re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
        mes = self._get_h_mes()
        try:
            dados = db.get_lancamentos_horario(sub_id, ano, mes)
        except Exception as e:
            print(f"[Hist] get_lancamentos_horario: {e}")
            return
        self.h_tbl.setRowCount(0)
        total = 0.0
        count = 0
        for dia in sorted(dados.keys()):
            for faixa, rec in sorted(dados[dia].items()):
                # Suporta formato novo {valor, obs} e legado escalar
                if isinstance(rec, dict):
                    val = rec.get("valor")
                    obs = rec.get("obs", "")
                else:
                    val = rec
                    obs = ""
                r = self.h_tbl.rowCount()
                self.h_tbl.insertRow(r)
                self.h_tbl.setItem(r, 0, QTableWidgetItem(str(dia)))
                is_hora = bool(_re_hora_pat.match(faixa.strip()))
                tipo_txt = "⏰ Horário" if is_hora else "☀️ Período"
                tipo_cor = "#1E40AF"    if is_hora else "#92400E"
                it_tipo = QTableWidgetItem(tipo_txt)
                it_tipo.setForeground(QColor(tipo_cor))
                it_tipo.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                self.h_tbl.setItem(r, 1, it_tipo)
                self.h_tbl.setItem(r, 2, QTableWidgetItem(faixa))
                v_txt = str(int(val)) if isinstance(val, float) and val == int(val) else str(val) if val is not None else ""
                self.h_tbl.setItem(r, 3, QTableWidgetItem(v_txt))
                self.h_tbl.setItem(r, 4, QTableWidgetItem(obs))
                # Container de ações: editar + excluir num único widget
                act_w = QWidget()
                act_w.setStyleSheet("background:transparent;")
                act_lay = QHBoxLayout(act_w)
                act_lay.setContentsMargins(2, 2, 2, 2)
                act_lay.setSpacing(4)

                btn_edit = QPushButton("E")
                btn_edit.setFixedSize(36, 28)
                btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_edit.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                btn_edit.setToolTip("Editar lançamento")
                btn_edit.setStyleSheet(
                    "QPushButton{background:#EFF6FF;color:#1D4ED8;"
                    "border:1px solid #93C5FD;border-radius:4px;}"
                    "QPushButton:hover{background:#DBEAFE;border-color:#3B82F6;}"
                )
                btn_edit.clicked.connect(lambda _, d=dia, f=faixa, v=val, o=obs, ih=is_hora:
                    self._editar_lancamento(d, f, v, o, ih))

                btn_del = QPushButton("X")
                btn_del.setFixedSize(36, 28)
                btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_del.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                btn_del.setToolTip("Excluir lançamento")
                btn_del.setStyleSheet(
                    f"QPushButton{{background:#FFF7ED;color:{LARANJA};"
                    f"border:1px solid #FDBA74;border-radius:4px;}}"
                    f"QPushButton:hover{{background:#FFEDD5;color:{VERMELHO_ESC};border-color:#FB923C;}}"
                )
                btn_del.clicked.connect(lambda _, s=sub_id, a=ano, m=mes, d=dia, p=faixa:
                    self._delete_lancamento(s, a, m, d, p))

                act_lay.addWidget(btn_edit)
                act_lay.addWidget(btn_del)
                self.h_tbl.setCellWidget(r, 5, act_w)
                if val is not None:
                    total += val
                    count += 1
        if count > 0:
            self.h_lbl_total.setText(f"Total no mês: {total:g}  |  {count} lançamento{'s' if count > 1 else ''}")
        else:
            self.h_lbl_total.setText("Nenhum lançamento registrado neste mês.")
        # Força largura da coluna de ações após carregar dados
        self.h_tbl.setColumnWidth(5, 90)

    def _editar_lancamento(self, dia: int, faixa: str, val, obs: str, is_hora: bool):
        """Preenche o formulário com os dados de um lançamento existente para edição."""
        self.h_inp_dia.setText(str(dia))
        if is_hora:
            # Limpa a máscara e coloca o valor
            self.h_inp_hora.clear()
            self.h_inp_hora.setText(faixa)
        else:
            self.h_inp_hora.clear()
            idx = self.h_sel_periodo.findText(faixa)
            if idx >= 0:
                self.h_sel_periodo.setCurrentIndex(idx)
        v_txt = str(int(val)) if isinstance(val, float) and val == int(val) else str(val) if val is not None else ""
        self.h_inp_val.setText(v_txt)
        self.h_inp_obs.setText(obs)
        self.h_lbl_info.setText("✏ Editando lançamento — altere os campos e clique em + Adicionar para salvar.")
        self.h_lbl_info.setStyleSheet("color:#3B82F6;background:transparent;border:none;font-weight:bold;")
        self.h_inp_dia.setFocus()

    def _add_lancamento_horario(self):
        import re as _re
        sub_id = getattr(self, "_h_sub_id", self._current_sub_id())
        ano    = getattr(self, "_h_ano",    self._current_ano())
        mes    = self._get_h_mes()
        if not sub_id:
            return
        if ano is None:
            self._set_historico_status(
                f"⚠️ Ano inválido. Use 4 dígitos entre {db.YEAR_MIN} e {db.YEAR_MAX}.",
                LARANJA,
            )
            return
        dia_txt = self.h_inp_dia.text().strip()
        val_txt = self.h_inp_val.text().strip().replace(",", ".")

        # Prioridade: HH:MM se preenchido e válido, senão Período
        hora_txt = self.h_inp_hora.text().strip()
        # inputMask deixa "__:__" quando vazio — tratar como vazio
        if hora_txt in ("__:__", "  :  ", ":", "_:_", ""):
            hora_txt = ""
        if hora_txt:
            if not _re.match(r"^(?:[01]\d|2[0-3]):[0-5]\d$", hora_txt):
                self.h_lbl_info.setText("⚠️ Horário inválido. Use HH:MM (ex: 08:30, 13:00).")
                self.h_lbl_info.setStyleSheet(f"color:{LARANJA};background:transparent;border:none;font-weight:bold;")
                return
            faixa = hora_txt
        else:
            faixa = self.h_sel_periodo.currentText()  # Manhã | Tarde | Noite

        if not dia_txt or not val_txt:
            self.h_lbl_info.setText("⚠️ Preencha Dia e Valor.")
            self.h_lbl_info.setStyleSheet(f"color:{LARANJA};background:transparent;border:none;font-weight:bold;")
            return
        try:
            dia = int(dia_txt)
            val = float(val_txt)
        except ValueError:
            self.h_lbl_info.setText("⚠️ Dia deve ser inteiro e Valor deve ser número.")
            self.h_lbl_info.setStyleSheet(f"color:{LARANJA};background:transparent;border:none;font-weight:bold;")
            return
        obs = self.h_inp_obs.text().strip()
        ok  = db.upsert_lancamento_horario(sub_id, ano, mes, dia, faixa, val, obs)
        if ok:
            self.h_inp_dia.clear()
            self.h_inp_hora.clear()
            self.h_inp_val.clear()
            self.h_inp_obs.clear()
            self.h_lbl_info.setText("✅ Lançamento adicionado!")
            self.h_lbl_info.setStyleSheet(f"color:{VERDE};background:transparent;border:none;font-weight:bold;")
            self._refresh_year_selector(ano)
            self._rebuild_horario_table(sub_id, ano)
            self._rebuild_saved_table(sub_id)  # Conferência Rápida atualizada
        else:
            self.h_lbl_info.setText("⚠️ Erro ao salvar.")
            self.h_lbl_info.setStyleSheet(f"color:{VERMELHO};background:transparent;border:none;font-weight:bold;")

    def _delete_lancamento(self, sub_id, ano, mes, dia, per):
        ok = db.delete_lancamento_horario(sub_id, ano, mes, dia, per)
        if ok:
            self._rebuild_horario_table(sub_id, ano)
            self._rebuild_saved_table(sub_id)  # Conferência Rápida atualizada
            self.h_lbl_info.setText("✅ Lançamento removido.")
            self.h_lbl_info.setStyleSheet(f"color:{VERDE};background:transparent;border:none;font-weight:bold;")

    def _consolidar_mes(self):
        sub_id = getattr(self, "_h_sub_id", self._current_sub_id())
        ano    = getattr(self, "_h_ano",    self._current_ano())
        mes    = self._get_h_mes()
        if not sub_id:
            return
        if ano is None:
            self._set_historico_status(
                f"⚠️ Ano inválido. Use 4 dígitos entre {db.YEAR_MIN} e {db.YEAR_MAX}.",
                LARANJA,
            )
            return
        total = db.consolidar_mensal_horario(sub_id, ano, mes)
        if total is None:
            self.h_lbl_info.setText("⚠️ Nenhum lançamento para consolidar.")
            self.h_lbl_info.setStyleSheet(f"color:{LARANJA};background:transparent;border:none;font-weight:bold;")
            return
        ok = db.upsert_historico(sub_id, ano, mes, total)
        if ok:
            self.h_lbl_info.setText(f"✅ Resultado do mês consolidado: {total:g}")
            self.h_lbl_info.setStyleSheet(f"color:{VERDE};background:transparent;border:none;font-weight:bold;")
            self._refresh_year_selector(ano)
            self._rebuild_saved_table(sub_id)  # Atualiza Conferência Rápida imediatamente
        else:
            self.h_lbl_info.setText("⚠️ Erro ao consolidar.")
            self.h_lbl_info.setStyleSheet(f"color:{VERMELHO};background:transparent;border:none;font-weight:bold;")


    def _rebuild_saved_table(self, sub_id):
        while self.saved_grid.count():
            it = self.saved_grid.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

        # Detecta o modo e monta hist {ano: {mes: valor}} adequadamente
        modo = db.get_modo_lancamento_sub(sub_id)

        if modo == "por_horario":
            # Lê diretamente de lancamentos_horario — sem precisar consolidar
            hist = {}
            for ano in db.get_anos_horario(sub_id):
                for mes in MESES:
                    val = db.consolidar_mensal_horario(sub_id, ano, mes)
                    if val is not None:
                        hist.setdefault(ano, {})[mes] = val
        else:
            # Caminho original: dados_historicos
            hist = db.get_historico_subindicador(sub_id)

        if not hist:
            lbl = _lbl("Nenhum dado lançado.", color="#9CA3AF", size=8)
            self.saved_grid.addWidget(lbl, 0, 0)
            return

        def _h(txt, col):
            label = _lbl(txt.upper(), bold=True, size=7, color="#64748B")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("letter-spacing: 1px; padding: 2px;")
            self.saved_grid.addWidget(label, 0, col)

        _h("Ano", 0)
        for ci, m in enumerate(MESES, 1):
            _h(m[:3], ci)

        for ri, ano in enumerate(sorted(hist.keys()), 1):
            la = _lbl(str(ano), bold=True, size=8, color=PRETO_TITULO)
            la.setAlignment(Qt.AlignmentFlag.AlignCenter)
            la.setStyleSheet("background: #F8FAFC; border-radius: 4px; padding: 4px;")
            self.saved_grid.addWidget(la, ri, 0)

            for ci, mes in enumerate(MESES, 1):
                val = hist[ano].get(mes)
                txt = str(int(val)) if isinstance(val, float) and val == int(val) else str(val) if val is not None else "—"
                cor = PRETO_TITULO if val is not None else "#CBD5E1"

                cell = _lbl(txt, size=8, color=cor)
                cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
                cell.setStyleSheet("padding: 4px;")
                self.saved_grid.addWidget(cell, ri, ci)


    def _set_historico_status(self, text: str, color: str):
        self._st(text, color)
        self.h_lbl_info.setText(text)
        self.h_lbl_info.setStyleSheet(
            f"color:{color};background:transparent;border:none;font-weight:bold;"
        )

    def _delete_year(self):
        sub_id = self._current_sub_id()
        ano = self._current_ano_raw()

        if not sub_id:
            self._set_historico_status("⚠️ Selecione indicador e subindicador.", LARANJA)
            return
        if ano is None:
            self._set_historico_status("⚠️ Selecione um ano numérico para excluir.", LARANJA)
            return

        sub = db.get_subindicador(sub_id)
        nome = sub["nome_subindicador"] if sub else f"ID:{sub_id}"
        confirmar = QMessageBox(self)
        confirmar.setIcon(QMessageBox.Icon.Warning)
        confirmar.setWindowTitle("Excluir histórico do ano")
        confirmar.setText(f"Excluir todo o histórico de {ano}?")
        confirmar.setInformativeText(
            f"Subindicador: {nome}\n\n"
            "Esta ação remove os valores mensais salvos e os lançamentos por horário desse ano."
        )
        btn_cancelar = confirmar.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        btn_excluir = confirmar.addButton("Excluir ano", QMessageBox.ButtonRole.DestructiveRole)
        confirmar.setDefaultButton(btn_excluir)
        confirmar.setEscapeButton(btn_cancelar)
        confirmar.exec()

        if confirmar.clickedButton() != btn_excluir:
            return

        deleted = db.delete_historico_ano(sub_id, ano)
        self._refresh_year_selector(db.DEFAULT_YEAR)
        self._load_historico()

        if deleted:
            self._set_historico_status(f"✅ Ano {ano} excluído ({deleted} registro(s)).", VERDE)
        else:
            self._set_historico_status(f"⚠️ Não havia registros salvos para {ano}.", LARANJA)


    def _save_historico(self):
        sub_id = self._current_sub_id()
        ano = self._current_ano()
        
        if not sub_id:
            self._st("⚠️ Selecione indicador e subindicador.", LARANJA)
            return
        if ano is None:
            self._set_historico_status(
                f"⚠️ Ano inválido. Use 4 dígitos entre {db.YEAR_MIN} e {db.YEAR_MAX}.",
                LARANJA,
            )
            return
            
        saved = errors = 0
        for mes in MESES:
            txt = self._inputs[mes].text().strip().replace(",", ".")
            if txt in ("", "—", "–", "-"):
                db.delete_historico_mes(sub_id, ano, mes)
                continue
            try:
                # O banco nativo tratará o dado, preservando 0 como 0 real
                if db.upsert_historico(sub_id, ano, mes, float(txt)):
                    saved += 1
                else:
                    errors += 1
            except ValueError:
                errors += 1
        
        if errors:
            self._st(f"⚠️ {errors} valores inválidos (use apenas números).", LARANJA)
        else:
            self._st("✅ Histórico salvo com sucesso!", VERDE)
            self._refresh_year_selector(ano)
            self._load_historico()

    def _clear_inputs(self):
        for inp in self._inputs.values():
            inp.clear()
            inp.setStyleSheet(f"""
                QLineEdit {{
                    background: #F9FAFB; border: 1px solid #E2E8F0; border-radius: 4px;
                    padding: 4px 8px; color: {PRETO_TITULO}; font-size: 11pt; font-weight: bold;
                }}
                QLineEdit:focus {{ border: 1.5px solid {VERMELHO_ESC}; background: #FFFFFF; }}
            """)
        self.lbl_info.setText("")
        for attr in ["kpi_preenchidos", "kpi_total", "kpi_media"]:
            getattr(self, attr).setText("—")

    def _st(self, msg, cor):
        self.lbl_info.setText(msg)
        self.lbl_info.setStyleSheet(f"color: {cor}; background: transparent; border: none; font-weight: bold;")
