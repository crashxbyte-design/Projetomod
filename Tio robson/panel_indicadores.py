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
    CINZA_TEXTO, STATUS_COLORS
)
from widgets import SectionTitle, StatusBadge, IndicadorRow, PendenciaCard, shadow


class TableHeader(QFrame):
    """Cabeçalho da tabela de indicadores."""
    def __init__(self, parent=None):
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
            ("Resultado Atual\n(Jan a Out/2026)", 110, 0),
            ("Tendência\n(Últimos 6 meses)", 120, 0),
            ("Status", 130, 0),
            ("Fonte de Dados", 0, 1),
        ]
        for text, width, stretch in cols:
            lbl = QLabel(text.upper() if "\n" not in text else text)
            lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            lbl.setStyleSheet("color: white; background: transparent; border: none;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter if width > 0 else Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)
            if width:
                lbl.setFixedWidth(width)
            ly.addWidget(lbl, stretch)


class LegendaStatus(QFrame):
    """Legenda de status à direita."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background: {BRANCO};
                border: 1px solid {CINZA_BORDA};
                border-radius: 10px;
            }}
        """)
        self.setGraphicsEffect(shadow(10, (0, 2), (0, 0, 0, 15)))
        self.setFixedWidth(230)

        ly = QVBoxLayout(self)
        ly.setContentsMargins(16, 16, 16, 16)
        ly.setSpacing(10)

        title = QLabel("LEGENDA DE STATUS")
        title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {PRETO_TITULO}; background: transparent; border: none;")
        ly.addWidget(title)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {CINZA_BORDA};")
        ly.addWidget(sep)

        items = [
            ("Em Atenção", "Resultado abaixo da meta, requer acompanhamento"),
            ("Acima da meta", "Resultado acima do limite máximo"),
            ("Pendente de processo", "Processo ou controle não implantado"),
            ("Pendente de controle", "Controle formal não criado"),
            ("Meta a definir", "Meta ainda não estabelecida"),
            ("A preencher", "Dados não disponíveis para o período"),
        ]
        for status, desc in items:
            row = QHBoxLayout()
            row.setSpacing(8)
            dot = StatusBadge(status)
            dot.setFixedWidth(140)
            dot.setFixedHeight(22)
            row.addWidget(dot)
            row.addStretch()
            ly.addLayout(row)
            d = QLabel(desc)
            d.setFont(QFont("Segoe UI", 8))
            d.setStyleSheet(f"color: {CINZA_SUAVE}; background: transparent; border: none;")
            d.setWordWrap(True)
            ly.addWidget(d)
            sep2 = QFrame()
            sep2.setFrameShape(QFrame.Shape.HLine)
            sep2.setStyleSheet(f"color: {CINZA_BORDA}44;")
            ly.addWidget(sep2)

        ly.addStretch()

        # Sobre esta página
        sobre = QLabel("SOBRE ESTA PÁGINA")
        sobre.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        sobre.setStyleSheet(f"color: {PRETO_TITULO}; background: transparent; border: none;")
        ly.addWidget(sobre)
        desc_page = QLabel(
            "Relação completa dos indicadores de Segurança Patrimonial, "
            "com metas, resultados disponíveis e status para Jan–Fev/2026."
        )
        desc_page.setFont(QFont("Segoe UI", 8))
        desc_page.setStyleSheet(f"color: {CINZA_SUAVE}; background: transparent; border: none;")
        desc_page.setWordWrap(True)
        ly.addWidget(desc_page)


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

        # ── Layout principal: tabela + legenda ─────────────────────────────
        body_row = QHBoxLayout()
        body_row.setSpacing(16)

        # Coluna tabela
        table_col = QVBoxLayout()
        table_col.setSpacing(0)

        header = TableHeader()
        table_col.addWidget(header)

        for i, ind in enumerate(self.data["indicadores"]):
            row = IndicadorRow(ind)
            if i % 2 == 1:
                row.setStyleSheet(row.styleSheet().replace(
                    f"background: {BRANCO};",
                    "background: #FAFBFC;"
                ).replace(
                    "background: #FAFBFC;\n            background: transparent;",
                    "background: transparent;"
                ))
            table_col.addWidget(row)
            table_col.addSpacing(4)

        table_col.addStretch()
        body_row.addLayout(table_col, 1)

        # Coluna legenda
        legenda = LegendaStatus()
        body_row.addWidget(legenda)

        main.addLayout(body_row)

        # ── Observações ────────────────────────────────────────────────────
        obs_frame = QFrame()
        obs_frame.setStyleSheet(f"""
            QFrame {{
                background: {BRANCO};
                border: 1px solid {CINZA_BORDA};
                border-radius: 10px;
            }}
        """)
        obs_frame.setGraphicsEffect(shadow(10, (0, 2), (0, 0, 0, 14)))
        obs_ly = QVBoxLayout(obs_frame)
        obs_ly.setContentsMargins(20, 16, 20, 16)
        obs_ly.setSpacing(8)

        obs_title = QLabel("📋  OBSERVAÇÕES DOS INDICADORES")
        obs_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        obs_title.setStyleSheet(f"color: {VERMELHO}; background: transparent; border: none;")
        obs_ly.addWidget(obs_title)

        # Gera observações dinamicamente dos indicadores sem dados ou com pendencia
        obs_items = []
        for ind in self.data["indicadores"]:
            obs = ind.get("origem") or ""
            if ind["status"] == "A preencher" and obs and obs != "—":
                obs_items.append((PENDENTE_FG, f"{ind['codigo']} – {ind['titulo']}: {obs}"))
            elif ind["status"] == "Em Atenção" and obs and obs != "—":
                obs_items.append((LARANJA, f"{ind['codigo']} – {ind['titulo']}: {obs}"))
        obs_items.append((CINZA_META, f"* Período de referência: {stats['periodo']}."))
        for color, txt in obs_items:
            row = QHBoxLayout()
            dot = QLabel("●")
            dot.setFont(QFont("Segoe UI", 10))
            dot.setStyleSheet(f"color: {color}; background: transparent; border: none;")
            dot.setFixedWidth(18)
            t = QLabel(txt)
            t.setFont(QFont("Segoe UI", 9))
            t.setStyleSheet(f"color: {CINZA_TEXTO}; background: transparent; border: none;")
            t.setWordWrap(True)
            row.addWidget(dot)
            row.addWidget(t)
            obs_ly.addLayout(row)

        main.addWidget(obs_frame)

        footer = QLabel(
            f"Período de referência: {stats['periodo']}   •   Responsável: {stats['responsavel']}"
        )
        footer.setFont(QFont("Segoe UI", 9))
        footer.setStyleSheet(f"color: {CINZA_SUAVE}; background: transparent;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main.addWidget(footer)
        main.addStretch()
