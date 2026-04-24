"""
panel_historico.py - Lançamento e edição de histórico mensal diretamente no app.
Fonte única: SQLite (database.dados_historicos).
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QPushButton, QComboBox, QLineEdit,
    QGridLayout, QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

import database as db
from styles import (
    VERMELHO, VERMELHO_ESC, BRANCO, CINZA_BG, CINZA_BORDA,
    CINZA_SUAVE, PRETO_TITULO, VERDE, LARANJA, PENDENTE_FG
)
from widgets import shadow

MESES = [
    "Janeiro","Fevereiro","Março","Abril","Maio","Junho",
    "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"
]
ANOS = [str(a) for a in range(2021, 2028)]

def _btn(txt, primary=False):
    b = QPushButton(txt)
    b.setFixedHeight(34)
    b.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold if primary else QFont.Weight.Normal))
    if primary:
        b.setStyleSheet(f"QPushButton{{background:{VERMELHO_ESC};color:{BRANCO};border:none;border-radius:5px;padding:0 18px;}}QPushButton:hover{{background:{VERMELHO};}}")
    else:
        b.setStyleSheet(f"QPushButton{{background:{BRANCO};color:{PRETO_TITULO};border:1px solid {CINZA_BORDA};border-radius:5px;padding:0 14px;}}QPushButton:hover{{background:#F5F5F5;}}")
    return b

def _field_edit(placeholder=""):
    w = QLineEdit()
    w.setPlaceholderText(placeholder)
    w.setFont(QFont("Segoe UI", 10))
    w.setFixedHeight(36)
    w.setStyleSheet(f"""
        QLineEdit{{
            background:{BRANCO};border:1px solid {CINZA_BORDA};
            border-radius:4px;padding:4px 10px;color:{PRETO_TITULO};
        }}
        QLineEdit:focus{{border-color:{VERMELHO};}}
    """)
    return w


class HistoricoPanel(QWidget):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self._inputs = {}   # {mes: QLineEdit}
        self._build_ui()
        self._populate_selector()

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root.addWidget(scroll)
        container = QWidget(); container.setStyleSheet(f"background:{CINZA_BG};")
        scroll.setWidget(container)
        main = QVBoxLayout(container); main.setContentsMargins(28,24,28,28); main.setSpacing(20)

        # ── Título ────────────────────────────────────────────────────────
        title = QLabel("LANÇAMENTO DE HISTÓRICO MENSAL")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{PRETO_TITULO};background:transparent;border:none;")
        sub = QLabel("Registre ou edite os valores mensais de cada indicador diretamente no sistema.")
        sub.setFont(QFont("Segoe UI", 9))
        sub.setStyleSheet(f"color:{CINZA_SUAVE};background:transparent;border:none;")
        main.addWidget(title); main.addWidget(sub)

        # ── Seletores ─────────────────────────────────────────────────────
        sel_frame = QFrame()
        sel_frame.setStyleSheet(f"QFrame{{background:{BRANCO};border:1px solid {CINZA_BORDA};border-radius:6px;}}")
        sel_frame.setGraphicsEffect(shadow(6,(0,2),(0,0,0,10)))
        sel_ly = QHBoxLayout(sel_frame); sel_ly.setContentsMargins(20,16,20,16); sel_ly.setSpacing(16)

        lbl_ind = QLabel("Indicador:")
        lbl_ind.setFont(QFont("Segoe UI",9,QFont.Weight.Bold))
        lbl_ind.setStyleSheet(f"color:{PRETO_TITULO};background:transparent;border:none;")
        sel_ly.addWidget(lbl_ind)

        self.sel_ind = QComboBox()
        self.sel_ind.setMinimumWidth(340)
        self.sel_ind.setFixedHeight(34)
        self.sel_ind.setFont(QFont("Segoe UI",9))
        self.sel_ind.setStyleSheet(f"QComboBox{{background:{BRANCO};border:1px solid {CINZA_BORDA};border-radius:4px;padding:4px 10px;}}QComboBox::drop-down{{border:none;}}")
        sel_ly.addWidget(self.sel_ind)

        lbl_ano = QLabel("Ano:")
        lbl_ano.setFont(QFont("Segoe UI",9,QFont.Weight.Bold))
        lbl_ano.setStyleSheet(f"color:{PRETO_TITULO};background:transparent;border:none;")
        sel_ly.addWidget(lbl_ano)

        self.sel_ano = QComboBox()
        self.sel_ano.addItems(ANOS)
        self.sel_ano.setCurrentText("2026")
        self.sel_ano.setFixedHeight(34); self.sel_ano.setFixedWidth(90)
        self.sel_ano.setFont(QFont("Segoe UI",9))
        self.sel_ano.setStyleSheet(f"QComboBox{{background:{BRANCO};border:1px solid {CINZA_BORDA};border-radius:4px;padding:4px 10px;}}QComboBox::drop-down{{border:none;}}")
        sel_ly.addWidget(self.sel_ano)

        self.btn_load = _btn("Carregar Dados")
        sel_ly.addWidget(self.btn_load)
        sel_ly.addStretch()
        main.addWidget(sel_frame)

        # ── Grade de meses ────────────────────────────────────────────────
        self.grade_frame = QFrame()
        self.grade_frame.setStyleSheet(f"QFrame{{background:{BRANCO};border:1px solid {CINZA_BORDA};border-radius:6px;}}")
        self.grade_frame.setGraphicsEffect(shadow(6,(0,2),(0,0,0,10)))
        grade_outer = QVBoxLayout(self.grade_frame); grade_outer.setContentsMargins(24,20,24,20); grade_outer.setSpacing(16)

        self.grade_title = QLabel("Selecione um indicador e clique em Carregar Dados")
        self.grade_title.setFont(QFont("Segoe UI",10,QFont.Weight.Bold))
        self.grade_title.setStyleSheet(f"color:{PRETO_TITULO};background:transparent;border:none;")
        grade_outer.addWidget(self.grade_title)

        # Grid 4x3 (meses em ordem)
        grid = QGridLayout(); grid.setSpacing(14)
        for idx, mes in enumerate(MESES):
            col = idx % 4; row_pos = idx // 4
            cell = QVBoxLayout(); cell.setSpacing(4)
            lbl = QLabel(mes)
            lbl.setFont(QFont("Segoe UI",8,QFont.Weight.Bold))
            lbl.setStyleSheet(f"color:{CINZA_SUAVE};background:transparent;border:none;")
            inp = _field_edit("—")
            inp.setAlignment(Qt.AlignmentFlag.AlignRight)
            self._inputs[mes] = inp
            cell.addWidget(lbl); cell.addWidget(inp)
            wrap = QWidget(); wrap.setStyleSheet("background:transparent;border:none;")
            wrap.setLayout(cell)
            grid.addWidget(wrap, row_pos, col)
        grade_outer.addLayout(grid)

        # Linha de ação
        act_ly = QHBoxLayout(); act_ly.setSpacing(10)
        self.lbl_info = QLabel("")
        self.lbl_info.setFont(QFont("Segoe UI",8,QFont.Weight.Bold))
        self.lbl_info.setStyleSheet("background:transparent;border:none;")
        act_ly.addWidget(self.lbl_info)
        act_ly.addStretch()
        self.btn_clear = _btn("Limpar Campos")
        self.btn_save  = _btn("💾  Salvar Histórico", primary=True)
        act_ly.addWidget(self.btn_clear)
        act_ly.addWidget(self.btn_save)
        grade_outer.addLayout(act_ly)
        main.addWidget(self.grade_frame, 1)

        # ── Tabela de valores já salvos ───────────────────────────────────
        saved_frame = QFrame()
        saved_frame.setStyleSheet(f"QFrame{{background:{BRANCO};border:1px solid {CINZA_BORDA};border-radius:6px;}}")
        saved_frame.setGraphicsEffect(shadow(6,(0,2),(0,0,0,10)))
        saved_outer = QVBoxLayout(saved_frame); saved_outer.setContentsMargins(20,16,20,16); saved_outer.setSpacing(8)

        hdr_lbl = QLabel("DADOS SALVOS NO BANCO — TODOS OS ANOS DISPONÍVEIS")
        hdr_lbl.setFont(QFont("Segoe UI",8,QFont.Weight.Bold))
        hdr_lbl.setStyleSheet(f"color:{BRANCO};background:{VERMELHO_ESC};border-radius:4px;padding:6px 12px;border:none;")
        saved_outer.addWidget(hdr_lbl)

        self.saved_grid = QGridLayout(); self.saved_grid.setSpacing(2)
        saved_outer.addLayout(self.saved_grid)
        main.addWidget(saved_frame)

        # Signals
        self.btn_load.clicked.connect(self._load_historico)
        self.btn_save.clicked.connect(self._save_historico)
        self.btn_clear.clicked.connect(self._clear_inputs)
        self.sel_ind.currentIndexChanged.connect(self._load_historico)
        self.sel_ano.currentIndexChanged.connect(self._load_historico)

    def _populate_selector(self):
        self.sel_ind.clear()
        inds = db.get_indicadores_ativos()
        for i in inds:
            self.sel_ind.addItem(f"{i['codigo_indicador']}  —  {i['nome_indicador']}", i['codigo_indicador'])

    def _current_codigo(self):
        return self.sel_ind.currentData()

    def _current_ano(self):
        return int(self.sel_ano.currentText())

    def _load_historico(self):
        cod  = self._current_codigo()
        ano  = self._current_ano()
        if not cod: return

        ind  = db.get_indicador(cod)
        nome = ind['nome_indicador'] if ind else cod
        self.grade_title.setText(f"{cod}  —  {nome}  |  Ano: {ano}")

        # Agrega histórico de todos os subindicadores do indicador
        hist = db.get_historico_indicador(cod, [ano])
        dados_ano = hist.get(ano, {})

        # Preenche inputs
        for mes in MESES:
            val = dados_ano.get(mes)
            inp = self._inputs[mes]
            inp.setText(str(int(val)) if isinstance(val, float) and val == int(val) else str(val) if val is not None else "")
            # Visual: verde se tem dado, normal se não tem
            cor_borda = VERDE if val is not None else CINZA_BORDA
            inp.setStyleSheet(f"""
                QLineEdit{{
                    background:{BRANCO};border:1px solid {cor_borda};
                    border-radius:4px;padding:4px 10px;color:{PRETO_TITULO};
                }}
                QLineEdit:focus{{border-color:{VERMELHO};}}
            """)

        self.lbl_info.setText("")
        self._rebuild_saved_table(cod)

    def _rebuild_saved_table(self, cod):
        while self.saved_grid.count():
            item = self.saved_grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        hist = db.get_historico_indicador(cod)
        if not hist:
            lbl = QLabel("Nenhum dado salvo para este indicador.")
            lbl.setStyleSheet(f"color:{CINZA_SUAVE};background:transparent;border:none;")
            self.saved_grid.addWidget(lbl, 0, 0)
            return

        def _hdr(txt, col):
            l = QLabel(txt.upper())
            l.setFont(QFont("Segoe UI",7,QFont.Weight.Bold))
            l.setStyleSheet(f"color:{CINZA_SUAVE};background:transparent;border:none;")
            l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.saved_grid.addWidget(l, 0, col)

        _hdr("Ano", 0)
        for ci, mes in enumerate(MESES, 1):
            _hdr(mes[:3], ci)

        for ri, ano in enumerate(sorted(hist.keys()), 1):
            lbl_ano = QLabel(str(ano))
            lbl_ano.setFont(QFont("Segoe UI",8,QFont.Weight.Bold))
            lbl_ano.setStyleSheet(f"color:{PRETO_TITULO};background:transparent;border:none;")
            lbl_ano.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.saved_grid.addWidget(lbl_ano, ri, 0)
            for ci, mes in enumerate(MESES, 1):
                val = hist[ano].get(mes)
                txt = str(int(val)) if isinstance(val, float) and val == int(val) else str(val) if val is not None else "–"
                cor = PRETO_TITULO if val is not None else CINZA_BORDA
                cell = QLabel(txt)
                cell.setFont(QFont("Segoe UI",8))
                cell.setStyleSheet(f"color:{cor};background:transparent;border:none;")
                cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.saved_grid.addWidget(cell, ri, ci)

    def _save_historico(self):
        cod = self._current_codigo()
        ano = self._current_ano()
        if not cod:
            self.lbl_info.setText("⚠️ Selecione um indicador.")
            self.lbl_info.setStyleSheet(f"color:{LARANJA};background:transparent;border:none;")
            return

        # Usa o primeiro subindicador do indicador (ou cria um padrão)
        subs = db.get_subindicadores(cod)
        if not subs:
            self.lbl_info.setText("⚠️ Crie pelo menos um subindicador primeiro.")
            self.lbl_info.setStyleSheet(f"color:{LARANJA};background:transparent;border:none;")
            return

        saved = 0; errors = 0
        # Salva no primeiro subindicador por simplicidade
        sub_id = subs[0]["id"]
        for mes in MESES:
            txt = self._inputs[mes].text().strip().replace(",", ".")
            if txt == "" or txt == "–":
                continue
            try:
                valor = float(txt)
                if db.upsert_historico(sub_id, ano, mes, valor):
                    saved += 1
                else:
                    errors += 1
            except ValueError:
                errors += 1

        if errors:
            self.lbl_info.setText(f"⚠️ {errors} valores inválidos (use números).")
            self.lbl_info.setStyleSheet(f"color:{LARANJA};background:transparent;border:none;")
        else:
            self.lbl_info.setText(f"✅ {saved} meses salvos no banco com sucesso!")
            self.lbl_info.setStyleSheet(f"color:{VERDE};background:transparent;border:none;")
            self._load_historico()  # Atualiza visual

    def _clear_inputs(self):
        for inp in self._inputs.values():
            inp.clear()
            inp.setStyleSheet(f"""
                QLineEdit{{
                    background:{BRANCO};border:1px solid {CINZA_BORDA};
                    border-radius:4px;padding:4px 10px;color:{PRETO_TITULO};
                }}
                QLineEdit:focus{{border-color:{VERMELHO};}}
            """)
        self.lbl_info.setText("")
