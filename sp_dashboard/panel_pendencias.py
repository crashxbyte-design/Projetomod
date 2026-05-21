"""
panel_pendencias.py - Tela de Pendências e Observações.
"""

import database as db
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QSplitter, QComboBox, QLineEdit, QTextEdit, QPushButton,
    QSizePolicy, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QCursor

from styles import (
    VERMELHO_ESC, BRANCO, CINZA_BG, CINZA_BORDA,
    CINZA_SUAVE, PRETO_TITULO, PENDENTE_FG, LARANJA, VERDE,
    CINZA_META, CINZA_TEXTO, COMBO_DROPDOWN_CSS
)
from widgets import SectionTitle, shadow


class PendenciaKPI(QFrame):
    def __init__(self, title, value, color, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background: {BRANCO};
                border: 1px solid {CINZA_BORDA};
                border-radius: 8px;
                border-top: 4px solid {color};
            }}
        """)
        self.setGraphicsEffect(shadow(4, (0, 2), (0, 0, 0, 15)))
        ly = QVBoxLayout(self)
        ly.setContentsMargins(16, 12, 16, 12)
        ly.setSpacing(4)
        
        lbl_t = QLabel(title.upper())
        lbl_t.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        lbl_t.setStyleSheet(f"color: {CINZA_SUAVE}; border: none;")
        
        lbl_v = QLabel(str(value))
        lbl_v.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        lbl_v.setStyleSheet(f"color: {PRETO_TITULO}; border: none;")
        
        ly.addWidget(lbl_t)
        ly.addWidget(lbl_v)


class PendenciaItemCard(QFrame):
    clicked = Signal(dict)
    
    def __init__(self, data, is_selected=False, parent=None):
        super().__init__(parent)
        self.data = data
        self.is_selected = is_selected
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        self._update_selection(is_selected)
        
        ly = QVBoxLayout(self)
        ly.setContentsMargins(16, 12, 16, 12)
        ly.setSpacing(8)
        
        h1 = QHBoxLayout()
        h1.setSpacing(8)
        
        cod = QLabel(self.data['codigo'])
        cod.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        cod.setStyleSheet(f"color: {PRETO_TITULO}; border: none; background: transparent;")
        h1.addWidget(cod)
        
        badge = QLabel(self.data['nivel'])
        badge.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        cor = PENDENTE_FG if self.data['nivel'] == 'CRÍTICO' else LARANJA
        badge.setStyleSheet(f"""
            color: {cor}; background: transparent; border: 1px solid {cor};
            border-radius: 4px; padding: 2px 6px;
        """)
        h1.addWidget(badge)
        h1.addStretch()
        ly.addLayout(h1)
        
        tit = QLabel(self.data['titulo'])
        tit.setFont(QFont("Segoe UI", 10))
        tit.setStyleSheet(f"color: {CINZA_SUAVE}; border: none; background: transparent;")
        tit.setWordWrap(True)
        ly.addWidget(tit)
        
        h2 = QHBoxLayout()
        resp = QLabel(f"👤 {self.data.get('responsavel', 'Não definido')}")
        resp.setFont(QFont("Segoe UI", 8))
        resp.setStyleSheet("color: #64748B; border: none; background: transparent;")
        h2.addWidget(resp)
        
        prazo = QLabel(f"📅 {self.data.get('prazo', 'Sem prazo')}")
        prazo.setFont(QFont("Segoe UI", 8))
        prazo.setStyleSheet("color: #64748B; border: none; background: transparent;")
        h2.addWidget(prazo)
        h2.addStretch()
        
        ly.addLayout(h2)

    def _update_selection(self, is_selected):
        self.is_selected = is_selected
        bg = "#F8FAFC" if is_selected else BRANCO
        border_col = VERMELHO_ESC if is_selected else CINZA_BORDA
        cor = PENDENTE_FG if self.data['nivel'] == 'CRÍTICO' else LARANJA
        self.setStyleSheet(f"""
            PendenciaItemCard {{
                background: {bg};
                border: 1.5px solid {border_col};
                border-left: 4px solid {cor};
                border-radius: 6px;
            }}
            PendenciaItemCard:hover {{
                background: #F1F5F9;
                border: 1.5px solid {CINZA_SUAVE};
                border-left: 4px solid {cor};
            }}
        """)

    def mousePressEvent(self, event):
        self.clicked.emit(self.data)
        super().mousePressEvent(event)


class PendenciaDetailPanel(QFrame):
    data_saved = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_editing = False
        self.current_data = None
        self.setStyleSheet(f"""
            PendenciaDetailPanel {{
                background: {BRANCO};
                border: 1px solid {CINZA_BORDA};
                border-radius: 8px;
            }}
        """)
        self.ly = QVBoxLayout(self)
        self.ly.setContentsMargins(32, 32, 32, 32)
        self.ly.setSpacing(24)
        self.set_empty()
        
    def set_empty(self):
        self._clear()
        lbl = QLabel("Selecione uma pendência na lista para visualizar os detalhes.")
        lbl.setFont(QFont("Segoe UI", 11))
        lbl.setStyleSheet(f"color: {CINZA_SUAVE}; border: none;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ly.addStretch()
        self.ly.addWidget(lbl)
        self.ly.addStretch()
        
    def _clear(self):
        while self.ly.count():
            item = self.ly.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
                
    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def update_detail(self, data, edit_mode=False):
        self.current_data = data
        self.is_editing = edit_mode
        self._clear()
        cor = PENDENTE_FG if data['nivel'] == 'CRÍTICO' else LARANJA
        
        # Cabeçalho da Pendência
        hdr = QHBoxLayout()
        cod_tit = QVBoxLayout()
        cod_tit.setSpacing(4)
        
        lbl_cod = QLabel(data['codigo'])
        lbl_cod.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        lbl_cod.setStyleSheet(f"color: {PRETO_TITULO}; border: none;")
        cod_tit.addWidget(lbl_cod)
        
        lbl_tit = QLabel(data['titulo'])
        lbl_tit.setFont(QFont("Segoe UI", 12))
        lbl_tit.setStyleSheet(f"color: {CINZA_SUAVE}; border: none;")
        lbl_tit.setWordWrap(True)
        cod_tit.addWidget(lbl_tit)
        
        hdr.addLayout(cod_tit, 1)
        
        # Botões de Ação
        if not self.is_editing:
            btn_edit = QPushButton("✏️ Editar")
            btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_edit.setStyleSheet(f"background: #F1F5F9; border: 1px solid {CINZA_BORDA}; border-radius: 6px; padding: 6px 14px; color: {PRETO_TITULO}; font-weight: bold;")
            btn_edit.clicked.connect(lambda: self.update_detail(self.current_data, True))
            hdr.addWidget(btn_edit, 0, Qt.AlignmentFlag.AlignTop)
        else:
            btn_cancel = QPushButton("Cancelar")
            btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_cancel.setStyleSheet(f"background: transparent; border: 1px solid {CINZA_BORDA}; border-radius: 6px; padding: 6px 14px; color: {CINZA_SUAVE}; font-weight: bold;")
            btn_cancel.clicked.connect(lambda: self.update_detail(self.current_data, False))
            
            btn_save = QPushButton("💾 Salvar")
            btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_save.setStyleSheet(f"background: {VERDE}; border: none; border-radius: 6px; padding: 6px 16px; color: {BRANCO}; font-weight: bold;")
            btn_save.clicked.connect(self._save_changes)
            
            hdr.addWidget(btn_cancel, 0, Qt.AlignmentFlag.AlignTop)
            hdr.addWidget(btn_save, 0, Qt.AlignmentFlag.AlignTop)
        
        badge = QLabel(data['nivel'])
        badge.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        badge.setStyleSheet(f"""
            color: {BRANCO}; background: {cor}; border: none;
            border-radius: 6px; padding: 6px 14px;
        """)
        hdr.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
        self.ly.addLayout(hdr)
        
        # Grid de Metadados
        grid = QGridLayout()
        grid.setSpacing(20)
        
        def _field_lbl(title, val):
            v = QVBoxLayout()
            v.setSpacing(4)
            t = QLabel(title.upper())
            t.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            t.setStyleSheet(f"color: {CINZA_META}; border: none;")
            l = QLabel(val if str(val).strip() else "Não informado")
            l.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
            l.setStyleSheet(f"color: {PRETO_TITULO}; border: none;")
            l.setWordWrap(True)
            v.addWidget(t)
            v.addWidget(l)
            return v
            
        def _field_edit(title, widget):
            v = QVBoxLayout()
            v.setSpacing(4)
            t = QLabel(title.upper())
            t.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            t.setStyleSheet(f"color: {VERMELHO_ESC}; border: none;")
            v.addWidget(t)
            v.addWidget(widget)
            return v
            
        if self.is_editing:
            self.input_resp = QLineEdit(data.get("responsavel", ""))
            self.input_resp.setStyleSheet(f"background:#F8FAFC;border:1px solid {CINZA_BORDA};border-radius:6px;padding:8px 12px;color:{PRETO_TITULO};font-size:10pt;")
            self.input_prazo = QLineEdit(str(data.get("prazo", "")))
            self.input_prazo.setStyleSheet(f"background:#F8FAFC;border:1px solid {CINZA_BORDA};border-radius:6px;padding:8px 12px;color:{PRETO_TITULO};font-size:10pt;")
            
            grid.addLayout(_field_edit("Responsável", self.input_resp), 0, 0)
            grid.addLayout(_field_edit("Prazo de Ação (ex: 15/05)", self.input_prazo), 0, 1)
        else:
            grid.addLayout(_field_lbl("Responsável", data.get("responsavel", "")), 0, 0)
            grid.addLayout(_field_lbl("Prazo de Ação", data.get("prazo", "")), 0, 1)
        
        self.ly.addLayout(grid)
        
        # Linha Separadora
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(f"background: {CINZA_BORDA}; border: none;")
        div.setFixedHeight(1)
        self.ly.addWidget(div)
        
        # Scroll para os campos textuais ricos
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        sc_container = QWidget()
        sc_container.setStyleSheet("background: transparent;")
        sc_ly = QVBoxLayout(sc_container)
        sc_ly.setContentsMargins(0, 0, 12, 0)
        sc_ly.setSpacing(24)
        
        def _rich_lbl(title, text):
            v = QVBoxLayout()
            v.setSpacing(8)
            t = QLabel(title.upper())
            t.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            t.setStyleSheet(f"color: {PRETO_TITULO}; border: none;")
            
            f = QFrame()
            f.setStyleSheet(f"background: #F8FAFC; border: 1px solid {CINZA_BORDA}; border-radius: 8px;")
            fly = QVBoxLayout(f)
            fly.setContentsMargins(16, 16, 16, 16)
            
            conteudo = str(text).strip()
            l = QLabel(conteudo if conteudo else "Nenhum detalhe registrado pelo operador.")
            l.setFont(QFont("Segoe UI", 10))
            l.setStyleSheet(f"color: {CINZA_TEXTO}; border: none; line-height: 1.4;")
            l.setWordWrap(True)
            l.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            fly.addWidget(l)
            v.addWidget(t)
            v.addWidget(f)
            return v
            
        def _rich_edit(title, widget):
            v = QVBoxLayout()
            v.setSpacing(8)
            t = QLabel(title.upper())
            t.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            t.setStyleSheet(f"color: {VERMELHO_ESC}; border: none;")
            v.addWidget(t)
            v.addWidget(widget)
            return v
            
        if self.is_editing:
            self.input_desc = QTextEdit(data.get("descricao", ""))
            css_text = f"background:#F8FAFC;border:1.5px solid #CBD5E1;border-radius:8px;padding:12px;color:{PRETO_TITULO};font-family:'Segoe UI';font-size:10pt;"
            self.input_desc.setStyleSheet(css_text)
            self.input_desc.setFixedHeight(100)
            
            self.input_causa = QTextEdit(data.get("causa", ""))
            self.input_causa.setStyleSheet(css_text)
            self.input_causa.setFixedHeight(100)
            
            self.input_acao = QTextEdit(data.get("acao", ""))
            self.input_acao.setStyleSheet(css_text)
            self.input_acao.setFixedHeight(140)
            
            sc_ly.addLayout(_rich_edit("Análise Crítica / Descrição do Problema", self.input_desc))
            sc_ly.addLayout(_rich_edit("Causa Raiz", self.input_causa))
            sc_ly.addLayout(_rich_edit("Plano de Ação Proposto", self.input_acao))
        else:
            sc_ly.addLayout(_rich_lbl("Análise Crítica / Descrição do Problema", data.get("descricao", "")))
            sc_ly.addLayout(_rich_lbl("Causa Raiz", data.get("causa", "")))
            sc_ly.addLayout(_rich_lbl("Plano de Ação Proposto", data.get("acao", "")))
            
        sc_ly.addStretch()
        scroll.setWidget(sc_container)
        self.ly.addWidget(scroll, 1)

    def _save_changes(self):
        rec = {
            "codigo_indicador": self.current_data["codigo"],
            "periodo": self.current_data.get("periodo", ""),
            "analise": self.input_desc.toPlainText().strip(),
            "causa": self.input_causa.toPlainText().strip(),
            "acao": self.input_acao.toPlainText().strip(),
            "responsavel": self.input_resp.text().strip(),
            "prazo": self.input_prazo.text().strip(),
            "nivel": self.current_data["nivel"]
        }
        db.upsert_analise_critica(rec)
        
        # Atualiza dicionário local para UI refletir instantaneamente
        self.current_data["descricao"] = rec["analise"]
        self.current_data["causa"] = rec["causa"]
        self.current_data["acao"] = rec["acao"]
        self.current_data["responsavel"] = rec["responsavel"]
        self.current_data["prazo"] = rec["prazo"]
        
        self.update_detail(self.current_data, False)
        self.data_saved.emit()


class PendenciasPanel(QWidget):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self.all_pends = []
        self.selected_codigo = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 32)
        root.setSpacing(24)
        
        title = SectionTitle("GESTÃO DE PENDÊNCIAS E ANÁLISE CRÍTICA")
        root.addWidget(title)
        
        pends_brutas = self.data.get("pendencias", [])
        self.all_pends = [
            p for p in pends_brutas 
            if (p.get("descricao") or "").strip() or (p.get("causa") or "").strip() or (p.get("acao") or "").strip()
        ]
        
        total = len(self.all_pends)
        criticos = sum(1 for p in self.all_pends if p.get('nivel') == 'CRÍTICO')
        atencao = sum(1 for p in self.all_pends if p.get('nivel') == 'ATENÇÃO')
        com_acao = sum(1 for p in self.all_pends if (p.get('acao') or "").strip())
        
        kpi_ly = QHBoxLayout()
        kpi_ly.setSpacing(16)
        kpi_ly.addWidget(PendenciaKPI("Total de Registros", total, "#3B82F6"))
        kpi_ly.addWidget(PendenciaKPI("Nível Crítico", criticos, PENDENTE_FG))
        kpi_ly.addWidget(PendenciaKPI("Nível Atenção", atencao, LARANJA))
        kpi_ly.addWidget(PendenciaKPI("Planos de Ação", com_acao, VERDE))
        root.addLayout(kpi_ly)
        
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)
        
        lbl_filtro = QLabel("Filtros:")
        lbl_filtro.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_filtro.setStyleSheet(f"color: {CINZA_SUAVE};")
        toolbar.addWidget(lbl_filtro)
        
        self.cb_nivel = QComboBox()
        self.cb_nivel.addItems(["Todos os Níveis", "CRÍTICO", "ATENÇÃO"])
        self.cb_nivel.setFixedWidth(180)
        self.cb_nivel.setStyleSheet(f"""
            QComboBox {{
                background:#FFFFFF;border:1px solid {CINZA_BORDA};border-radius:6px;
                padding:4px 12px;color:{PRETO_TITULO};font-size:10pt;
            }}
            {COMBO_DROPDOWN_CSS}
        """)
        self.cb_nivel.currentIndexChanged.connect(self._apply_filters)
        toolbar.addWidget(self.cb_nivel)
        
        self.txt_busca = QLineEdit()
        self.txt_busca.setPlaceholderText("Buscar por código, título ou responsável...")
        self.txt_busca.setFixedHeight(34)
        self.txt_busca.setStyleSheet(f"""
            QLineEdit {{
                background:#FFFFFF;border:1px solid {CINZA_BORDA};border-radius:6px;
                padding:4px 12px;color:{PRETO_TITULO};font-size:10pt;
            }}
            QLineEdit:focus {{ border: 1.5px solid {VERMELHO_ESC}; }}
        """)
        self.txt_busca.textChanged.connect(self._apply_filters)
        toolbar.addWidget(self.txt_busca, 1)
        root.addLayout(toolbar)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle { background: transparent; width: 16px; }
        """)
        
        self.list_container = QScrollArea()
        self.list_container.setWidgetResizable(True)
        self.list_container.setStyleSheet(f"""
            QScrollArea {{ border: none; background: transparent; }}
            QScrollBar:vertical {{ width: 6px; background: transparent; }}
            QScrollBar::handle:vertical {{ background: {CINZA_BORDA}; border-radius: 3px; }}
        """)
        
        self.list_widget = QWidget()
        self.list_widget.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setContentsMargins(0, 0, 8, 0)
        self.list_layout.setSpacing(12)
        self.list_layout.addStretch()
        self.list_container.setWidget(self.list_widget)
        
        self.detail_panel = PendenciaDetailPanel()
        self.detail_panel.data_saved.connect(self._apply_filters) # Recarrega a lista para mostrar novos dados
        
        self.list_container.setMinimumWidth(300)
        self.detail_panel.setMinimumWidth(400)
        
        splitter.addWidget(self.list_container)
        splitter.addWidget(self.detail_panel)
        
        splitter.setStretchFactor(0, 35)
        splitter.setStretchFactor(1, 65)
        root.addWidget(splitter, 1)
        
        self._populate_list(self.all_pends)

    def _apply_filters(self):
        nivel = self.cb_nivel.currentText()
        busca = self.txt_busca.text().lower()
        
        filtradas = []
        for p in self.all_pends:
            if nivel != "Todos os Níveis" and str(p.get("nivel")).upper() != nivel:
                continue
            
            if busca:
                texto = f"{p.get('codigo','')} {p.get('titulo','')} {p.get('responsavel','')} {p.get('descricao','')} {p.get('acao','')}".lower()
                if busca not in texto:
                    continue
                    
            filtradas.append(p)
            
        self._populate_list(filtradas)

    def _populate_list(self, pendencias):
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        if not pendencias:
            lbl = QLabel("Nenhuma pendência ou análise encontrada para os filtros aplicados.")
            lbl.setFont(QFont("Segoe UI", 10))
            lbl.setStyleSheet(f"color: {CINZA_SUAVE};")
            self.list_layout.insertWidget(0, lbl)
            self.detail_panel.set_empty()
            return
            
        for p in pendencias:
            is_sel = (p['codigo'] == self.selected_codigo)
            card = PendenciaItemCard(p, is_selected=is_sel)
            card.clicked.connect(self._on_item_clicked)
            self.list_layout.insertWidget(self.list_layout.count() - 1, card)
            
    def _on_item_clicked(self, data):
        self.selected_codigo = data['codigo']
        self.detail_panel.update_detail(data)
        
        for i in range(self.list_layout.count() - 1):
            w = self.list_layout.itemAt(i).widget()
            if isinstance(w, PendenciaItemCard):
                w._update_selection(w.data['codigo'] == self.selected_codigo)
