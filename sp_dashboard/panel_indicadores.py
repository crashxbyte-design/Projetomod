"""
panel_indicadores.py - Tela Indicadores com tabela completa.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QSizePolicy, QGridLayout, QSplitter
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from styles import (
    VERMELHO, VERMELHO_ESC, BRANCO, CINZA_BG, CINZA_BORDA,
    CINZA_SUAVE, PRETO_TITULO, VERDE, VERDE_SOFT, LARANJA, LARANJA_SOFT,
    CINZA_META, CINZA_META_BG, PENDENTE_FG, PENDENTE_BG,
    CINZA_TEXTO, STATUS_COLORS, COMBO_DROPDOWN_CSS
)
from widgets import SectionTitle, StatusBadge, IndicadorRow, PendenciaCard, shadow


class TableHeader(QFrame):
    """Cabeçalho da tabela de indicadores."""
    def __init__(self, periodo_ref="2026", parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setStyleSheet(f"""
            QFrame {{
                background: {VERMELHO_ESC};
                border-radius: 8px 8px 0px 0px;
                border: none;
            }}
        """)
        ly = QHBoxLayout(self)
        ly.setContentsMargins(16, 0, 16, 0)
        ly.setSpacing(12)

        def hdr(text, width=None, stretch=0):
            lbl = QLabel(text)
            lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            lbl.setStyleSheet("color: white; background: transparent; border: none; letter-spacing: 0.5px;")
            if width:
                lbl.setFixedWidth(width)
            return lbl, stretch

        cols = [
            ("Código", 70, 0),
            ("Indicador", 0, 2),
            ("Tipo", 90, 0),
            ("Periodicidade", 90, 0),
            ("Meta", 90, 0),
            (f"Resultado Atual\n({periodo_ref})", 110, 0),
            (f"Tendência\n(Meses de {periodo_ref})", 120, 0),
            ("Status", 130, 0),
        ]
        for text, width, stretch in cols:
            lbl = QLabel(text.upper() if "\n" not in text else text)
            lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            lbl.setStyleSheet("color: white; background: transparent; border: none;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter if width > 0 else Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)
            if width:
                lbl.setFixedWidth(width)
            ly.addWidget(lbl, stretch)
        ly.addSpacing(20)


class LegendaStatusInline(QFrame):
    """Legenda de status horizontal para ocupar menos espaço."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(36)
        self.setStyleSheet(f"""
            QFrame {{
                background: {BRANCO};
                border: 1px solid {CINZA_BORDA};
                border-radius: 18px;
            }}
        """)
        
        ly = QHBoxLayout(self)
        ly.setContentsMargins(16, 0, 16, 0)
        ly.setSpacing(16)

        title = QLabel("LEGENDA:")
        title.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {PRETO_TITULO}; background: transparent; border: none;")
        ly.addWidget(title)

        items = [
            ("Dentro da meta", "Atinge a meta"),
            ("Em Atenção", "Abaixo/Fora"),
            ("Sem meta", "Apenas mon."),
            ("A preencher", "Sem dados"),
        ]
        for status, desc in items:
            row = QHBoxLayout()
            row.setSpacing(6)
            fg, _, _ = STATUS_COLORS.get(status, (CINZA_META, CINZA_META_BG, CINZA_BORDA))
            dot = QLabel("●")
            dot.setFont(QFont("Segoe UI", 10))
            dot.setStyleSheet(f"color: {fg}; background: transparent; border: none;")
            row.addWidget(dot)
            d = QLabel(desc)
            d.setFont(QFont("Segoe UI", 8))
            d.setStyleSheet(f"color: {CINZA_SUAVE}; background: transparent; border: none;")
            row.addWidget(d)
            ly.addLayout(row)

        ly.addStretch()


class IndicadoresPanel(QWidget):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        root.addWidget(scroll)

        container = QWidget()
        container.setStyleSheet(f"background: {CINZA_BG};")
        scroll.setWidget(container)

        main = QVBoxLayout(container)
        main.setContentsMargins(28, 24, 28, 32)
        main.setSpacing(20)

        stats = self.data["stats"]

        # ── KPI cards compactos ────────────────────────────────────────────
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(12)
        cards_data = [
            ("Total de Indicadores", stats["total"], "100% do total", PRETO_TITULO),
            ("Com Meta", stats["com_meta"], f"{stats['com_meta']/max(stats['total'],1)*100:.0f}% do total", VERDE),
            ("Sem Meta", stats["sem_meta"], f"{stats['sem_meta']/max(stats['total'],1)*100:.0f}% do total", PRETO_TITULO),
            ("Em Atenção", stats["em_atencao"], f"{stats['em_atencao']/max(stats['total'],1)*100:.0f}% do total", LARANJA),
            ("A Preencher", stats["a_preencher"], f"{stats['a_preencher']/max(stats['total'],1)*100:.0f}% do total", PENDENTE_FG),
        ]
        from widgets import KPICard
        for label, val, sub, color in cards_data:
            c = KPICard(label, val, sub, color)
            c.setFixedHeight(95)
            kpi_row.addWidget(c)
        main.addLayout(kpi_row)

        # ── Título tabela ──────────────────────────────────────────────────
        main.addWidget(SectionTitle("RELAÇÃO DE INDICADORES – SEGURANÇA PATRIMONIAL"))

        # ── Barra de Ferramentas (Filtros + Legenda) ───────────────────────
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)
        
        lbl_filtro = QLabel("🔍 Filtrar Status:")
        lbl_filtro.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_filtro.setStyleSheet(f"color: {CINZA_SUAVE}; background: transparent;")
        toolbar.addWidget(lbl_filtro)
        
        from PySide6.QtWidgets import QComboBox, QLineEdit
        
        lbl_ano = QLabel("📅 Ano:")
        lbl_ano.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_ano.setStyleSheet(f"color: {CINZA_SUAVE}; background: transparent;")
        toolbar.addWidget(lbl_ano)
        
        self.cb_ano = QComboBox()
        anos = set()
        for ind in self.data.get("indicadores", []):
            anos.update(ind.get("historicos", {}).keys())
        anos_list = sorted(list(anos))
        if not anos_list: anos_list = [2026]
        self.cb_ano.addItems([str(y) for y in anos_list])
        self.cb_ano.setFixedWidth(100)
        self.cb_ano.setStyleSheet(f"""
            QComboBox {{
                border: 1px solid {CINZA_BORDA}; border-radius: 6px; padding: 4px 8px;
                color: #1E293B; background: {BRANCO}; font-size: 12px;
            }}
            {COMBO_DROPDOWN_CSS}
        """)
        toolbar.addWidget(self.cb_ano)
        self.cb_status = QComboBox()
        self.cb_status.addItems(["Todos", "Dentro da meta", "Em Atenção", "Sem meta", "A preencher"])
        self.cb_status.setFixedWidth(160)
        self.cb_status.setStyleSheet(f"""
            QComboBox {{
                border: 1px solid {CINZA_BORDA}; border-radius: 6px; padding: 4px 8px;
                color: #1E293B; background: {BRANCO}; font-size: 12px;
            }}
            {COMBO_DROPDOWN_CSS}
        """)
        toolbar.addWidget(self.cb_status)

        self.txt_busca = QLineEdit()
        self.txt_busca.setPlaceholderText("Buscar por código ou nome...")
        self.txt_busca.setFixedWidth(250)
        self.txt_busca.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid {CINZA_BORDA}; border-radius: 6px; padding: 4px 8px;
                color: #1E293B; background: {BRANCO}; font-size: 12px;
            }}
        """)
        toolbar.addWidget(self.txt_busca)
        toolbar.addStretch()

        legenda_inline = LegendaStatusInline()
        toolbar.addWidget(legenda_inline)

        main.addLayout(toolbar)

        # ── Layout principal: tabela (sem legenda vertical) ────────────────
        table_frame = QFrame()
        table_frame.setStyleSheet(f"QFrame {{ background: {BRANCO}; border: 1px solid {CINZA_BORDA}; border-radius: 12px; }}")
        table_frame.setGraphicsEffect(shadow(12, (0, 4), (0, 0, 0, 8)))
        
        self.table_col = QVBoxLayout(table_frame)
        self.table_col.setContentsMargins(0, 0, 0, 0)
        self.table_col.setSpacing(0)
        
        main.addWidget(table_frame, 1)

        # Conectar filtros
        self.cb_status.currentTextChanged.connect(self._apply_filters)
        self.txt_busca.textChanged.connect(self._apply_filters)
        self.cb_ano.currentTextChanged.connect(self._populate_table)
        
        self._populate_table()

        # ── Observações (Versão Compacta e Útil) ───────────────────────────
        obs_frame = QFrame()
        obs_frame.setStyleSheet(f"""
            QFrame {{
                background: #F8FAFC;
                border: 1px dashed {CINZA_BORDA};
                border-radius: 8px;
            }}
        """)
        obs_ly = QHBoxLayout(obs_frame)
        obs_ly.setContentsMargins(16, 12, 16, 12)
        obs_ly.setSpacing(12)
        
        info_icon = QLabel("ℹ️")
        info_icon.setFont(QFont("Segoe UI", 12))
        info_icon.setStyleSheet("background:transparent; border:none;")
        obs_ly.addWidget(info_icon)
        
        info_txt = QLabel(
            "Os resultados e tendências refletem a última apuração "
            f"dentro do exercício de {stats.get('periodo', '2026')}. "
            "Indicadores 'Em Atenção' exigem plano de ação via painel de Controle."
        )
        info_txt.setFont(QFont("Segoe UI", 9))
        info_txt.setStyleSheet(f"color: {CINZA_TEXTO}; background: transparent; border: none;")
        obs_ly.addWidget(info_txt, 1)
        
        main.addWidget(obs_frame)

        footer = QLabel(
            f"Período de referência atual: {stats.get('periodo', '2026')}   •   Responsável: {stats['responsavel']}"
        )
        footer.setFont(QFont("Segoe UI", 9))
        footer.setStyleSheet(f"color: {CINZA_SUAVE}; background: transparent;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main.addWidget(footer)
        main.addStretch()

    def _populate_table(self):
        # Limpar tabela atual
        while self.table_col.count():
            item = self.table_col.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        try:
            ano_sel = int(self.cb_ano.currentText())
        except:
            ano_sel = 2026
            
        header = TableHeader(str(ano_sel))
        self.table_col.addWidget(header)

        self.row_widgets = []
        for i, ind in enumerate(self.data["indicadores"]):
            row = IndicadorRow(ind, ano_sel)
            if i % 2 == 1:
                row.setStyleSheet(row.styleSheet().replace(
                    f"background: {BRANCO};",
                    "background: #FAFBFC;"
                ).replace(
                    "background: #FAFBFC;\n            background: transparent;",
                    "background: transparent;"
                ))
            self.table_col.addWidget(row)
            self.row_widgets.append((ind, row))

        self.table_col.addStretch()
        self._apply_filters()

    def _apply_filters(self):
        st = self.cb_status.currentText()
        txt = self.txt_busca.text().lower()
        
        for ind, row_widget in self.row_widgets:
            match_st = (st == "Todos") or (ind["status"] == st)
            match_txt = (txt in ind["codigo"].lower()) or (txt in ind["titulo"].lower())
            row_widget.setVisible(match_st and match_txt)
