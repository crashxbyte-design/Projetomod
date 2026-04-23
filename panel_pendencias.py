"""
panel_pendencias.py - Tela de Pendências e Observações.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from styles import (
    VERMELHO_ESC, BRANCO, CINZA_BG, CINZA_BORDA,
    CINZA_SUAVE, PRETO_TITULO, PENDENTE_FG, LARANJA
)
from widgets import SectionTitle, shadow

class PendenciaDetalheCard(QFrame):
    def __init__(self, p, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background: {BRANCO};
                border: 1px solid {CINZA_BORDA};
                border-left: 4px solid {PENDENTE_FG if p['nivel'] == 'CRÍTICO' else LARANJA};
                border-radius: 6px;
            }}
        """)
        self.setGraphicsEffect(shadow(6, (0, 1), (0, 0, 0, 10)))
        
        ly = QVBoxLayout(self)
        ly.setContentsMargins(20, 16, 20, 16)
        ly.setSpacing(8)
        
        # Header: Cod + Titulo + Badge
        header = QHBoxLayout()
        header.setSpacing(12)
        
        cod = QLabel(p['codigo'])
        cod.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        cod.setStyleSheet(f"color: {PRETO_TITULO}; border: none;")
        header.addWidget(cod)
        
        tit = QLabel(p['titulo'])
        tit.setFont(QFont("Segoe UI", 10))
        tit.setStyleSheet(f"color: {CINZA_SUAVE}; border: none;")
        header.addWidget(tit, 1)
        
        badge = QLabel(p['nivel'])
        badge.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        cor = PENDENTE_FG if p['nivel'] == 'CRÍTICO' else LARANJA
        badge.setStyleSheet(f"""
            color: {cor};
            background: transparent;
            border: 1px solid {cor};
            border-radius: 4px;
            padding: 4px 8px;
        """)
        header.addWidget(badge)
        ly.addLayout(header)
        
        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(f"color: {CINZA_BORDA};")
        ly.addWidget(div)
        
        # Content
        content = QHBoxLayout()
        
        desc_ly = QVBoxLayout()
        dl = QLabel("ANÁLISE CRÍTICA / PENDÊNCIA")
        dl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        dl.setStyleSheet(f"color: {CINZA_SUAVE}; border: none;")
        desc_ly.addWidget(dl)
        dv = QLabel(p['descricao'])
        dv.setFont(QFont("Segoe UI", 10))
        dv.setStyleSheet(f"color: {PRETO_TITULO}; border: none;")
        dv.setWordWrap(True)
        desc_ly.addWidget(dv)
        content.addLayout(desc_ly, 2)
        
        resp_ly = QVBoxLayout()
        rl = QLabel("PRAZO")
        rl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        rl.setStyleSheet(f"color: {CINZA_SUAVE}; border: none;")
        resp_ly.addWidget(rl)
        rv = QLabel(str(p['prazo']))
        rv.setFont(QFont("Segoe UI", 10))
        rv.setStyleSheet(f"color: {PRETO_TITULO}; border: none;")
        resp_ly.addWidget(rv)
        content.addLayout(resp_ly, 1)
        
        ly.addLayout(content)

class PendenciasPanel(QWidget):
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
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root.addWidget(scroll)

        container = QWidget()
        container.setStyleSheet(f"background: {CINZA_BG};")
        scroll.setWidget(container)

        main = QVBoxLayout(container)
        main.setContentsMargins(28, 24, 28, 32)
        main.setSpacing(24)

        title = SectionTitle("PENDÊNCIAS E ANÁLISE CRÍTICA")
        main.addWidget(title)

        info = QLabel("Acompanhamento de planos de ação e justificativas para indicadores críticos ou em atenção.")
        info.setFont(QFont("Segoe UI", 10))
        info.setStyleSheet(f"color: {CINZA_SUAVE};")
        main.addWidget(info)

        ac_raw = self.data.get("ac_raw", [])
        pendencias = self.data.get("pendencias", [])

        if not pendencias:
            lbl = QLabel("Nenhuma análise crítica ou pendência registrada no período.")
            lbl.setFont(QFont("Segoe UI", 11))
            lbl.setStyleSheet(f"color: {CINZA_SUAVE};")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            main.addWidget(lbl)
        else:
            for p in pendencias:
                main.addWidget(PendenciaDetalheCard(p))

        main.addStretch()
