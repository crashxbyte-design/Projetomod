"""
panel_base_dados.py - Tela Base de Dados com backend SQLite real.
"""
import os
import openpyxl
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QPushButton, QSizePolicy, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView,
    QTextEdit, QCheckBox, QComboBox, QLineEdit, QMessageBox,
    QSplitter, QDialog, QFileDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

import database as db
from styles import (
    VERMELHO, VERMELHO_ESC, BRANCO, CINZA_BG, CINZA_BORDA,
    CINZA_SUAVE, PRETO_TITULO, VERDE, LARANJA, PENDENTE_FG
)
from widgets import shadow
from mapping_db import STATUS_MAPEADO, STATUS_PENDENTE_PROCESSO, STATUS_PENDENTE_CONTROLE, STATUS_SEM_VINCULO

STATUS_LIST = [STATUS_MAPEADO, STATUS_PENDENTE_PROCESSO, STATUS_PENDENTE_CONTROLE, STATUS_SEM_VINCULO]
STATUS_CORES = {
    STATUS_MAPEADO:           (VERDE,       "#E8F5E9"),
    STATUS_PENDENTE_PROCESSO: (LARANJA,     "#FFF3E0"),
    STATUS_PENDENTE_CONTROLE: (PENDENTE_FG, "#FFEBEE"),
    STATUS_SEM_VINCULO:       (CINZA_SUAVE, "#F5F5F5"),
}

def _kpi(icon, title, value, sub, ic, bg):
    f = QFrame()
    f.setStyleSheet(f"QFrame{{background:{BRANCO};border:1px solid {CINZA_BORDA};border-radius:6px;}}")
    f.setGraphicsEffect(shadow(6,(0,2),(0,0,0,10)))
    f.setMinimumWidth(140)
    ly = QHBoxLayout(f); ly.setContentsMargins(14,12,14,12); ly.setSpacing(12)
    ico = QFrame(); ico.setFixedSize(44,44)
    ico.setStyleSheet(f"background:{bg};border-radius:22px;border:none;")
    il = QVBoxLayout(ico); il.setContentsMargins(0,0,0,0)
    il2 = QLabel(icon); il2.setFont(QFont("Segoe UI Emoji",20))
    il2.setAlignment(Qt.AlignmentFlag.AlignCenter)
    il2.setStyleSheet(f"color:{ic};background:transparent;border:none;")
    il.addWidget(il2); ly.addWidget(ico)
    tl = QVBoxLayout(); tl.setSpacing(2)
    t = QLabel(title.upper()); t.setFont(QFont("Segoe UI",7,QFont.Weight.Bold))
    t.setStyleSheet(f"color:{CINZA_SUAVE};background:transparent;border:none;")
    v = QLabel(str(value)); v.setFont(QFont("Segoe UI",20,QFont.Weight.Bold))
    v.setStyleSheet(f"color:{PRETO_TITULO};background:transparent;border:none;")
    s = QLabel(sub); s.setFont(QFont("Segoe UI",8))
    s_color = CINZA_SUAVE if ic == BRANCO else ic 
    s.setStyleSheet(f"color:{s_color};background:transparent;border:none;")
    for w in [t,v,s]: tl.addWidget(w)
    ly.addLayout(tl); return f

def _btn(txt, primary=False, outline_color=CINZA_BORDA, danger=False):
    b = QPushButton(txt); b.setFixedHeight(34)
    b.setFont(QFont("Segoe UI",9,QFont.Weight.Bold if primary or danger else QFont.Weight.Normal))
    if primary:
        b.setStyleSheet(f"QPushButton{{background:{VERMELHO_ESC};color:{BRANCO};border:none;border-radius:5px;padding:0 14px;}}QPushButton:hover{{background:{VERMELHO};}}")
    elif danger:
        b.setStyleSheet(f"QPushButton{{background:{BRANCO};color:{VERMELHO_ESC};border:1px solid {VERMELHO_ESC};border-radius:5px;padding:0 14px;}}QPushButton:hover{{background:#FFEBEE;}}")
    else:
        b.setStyleSheet(f"QPushButton{{background:{BRANCO};color:{PRETO_TITULO};border:1px solid {outline_color};border-radius:5px;padding:0 14px;}}QPushButton:hover{{background:#F5F5F5;}}")
    return b

class _FieldRow(QWidget):
    def __init__(self, label, widget, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;border:none;")
        ly = QVBoxLayout(self); ly.setContentsMargins(0,0,0,0); ly.setSpacing(3)
        if label:
            lbl = QLabel(label)
            lbl.setFont(QFont("Segoe UI",8))
            lbl.setStyleSheet(f"color:{PRETO_TITULO};background:transparent;border:none;")
            ly.addWidget(lbl)
        ly.addWidget(widget)

def _section_lbl(txt):
    l = QLabel(txt)
    l.setFont(QFont("Segoe UI",8,QFont.Weight.Bold))
    l.setStyleSheet(f"color:{PRETO_TITULO};background:transparent;border:none;letter-spacing:0.5px;")
    return l


class BaseDadosPanel(QWidget):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self._current_codigo = None
        self._original_record = None
        self._available_sheets = set()
        self._build_ui()
        self._load_table()
        if self.table.rowCount() > 0:
            self.table.selectRow(0)

    # ── UI ──────────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root.addWidget(scroll)
        container = QWidget(); container.setStyleSheet(f"background:{CINZA_BG};")
        scroll.setWidget(container)
        main = QVBoxLayout(container); main.setContentsMargins(24,20,24,24); main.setSpacing(16)

        # KPI Row
        self.kpi_row = QHBoxLayout(); self.kpi_row.setSpacing(14)
        main.addLayout(self.kpi_row)
        self._refresh_kpis()

        # Toolbar
        tb = QHBoxLayout(); tb.setSpacing(10)
        self.btn_import   = _btn("📗  Importar do Excel")
        self.btn_refresh  = _btn("🔄  Atualizar Vínculos")
        self.btn_new      = _btn("＋  Novo Registro", primary=True)
        for b in [self.btn_import, self.btn_refresh, self.btn_new]:
            tb.addWidget(b)
        
        tb.addStretch()
        
        self.f_busca = QLineEdit()
        self.f_busca.setPlaceholderText("🔍 Buscar indicador ou código...")
        self.f_busca.setFont(QFont("Segoe UI",9))
        self.f_busca.setFixedHeight(34)
        self.f_busca.setMinimumWidth(260)
        self.f_busca.setStyleSheet(f"QLineEdit{{background:{BRANCO};border:1px solid {CINZA_BORDA};border-radius:4px;padding:0 8px;}}")
        tb.addWidget(self.f_busca)
        
        main.addLayout(tb)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle{background:transparent;}")
        splitter.setHandleWidth(12)

        # Tabela
        tf = QFrame()
        tf.setStyleSheet(f"QFrame{{background:{BRANCO};border:1px solid {CINZA_BORDA};border-radius:6px;}}")
        tf.setGraphicsEffect(shadow(6,(0,2),(0,0,0,10)))
        tl = QVBoxLayout(tf); tl.setContentsMargins(0,0,0,0)

        COLS = ["Código","Indicador","Usa Dados\nOperacionais","Aba Origem",
                "Campo Origem","Resultado\nRepresenta","Subindicadores",
                "Status do Mapeamento","Observações"]
        self.table = QTableWidget(0, len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(f"""
            QTableWidget{{border:none;font-size:9pt;gridline-color:{CINZA_BORDA};}}
            QTableWidget::item{{padding:5px 8px;color:{PRETO_TITULO};}}
            QTableWidget::item:selected{{background:#FFEBEE;color:{PRETO_TITULO};}}
            QHeaderView::section{{background:{VERMELHO_ESC};color:{BRANCO};font-weight:bold;
                font-size:8pt;padding:7px 8px;border:none;border-right:1px solid #8B0000;}}
            QTableWidget::item:alternate{{background:#FAFAFA;}}
        """)
        hdr = self.table.horizontalHeader()
        widths = [110,0,80,100,120,100,80,130,120]
        for i, w in enumerate(widths):
            if w == 0: hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            else:      hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(i, w)
        tl.addWidget(self.table)
        
        # Paginação Footer
        pag_ly = QHBoxLayout()
        pag_ly.setContentsMargins(12, 6, 12, 6)
        self.footer_lbl = QLabel("")
        self.footer_lbl.setFont(QFont("Segoe UI",8))
        self.footer_lbl.setStyleSheet(f"color:{CINZA_SUAVE};background:transparent;border:none;")
        pag_ly.addWidget(self.footer_lbl)
        pag_ly.addStretch()
        
        for ptxt in ["Primeiro", "< Anterior", "1", "Próximo >", "Último"]:
            pb = QPushButton(ptxt)
            pb.setFont(QFont("Segoe UI",8, QFont.Weight.Bold if ptxt == "1" else QFont.Weight.Normal))
            pb.setFixedHeight(24)
            if ptxt == "1":
                pb.setStyleSheet(f"QPushButton{{background:{VERMELHO_ESC};color:{BRANCO};border:none;border-radius:3px;padding:0 8px;}}")
            else:
                pb.setStyleSheet(f"QPushButton{{background:{BRANCO};color:{PRETO_TITULO};border:1px solid {CINZA_BORDA};border-radius:3px;padding:0 8px;}}QPushButton:hover{{background:#F5F5F5;}}")
            pag_ly.addWidget(pb)
        
        tl.addLayout(pag_ly)
        splitter.addWidget(tf)

        # Painel lateral editável
        det_frame = QFrame()
        det_frame.setMinimumWidth(290); det_frame.setMaximumWidth(360)
        det_frame.setStyleSheet(f"QFrame{{background:{BRANCO};border:1px solid {CINZA_BORDA};border-radius:6px;}}")
        det_frame.setGraphicsEffect(shadow(6,(0,2),(0,0,0,10)))
        det_outer = QVBoxLayout(det_frame); det_outer.setContentsMargins(0,0,0,0); det_outer.setSpacing(0)

        det_hdr = QLabel("DETALHES DO INDICADOR SELECIONADO")
        det_hdr.setFont(QFont("Segoe UI",8,QFont.Weight.Bold))
        det_hdr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        det_hdr.setStyleSheet(f"color:{BRANCO};background:{VERMELHO_ESC};border-top-left-radius:6px;border-top-right-radius:6px;padding:9px;border:none;")
        det_outer.addWidget(det_hdr)

        det_scroll = QScrollArea(); det_scroll.setWidgetResizable(True)
        det_scroll.setStyleSheet("border:none;background:transparent;")
        det_inner = QWidget(); det_inner.setStyleSheet("background:transparent;")
        self.det_ly = QVBoxLayout(det_inner); self.det_ly.setContentsMargins(16,16,16,16); self.det_ly.setSpacing(10)
        det_scroll.setWidget(det_inner)
        det_outer.addWidget(det_scroll, 1)

        # Campos editáveis
        def _edit(placeholder=""):
            w = QLineEdit(); w.setPlaceholderText(placeholder)
            w.setFont(QFont("Segoe UI",9))
            w.setStyleSheet(f"QLineEdit{{background:{BRANCO};border:1px solid {CINZA_BORDA};border-radius:4px;padding:5px 8px;color:{PRETO_TITULO};}}QLineEdit:focus{{border-color:{VERMELHO};}}")
            return w
        def _combo(editable=False):
            w = QComboBox()
            w.setEditable(editable)
            w.setFont(QFont("Segoe UI",9))
            w.setStyleSheet(f"QComboBox{{background:{BRANCO};border:1px solid {CINZA_BORDA};border-radius:4px;padding:4px 8px;color:{PRETO_TITULO};}}QComboBox:focus{{border-color:{VERMELHO};}} QComboBox::drop-down{{border:none;}}")
            return w

        self.f_codigo = _edit("Ex: SP.IND.012")
        self.f_nome   = _edit("Nome do indicador")
        
        self.det_ly.addWidget(_FieldRow("Código", self.f_codigo))
        self.det_ly.addWidget(_FieldRow("Indicador", self.f_nome))
        self.det_ly.addSpacing(4)
        
        self.det_ly.addWidget(_section_lbl("CLASSIFICAÇÃO"))

        self.f_tipo = _combo()
        self.f_tipo.addItems(["Operacional", "Estratégico", "Tático"])
        self.f_periodo = _combo()
        self.f_periodo.addItems(["Mensal", "Bimestral", "Trimestral", "Semestral", "Anual"])
        self.f_unidade = _edit("Ex: evasões, óbitos, %")
        self.det_ly.addWidget(_FieldRow("Tipo", self.f_tipo))
        self.det_ly.addWidget(_FieldRow("Periodicidade", self.f_periodo))
        self.det_ly.addWidget(_FieldRow("Unidade", self.f_unidade))
        self.det_ly.addSpacing(4)

        self.det_ly.addWidget(_section_lbl("META"))

        self.f_meta_texto  = _edit("Ex: ≤ 3  ou  ≥ 95%")
        self.f_meta_numero = _edit("Número para cálculo automático")
        self.chk_menor = QCheckBox("Menor valor é melhor")
        self.chk_menor.setStyleSheet(f"color:{PRETO_TITULO};background:transparent;border:none;font-size:9pt;")
        self.det_ly.addWidget(_FieldRow("Meta (texto)", self.f_meta_texto))
        self.det_ly.addWidget(_FieldRow("Meta (número)", self.f_meta_numero))
        self.det_ly.addWidget(self.chk_menor)
        self.det_ly.addSpacing(4)

        self.det_ly.addWidget(_section_lbl("MAPEAMENTO"))

        self.f_aba    = _combo(editable=True)
        self.f_campo  = _combo(editable=True)
        self.f_result = _combo(editable=True)
        self.f_modo   = _combo(editable=True)
        self.f_modo.addItems(["2025 x 2026", "2024 x 2025"])

        self.det_ly.addWidget(_FieldRow("Aba (Origem)", self.f_aba))
        self.det_ly.addWidget(_FieldRow("Campo (Origem)", self.f_campo))
        self.det_ly.addWidget(_FieldRow("Resultado Representa", self.f_result))
        self.det_ly.addWidget(_FieldRow("Modo de Comparação", self.f_modo))
        
        self.det_ly.addSpacing(4)

        self.det_ly.addSpacing(4)
        self.det_ly.addWidget(_section_lbl("OPÇÕES"))
        self.chk_usa  = QCheckBox("Utiliza dados operacionais"); self.chk_usa.setStyleSheet(f"color:{PRETO_TITULO};background:transparent;border:none;font-size:9pt;")
        self.chk_sub  = QCheckBox("Possui subindicadores");      self.chk_sub.setStyleSheet(f"color:{PRETO_TITULO};background:transparent;border:none;font-size:9pt;")
        self.chk_ativo= QCheckBox("Indicador ativo");             self.chk_ativo.setStyleSheet(f"color:{PRETO_TITULO};background:transparent;border:none;font-size:9pt;")
        self.det_ly.addWidget(self.chk_usa)
        self.det_ly.addWidget(self.chk_sub)
        self.det_ly.addWidget(self.chk_ativo)
        self.det_ly.addSpacing(4)
        
        self.det_ly.addWidget(_section_lbl("OBSERVAÇÕES"))
        
        self.f_obs    = QTextEdit()
        self.f_obs.setFont(QFont("Segoe UI",9)); self.f_obs.setMaximumHeight(70)
        self.f_obs.setStyleSheet(f"QTextEdit{{background:{BRANCO};border:1px solid {CINZA_BORDA};border-radius:4px;padding:4px;color:{PRETO_TITULO};}}QTextEdit:focus{{border-color:{VERMELHO};}}")
        self.det_ly.addWidget(self.f_obs)
        
        self.lbl_char_count = QLabel("0 / 500 caracteres")
        self.lbl_char_count.setFont(QFont("Segoe UI",7))
        self.lbl_char_count.setStyleSheet(f"color:{CINZA_SUAVE};background:transparent;border:none;")
        self.det_ly.addWidget(self.lbl_char_count)
        self.f_obs.textChanged.connect(self._update_char_count)

        self.det_ly.addStretch()

        # Botões de Ação no Painel Direito
        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        self.btn_cancel = _btn("Cancelar")
        self.btn_save   = _btn("Salvar Alterações", primary=True)
        btn_row.addWidget(self.btn_cancel); btn_row.addWidget(self.btn_save, 1)
        self.det_ly.addLayout(btn_row)
        
        self.btn_delete = _btn("Excluir Indicador", danger=True)
        self.det_ly.addWidget(self.btn_delete)

        splitter.addWidget(det_frame)
        splitter.setSizes([880, 300])
        main.addWidget(splitter, 1)

        # Info bar
        info = QLabel("ℹ️  Importe arquivos Excel para atualizar a base. Todos os mapeamentos salvos no painel direito são armazenados de forma persistente no banco SQLite local.")
        info.setFont(QFont("Segoe UI",8)); info.setWordWrap(True)
        info.setStyleSheet(f"color:{CINZA_SUAVE};background:transparent;border:none;padding:8px 0px;")
        main.addWidget(info)
        
        # Status Label para Mensagens Globais
        self.lbl_status = QLabel("")
        self.lbl_status.setFont(QFont("Segoe UI",8, QFont.Weight.Bold))
        self.lbl_status.setStyleSheet("background:transparent;border:none;")
        main.addWidget(self.lbl_status)

        # Signals
        self.table.selectionModel().selectionChanged.connect(self._on_select)
        self.btn_save.clicked.connect(self._save)
        self.btn_cancel.clicked.connect(self._cancel)
        self.btn_delete.clicked.connect(self._delete_record)
        self.btn_new.clicked.connect(self._new_record)
        self.btn_import.clicked.connect(self._import_excel)
        self.btn_refresh.clicked.connect(self._refresh_links)
        self.f_busca.textChanged.connect(self._filter_table)

    # ── Lógica e Dados ──────────────────────────────────────────────────────
    def _update_char_count(self):
        txt = self.f_obs.toPlainText()
        self.lbl_char_count.setText(f"{len(txt)} / 500 caracteres")

    def _refresh_kpis(self):
        while self.kpi_row.count():
            item = self.kpi_row.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        s = db.get_stats()
        self.kpi_row.addWidget(_kpi("🗺️","Indicadores Mapeados",s["mapeados"],f"{s['pct_mapeados']}% do total",BRANCO,"#2E7D32"))
        self.kpi_row.addWidget(_kpi("🔗","Sem Vínculo",s["sem_vinculo"],f"{s['pct_sem']}% do total",BRANCO,"#616161"))
        self.kpi_row.addWidget(_kpi("⏱","Pendentes",s["pendentes"],f"{s['pct_pend']}% do total",BRANCO,"#E65100"))
        self.kpi_row.addWidget(_kpi("🛢","Linhas no Banco",s["linhas_banco"],"100% do total",BRANCO,"#1565C0"))
        self.kpi_row.addWidget(_kpi("☁","Última Importação","Excel",s.get("ultima_import","—").replace("\n", " - "),BRANCO,"#6A1B9A"))

    def _badge(self, text, status):
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI",8,QFont.Weight.Bold))
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cor, bg = STATUS_CORES.get(status, (CINZA_SUAVE, "#F5F5F5"))
        lbl.setStyleSheet(f"color:{cor};background:{bg};border:1px solid {cor};border-radius:4px;margin:4px 10px;")
        return lbl

    def _load_table(self):
        rows = db.get_all()
        self.table.setRowCount(len(rows))
        
        abas = self._available_sheets.copy(); campos = set(); results = set()
        
        for r, m in enumerate(rows):
            if m.get("aba_origem_excel"): abas.add(m.get("aba_origem_excel"))
            if m.get("campo_origem"): campos.add(m.get("campo_origem"))
            if m.get("resultado_representa"): results.add(m.get("resultado_representa"))
            
            def ci(txt, center=False):
                it = QTableWidgetItem(str(txt) if txt else "–")
                if center: it.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
                return it
            
            is_selected = self._current_codigo == m["codigo_indicador"]
            rad = "◉ " if is_selected else "○ "
            it_cod = ci(rad + m["codigo_indicador"])
            if is_selected: it_cod.setForeground(QColor(VERMELHO))
            self.table.setItem(r, 0, it_cod)
            
            self.table.setItem(r, 1, ci(m["nome_indicador"]))
            usa = "Sim" if m.get("usa_dados_operacionais") else "Não"
            it_usa = ci(usa, True); it_usa.setForeground(QColor(VERDE if usa=="Sim" else PENDENTE_FG))
            self.table.setItem(r, 2, it_usa)
            self.table.setItem(r, 3, ci(m.get("aba_origem_excel") or "–", True))
            self.table.setItem(r, 4, ci(m.get("campo_origem") or "–"))
            self.table.setItem(r, 5, ci(m.get("resultado_representa") or "–"))
            
            sub = str(m.get("subindicadores_existem", 0))
            it_sub = ci(sub, True); 
            self.table.setItem(r, 6, it_sub)
            
            st = m.get("status_mapeamento") or STATUS_SEM_VINCULO
            self.table.setCellWidget(r, 7, self._badge(st, st))
            
            self.table.setItem(r, 8, ci(m.get("observacoes") or ""))
            self.table.setRowHeight(r, 38)
            
        self.footer_lbl.setText(f"Exibindo 1 a {len(rows)} de {len(rows)} registros")
        self._refresh_kpis()
        
        cur_aba = self.f_aba.currentText()
        cur_campo = self.f_campo.currentText()
        cur_result = self.f_result.currentText()
        
        self.f_aba.clear(); self.f_aba.addItems(sorted(list(abas)))
        self.f_campo.clear(); self.f_campo.addItems(sorted(list(campos)))
        self.f_result.clear(); self.f_result.addItems(sorted(list(results)))
        
        self.f_aba.setCurrentText(cur_aba)
        self.f_campo.setCurrentText(cur_campo)
        self.f_result.setCurrentText(cur_result)
        
        self._filter_table()

    def _filter_table(self):
        txt = self.f_busca.text().lower()
        visible_count = 0
        for row in range(self.table.rowCount()):
            cod = self.table.item(row, 0).text().lower().replace("◉ ", "").replace("○ ", "")
            nome = self.table.item(row, 1).text().lower()
            if txt in cod or txt in nome:
                self.table.setRowHidden(row, False)
                visible_count += 1
            else:
                self.table.setRowHidden(row, True)
        self.footer_lbl.setText(f"Exibindo 1 a {visible_count} de {self.table.rowCount()} registros")

    def _on_select(self, selected, _):
        rows = [i.row() for i in selected.indexes()]
        if not rows: return
        cod = self.table.item(rows[0], 0).text().replace("◉ ", "").replace("○ ", "")
        
        m = db.get_by_codigo(cod)
        if not m: return
        
        self._current_codigo = m["codigo_indicador"]
        for r in range(self.table.rowCount()):
            it = self.table.item(r, 0)
            if it:
                r_cod = it.text().replace("◉ ", "").replace("○ ", "")
                if r == rows[0]:
                    it.setText("◉ " + r_cod)
                    it.setForeground(QColor(VERMELHO))
                else:
                    it.setText("○ " + r_cod)
                    it.setForeground(QColor(PRETO_TITULO))
        
        self._original_record = dict(m)
        self._fill_fields(m)

    def _fill_fields(self, m):
        self.f_codigo.setText(m.get("codigo_indicador") or "")
        self.f_nome.setText(m.get("nome_indicador") or "")
        # Classificação
        tipo = m.get("tipo") or "Operacional"
        idx = self.f_tipo.findText(tipo)
        self.f_tipo.setCurrentIndex(idx if idx >= 0 else 0)
        per = m.get("periodicidade") or "Mensal"
        idx = self.f_periodo.findText(per)
        self.f_periodo.setCurrentIndex(idx if idx >= 0 else 0)
        self.f_unidade.setText(m.get("unidade") or "")
        # Meta
        self.f_meta_texto.setText(m.get("meta_texto") or "")
        meta_num = m.get("meta_numero")
        self.f_meta_numero.setText(str(int(meta_num)) if isinstance(meta_num, float) and meta_num == int(meta_num) else str(meta_num) if meta_num is not None else "")
        self.chk_menor.setChecked(bool(m.get("menor_melhor", 1)))
        # Mapeamento
        self.f_aba.setCurrentText(m.get("aba_origem_excel") or "")
        self.f_campo.setCurrentText(m.get("campo_origem") or "")
        self.f_result.setCurrentText(m.get("resultado_representa") or "")
        self.f_modo.setCurrentText(m.get("modo_comparacao") or "2025 x 2026")
        # Opções
        self.f_obs.setPlainText(m.get("observacoes") or "")
        self.chk_usa.setChecked(bool(m.get("usa_dados_operacionais", 1)))
        self.chk_sub.setChecked(int(m.get("subindicadores_existem", 0)) > 0)
        self.chk_ativo.setChecked(bool(m.get("indicador_ativo", 1)))
        self.f_codigo.setReadOnly(True)
        self.f_codigo.setStyleSheet(f"QLineEdit{{background:#F0F0F0;border:1px solid {CINZA_BORDA};border-radius:4px;padding:5px 8px;color:{CINZA_SUAVE};}}")
        self.btn_delete.setVisible(True)

    def _collect_fields(self) -> dict:
        meta_num = None
        try:
            v = self.f_meta_numero.text().strip().replace(",",".")
            meta_num = float(v) if v else None
        except ValueError:
            pass
        return {
            "codigo_indicador":       self.f_codigo.text().strip(),
            "nome_indicador":         self.f_nome.text().strip(),
            "tipo":                   self.f_tipo.currentText(),
            "periodicidade":          self.f_periodo.currentText(),
            "unidade":                self.f_unidade.text().strip() or None,
            "meta_texto":             self.f_meta_texto.text().strip() or None,
            "meta_numero":            meta_num,
            "menor_melhor":           1 if self.chk_menor.isChecked() else 0,
            "usa_dados_operacionais": 1 if self.chk_usa.isChecked() else 0,
            "aba_origem_excel":       self.f_aba.currentText().strip() or None,
            "campo_origem":           self.f_campo.currentText().strip() or None,
            "resultado_representa":   self.f_result.currentText().strip() or None,
            "subindicadores_existem": 1 if self.chk_sub.isChecked() else 0,
            "subindicadores_status":  "",
            "status_mapeamento":      STATUS_SEM_VINCULO,
            "observacoes":            self.f_obs.toPlainText().strip() or None,
            "indicador_ativo":        1 if self.chk_ativo.isChecked() else 0,
            "modo_comparacao":        self.f_modo.currentText().strip(),
        }

    # ── Ações ───────────────────────────────────────────────────────────────
    def _save(self):
        record = self._collect_fields()
        if not record["codigo_indicador"]:
            self.lbl_status.setText("⚠️ O Código do indicador é obrigatório.")
            self.lbl_status.setStyleSheet(f"color:{LARANJA};")
            return
        
        if record["aba_origem_excel"] and record["campo_origem"]:
            record["status_mapeamento"] = STATUS_MAPEADO
        elif not record["aba_origem_excel"] and not record["campo_origem"]:
            record["status_mapeamento"] = STATUS_SEM_VINCULO
        else:
            record["status_mapeamento"] = STATUS_PENDENTE_PROCESSO

        ok = db.upsert(record)
        if ok:
            self.lbl_status.setText(f"✅ O indicador '{record['codigo_indicador']}' foi salvo com sucesso no banco!")
            self.lbl_status.setStyleSheet(f"color:{VERDE};")
            self._current_codigo = record["codigo_indicador"]
            self._load_table()
        else:
            self.lbl_status.setText("❌ Ocorreu um erro interno ao salvar as alterações.")
            self.lbl_status.setStyleSheet(f"color:{VERMELHO};")

    def _cancel(self):
        if self._original_record:
            self._fill_fields(self._original_record)
            self.lbl_status.setText("↩️ Alterações não salvas foram revertidas.")
            self.lbl_status.setStyleSheet(f"color:{CINZA_SUAVE};")
        else:
            if self.table.rowCount() > 0:
                self.table.selectRow(0)

    def _new_record(self):
        self._current_codigo = None
        self._original_record = None
        blank = {k: "" for k in ["codigo_indicador","nome_indicador","aba_origem_excel",
                                   "campo_origem","resultado_representa","observacoes"]}
        blank.update({"usa_dados_operacionais":1,"subindicadores_existem":0,
                      "indicador_ativo":1,"status_mapeamento":STATUS_SEM_VINCULO,
                      "modo_comparacao": "2025 x 2026"})
        
        self.f_codigo.setReadOnly(False)
        self.f_codigo.setStyleSheet(f"QLineEdit{{background:{BRANCO};border:1px solid {CINZA_BORDA};border-radius:4px;padding:5px 8px;color:{PRETO_TITULO};}}QLineEdit:focus{{border-color:{VERMELHO};}}")
        self._fill_fields(blank)
        self.f_codigo.clear()
        self.btn_delete.setVisible(False)
        self.table.clearSelection()
        
        self.lbl_status.setText("📝 Criando novo indicador. Preencha os campos e clique em Salvar.")
        self.lbl_status.setStyleSheet(f"color:{LARANJA};")
        self.f_codigo.setFocus()

    def _delete_record(self):
        cod = self.f_codigo.text().strip()
        if not cod: return
        
        reply = QMessageBox.question(self, "Confirmação de Exclusão", 
                                     f"Tem certeza que deseja remover o indicador {cod} definitivamente do banco de dados?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                     QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            if db.delete_by_codigo(cod):
                self.lbl_status.setText(f"🗑️ Indicador '{cod}' removido.")
                self.lbl_status.setStyleSheet(f"color:{VERDE};")
                self._current_codigo = None
                self._load_table()
                if self.table.rowCount() > 0:
                    self.table.selectRow(0)
                else:
                    self._new_record()
            else:
                self.lbl_status.setText("❌ Erro ao remover.")
                self.lbl_status.setStyleSheet(f"color:{VERMELHO};")

    def _import_excel(self):
        path, _ = QFileDialog.getOpenFileName(self, "Selecionar Planilha Operacional", "", "Excel Files (*.xlsx)")
        if not path: return
        
        try:
            wb = openpyxl.load_workbook(path, read_only=True)
            self._available_sheets = set(wb.sheetnames)
            wb.close()
        except Exception as e:
            QMessageBox.warning(self, "Aviso", f"Não foi possível ler as abas do arquivo: {e}")
            
        count, msg = db.import_from_excel(path)
        if count > 0:
            QMessageBox.information(self, "Importação Concluída", msg)
            self._load_table()
            self.lbl_status.setText(f"📥 {msg}")
            self.lbl_status.setStyleSheet(f"color:{VERDE};")
        else:
            QMessageBox.warning(self, "Importação", msg)

    def _refresh_links(self):
        rows = db.get_all()
        updated = 0
        for m in rows:
            has_aba   = bool(m.get("aba_origem_excel"))
            has_campo = bool(m.get("campo_origem"))
            cur_st    = m.get("status_mapeamento","")
            new_st    = STATUS_SEM_VINCULO
            if has_aba and has_campo:
                new_st = STATUS_MAPEADO
            elif has_aba or has_campo:
                new_st = STATUS_PENDENTE_PROCESSO
                
            if cur_st != new_st:
                m["status_mapeamento"] = new_st
                db.upsert(m); updated += 1
                
        self._load_table()
        self.lbl_status.setText(f"🔄 Status dos vínculos atualizados. {updated} indicadores alterados automaticamente.")
        self.lbl_status.setStyleSheet(f"color:{VERDE};")
