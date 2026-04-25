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
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; background: transparent; border-top: 1px solid #E0E0E0; }}
            QTabBar::tab {{ background: transparent; border: none; border-bottom: 2px solid transparent; padding: 12px 24px; color: #757575; font-family: 'Segoe UI'; font-size: 14px; font-weight: bold; margin-right: 4px; }}
            QTabBar::tab:hover {{ color: #424242; }}
            QTabBar::tab:selected {{ color: {VERMELHO_ESC}; border-bottom: 2px solid {VERMELHO_ESC}; }}
        """)
        root.addWidget(self.tabs)

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
        ly = QVBoxLayout(self.tab_ind); ly.setContentsMargins(20,20,20,20); ly.setSpacing(16)
        
        # Toolbar
        tb = QHBoxLayout()
        self.btn_new_ind = _btn("＋  Novo Indicador", primary=True)
        tb.addWidget(self.btn_new_ind)
        tb.addStretch()
        self.lbl_status_ind = QLabel("")
        self.lbl_status_ind.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        tb.addWidget(self.lbl_status_ind)
        ly.addLayout(tb)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle{background:transparent;}")
        
        # Tabela
        self.tbl_ind = QTableWidget(0, 6)
        self.tbl_ind.setHorizontalHeaderLabels(["Código", "Indicador", "Tipo", "Periodicidade", "Meta", "Ativo"])
        self.tbl_ind.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_ind.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_ind.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_ind.verticalHeader().setVisible(False)
        self.tbl_ind.setAlternatingRowColors(True)
        self.tbl_ind.setStyleSheet(f"""
            QTableWidget {{ border: 1px solid #E1E4E8; border-radius: 6px; font-size: 9pt; background: {BRANCO}; gridline-color: transparent; }}
            QTableWidget::item {{ padding: 6px 12px; color: #24292F; border-bottom: 1px solid #EAECEF; }}
            QTableWidget::item:selected {{ background: #F0F7FF; color: #0366D6; }}
            QHeaderView::section {{ background: #F6F8FA; color: #57606A; font-weight: bold; font-size: 9pt; padding: 10px; border: none; border-bottom: 1px solid #D0D7DE; border-right: 1px solid #E1E4E8; }}
            QTableWidget::item:alternate {{ background: #F8F9FA; }}
        """)
        hdr = self.tbl_ind.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for i in range(2, 6): hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        splitter.addWidget(self.tbl_ind)

        # Painel Form
        form_frame = QFrame()
        form_frame.setMinimumWidth(320); form_frame.setMaximumWidth(400)
        form_frame.setStyleSheet(f"QFrame{{background:{BRANCO};border:1px solid #E1E4E8;border-radius:8px;}}")
        form_frame.setGraphicsEffect(shadow(12, (0,4), (0,0,0,15)))
        form_ly = QVBoxLayout(form_frame); form_ly.setContentsMargins(20,20,20,20); form_ly.setSpacing(12)

        def _edit():
            w = QLineEdit()
            w.setFixedHeight(34)
            w.setStyleSheet(f"QLineEdit{{background:{BRANCO};border:1px solid #D0D7DE;border-radius:6px;padding:4px 10px;color:#24292F;}}QLineEdit:focus{{border:1px solid {VERMELHO_ESC};}}")
            return w
        def _combo():
            w = QComboBox()
            w.setFixedHeight(34)
            w.setStyleSheet(f"QComboBox{{background:#F6F8FA;border:1px solid #D0D7DE;border-radius:6px;padding:4px 10px;color:#24292F;}}QComboBox:focus{{border:1px solid {VERMELHO_ESC};}} QComboBox::drop-down{{border:none;}}")
            return w

        self.f_ind_cod = _edit()
        self.f_ind_nome = _edit()
        self.f_ind_tipo = _combo(); self.f_ind_tipo.addItems(["Operacional", "Estratégico", "Tático"])
        self.f_ind_per = _combo(); self.f_ind_per.addItems(["Mensal", "Bimestral", "Trimestral", "Semestral", "Anual"])
        self.f_ind_uni = _edit()
        self.f_ind_meta_txt = _edit()
        self.f_ind_meta_num = _edit()
        self.f_ind_menor = QCheckBox("Menor valor é melhor")
        self.f_ind_menor.setStyleSheet("color:#24292F;")
        self.f_ind_obs = QTextEdit(); self.f_ind_obs.setMaximumHeight(70)
        self.f_ind_obs.setStyleSheet(f"QTextEdit{{background:{BRANCO};border:1px solid #D0D7DE;border-radius:6px;padding:6px;color:#24292F;}}QTextEdit:focus{{border:1px solid {VERMELHO_ESC};}}")
        self.f_ind_ativo = QCheckBox("Ativo")
        self.f_ind_ativo.setStyleSheet("color:#24292F;font-weight:bold;")

        form_ly.addWidget(_section_lbl("DADOS PRINCIPAIS"))
        form_ly.addWidget(_FieldRow("Código do Indicador", self.f_ind_cod))
        form_ly.addWidget(_FieldRow("Nome do Indicador", self.f_ind_nome))
        form_ly.addWidget(_FieldRow("Tipo", self.f_ind_tipo))
        form_ly.addWidget(_FieldRow("Periodicidade", self.f_ind_per))
        form_ly.addWidget(_FieldRow("Unidade (ex: %, unidades)", self.f_ind_uni))
        
        form_ly.addSpacing(10)
        form_ly.addWidget(_section_lbl("META E COMPORTAMENTO"))
        form_ly.addWidget(_FieldRow("Meta Texto (ex: ≤ 3)", self.f_ind_meta_txt))
        form_ly.addWidget(_FieldRow("Meta Número (ex: 3)", self.f_ind_meta_num))
        form_ly.addWidget(self.f_ind_menor)
        self.f_ind_ativo.setChecked(True)
        form_ly.addWidget(self.f_ind_ativo)
        
        form_ly.addSpacing(10)
        form_ly.addWidget(_FieldRow("Observações", self.f_ind_obs))
        
        form_ly.addStretch()

        btn_row = QHBoxLayout()
        self.btn_ind_save = _btn("Salvar", primary=True)
        self.btn_ind_del = _btn("Excluir", danger=True)
        btn_row.addWidget(self.btn_ind_del)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_ind_save)
        form_ly.addLayout(btn_row)

        splitter.addWidget(form_frame)
        splitter.setSizes([700, 350])
        ly.addWidget(splitter, 1)

        # Signals
        self.tbl_ind.selectionModel().selectionChanged.connect(self._on_ind_select)
        self.btn_new_ind.clicked.connect(self._new_ind)
        self.btn_ind_save.clicked.connect(self._save_ind)
        self.btn_ind_del.clicked.connect(self._delete_ind)


    def _build_tab_subindicadores(self):
        ly = QVBoxLayout(self.tab_sub); ly.setContentsMargins(20,20,20,20); ly.setSpacing(16)
        
        # Toolbar
        tb = QHBoxLayout()
        tb.addWidget(QLabel("Filtrar por Indicador:"))
        self.cb_filter_ind = QComboBox()
        self.cb_filter_ind.setMinimumWidth(300)
        self.cb_filter_ind.setStyleSheet(f"QComboBox{{background:{BRANCO};border:1px solid {CINZA_BORDA};border-radius:4px;padding:4px 8px;}}")
        tb.addWidget(self.cb_filter_ind)
        tb.addSpacing(20)
        self.btn_new_sub = _btn("＋  Novo Subindicador", primary=True)
        tb.addWidget(self.btn_new_sub)
        tb.addStretch()
        self.lbl_status_sub = QLabel("")
        self.lbl_status_sub.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        tb.addWidget(self.lbl_status_sub)
        ly.addLayout(tb)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle{background:transparent;}")
        
        # Tabela
        self.tbl_sub = QTableWidget(0, 5)
        self.tbl_sub.setHorizontalHeaderLabels(["ID", "Indicador Pai", "Nome do Subindicador", "Ordem", "Ativo"])
        self.tbl_sub.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_sub.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_sub.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_sub.verticalHeader().setVisible(False)
        self.tbl_sub.setAlternatingRowColors(True)
        self.tbl_sub.setStyleSheet(self.tbl_ind.styleSheet())
        
        hdr = self.tbl_sub.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        splitter.addWidget(self.tbl_sub)

        # Painel Form
        form_frame = QFrame()
        form_frame.setMinimumWidth(320); form_frame.setMaximumWidth(400)
        form_frame.setStyleSheet(f"QFrame{{background:{BRANCO};border:1px solid #E1E4E8;border-radius:8px;}}")
        form_frame.setGraphicsEffect(shadow(12, (0,4), (0,0,0,15)))
        form_ly = QVBoxLayout(form_frame); form_ly.setContentsMargins(20,20,20,20); form_ly.setSpacing(12)

        self.f_sub_id = QLineEdit(); self.f_sub_id.setReadOnly(True); self.f_sub_id.setFixedHeight(34)
        self.f_sub_id.setStyleSheet(f"QLineEdit{{background:#F3F4F6;border:1px solid #D0D7DE;border-radius:6px;padding:4px 10px;color:#6E7781;}}")
        self.f_sub_pai = QComboBox(); self.f_sub_pai.setFixedHeight(34)
        self.f_sub_pai.setStyleSheet(f"QComboBox{{background:#F6F8FA;border:1px solid #D0D7DE;border-radius:6px;padding:4px 10px;color:#24292F;}}")
        self.f_sub_nome = QLineEdit(); self.f_sub_nome.setFixedHeight(34)
        self.f_sub_nome.setStyleSheet(f"QLineEdit{{background:{BRANCO};border:1px solid #D0D7DE;border-radius:6px;padding:4px 10px;color:#24292F;}}QLineEdit:focus{{border:1px solid {VERMELHO_ESC};}}")
        self.f_sub_ordem = QLineEdit(); self.f_sub_ordem.setFixedHeight(34)
        self.f_sub_ordem.setStyleSheet(self.f_sub_nome.styleSheet())
        self.f_sub_obs = QTextEdit(); self.f_sub_obs.setMaximumHeight(70)
        self.f_sub_obs.setStyleSheet(f"QTextEdit{{background:{BRANCO};border:1px solid #D0D7DE;border-radius:6px;padding:6px;color:#24292F;}}QTextEdit:focus{{border:1px solid {VERMELHO_ESC};}}")
        self.f_sub_ativo = QCheckBox("Ativo")
        self.f_sub_ativo.setStyleSheet("color:#24292F;font-weight:bold;")

        form_ly.addWidget(_section_lbl("DADOS DO SUBINDICADOR"))
        form_ly.addWidget(_FieldRow("ID (Automático)", self.f_sub_id))
        form_ly.addWidget(_FieldRow("Indicador Pai", self.f_sub_pai))
        form_ly.addWidget(_FieldRow("Nome do Subindicador", self.f_sub_nome))
        form_ly.addWidget(_FieldRow("Ordem (Numérico)", self.f_sub_ordem))
        self.f_sub_ativo.setChecked(True)
        form_ly.addWidget(self.f_sub_ativo)
        form_ly.addWidget(_FieldRow("Observações", self.f_sub_obs))
        form_ly.addStretch()

        btn_row = QHBoxLayout()
        self.btn_sub_save = _btn("Salvar", primary=True)
        self.btn_sub_del = _btn("Excluir", danger=True)
        btn_row.addWidget(self.btn_sub_del)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_sub_save)
        form_ly.addLayout(btn_row)

        splitter.addWidget(form_frame)
        splitter.setSizes([700, 350])
        ly.addWidget(splitter, 1)

        # Signals
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
        self.f_sub_pai.setEnabled(False) # Não muda o pai depois de criado
        self.f_sub_nome.setText(s["nome_subindicador"])
        self.f_sub_ordem.setText(str(s.get("ordem", 0)))
        self.f_sub_ativo.setChecked(bool(s.get("ativo", 1)))
        self.f_sub_obs.setPlainText(s.get("observacoes") or "")
        self.btn_sub_del.setVisible(True)

    def _new_sub(self):
        self.tbl_sub.clearSelection()
        self.f_sub_id.clear()
        self.f_sub_pai.setEnabled(True)
        # Tenta pegar do filtro se não for TODOS
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
