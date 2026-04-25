"""panel_historico.py — Lançamento e edição de histórico mensal."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QPushButton, QComboBox, QLineEdit,
    QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import database as db
from styles import (
    VERMELHO, VERMELHO_ESC, BRANCO, CINZA_BG, CINZA_BORDA,
    CINZA_SUAVE, PRETO_TITULO, VERDE, LARANJA, PENDENTE_FG
)
from widgets import shadow

MESES = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
         "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
ANOS  = [str(a) for a in range(2021, 2028)]
TRIM_LABELS = ["T1 — JAN / FEV / MAR", "T2 — ABR / MAI / JUN",
               "T3 — JUL / AGO / SET", "T4 — OUT / NOV / DEZ"]

CSS_FLD = ("background:#fff;border:1px solid #D1D5DB;border-radius:6px;"
           "padding:4px 8px;color:#111827;font-family:'Segoe UI';text-align:center;")

def _lbl(t, bold=False, size=9, color=PRETO_TITULO):
    l = QLabel(t); l.setFont(QFont("Segoe UI", size, QFont.Weight.Bold if bold else QFont.Weight.Normal))
    l.setStyleSheet(f"color:{color};background:transparent;border:none;"); return l

def _cbx():
    w = QComboBox(); w.setFixedHeight(36)
    w.setStyleSheet(
        f"QComboBox{{background:#fff;border:1px solid #D1D5DB;border-radius:6px;padding:4px 10px;color:#111827;}}"
        f"QComboBox::drop-down{{border:none;}}QComboBox:focus{{border:1.5px solid {VERMELHO_ESC};}}")
    return w

def _btn(t, primary=False):
    b = QPushButton(t); b.setFixedHeight(36); b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
    if primary:
        b.setStyleSheet(f"QPushButton{{background:{VERMELHO_ESC};color:#fff;border:none;border-radius:6px;padding:0 20px;}}QPushButton:hover{{background:{VERMELHO};}}")
    else:
        b.setStyleSheet(f"QPushButton{{background:#F3F4F6;color:#374151;border:1px solid #D1D5DB;border-radius:6px;padding:0 16px;}}QPushButton:hover{{background:#E5E7EB;}}")
    return b

def _fld():
    w = QLineEdit(); w.setFixedHeight(38); w.setAlignment(Qt.AlignmentFlag.AlignRight)
    w.setPlaceholderText("—")
    w.setStyleSheet(f"QLineEdit{{{CSS_FLD}}}QLineEdit:focus{{border:1.5px solid {VERMELHO_ESC};}}")
    return w

def _sec_badge(t, color="#6366F1"):
    f = QFrame(); f.setStyleSheet(f"QFrame{{background:{color}18;border:1px solid {color}40;border-radius:4px;}}")
    l = QHBoxLayout(f); l.setContentsMargins(10,4,10,4)
    lb = _lbl(t, bold=True, size=8, color=color); l.addWidget(lb); return f


class HistoricoPanel(QWidget):
    def __init__(self, data, parent=None):
        super().__init__(parent); self.data = data
        self._inputs = {}
        self._build_ui(); self._populate_selector()

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        root.addWidget(scroll)
        ctr = QWidget(); ctr.setStyleSheet("background:transparent;")
        scroll.setWidget(ctr)
        main = QVBoxLayout(ctr); main.setContentsMargins(32,32,32,32); main.setSpacing(24)

        # ── Header bar ────────────────────────────────────────────────
        hdr = QFrame()
        hdr.setStyleSheet(f"QFrame{{background:{BRANCO};border:1px solid #E2E8F0;border-radius:12px;}}")
        hdr.setGraphicsEffect(shadow(12,(0,4),(0,0,0,10)))
        hdr_ly = QHBoxLayout(hdr); hdr_ly.setContentsMargins(32,24,32,24); hdr_ly.setSpacing(24)

        ttl = QVBoxLayout(); ttl.setSpacing(6)
        ttl.addWidget(_lbl("Lançamento Mensal", bold=True, size=16, color="#0F172A"))
        ttl.addWidget(_lbl("Selecione os parâmetros abaixo para inserir resultados.", size=10, color="#64748B"))
        hdr_ly.addLayout(ttl, 1)

        sep1 = QFrame(); sep1.setFrameShape(QFrame.Shape.VLine); sep1.setStyleSheet("background:#E2E8F0;border:none;"); sep1.setFixedWidth(1)
        hdr_ly.addWidget(sep1)

        params_ly = QHBoxLayout(); params_ly.setSpacing(16)
        def _lbl2(t): return _lbl(t, bold=True, size=9, color="#475569")
        
        ind_col = QVBoxLayout(); ind_col.setSpacing(6)
        ind_col.addWidget(_lbl2("Indicador Pai"))
        self.sel_ind = _cbx(); self.sel_ind.setMinimumWidth(260)
        self.sel_ind.setStyleSheet(f"QComboBox{{background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:6px 12px;color:#0F172A;font-size:10pt;}}QComboBox::drop-down{{border:none;}}")
        ind_col.addWidget(self.sel_ind)
        params_ly.addLayout(ind_col)

        sub_col = QVBoxLayout(); sub_col.setSpacing(6)
        sub_col.addWidget(_lbl2("Subindicador Alvo"))
        self.sel_sub = _cbx(); self.sel_sub.setMinimumWidth(220)
        self.sel_sub.setStyleSheet(f"QComboBox{{background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:6px 12px;color:#0F172A;font-size:10pt;}}QComboBox::drop-down{{border:none;}}")
        sub_col.addWidget(self.sel_sub)
        params_ly.addLayout(sub_col)

        ano_col = QVBoxLayout(); ano_col.setSpacing(6)
        ano_col.addWidget(_lbl2("Ano"))
        self.sel_ano = _cbx(); self.sel_ano.addItems(ANOS); self.sel_ano.setCurrentText("2026")
        self.sel_ano.setFixedWidth(100)
        self.sel_ano.setStyleSheet(f"QComboBox{{background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:6px 12px;color:#0F172A;font-size:10pt;}}QComboBox::drop-down{{border:none;}}")
        ano_col.addWidget(self.sel_ano)
        params_ly.addLayout(ano_col)
        
        hdr_ly.addLayout(params_ly)

        self.btn_load = QPushButton("Carregar Histórico")
        self.btn_load.setFixedHeight(42); self.btn_load.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_load.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.btn_load.setStyleSheet(f"QPushButton{{background:#0F172A;color:#fff;border:none;border-radius:8px;padding:0 24px;}}QPushButton:hover{{background:#334155;}}")
        
        load_col = QVBoxLayout()
        load_col.addStretch(); load_col.addWidget(self.btn_load)
        hdr_ly.addLayout(load_col)
        
        main.addWidget(hdr)

        # ── Grade mensal em trimestres ─────────────────────────────────
        self.grade_frame = QFrame()
        self.grade_frame.setStyleSheet(f"QFrame{{background:{BRANCO};border:1px solid #E2E8F0;border-radius:12px;}}")
        self.grade_frame.setGraphicsEffect(shadow(12,(0,4),(0,0,0,10)))
        g_ly = QVBoxLayout(self.grade_frame); g_ly.setContentsMargins(32,32,32,32); g_ly.setSpacing(24)

        # Title + mini-summary row
        title_row = QHBoxLayout(); title_row.setSpacing(16)
        self.grade_title = _lbl("Nenhum subindicador carregado", bold=True, size=14, color="#0F172A")
        title_row.addWidget(self.grade_title, 1)
        # Mini KPIs
        kpi_colors = [("kpi_preenchidos","MESES","#6366F1","#EEF2FF"),
                      ("kpi_total","ACUMULADO","#0891B2","#ECFEFF"),
                      ("kpi_media","MÉDIA","#059669","#ECFDF5")]
        for attr, label, accent_c, bg_c in kpi_colors:
            kpi = QFrame()
            kpi.setStyleSheet(f"QFrame{{background:{bg_c};border:1.5px solid {accent_c}30;border-radius:10px;}}")
            kpi.setMinimumWidth(110)
            kpi_ly = QVBoxLayout(kpi); kpi_ly.setContentsMargins(16,12,16,12); kpi_ly.setSpacing(3)
            val_lbl = _lbl("—", bold=True, size=18, color=accent_c)
            lbl_lbl = _lbl(label, size=7, color=accent_c)
            lbl_lbl.setStyleSheet(f"color:{accent_c};letter-spacing:1.5px;background:transparent;border:none;font-weight:bold;")
            kpi_ly.addWidget(val_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
            kpi_ly.addWidget(lbl_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
            setattr(self, attr, val_lbl)
            title_row.addWidget(kpi)
        g_ly.addLayout(title_row)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine); sep2.setStyleSheet("background:#E2E8F0;border:none;")
        g_ly.addWidget(sep2)

        # Grid 4 trimestres x 3 meses
        grid = QGridLayout(); grid.setSpacing(10)
        TRIM_COLORS = ["#7C3AED","#0891B2","#059669","#D97706"]
        for ti, trim in enumerate(TRIM_LABELS):
            accent_c = TRIM_COLORS[ti]
            # Trim header
            th = QLabel(trim)
            th.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            th.setStyleSheet(
                f"color:{accent_c};background:{accent_c}12;"
                f"border:1.5px solid {accent_c}40;border-radius:7px;"
                f"padding:10px 16px;letter-spacing:1px;"
            )
            th.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(th, ti*2, 0, 1, 3)
            # 3 months
            for mi in range(3):
                mes_idx = ti*3 + mi
                mes = MESES[mes_idx]
                cell = QFrame()
                cell.setStyleSheet(
                    f"QFrame{{background:#FAFAFA;border:1px solid #E8EDF4;"
                    f"border-radius:8px;}}"
                )
                c_ly = QVBoxLayout(cell); c_ly.setContentsMargins(6,10,6,8); c_ly.setSpacing(5)
                lbl = _lbl(mes[:3].upper(), bold=True, size=7, color="#94A3B8")
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setStyleSheet("color:#94A3B8;letter-spacing:1.5px;background:transparent;border:none;font-weight:bold;")
                inp = QLineEdit(); inp.setFixedHeight(40); inp.setAlignment(Qt.AlignmentFlag.AlignCenter)
                inp.setPlaceholderText("—")
                inp.setStyleSheet(
                    f"QLineEdit{{background:#FFFFFF;border:1.5px solid #E2E8F0;border-radius:6px;"
                    f"padding:4px 8px;color:#0F172A;font-size:13pt;font-weight:bold;}}"
                    f"QLineEdit:focus{{border:1.5px solid {VERMELHO_ESC};background:#FFFFFF;"
                    f"box-shadow:0 0 0 3px rgba(185,28,28,0.12);}}"
                )
                self._inputs[mes] = inp
                c_ly.addWidget(lbl); c_ly.addWidget(inp)
                grid.addWidget(cell, ti*2+1, mi)
        g_ly.addLayout(grid)

        # Action row
        act = QHBoxLayout(); act.setSpacing(12)
        self.lbl_info = _lbl("", bold=True, size=10, color=VERDE)
        act.addWidget(self.lbl_info); act.addStretch()
        
        self.btn_clear = QPushButton("Limpar Campos")
        self.btn_clear.setFixedHeight(42); self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.setStyleSheet(f"QPushButton{{background:transparent;color:#475569;border:1px solid #CBD5E1;border-radius:8px;padding:0 24px;font-weight:bold;font-size:10pt;}}QPushButton:hover{{background:#F1F5F9;}}")
        
        self.btn_save = QPushButton("Salvar Histórico")
        self.btn_save.setFixedHeight(42); self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setStyleSheet(f"QPushButton{{background:{VERMELHO_ESC};color:#fff;border:none;border-radius:8px;padding:0 32px;font-weight:bold;font-size:10pt;}}QPushButton:hover{{background:{VERMELHO};}}")
        
        act.addWidget(self.btn_clear); act.addWidget(self.btn_save)
        g_ly.addSpacing(8)
        g_ly.addLayout(act)
        main.addWidget(self.grade_frame)

        # ── Tabela histórico salvo ─────────────────────────────────────
        sv = QFrame()
        sv.setStyleSheet(f"QFrame{{background:{BRANCO};border:1px solid #E2E8F0;border-radius:12px;}}")
        sv.setGraphicsEffect(shadow(12,(0,4),(0,0,0,10)))
        sv_ly = QVBoxLayout(sv); sv_ly.setContentsMargins(32,24,32,24); sv_ly.setSpacing(16)

        sh_row = QHBoxLayout()
        sh_row.addWidget(_lbl("VALORES ATUAIS NO BANCO DE DADOS", bold=True, size=9, color="#475569"))
        sh_row.addStretch()
        sv_ly.addLayout(sh_row)
        sep3 = QFrame(); sep3.setFrameShape(QFrame.Shape.HLine)
        sep3.setStyleSheet("background:#E2E8F0;border:none;"); sep3.setFixedHeight(1)
        sv_ly.addWidget(sep3)

        self.saved_grid = QGridLayout(); self.saved_grid.setSpacing(4)
        sv_ly.addLayout(self.saved_grid)
        main.addWidget(sv)

        # Signals
        self.btn_load.clicked.connect(self._load_historico)
        self.btn_save.clicked.connect(self._save_historico)
        self.btn_clear.clicked.connect(self._clear_inputs)
        self.sel_ind.currentIndexChanged.connect(self._on_indicador_changed)
        self.sel_sub.currentIndexChanged.connect(self._clear_inputs)
        self.sel_ano.currentIndexChanged.connect(self._load_historico)

    # ── Lógica ────────────────────────────────────────────────────────
    def _populate_selector(self):
        self.sel_ind.blockSignals(True)
        self.sel_ind.clear()
        for i in db.get_indicadores_ativos():
            self.sel_ind.addItem(f"{i['codigo_indicador']}  —  {i['nome_indicador']}", i['codigo_indicador'])
        self.sel_ind.blockSignals(False)
        self._on_indicador_changed()

    def _on_indicador_changed(self):
        cod = self.sel_ind.currentData()
        self.sel_sub.clear()
        if cod:
            for s in db.get_subindicadores(cod):
                self.sel_sub.addItem(s['nome_subindicador'], s['id'])
        self._clear_inputs()

    def _current_sub_id(self): return self.sel_sub.currentData()
    def _current_ano(self): return int(self.sel_ano.currentText())

    def _load_historico(self):
        sub_id = self._current_sub_id()
        ano    = self._current_ano()
        if not sub_id: return
        sub  = db.get_subindicador(sub_id)
        nome = sub['nome_subindicador'] if sub else f"ID:{sub_id}"
        self.grade_title.setText(f"Subindicador: {nome}  |  {ano}")

        hist = db.get_historico_subindicador(sub_id, [ano])
        dados = hist.get(ano, {})

        vals = []
        for mes in MESES:
            val = dados.get(mes)
            inp = self._inputs[mes]
            inp.setText(str(int(val)) if isinstance(val,float) and val==int(val) else str(val) if val is not None else "")
            cor = "#10B981" if val is not None else CINZA_BORDA
            inp.setStyleSheet(f"QLineEdit{{background:#fff;border:1.5px solid {cor};border-radius:6px;padding:4px 8px;text-align:center;color:#111827;}}QLineEdit:focus{{border-color:{VERMELHO_ESC};}}")
            if val is not None: vals.append(val)

        # Update mini KPIs
        self.kpi_preenchidos.setText(f"{len(vals)}/12")
        self.kpi_total.setText(f"{int(sum(vals))}" if vals else "—")
        med = sum(vals)/len(vals) if vals else None
        self.kpi_media.setText(f"{med:.1f}" if med is not None else "—")

        self.lbl_info.setText("")
        self._rebuild_saved_table(sub_id)

    def _rebuild_saved_table(self, sub_id):
        while self.saved_grid.count():
            it = self.saved_grid.takeAt(0)
            if it.widget(): it.widget().deleteLater()

        hist = db.get_historico_subindicador(sub_id)
        if not hist:
            lbl = _lbl("Nenhum dado salvo para este subindicador.", color="#9CA3AF", size=9)
            self.saved_grid.addWidget(lbl, 0, 0); return

        def _h(txt, col):
            l = _lbl(txt.upper(), bold=True, size=7, color="#9CA3AF")
            l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            l.setStyleSheet("color:#9CA3AF;letter-spacing:1px;background:transparent;border:none;padding:4px;")
            self.saved_grid.addWidget(l, 0, col)
        _h("Ano", 0)
        for ci, m in enumerate(MESES, 1): _h(m[:3], ci)

        for ri, ano in enumerate(sorted(hist.keys()), 1):
            la = _lbl(str(ano), bold=True, size=9, color="#374151")
            la.setAlignment(Qt.AlignmentFlag.AlignCenter)
            la.setStyleSheet(f"color:#374151;background:#F9FAFB;border:1px solid #E5E7EB;border-radius:4px;padding:4px;font-weight:bold;")
            self.saved_grid.addWidget(la, ri, 0)
            for ci, mes in enumerate(MESES, 1):
                val = hist[ano].get(mes)
                txt = str(int(val)) if isinstance(val,float) and val==int(val) else str(val) if val is not None else "–"
                cor = "#111827" if val is not None else "#D1D5DB"
                cell = _lbl(txt, size=9, color=cor)
                cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
                cell.setStyleSheet(f"color:{cor};background:transparent;border:none;padding:4px;")
                self.saved_grid.addWidget(cell, ri, ci)

    def _save_historico(self):
        sub_id = self._current_sub_id(); ano = self._current_ano()
        if not sub_id:
            self._st("⚠️ Selecione indicador e subindicador.", LARANJA); return
        saved = errors = 0
        for mes in MESES:
            txt = self._inputs[mes].text().strip().replace(",",".")
            if txt in ("","–"):
                db.delete_historico_mes(sub_id, ano, mes)
                continue
            try:
                if db.upsert_historico(sub_id, ano, mes, float(txt)): saved += 1
                else: errors += 1
            except ValueError: errors += 1
        
        if errors:
            self._st(f"⚠️ {errors} valores inválidos.", LARANJA)
        else:
            self._st(f"✅ Histórico salvo com sucesso!", VERDE)
            self._load_historico()

    def _clear_inputs(self):
        for inp in self._inputs.values():
            inp.clear()
            inp.setStyleSheet(f"QLineEdit{{background:#fff;border:1px solid #D1D5DB;border-radius:6px;padding:4px 8px;text-align:center;color:#111827;}}QLineEdit:focus{{border-color:{VERMELHO_ESC};}}")
        self.lbl_info.setText("")
        for attr in ["kpi_preenchidos","kpi_total","kpi_media"]:
            getattr(self, attr).setText("—")

    def _st(self, msg, cor):
        self.lbl_info.setText(msg)
        self.lbl_info.setStyleSheet(f"color:{cor};background:transparent;border:none;font-weight:bold;")
