"""
panel_base_dados.py - Tela Base de Dados com abas para Indicadores e Subindicadores.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QTextEdit, QCheckBox,
    QComboBox, QLineEdit, QMessageBox, QSplitter, QTabWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

import database as db
from panel_historico import HistoricoPanel
from panel_analise_critica import AnaliseCriticaPanel
from panel_config import ConfigPanel
from styles import (
    VERMELHO, VERMELHO_ESC, BRANCO, CINZA_BG, CINZA_BORDA,
    CINZA_SUAVE, PRETO_TITULO, VERDE, LARANJA
)
from widgets import shadow


def _btn(txt, primary=False, danger=False):
    b = QPushButton(txt); b.setFixedHeight(36)
    b.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if primary:
        b.setStyleSheet(f"QPushButton{{background:{VERMELHO_ESC};color:{BRANCO};border:none;border-radius:6px;padding:0 20px;}}QPushButton:hover{{background:{VERMELHO};}}")
    elif danger:
        b.setStyleSheet(f"QPushButton{{background:transparent;color:{VERMELHO_ESC};border:1px solid {VERMELHO_ESC};border-radius:6px;padding:0 20px;}}QPushButton:hover{{background:#FFEBEE;}}")
    else:
        b.setStyleSheet(f"QPushButton{{background:#F6F8FA;color:#24292F;border:1px solid #D0D7DE;border-radius:6px;padding:0 20px;}}QPushButton:hover{{background:#F3F4F6;}}")
    return b

class _FieldRow(QWidget):
    def __init__(self, label, widget, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;border:none;")
        ly = QVBoxLayout(self); ly.setContentsMargins(0,0,0,0); ly.setSpacing(3)
        if label:
            lbl = QLabel(label)
            lbl.setFont(QFont("Segoe UI", 8))
            lbl.setStyleSheet(f"color:{PRETO_TITULO};background:transparent;border:none;")
            ly.addWidget(lbl)
        ly.addWidget(widget)

def _section_lbl(txt):
    l = QLabel(txt)
    l.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
    l.setStyleSheet(f"color:{PRETO_TITULO};background:transparent;border:none;letter-spacing:0.5px;")
    return l


class BaseDadosPanel(QWidget):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self._build_ui()
        self._load_indicadores_table()
        self._load_subindicadores_combos()
        self._load_subindicadores_table()

    # ── UI BUILDER ────────────────────────────────────────────────────────
    def _build_ui(self):
        self.setStyleSheet("background: #EEF2F7;")
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        # Tab bar header strip
        tab_bar_strip = QFrame()
        tab_bar_strip.setStyleSheet("background:#FFFFFF; border-bottom:2px solid #E2E8F0;")
        tab_bar_layout = QVBoxLayout(tab_bar_strip); tab_bar_layout.setContentsMargins(0,0,0,0); tab_bar_layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; background: transparent; }}
            QTabBar {{ background: #FFFFFF; border: none; }}
            QTabBar::tab {{
                background: transparent;
                border: none;
                border-bottom: 3px solid transparent;
                padding: 18px 32px;
                color: #94A3B8;
                font-family: 'Segoe UI';
                font-size: 13px;
                font-weight: bold;
                letter-spacing: 0.2px;
                margin-right: 2px;
            }}
            QTabBar::tab:hover {{
                color: #334155;
                background: #F8FAFC;
                border-bottom: 3px solid #CBD5E1;
            }}
            QTabBar::tab:selected {{
                color: {VERMELHO_ESC};
                border-bottom: 3px solid {VERMELHO_ESC};
                background: #FFFFFF;
            }}
        """)
        tab_bar_layout.addWidget(self.tabs)
        root.addWidget(tab_bar_strip)

        self.tab_ind = QWidget()
        self.tab_sub = QWidget()
        self.tab_hist = HistoricoPanel(self.data)
        self.tab_analise = AnaliseCriticaPanel(self.data)
        self.tab_config = ConfigPanel(self.data)

        self.tabs.addTab(self.tab_ind, "Indicadores Principais")
        self.tabs.addTab(self.tab_sub, "Subindicadores")
        self.tabs.addTab(self.tab_hist, "Histórico Mensal")
        self.tabs.addTab(self.tab_analise, "Análise Crítica")
        self.tabs.addTab(self.tab_config, "Configurações")

        self._build_tab_indicadores()
        self._build_tab_subindicadores()

        # Connect tab change to refresh contents
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, index):
        if index == 1: # Subindicadores
            self._load_subindicadores_combos()
            self._load_subindicadores_table()
        elif index == 2: # Histórico
            if hasattr(self.tab_hist, '_populate_selector'):
                self.tab_hist._populate_selector()
        elif index == 3: # Análise
            if hasattr(self.tab_analise, '_populate_selector'):
                self.tab_analise._populate_selector()

    def _build_tab_indicadores(self):
        self.tab_ind.setStyleSheet("background:transparent;")
        ly = QVBoxLayout(self.tab_ind); ly.setContentsMargins(0,0,0,0); ly.setSpacing(0)

        # ── Cabeçalho Hero ──────────────────────────────────────────────────
        header = QFrame()
        header.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #FFFFFF, stop:1 #F8FAFC);"
            "border-bottom: 1px solid #DDE3EC;"
        )
        h_ly = QHBoxLayout(header); h_ly.setContentsMargins(40,28,40,28); h_ly.setSpacing(24)

        # Accent bar
        accent = QFrame(); accent.setFixedWidth(4); accent.setFixedHeight(44)
        accent.setStyleSheet(f"background:{VERMELHO_ESC};border-radius:2px;border:none;")
        h_ly.addWidget(accent)

        ttl_col = QVBoxLayout(); ttl_col.setSpacing(5)
        t1 = QLabel("Catálogo de Indicadores Principais")
        t1.setFont(QFont("Segoe UI", 17, QFont.Weight.Bold))
        t1.setStyleSheet("color:#0F172A; background:transparent; border:none;")
        t2 = QLabel("Gerencie a estrutura central do seu book de performance.")
        t2.setFont(QFont("Segoe UI", 10))
        t2.setStyleSheet("color:#64748B; background:transparent; border:none;")
        ttl_col.addWidget(t1); ttl_col.addWidget(t2)
        h_ly.addLayout(ttl_col, 1)

        self.btn_new_ind = QPushButton("＋  Novo Indicador")
        self.btn_new_ind.setFixedHeight(44); self.btn_new_ind.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new_ind.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.btn_new_ind.setStyleSheet(
            f"QPushButton{{background:{VERMELHO_ESC};color:#fff;border:none;"
            f"border-radius:8px;padding:0 28px;letter-spacing:0.3px;}}"
            f"QPushButton:hover{{background:{VERMELHO};box-shadow:0 4px 12px rgba(185,28,28,0.35);}}"
            f"QPushButton:pressed{{background:#991B1B;}}"
        )
        h_ly.addWidget(self.btn_new_ind)
        ly.addWidget(header)

        # ── Área de Conteúdo (Splitter) ──────────────────────────────────
        content_wrap = QWidget(); content_wrap.setStyleSheet("background:transparent;")
        cw_ly = QVBoxLayout(content_wrap); cw_ly.setContentsMargins(32,32,32,32); cw_ly.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle{background:transparent;width:24px;}")
        splitter.setHandleWidth(24)

        # Tabela
        tbl_frame = QFrame()
        tbl_frame.setStyleSheet(f"QFrame{{background:{BRANCO};border:1px solid #DDE3EC;border-radius:12px;}}")
        tbl_frame.setGraphicsEffect(shadow(16,(0,4),(0,0,0,12)))
        tf_ly = QVBoxLayout(tbl_frame); tf_ly.setContentsMargins(0,0,0,0); tf_ly.setSpacing(0)

        self.tbl_ind = QTableWidget(0, 6)
        self.tbl_ind.setHorizontalHeaderLabels(["Código","Nome do Indicador","Tipo","Periodicidade","Meta","Ativo"])
        self.tbl_ind.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_ind.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_ind.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_ind.verticalHeader().setVisible(False)
        self.tbl_ind.setAlternatingRowColors(False)
        self.tbl_ind.setShowGrid(False)
        self.tbl_ind.setStyleSheet(f"""
            QTableWidget {{
                border: none;
                font-size: 10pt;
                font-family: 'Segoe UI';
                background: {BRANCO};
                border-radius: 12px;
                outline: none;
            }}
            QTableWidget::item {{
                padding: 0px 18px;
                color: #1E293B;
                border-bottom: 1px solid #F1F5F9;
            }}
            QTableWidget::item:hover {{
                background: #F8FAFC;
            }}
            QTableWidget::item:selected {{
                background: #FEF2F2;
                color: {VERMELHO_ESC};
                border-left: 3px solid {VERMELHO_ESC};
                font-weight: bold;
            }}
            QHeaderView::section {{
                background: #F8FAFC;
                color: #64748B;
                font-weight: bold;
                font-size: 8pt;
                font-family: 'Segoe UI';
                padding: 16px 18px;
                border: none;
                border-bottom: 2px solid #E2E8F0;
                letter-spacing: 1px;
                text-transform: uppercase;
            }}
        """)
        hdr = self.tbl_ind.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for i in range(2,6): hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setStretchLastSection(False)
        self.tbl_ind.verticalHeader().setDefaultSectionSize(48)
        tf_ly.addWidget(self.tbl_ind)

        # Status bar below table
        status_bar = QFrame()
        status_bar.setStyleSheet("background:#F8FAFC;border-top:1px solid #F1F5F9;border-radius:0px;")
        sb_ly = QHBoxLayout(status_bar); sb_ly.setContentsMargins(18,8,18,8)
        self.lbl_status_ind = QLabel("")
        self.lbl_status_ind.setFont(QFont("Segoe UI", 9))
        self.lbl_status_ind.setStyleSheet("background:transparent;border:none;color:#64748B;")
        sb_ly.addWidget(self.lbl_status_ind)
        tf_ly.addWidget(status_bar)
        splitter.addWidget(tbl_frame)

        # ── Painel lateral ────────────────────────────────────────────────
        form_scroll = QScrollArea(); form_scroll.setWidgetResizable(True)
        form_scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        form_scroll.setMinimumWidth(330); form_scroll.setMaximumWidth(420)

        form_w = QWidget(); form_w.setStyleSheet("background:transparent;")
        form_ly = QVBoxLayout(form_w); form_ly.setContentsMargins(0,0,0,0); form_ly.setSpacing(16)

        # ── Seção helper ─────────────────────────────────────
        def _section(title):
            f = QFrame(); f.setStyleSheet("background:transparent;border:none;")
            hl = QHBoxLayout(f); hl.setContentsMargins(0,14,0,8); hl.setSpacing(10)
            bar = QFrame(); bar.setFixedSize(4,18)
            bar.setStyleSheet(f"background:{VERMELHO_ESC};border-radius:2px;border:none;")
            lbl = QLabel(title.upper()); lbl.setFont(QFont("Segoe UI",8,QFont.Weight.Bold))
            lbl.setStyleSheet("color:#334155;letter-spacing:1.2px;background:transparent;border:none;")
            hl.addWidget(bar); hl.addWidget(lbl); hl.addStretch()
            return f

        def _fld(ph=""):
            w = QLineEdit(); w.setPlaceholderText(ph); w.setFixedHeight(40)
            w.setStyleSheet(
                f"QLineEdit{{background:#F9FAFB;border:1.5px solid #E2E8F0;border-radius:7px;"
                f"padding:6px 14px;color:#0F172A;font-size:10pt;}}"
                f"QLineEdit:focus{{border:1.5px solid {VERMELHO_ESC};background:#FFFFFF;"
                f"box-shadow:0 0 0 3px rgba(185,28,28,0.12);}}"
                f"QLineEdit::placeholder{{color:#94A3B8;}}"
            ); return w
        def _cbo(items):
            w = QComboBox(); w.addItems(items); w.setFixedHeight(40)
            w.setStyleSheet(
                f"QComboBox{{background:#F9FAFB;border:1.5px solid #E2E8F0;border-radius:7px;"
                f"padding:6px 14px;color:#0F172A;font-size:10pt;}}"
                f"QComboBox::drop-down{{border:none;width:20px;}}"
                f"QComboBox:focus{{border:1.5px solid {VERMELHO_ESC};background:#FFFFFF;}}"
            ); return w
        def _row(lbl, w):
            f = QFrame(); f.setStyleSheet("background:transparent;border:none;")
            v = QVBoxLayout(f); v.setContentsMargins(0,0,0,0); v.setSpacing(5)
            l = QLabel(lbl); l.setFont(QFont("Segoe UI",8, QFont.Weight.Bold))
            l.setStyleSheet("color:#475569;background:transparent;border:none;letter-spacing:0.3px;")
            v.addWidget(l); v.addWidget(w); return f

        # Card form
        card = QFrame()
        card.setStyleSheet(
            f"QFrame{{background:{BRANCO};border:1px solid #DDE3EC;"
            f"border-radius:14px;}}"
        )
        card.setGraphicsEffect(shadow(16,(0,4),(0,0,0,12)))
        card_ly = QVBoxLayout(card); card_ly.setContentsMargins(28,24,28,28); card_ly.setSpacing(12)

        # Identificação
        card_ly.addWidget(_section("Identificação"))
        code_row = QHBoxLayout(); code_row.setSpacing(16)
        self.f_ind_cod = _fld("Ex: SP.IND.012"); self.f_ind_cod.setMaximumWidth(160)
        self.f_ind_nome = _fld("Nome completo do indicador")
        code_row.addWidget(_row("Código", self.f_ind_cod))
        code_row.addWidget(_row("Nome do Indicador", self.f_ind_nome), 1)
        card_ly.addLayout(code_row)

        sep1 = QFrame(); sep1.setFrameShape(QFrame.Shape.HLine); sep1.setStyleSheet("background:#E2E8F0;")
        card_ly.addWidget(sep1)

        # Classificação
        card_ly.addWidget(_section("Classificação e Medida"))
        cls_row = QHBoxLayout(); cls_row.setSpacing(16)
        self.f_ind_tipo = _cbo(["Operacional","Estratégico","Tático"])
        self.f_ind_per  = _cbo(["Mensal","Bimestral","Trimestral","Semestral","Anual"])
        self.f_ind_uni  = _fld("Ex: %, unidades, óbitos")
        cls_row.addWidget(_row("Tipo", self.f_ind_tipo))
        cls_row.addWidget(_row("Periodicidade", self.f_ind_per))
        card_ly.addLayout(cls_row)
        card_ly.addWidget(_row("Unidade de Medida", self.f_ind_uni))

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine); sep2.setStyleSheet("background:#E2E8F0;")
        card_ly.addWidget(sep2)

        # Meta
        card_ly.addWidget(_section("Meta e Comportamento"))
        meta_row = QHBoxLayout(); meta_row.setSpacing(16)
        self.f_ind_meta_txt = _fld("Ex: ≤ 3")
        self.f_ind_meta_num = _fld("3")
        meta_row.addWidget(_row("Meta (texto)", self.f_ind_meta_txt), 2)
        meta_row.addWidget(_row("Meta (número numérico)", self.f_ind_meta_num), 1)
        card_ly.addLayout(meta_row)

        chk_row = QHBoxLayout(); chk_row.setSpacing(24)
        self.f_ind_menor = QCheckBox("Menor valor é melhor")
        self.f_ind_ativo = QCheckBox("Indicador Ativo no Sistema")
        self.f_ind_ativo.setChecked(True)
        for c in [self.f_ind_menor, self.f_ind_ativo]:
            c.setStyleSheet(f"QCheckBox{{color:#0F172A;font-family:'Segoe UI';font-size:10pt;font-weight:500;background:transparent;border:none;}} QCheckBox::indicator{{width:18px;height:18px;border:1px solid #CBD5E1;border-radius:4px;background:#F8FAFC;}} QCheckBox::indicator:checked{{background:{VERMELHO_ESC};border-color:{VERMELHO_ESC};}}")
        chk_row.addWidget(self.f_ind_menor); chk_row.addWidget(self.f_ind_ativo); chk_row.addStretch()
        card_ly.addSpacing(6)
        card_ly.addLayout(chk_row)

        sep3 = QFrame(); sep3.setFrameShape(QFrame.Shape.HLine); sep3.setStyleSheet("background:#E2E8F0;")
        card_ly.addWidget(sep3)

        # Observações
        card_ly.addWidget(_section("Observações Adicionais"))
        self.f_ind_obs = QTextEdit(); self.f_ind_obs.setMaximumHeight(80)
        self.f_ind_obs.setStyleSheet(f"QTextEdit{{background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:10px;color:#0F172A;font-family:'Segoe UI';font-size:10pt;}}QTextEdit:focus{{border:1.5px solid {VERMELHO_ESC};background:#FFFFFF;}}")
        card_ly.addWidget(self.f_ind_obs)

        form_ly.addWidget(card)

        # Botões
        btn_row = QHBoxLayout(); btn_row.setSpacing(10)
        self.btn_ind_del = QPushButton("Excluir")
        self.btn_ind_del.setFixedHeight(40); self.btn_ind_del.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ind_del.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.btn_ind_del.setStyleSheet(
            f"QPushButton{{background:transparent;color:#94A3B8;border:1.5px solid #E2E8F0;"
            f"border-radius:8px;padding:0 18px;}}"
            f"QPushButton:hover{{color:{VERMELHO_ESC};border-color:{VERMELHO_ESC};background:#FEF2F2;}}"
        )
        self.btn_ind_save = QPushButton("Salvar Alterações")
        self.btn_ind_save.setFixedHeight(40); self.btn_ind_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ind_save.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.btn_ind_save.setStyleSheet(
            f"QPushButton{{background:{VERMELHO_ESC};color:#fff;border:none;"
            f"border-radius:8px;padding:0 28px;letter-spacing:0.2px;}}"
            f"QPushButton:hover{{background:{VERMELHO};}}"
            f"QPushButton:pressed{{background:#991B1B;}}"
        )
        btn_row.addWidget(self.btn_ind_del); btn_row.addStretch(); btn_row.addWidget(self.btn_ind_save)
        form_ly.addSpacing(8)
        form_ly.addLayout(btn_row)
        form_ly.addStretch()

        form_scroll.setWidget(form_w)
        splitter.addWidget(form_scroll)
        splitter.setSizes([720, 480])
        cw_ly.addWidget(splitter, 1)
        ly.addWidget(content_wrap, 1)

        self.tbl_ind.selectionModel().selectionChanged.connect(self._on_ind_select)
        self.btn_new_ind.clicked.connect(self._new_ind)
        self.btn_ind_save.clicked.connect(self._save_ind)
        self.btn_ind_del.clicked.connect(self._delete_ind)


    def _build_tab_subindicadores(self):
        self.tab_sub.setStyleSheet("background:transparent;")
        ly = QVBoxLayout(self.tab_sub); ly.setContentsMargins(0,0,0,0); ly.setSpacing(0)

        # ── Cabeçalho Hero ───────────────────────────────────
        header = QFrame()
        header.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #FFFFFF, stop:1 #F8FAFC);"
            "border-bottom: 1px solid #DDE3EC;"
        )
        h_ly = QHBoxLayout(header); h_ly.setContentsMargins(40,28,40,28); h_ly.setSpacing(24)

        accent2 = QFrame(); accent2.setFixedWidth(4); accent2.setFixedHeight(44)
        accent2.setStyleSheet(f"background:{VERMELHO_ESC};border-radius:2px;border:none;")
        h_ly.addWidget(accent2)

        ttl_col = QVBoxLayout(); ttl_col.setSpacing(5)
        t1 = QLabel("Catálogo de Subindicadores")
        t1.setFont(QFont("Segoe UI",17,QFont.Weight.Bold))
        t1.setStyleSheet("color:#0F172A; background:transparent; border:none;")
        t2 = QLabel("Configure os indicadores granulares e crie o detalhamento de cada meta.")
        t2.setFont(QFont("Segoe UI",10))
        t2.setStyleSheet("color:#64748B; background:transparent; border:none;")
        ttl_col.addWidget(t1); ttl_col.addWidget(t2)
        h_ly.addLayout(ttl_col, 1)

        vsep = QFrame(); vsep.setFrameShape(QFrame.Shape.VLine)
        vsep.setStyleSheet("background:#DDE3EC; border:none;"); vsep.setFixedWidth(1)
        h_ly.addWidget(vsep)

        fil_col = QVBoxLayout(); fil_col.setSpacing(5)
        fil_lbl = QLabel("Filtrar por Indicador Pai")
        fil_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        fil_lbl.setStyleSheet("color:#475569; background:transparent; border:none; letter-spacing:0.3px;")
        self.cb_filter_ind = QComboBox(); self.cb_filter_ind.setFixedHeight(40); self.cb_filter_ind.setMinimumWidth(300)
        self.cb_filter_ind.setStyleSheet(
            f"QComboBox{{background:#F9FAFB;border:1.5px solid #E2E8F0;border-radius:7px;"
            f"padding:6px 14px;color:#0F172A;font-size:10pt;}}"
            f"QComboBox::drop-down{{border:none;width:20px;}}"
            f"QComboBox:focus{{border:1.5px solid {VERMELHO_ESC};background:#FFFFFF;}}"
        )
        fil_col.addWidget(fil_lbl); fil_col.addWidget(self.cb_filter_ind)
        h_ly.addLayout(fil_col)

        vsep2 = QFrame(); vsep2.setFrameShape(QFrame.Shape.VLine)
        vsep2.setStyleSheet("background:#DDE3EC; border:none;"); vsep2.setFixedWidth(1)
        h_ly.addWidget(vsep2)

        self.btn_new_sub = QPushButton("＋  Novo Subindicador")
        self.btn_new_sub.setFixedHeight(44); self.btn_new_sub.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new_sub.setFont(QFont("Segoe UI",10,QFont.Weight.Bold))
        self.btn_new_sub.setStyleSheet(
            f"QPushButton{{background:{VERMELHO_ESC};color:#fff;border:none;"
            f"border-radius:8px;padding:0 24px;letter-spacing:0.3px;}}"
            f"QPushButton:hover{{background:{VERMELHO};}}"
            f"QPushButton:pressed{{background:#991B1B;}}"
        )
        h_ly.addWidget(self.btn_new_sub)
        ly.addWidget(header)

        # ── Área de Conteúdo (Splitter) ──────────────────────────────────
        content_wrap = QWidget(); content_wrap.setStyleSheet("background:transparent;")
        cw_ly = QVBoxLayout(content_wrap); cw_ly.setContentsMargins(32,32,32,32); cw_ly.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle{background:transparent;width:24px;}")
        splitter.setHandleWidth(24)

        # Tabela
        tbl_frame = QFrame()
        tbl_frame.setStyleSheet(f"QFrame{{background:{BRANCO};border:1px solid #DDE3EC;border-radius:12px;}}")
        tbl_frame.setGraphicsEffect(shadow(16,(0,4),(0,0,0,12)))
        tf_ly = QVBoxLayout(tbl_frame); tf_ly.setContentsMargins(0,0,0,0); tf_ly.setSpacing(0)

        self.tbl_sub = QTableWidget(0, 5)
        self.tbl_sub.setHorizontalHeaderLabels(["ID","Indicador Pai","Nome do Subindicador","Ordem","Ativo"])
        self.tbl_sub.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_sub.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_sub.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_sub.verticalHeader().setVisible(False)
        self.tbl_sub.setAlternatingRowColors(False)
        self.tbl_sub.setShowGrid(False)
        self.tbl_sub.setStyleSheet(f"""
            QTableWidget {{
                border: none; font-size: 10pt; font-family: 'Segoe UI';
                background: {BRANCO}; border-radius: 12px; outline: none;
            }}
            QTableWidget::item {{
                padding: 0px 18px; color: #1E293B;
                border-bottom: 1px solid #F1F5F9;
            }}
            QTableWidget::item:hover {{ background: #F8FAFC; }}
            QTableWidget::item:selected {{
                background: #FEF2F2; color: {VERMELHO_ESC};
                border-left: 3px solid {VERMELHO_ESC}; font-weight: bold;
            }}
            QHeaderView::section {{
                background: #F8FAFC; color: #64748B; font-weight: bold;
                font-size: 8pt; font-family: 'Segoe UI';
                padding: 16px 18px; border: none;
                border-bottom: 2px solid #E2E8F0;
                letter-spacing: 1px; text-transform: uppercase;
            }}
        """)
        hdr = self.tbl_sub.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_sub.verticalHeader().setDefaultSectionSize(48)
        tf_ly.addWidget(self.tbl_sub)

        status_bar_sub = QFrame()
        status_bar_sub.setStyleSheet("background:#F8FAFC;border-top:1px solid #F1F5F9;")
        sb2_ly = QHBoxLayout(status_bar_sub); sb2_ly.setContentsMargins(18,8,18,8)
        self.lbl_status_sub = QLabel("")
        self.lbl_status_sub.setFont(QFont("Segoe UI", 9))
        self.lbl_status_sub.setStyleSheet("background:transparent;border:none;color:#64748B;")
        sb2_ly.addWidget(self.lbl_status_sub)
        tf_ly.addWidget(status_bar_sub)
        splitter.addWidget(tbl_frame)

        # ── Painel lateral ───────────────────────────────────────
        form_scroll = QScrollArea(); form_scroll.setWidgetResizable(True)
        form_scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        form_scroll.setMinimumWidth(330); form_scroll.setMaximumWidth(420)

        form_w = QWidget(); form_w.setStyleSheet("background:transparent;")
        form_ly = QVBoxLayout(form_w); form_ly.setContentsMargins(0,0,0,0); form_ly.setSpacing(16)

        def _section(title):
            f = QFrame(); f.setStyleSheet("background:transparent;border:none;")
            hl = QHBoxLayout(f); hl.setContentsMargins(0,14,0,8); hl.setSpacing(10)
            bar = QFrame(); bar.setFixedSize(4,18)
            bar.setStyleSheet(f"background:{VERMELHO_ESC};border-radius:2px;border:none;")
            lbl = QLabel(title.upper()); lbl.setFont(QFont("Segoe UI",8,QFont.Weight.Bold))
            lbl.setStyleSheet("color:#334155;letter-spacing:1.2px;background:transparent;border:none;")
            hl.addWidget(bar); hl.addWidget(lbl); hl.addStretch()
            return f

        def _fld(ph="", ro=False):
            w = QLineEdit(); w.setPlaceholderText(ph); w.setFixedHeight(40); w.setReadOnly(ro)
            bg = "#F1F5F9" if ro else "#F9FAFB"
            col = "#94A3B8" if ro else "#0F172A"
            w.setStyleSheet(
                f"QLineEdit{{background:{bg};border:1.5px solid #E2E8F0;border-radius:7px;"
                f"padding:6px 14px;color:{col};font-size:10pt;}}"
                f"QLineEdit:focus{{border:1.5px solid {VERMELHO_ESC};background:#FFFFFF;"
                f"box-shadow:0 0 0 3px rgba(185,28,28,0.12);}}"
            ); return w
        def _cbo():
            w = QComboBox(); w.setFixedHeight(40)
            w.setStyleSheet(
                f"QComboBox{{background:#F9FAFB;border:1.5px solid #E2E8F0;border-radius:7px;"
                f"padding:6px 14px;color:#0F172A;font-size:10pt;}}"
                f"QComboBox::drop-down{{border:none;width:20px;}}"
                f"QComboBox:focus{{border:1.5px solid {VERMELHO_ESC};background:#FFFFFF;}}"
            ); return w
        def _row(lbl, w):
            f = QFrame(); f.setStyleSheet("background:transparent;border:none;")
            v = QVBoxLayout(f); v.setContentsMargins(0,0,0,0); v.setSpacing(5)
            l = QLabel(lbl); l.setFont(QFont("Segoe UI",8, QFont.Weight.Bold))
            l.setStyleSheet("color:#475569;background:transparent;border:none;letter-spacing:0.3px;")
            v.addWidget(l); v.addWidget(w); return f

        # Badge indicador pai
        self._sub_pai_badge = QFrame()
        self._sub_pai_badge.setStyleSheet(f"QFrame{{background:#ECFDF5;border:1px solid #6EE7B7;border-radius:8px;}}")
        badge_ly = QHBoxLayout(self._sub_pai_badge); badge_ly.setContentsMargins(16,12,16,12); badge_ly.setSpacing(12)
        dot = QLabel("●"); dot.setStyleSheet(f"color:#059669;background:transparent;border:none;font-size:12pt;")
        self._sub_pai_lbl = QLabel("Nenhum indicador pai selecionado")
        self._sub_pai_lbl.setFont(QFont("Segoe UI",10,QFont.Weight.Bold))
        self._sub_pai_lbl.setStyleSheet("color:#065F46;background:transparent;border:none;")
        badge_ly.addWidget(dot); badge_ly.addWidget(self._sub_pai_lbl); badge_ly.addStretch()
        form_ly.addWidget(self._sub_pai_badge)

        # Card form
        card = QFrame()
        card.setStyleSheet(f"QFrame{{background:{BRANCO};border:1px solid #E2E8F0;border-radius:12px;}}")
        card.setGraphicsEffect(shadow(12,(0,4),(0,0,0,10)))
        card_ly = QVBoxLayout(card); card_ly.setContentsMargins(28,28,28,28); card_ly.setSpacing(14)

        card_ly.addWidget(_section("Identificação do Subindicador"))
        self.f_sub_id  = _fld("Gerado automaticamente", ro=True)
        self.f_sub_pai = _cbo()
        nome_ord = QHBoxLayout(); nome_ord.setSpacing(16)
        self.f_sub_nome  = _fld("Nome do subindicador")
        self.f_sub_ordem = _fld("0"); self.f_sub_ordem.setMaximumWidth(100)
        nome_ord.addWidget(_row("Nome do Subindicador", self.f_sub_nome), 1)
        nome_ord.addWidget(_row("Ordem de Exibição", self.f_sub_ordem))
        
        card_ly.addWidget(_row("ID do Sistema", self.f_sub_id))
        card_ly.addWidget(_row("Vincular ao Indicador Pai", self.f_sub_pai))
        card_ly.addLayout(nome_ord)

        sep1 = QFrame(); sep1.setFrameShape(QFrame.Shape.HLine); sep1.setStyleSheet("background:#E2E8F0;")
        card_ly.addWidget(sep1)

        card_ly.addWidget(_section("Status e Observações"))
        self.f_sub_ativo = QCheckBox("Subindicador Ativo no Sistema")
        self.f_sub_ativo.setChecked(True)
        self.f_sub_ativo.setStyleSheet(f"QCheckBox{{color:#0F172A;font-family:'Segoe UI';font-size:10pt;font-weight:500;background:transparent;border:none;}} QCheckBox::indicator{{width:18px;height:18px;border:1px solid #CBD5E1;border-radius:4px;background:#F8FAFC;}} QCheckBox::indicator:checked{{background:{VERMELHO_ESC};border-color:{VERMELHO_ESC};}}")
        card_ly.addWidget(self.f_sub_ativo)
        
        self.f_sub_obs = QTextEdit(); self.f_sub_obs.setMaximumHeight(80)
        self.f_sub_obs.setStyleSheet(f"QTextEdit{{background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:10px;color:#0F172A;font-family:'Segoe UI';font-size:10pt;}}QTextEdit:focus{{border:1.5px solid {VERMELHO_ESC};background:#FFFFFF;}}")
        card_ly.addWidget(_row("Observações Adicionais", self.f_sub_obs))
        form_ly.addWidget(card)

        # Botões
        btn_row = QHBoxLayout(); btn_row.setSpacing(12)
        self.btn_sub_del = QPushButton("Excluir Subindicador")
        self.btn_sub_del.setFixedHeight(42); self.btn_sub_del.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sub_del.setStyleSheet(f"QPushButton{{background:transparent;color:{VERMELHO_ESC};border:1px solid {VERMELHO_ESC};border-radius:8px;padding:0 20px;font-weight:bold;font-size:10pt;}}QPushButton:hover{{background:#FFF1F2;}}")
        self.btn_sub_save = QPushButton("Salvar Alterações")
        self.btn_sub_save.setFixedHeight(42); self.btn_sub_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sub_save.setStyleSheet(f"QPushButton{{background:{VERMELHO_ESC};color:#fff;border:none;border-radius:8px;padding:0 32px;font-weight:bold;font-size:10pt;}}QPushButton:hover{{background:{VERMELHO};}}")
        btn_row.addWidget(self.btn_sub_del); btn_row.addStretch(); btn_row.addWidget(self.btn_sub_save)
        form_ly.addSpacing(4)
        form_ly.addLayout(btn_row)
        form_ly.addStretch()

        form_scroll.setWidget(form_w)
        splitter.addWidget(form_scroll)
        splitter.setSizes([750, 450])
        cw_ly.addWidget(splitter, 1)
        ly.addWidget(content_wrap, 1)

        self.cb_filter_ind.currentIndexChanged.connect(self._load_subindicadores_table)
        self.tbl_sub.selectionModel().selectionChanged.connect(self._on_sub_select)
        self.btn_new_sub.clicked.connect(self._new_sub)
        self.btn_sub_save.clicked.connect(self._save_sub)
        self.btn_sub_del.clicked.connect(self._delete_sub)

    # ── LOGICA INDICADORES ────────────────────────────────────────────────
    def _msg_ind(self, txt, cor):
        self.lbl_status_ind.setText(txt)
        self.lbl_status_ind.setStyleSheet(f"color:{cor};")

    def _load_indicadores_table(self):
        rows = db.get_all_indicadores()
        self.tbl_ind.setRowCount(len(rows))
        for r, m in enumerate(rows):
            def ci(txt): return QTableWidgetItem(str(txt) if txt else "–")
            self.tbl_ind.setItem(r, 0, ci(m["codigo_indicador"]))
            self.tbl_ind.setItem(r, 1, ci(m["nome_indicador"]))
            self.tbl_ind.setItem(r, 2, ci(m.get("tipo")))
            self.tbl_ind.setItem(r, 3, ci(m.get("periodicidade")))
            self.tbl_ind.setItem(r, 4, ci(m.get("meta_texto")))
            ativo = "Sim" if m.get("indicador_ativo") else "Não"
            it_at = ci(ativo)
            it_at.setForeground(QColor(VERDE if ativo == "Sim" else LARANJA))
            self.tbl_ind.setItem(r, 5, it_at)

    def _on_ind_select(self, selected, _):
        if not selected.indexes(): return
        r = selected.indexes()[0].row()
        cod = self.tbl_ind.item(r, 0).text()
        m = db.get_indicador(cod)
        if not m: return
        
        self.f_ind_cod.setText(m["codigo_indicador"])
        self.f_ind_cod.setReadOnly(True)
        self.f_ind_nome.setText(m["nome_indicador"])
        self.f_ind_tipo.setCurrentText(m.get("tipo") or "Operacional")
        self.f_ind_per.setCurrentText(m.get("periodicidade") or "Mensal")
        self.f_ind_uni.setText(m.get("unidade") or "")
        self.f_ind_meta_txt.setText(m.get("meta_texto") or "")
        mn = m.get("meta_numero")
        self.f_ind_meta_num.setText(str(mn) if mn is not None else "")
        self.f_ind_menor.setChecked(bool(m.get("menor_melhor", 1)))
        self.f_ind_ativo.setChecked(bool(m.get("indicador_ativo", 1)))
        self.f_ind_obs.setPlainText(m.get("observacoes") or "")
        self.btn_ind_del.setVisible(True)

    def _new_ind(self):
        self.tbl_ind.clearSelection()
        self.f_ind_cod.clear()
        self.f_ind_cod.setReadOnly(False)
        self.f_ind_nome.clear()
        self.f_ind_uni.clear()
        self.f_ind_meta_txt.clear()
        self.f_ind_meta_num.clear()
        self.f_ind_obs.clear()
        self.f_ind_ativo.setChecked(True)
        self.btn_ind_del.setVisible(False)
        self._msg_ind("Preencha os dados e salve.", PRETO_TITULO)
        self.f_ind_cod.setFocus()

    def _save_ind(self):
        cod = self.f_ind_cod.text().strip()
        if not cod:
            self._msg_ind("Código é obrigatório.", LARANJA)
            return
        
        mn = self.f_ind_meta_num.text().strip().replace(",", ".")
        try: mn = float(mn) if mn else None
        except ValueError: mn = None

        rec = {
            "codigo_indicador": cod,
            "nome_indicador": self.f_ind_nome.text().strip(),
            "tipo": self.f_ind_tipo.currentText(),
            "periodicidade": self.f_ind_per.currentText(),
            "unidade": self.f_ind_uni.text().strip(),
            "meta_texto": self.f_ind_meta_txt.text().strip(),
            "meta_numero": mn,
            "menor_melhor": 1 if self.f_ind_menor.isChecked() else 0,
            "indicador_ativo": 1 if self.f_ind_ativo.isChecked() else 0,
            "observacoes": self.f_ind_obs.toPlainText().strip()
        }
        if db.upsert_indicador(rec):
            self._msg_ind(f"Indicador {cod} salvo!", VERDE)
            self._load_indicadores_table()
            self._load_subindicadores_combos()
        else:
            self._msg_ind("Erro ao salvar.", VERMELHO)

    def _delete_ind(self):
        cod = self.f_ind_cod.text().strip()
        if not cod: return
        r = QMessageBox.question(self, "Excluir", f"Remover indicador {cod} e seus subindicadores/histórico?",
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            if db.delete_indicador(cod):
                self._msg_ind("Indicador removido.", VERDE)
                self._load_indicadores_table()
                self._load_subindicadores_combos()
                self._new_ind()
            else:
                self._msg_ind("Erro ao excluir.", VERMELHO)


    # ── LOGICA SUBINDICADORES ─────────────────────────────────────────────
    def _msg_sub(self, txt, cor):
        self.lbl_status_sub.setText(txt)
        self.lbl_status_sub.setStyleSheet(f"color:{cor};")

    def _load_subindicadores_combos(self):
        inds = db.get_all_indicadores()
        
        # Filtro
        cur_filter = self.cb_filter_ind.currentData()
        self.cb_filter_ind.blockSignals(True)
        self.cb_filter_ind.clear()
        self.cb_filter_ind.addItem("Todos os Indicadores", "TODOS")
        for i in inds:
            self.cb_filter_ind.addItem(f"{i['codigo_indicador']} - {i['nome_indicador']}", i['codigo_indicador'])
        idx = self.cb_filter_ind.findData(cur_filter)
        if idx >= 0: self.cb_filter_ind.setCurrentIndex(idx)
        self.cb_filter_ind.blockSignals(False)

        # Form Combo
        cur_pai = self.f_sub_pai.currentData()
        self.f_sub_pai.clear()
        for i in inds:
            self.f_sub_pai.addItem(i['codigo_indicador'], i['codigo_indicador'])
        idx = self.f_sub_pai.findData(cur_pai)
        if idx >= 0: self.f_sub_pai.setCurrentIndex(idx)

    def _load_subindicadores_table(self):
        filtro = self.cb_filter_ind.currentData()
        subs = db.get_all_subindicadores()
        if filtro and filtro != "TODOS":
            subs = [s for s in subs if s["codigo_indicador"] == filtro]
        
        self.tbl_sub.setRowCount(len(subs))
        for r, s in enumerate(subs):
            def ci(txt): return QTableWidgetItem(str(txt) if txt else "–")
            self.tbl_sub.setItem(r, 0, ci(s["id"]))
            self.tbl_sub.setItem(r, 1, ci(s["codigo_indicador"]))
            self.tbl_sub.setItem(r, 2, ci(s["nome_subindicador"]))
            self.tbl_sub.setItem(r, 3, ci(s.get("ordem", 0)))
            ativo = "Sim" if s.get("ativo") else "Não"
            it_at = ci(ativo)
            it_at.setForeground(QColor(VERDE if ativo == "Sim" else LARANJA))
            self.tbl_sub.setItem(r, 4, it_at)

    def _on_sub_select(self, selected, _):
        if not selected.indexes(): return
        r = selected.indexes()[0].row()
        sid = int(self.tbl_sub.item(r, 0).text())
        s = db.get_subindicador(sid)
        if not s: return
        
        self.f_sub_id.setText(str(s["id"]))
        idx = self.f_sub_pai.findData(s["codigo_indicador"])
        if idx >= 0: self.f_sub_pai.setCurrentIndex(idx)
        self.f_sub_pai.setEnabled(False)
        self.f_sub_nome.setText(s["nome_subindicador"])
        self.f_sub_ordem.setText(str(s.get("ordem", 0)))
        self.f_sub_ativo.setChecked(bool(s.get("ativo", 1)))
        self.f_sub_obs.setPlainText(s.get("observacoes") or "")
        self.btn_sub_del.setVisible(True)
        # Atualiza badge
        ind = db.get_indicador(s["codigo_indicador"])
        nome_ind = ind["nome_indicador"] if ind else s["codigo_indicador"]
        self._sub_pai_lbl.setText(f"{s['codigo_indicador']}  —  {nome_ind}")

    def _new_sub(self):
        self.tbl_sub.clearSelection()
        self.f_sub_id.clear()
        self.f_sub_pai.setEnabled(True)
        self._sub_pai_lbl.setText("Novo subindicador — selecione o indicador pai abaixo")
        filtro = self.cb_filter_ind.currentData()
        if filtro and filtro != "TODOS":
            idx = self.f_sub_pai.findData(filtro)
            if idx >= 0: self.f_sub_pai.setCurrentIndex(idx)
        
        self.f_sub_nome.clear()
        self.f_sub_ordem.setText("0")
        self.f_sub_ativo.setChecked(True)
        self.f_sub_obs.clear()
        self.btn_sub_del.setVisible(False)
        self._msg_sub("Preencha os dados e salve.", PRETO_TITULO)
        self.f_sub_nome.setFocus()

    def _save_sub(self):
        if not self.f_sub_pai.currentData():
            self._msg_sub("Selecione um Indicador Pai.", LARANJA)
            return
        if not self.f_sub_nome.text().strip():
            self._msg_sub("Nome do subindicador é obrigatório.", LARANJA)
            return
            
        ordem = 0
        try: ordem = int(self.f_sub_ordem.text().strip() or "0")
        except ValueError: pass

        sid = self.f_sub_id.text().strip()
        rec = {
            "codigo_indicador": self.f_sub_pai.currentData(),
            "nome_subindicador": self.f_sub_nome.text().strip(),
            "ordem": ordem,
            "ativo": 1 if self.f_sub_ativo.isChecked() else 0,
            "observacoes": self.f_sub_obs.toPlainText().strip()
        }
        if sid: rec["id"] = int(sid)

        res = db.upsert_subindicador(rec)
        if res:
            self._msg_sub("Subindicador salvo!", VERDE)
            self._load_subindicadores_table()
            # Seleciona de volta
            for r in range(self.tbl_sub.rowCount()):
                if self.tbl_sub.item(r, 0).text() == str(res):
                    self.tbl_sub.selectRow(r)
                    break
        else:
            self._msg_sub("Erro ao salvar.", VERMELHO)

    def _delete_sub(self):
        sid = self.f_sub_id.text().strip()
        if not sid: return
        r = QMessageBox.question(self, "Excluir", f"Remover subindicador ID {sid} e seu histórico?",
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            if db.delete_subindicador(int(sid)):
                self._msg_sub("Subindicador removido.", VERDE)
                self._load_subindicadores_table()
                self._new_sub()
            else:
                self._msg_sub("Erro ao excluir.", VERMELHO)
