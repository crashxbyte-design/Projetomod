"""
panel_subindicadores.py - Tela Gráficos e Subindicadores.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from styles import (
    VERMELHO, VERMELHO_ESC, BRANCO, CINZA_BG, CINZA_BORDA,
    CINZA_SUAVE, PRETO_TITULO, VERDE, LARANJA, CINZA_META,
    PENDENTE_FG
)
from widgets import SectionTitle, shadow

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

def _make_comparative_bar_chart(sub_data, indicator_name):
    """Cria um gráfico de barras vertical comparando os meses do subindicador."""
    fig, ax = plt.subplots(figsize=(4.5, 2.5), dpi=96)
    fig.patch.set_facecolor(BRANCO)
    ax.set_facecolor(BRANCO)

    labels = []
    values = []
    colors = []
    
    # Processar dados
    # sub_data é uma lista de dicts: [{'mes': 'Janeiro', 'valor': 10}, ...]
    for s in sub_data:
        val = s.get('valor')
        if val is not None:
            labels.append(s['mes'][:3]) # Jan, Fev
            values.append(val)
            colors.append(VERMELHO)

    if not values:
        ax.text(0.5, 0.5, "Sem dados no período", ha='center', va='center', color=CINZA_SUAVE)
        ax.axis('off')
        return fig

    bars = ax.bar(labels, values, color=colors, width=0.4, edgecolor="none")
    
    ax.set_ylim(0, max(values) * 1.3 if max(values) > 0 else 10)
    ax.set_ylabel("")
    ax.tick_params(axis="y", labelsize=8, colors=PRETO_TITULO)
    ax.tick_params(axis="x", labelsize=9, colors=PRETO_TITULO)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color(CINZA_BORDA)
    ax.yaxis.grid(True, color=CINZA_BORDA, linewidth=0.5, linestyle='--')
    ax.set_axisbelow(True)

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + (max(values)*0.05),
                f"{val}", va="bottom", ha="center", fontsize=9, fontweight='bold', color=PRETO_TITULO)

    fig.tight_layout(pad=0.5)
    return fig


class SubindicadoresPanel(QWidget):
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

        title = SectionTitle("COMPARATIVO PERIÓDICO DOS SUBINDICADORES")
        main.addWidget(title)
        
        info = QLabel("Análise detalhada do desempenho mensal de cada subindicador.")
        info.setFont(QFont("Segoe UI", 10))
        info.setStyleSheet(f"color: {CINZA_SUAVE};")
        main.addWidget(info)

        sub_raw = self.data.get("sub_raw", [])
        
        # Agrupar subindicadores por nome (não apenas código, pois pode haver vários por código)
        # Formato: { "Nome do Subindicador": [ {"mes": "Jan", "valor": 10}, ... ] }
        grupos = {}
        for s in sub_raw:
            nome = s.get('nome_subindicador')
            if not nome: continue
            if nome not in grupos:
                grupos[nome] = []
            grupos[nome].append(s)
            
        # Criar Grid de Gráficos
        grid = QGridLayout()
        grid.setSpacing(20)
        
        row = 0
        col = 0
        
        for nome_sub, dados_meses in grupos.items():
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background: {BRANCO};
                    border: 1px solid {CINZA_BORDA};
                    border-radius: 6px;
                }}
            """)
            card.setGraphicsEffect(shadow(6, (0, 2), (0, 0, 0, 10)))
            
            c_ly = QVBoxLayout(card)
            c_ly.setContentsMargins(16, 16, 16, 16)
            c_ly.setSpacing(8)
            
            t = QLabel(nome_sub.upper())
            t.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            t.setStyleSheet(f"color: {PRETO_TITULO}; border: none;")
            t.setAlignment(Qt.AlignmentFlag.AlignCenter)
            c_ly.addWidget(t)
            
            if HAS_MPL:
                fig = _make_comparative_bar_chart(dados_meses, nome_sub)
                canvas = FigureCanvas(fig)
                canvas.setStyleSheet("border: none; background: transparent;")
                c_ly.addWidget(canvas)
            else:
                l = QLabel("Gráfico indisponível (matplotlib ausente)")
                l.setAlignment(Qt.AlignmentFlag.AlignCenter)
                c_ly.addWidget(l)
                
            grid.addWidget(card, row, col)
            col += 1
            if col > 1:
                col = 0
                row += 1
                
        main.addLayout(grid)
        main.addStretch()
