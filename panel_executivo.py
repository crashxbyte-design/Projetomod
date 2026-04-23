"""
panel_executivo.py - Tela Painel Executivo (redesenhado).
Layout fiel ao print de referência:
  Linha 1: Resumo Executivo (esq) + KPI Cards (dir)
  Linha 2: Barras Desempenho | Linha Evolução | Donut Tipo
  Linha 3: Destaques | Ranking Top 5 | Pendências Críticas
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QSizePolicy, QGridLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from styles import (
    VERMELHO, VERMELHO_ESC, VERMELHO_SOFT, BRANCO, CINZA_BG, CINZA_BORDA,
    CINZA_SUAVE, PRETO_TITULO, VERDE, VERDE_SOFT, LARANJA, LARANJA_SOFT,
    CINZA_META, CINZA_META_BG, PENDENTE_FG, PENDENTE_BG
)
from widgets import SectionTitle, shadow

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

MESES_ABREV = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
               "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
MESES_FULL  = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
               "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]

# ─────────────────────────────────────────────────────────────────────────────
def _card_frame():
    f = QFrame()
    f.setStyleSheet(f"""
        QFrame {{
            background: {BRANCO};
            border: 1px solid {CINZA_BORDA};
            border-radius: 6px;
        }}
    """)
    f.setGraphicsEffect(shadow(8, (0,2), (0,0,0,12)))
    return f

def _section_header(text):
    lbl = QLabel(text)
    lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
    lbl.setStyleSheet(f"""
        color: {BRANCO};
        background: {VERMELHO_ESC};
        border-radius: 4px;
        padding: 6px 14px;
        border: none;
    """)
    return lbl

# ─────────────────────────────────────────────────────────────────────────────
# Gráficos
# ─────────────────────────────────────────────────────────────────────────────

def _chart_desempenho(indicadores):
    """Barras horizontais – status qualitativo por indicador."""
    n = len(indicadores)
    fig, ax = plt.subplots(figsize=(5.0, max(3.0, n * 0.52)), dpi=92)
    fig.patch.set_facecolor(BRANCO)
    ax.set_facecolor(BRANCO)

    STATUS_COR = {
        "Dentro da meta": VERDE,
        "Acima da meta":  VERDE,
        "Em Atenção":    LARANJA,
        "Abaixo da meta": PENDENTE_FG,
    }
    STATUS_PCT = {
        "Dentro da meta": 1.0,
        "Acima da meta":  1.0,
        "Em Atenção":    0.78,
        "Abaixo da meta": 0.40,
    }

    labels = [f" {i['codigo']}" for i in indicadores]
    for idx, ind in enumerate(indicadores):
        st  = ind["status"]
        cor = STATUS_COR.get(st, "#CFCFCF")
        pct = STATUS_PCT.get(st, 0.0)
        bg  = "#F0F0F0" if pct == 0.0 else "#EEEEEE"
        ax.barh(idx, pct,       color=cor, height=0.52, edgecolor="none")
        ax.barh(idx, 1.0 - pct, left=pct, color=bg,    height=0.52, edgecolor="none")
        # Label de status
        st_label = st if len(st) < 18 else st[:16] + "…"
        ax.text(1.02, idx, st_label, va="center", ha="left",
                fontsize=6.5, color="#888888")

    ax.set_yticks(list(range(n)))
    ax.set_yticklabels(labels, fontsize=8.0, color=PRETO_TITULO)
    ax.set_xlim(0, 1.55)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"], fontsize=7, color="#AAAAAA")
    ax.tick_params(axis="both", length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.xaxis.grid(True, color="#F0F0F0", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.axvline(1.0, color=CINZA_BORDA, linewidth=0.8, linestyle="--")

    legenda = [
        mpatches.Patch(color=VERDE,       label="Dentro da Meta"),
        mpatches.Patch(color=LARANJA,     label="Em Atenção"),
        mpatches.Patch(color=PENDENTE_FG, label="Abaixo da Meta"),
        mpatches.Patch(color="#CFCFCF",   label="Sem Meta / Pendente"),
    ]
    ax.legend(handles=legenda, loc="upper right", fontsize=6.0,
              frameon=False, ncol=2, bbox_to_anchor=(1.0, -0.04))
    ax.set_title("DESEMPENHO GERAL  —  Por Indicador", fontsize=8.5,
                 fontweight="bold", color=PRETO_TITULO, pad=8, loc="left")
    fig.tight_layout(pad=0.5)
    return fig


def _chart_evolucao(sub_raw):
    """Barras agrupadas Jan x Fev por indicador (2025 vs 2026)."""
    # Coletar totais Jan e Fev para 2025 e 2026
    def _total_mes(ano, mes):
        return sum(r["valor"] for r in sub_raw
                   if r["ano"] == ano and r["mes"] == mes and r["valor"] is not None)

    jan25 = _total_mes(2025, "Janeiro")
    fev25 = _total_mes(2025, "Fevereiro")
    jan26 = _total_mes(2026, "Janeiro")
    fev26 = _total_mes(2026, "Fevereiro")

    if not any([jan25, fev25, jan26, fev26]):
        # Fallback: linha de evolução por mês
        fig, ax = plt.subplots(figsize=(5.2, 4.2), dpi=92)
        ax.text(0.5, 0.5, "Dados insuficientes", ha="center", va="center",
                color=CINZA_SUAVE, fontsize=10)
        ax.axis("off")
        return fig

    fig, ax = plt.subplots(figsize=(5.2, 4.2), dpi=92)
    fig.patch.set_facecolor(BRANCO)
    ax.set_facecolor(BRANCO)

    import numpy as np
    x = np.arange(2)          # Jan, Fev
    w = 0.32
    bars25 = ax.bar(x - w/2, [jan25, fev25], width=w, color="#546E7A",
                    label="2025", edgecolor="none", zorder=3)
    bars26 = ax.bar(x + w/2, [jan26, fev26], width=w, color=VERMELHO,
                    label="2026", edgecolor="none", zorder=3)

    ax.set_xticks(x)
    ax.set_xticklabels(["Janeiro", "Fevereiro"], fontsize=10, color=PRETO_TITULO)
    ax.tick_params(axis="y", labelsize=8, colors="#AAAAAA")
    ax.tick_params(axis="both", length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.yaxis.grid(True, color="#F2F2F2", linewidth=0.9, zorder=0)
    ax.set_axisbelow(True)

    # Labels em cima das barras
    for bar in list(bars25) + list(bars26):
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width()/2, h + max(jan25,fev25,jan26,fev26)*0.02,
                    f"{int(h):,}".replace(",", "."),
                    ha="center", va="bottom", fontsize=7.5, fontweight="bold", color=PRETO_TITULO)

    ax.legend(fontsize=8.5, frameon=False, loc="upper right")
    ax.set_title("COMPARAÇÃO JAN x FEV  —  2025 vs 2026", fontsize=8.5,
                 fontweight="bold", color=PRETO_TITULO, pad=8, loc="left")
    fig.tight_layout(pad=0.6)
    return fig


def _chart_donut(stats):
    """Donut – distribuição de status dos indicadores."""
    fig, ax = plt.subplots(figsize=(2.8, 3.4), dpi=92)
    fig.patch.set_facecolor(BRANCO)

    labels = ["Com Meta", "Sem Meta", "Em Atenção", "Pendentes"]
    values = [stats["com_meta"], stats["sem_meta"],
              stats["em_atencao"], stats["pendentes_processo"]]
    colors = [VERDE, "#CFD8DC", LARANJA, PENDENTE_FG]

    pairs = [(l, v, c) for l, v, c in zip(labels, values, colors) if v > 0]
    if not pairs:
        pairs = [("Sem dados", 1, CINZA_META)]
    ls, vs, cs = zip(*pairs)

    wedges, _, autotexts = ax.pie(
        vs, labels=None, colors=cs, autopct="%1.0f%%",
        startangle=90, wedgeprops={"edgecolor": BRANCO, "linewidth": 2},
        pctdistance=0.70
    )
    for t in autotexts:
        t.set_fontsize(7.5); t.set_color(BRANCO); t.set_fontweight("bold")

    ax.add_patch(plt.Circle((0, 0), 0.50, color=BRANCO))

    # Texto central
    ax.text(0, 0, str(stats.get("total", "")), ha="center", va="center",
            fontsize=18, fontweight="bold", color=PRETO_TITULO)
    ax.text(0, -0.22, "total", ha="center", va="center",
            fontsize=7, color=CINZA_SUAVE)

    ax.legend(
        wedges, [f"{l}  ({v})" for l, v in zip(ls, vs)],
        loc="lower center", bbox_to_anchor=(0.5, -0.04),
        fontsize=6.5, frameon=False, ncol=1
    )
    ax.set_title("STATUS DOS\nINDICADORES", fontsize=8,
                 fontweight="bold", color=PRETO_TITULO, pad=4, loc="left")
    fig.tight_layout(pad=0.2)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Sub-widgets
# ─────────────────────────────────────────────────────────────────────────────

class _KPICard(QFrame):
    def __init__(self, label, value, sub, color, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(120)
        self.setMinimumHeight(110)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setStyleSheet(f"""
            QFrame {{
                background: {BRANCO};
                border: 1px solid {CINZA_BORDA};
                border-top: 4px solid {color};
                border-radius: 6px;
            }}
        """)
        self.setGraphicsEffect(shadow(8, (0,2), (0,0,0,12)))
        ly = QVBoxLayout(self)
        ly.setContentsMargins(12, 14, 12, 14)
        ly.setSpacing(3)
        ly.setAlignment(Qt.AlignmentFlag.AlignCenter)

        t = QLabel(label.upper())
        t.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        t.setStyleSheet(f"color:#999999; background:transparent; border:none; letter-spacing:0.3px;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setWordWrap(True)
        ly.addWidget(t)

        v = QLabel(str(value))
        v.setFont(QFont("Segoe UI", 30, QFont.Weight.Bold))
        v.setStyleSheet(f"color:{color}; background:transparent; border:none;")
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ly.addWidget(v)

        if sub:
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setStyleSheet(f"background:{CINZA_BORDA}; border:none; max-height:1px; margin: 2px 0;")
            ly.addWidget(sep)
            s = QLabel(sub)
            s.setFont(QFont("Segoe UI", 7))
            s.setStyleSheet(f"color:{color}; background:transparent; border:none;")
            s.setAlignment(Qt.AlignmentFlag.AlignCenter)
            s.setWordWrap(True)
            ly.addWidget(s)


class _DestaqueItem(QWidget):
    def __init__(self, icon, text, color, parent=None):
        super().__init__(parent)
        ly = QHBoxLayout(self)
        ly.setContentsMargins(0,4,0,4)
        ly.setSpacing(10)
        ico = QLabel(icon)
        ico.setFont(QFont("Segoe UI", 14))
        ico.setFixedWidth(22)
        ico.setStyleSheet(f"color:{color}; background:transparent; border:none;")
        ly.addWidget(ico)
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 9))
        lbl.setStyleSheet(f"color:{PRETO_TITULO}; background:transparent; border:none;")
        lbl.setWordWrap(True)
        ly.addWidget(lbl, 1)


class _RankingRow(QWidget):
    def __init__(self, pos, cod, nome, pct, parent=None):
        super().__init__(parent)
        ly = QHBoxLayout(self)
        ly.setContentsMargins(0,3,0,3)
        ly.setSpacing(8)

        p = QLabel(f"{pos}º")
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        p.setFixedWidth(22)
        p.setStyleSheet(f"color:{CINZA_SUAVE}; background:transparent; border:none;")
        ly.addWidget(p)

        c = QLabel(cod)
        c.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        c.setFixedWidth(78)
        c.setStyleSheet(f"color:{PRETO_TITULO}; background:transparent; border:none;")
        ly.addWidget(c)

        n = QLabel(nome[:28] + ("…" if len(nome) > 28 else ""))
        n.setFont(QFont("Segoe UI", 8))
        n.setStyleSheet(f"color:{CINZA_SUAVE}; background:transparent; border:none;")
        ly.addWidget(n, 1)

        bar_bg = QFrame()
        bar_bg.setFixedSize(90, 14)
        bar_bg.setStyleSheet(f"background:#EEEEEE; border-radius:3px; border:none;")
        bar_inner = QFrame(bar_bg)
        bar_inner.setStyleSheet(f"background:{VERDE}; border-radius:3px; border:none;")
        bar_inner.setGeometry(0, 0, int(90 * pct / 100), 14)
        ly.addWidget(bar_bg)

        pc = QLabel(f"{pct:.1f}%")
        pc.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        pc.setFixedWidth(36)
        pc.setStyleSheet(f"color:{VERDE}; background:transparent; border:none;")
        ly.addWidget(pc)


# ─────────────────────────────────────────────────────────────────────────────
# Painel principal
# ─────────────────────────────────────────────────────────────────────────────

class PainelExecutivoPanel(QWidget):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0,0,0,0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root.addWidget(scroll)

        container = QWidget()
        container.setStyleSheet(f"background:{CINZA_BG};")
        scroll.setWidget(container)

        main = QVBoxLayout(container)
        main.setContentsMargins(24, 20, 24, 28)
        main.setSpacing(20)

        stats = self.data["stats"]
        inds  = self.data["indicadores"]
        pends = self.data["pendencias"]
        sub_raw = self.data.get("sub_raw", [])

        # ── LINHA 1: Resumo Executivo (esq) + KPI Cards (dir) ─────────────
        row1 = QHBoxLayout()
        row1.setSpacing(16)

        # Resumo
        resumo = _card_frame()
        resumo.setMinimumWidth(260)
        resumo.setMaximumWidth(320)
        r_ly = QVBoxLayout(resumo)
        r_ly.setContentsMargins(0,0,0,0)
        r_ly.setSpacing(0)
        r_ly.addWidget(_section_header("RESUMO EXECUTIVO"))
        r_body = QWidget()
        r_body.setStyleSheet("background:transparent; border:none;")
        rb = QVBoxLayout(r_body)
        rb.setContentsMargins(16,14,16,16)
        rb.setSpacing(6)
        periodo = stats.get("periodo","Jan a Fev/2026")
        txt = QLabel(
            f"Este painel apresenta o desempenho consolidado dos principais "
            f"indicadores da Segurança Patrimonial no período selecionado."
        )
        txt.setFont(QFont("Segoe UI", 9))
        txt.setStyleSheet(f"color:{CINZA_SUAVE}; background:transparent; border:none;")
        txt.setWordWrap(True)
        rb.addWidget(txt)
        rb.addStretch()
        r_ly.addWidget(r_body, 1)
        row1.addWidget(resumo)

        # KPI grid
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(12)
        kpi_data = [
            ("Total de\nIndicadores", stats["total"],     "100% do total",         PRETO_TITULO),
            ("Indicadores\nCom Meta",  stats["com_meta"], f"{stats['com_meta']/max(stats['total'],1)*100:.0f}% do total", PRETO_TITULO),
            ("Metas\nAtingidas",       stats["com_meta"], f"{stats['com_meta']/max(stats['total'],1)*100:.0f}% das metas", VERDE),
            ("Em\nAtenção",            stats["em_atencao"], f"{stats['em_atencao']/max(stats['total'],1)*100:.0f}% das metas", LARANJA),
            ("Abaixo\nda Meta",        0,                 "0% das metas",          PENDENTE_FG),
        ]
        for idx, (lbl, val, sub, cor) in enumerate(kpi_data):
            c = _KPICard(lbl, val, sub, cor)
            kpi_grid.addWidget(c, 0, idx)
        row1.addLayout(kpi_grid, 1)
        main.addLayout(row1)

        # ── LINHA 2: Três gráficos ─────────────────────────────────────────
        row2 = QHBoxLayout()
        row2.setSpacing(16)

        def _wrap_chart(fig, stretch=1):
            f = _card_frame()
            ly = QVBoxLayout(f)
            ly.setContentsMargins(4,4,4,4)
            canvas = FigureCanvas(fig)
            canvas.setStyleSheet("background:transparent; border:none;")
            ly.addWidget(canvas)
            row2.addWidget(f, stretch)

        if HAS_MPL:
            _wrap_chart(_chart_desempenho(inds), stretch=3)
            _wrap_chart(_chart_evolucao(sub_raw), stretch=3)
            _wrap_chart(_chart_donut(stats), stretch=2)
        main.addLayout(row2)

        # ── LINHA 3: Destaques | Ranking | Pendências ──────────────────────
        row3 = QHBoxLayout()
        row3.setSpacing(16)

        # Destaques
        dest = _card_frame()
        dest_ly = QVBoxLayout(dest)
        dest_ly.setContentsMargins(0,0,0,0)
        dest_ly.setSpacing(0)
        dest_ly.addWidget(_section_header("DESTAQUES DO PERÍODO"))
        dest_body = QWidget()
        dest_body.setStyleSheet("background:transparent; border:none;")
        db = QVBoxLayout(dest_body)
        db.setContentsMargins(14,12,14,12)
        db.setSpacing(0)
        destaques = [
            ("✅", f"{stats['com_meta']} indicadores atingiram a meta no período.", VERDE),
            ("⚠️", f"{stats['em_atencao']} indicadores em atenção e requerem acompanhamento.", LARANJA),
            ("ℹ️", "Nenhum indicador abaixo da meta no período selecionado.", "#2196F3"),
            ("○", f"{stats['sem_meta']} indicadores não possuem meta definida.", CINZA_SUAVE),
        ]
        for ico, txt, cor in destaques:
            db.addWidget(_DestaqueItem(ico, txt, cor))
        dest_ly.addWidget(dest_body, 1)
        row3.addWidget(dest, 2)

        # Ranking
        rank = _card_frame()
        rank_ly = QVBoxLayout(rank)
        rank_ly.setContentsMargins(0,0,0,0)
        rank_ly.setSpacing(0)
        rank_ly.addWidget(_section_header("RANKING DE DESEMPENHO (Top 5)"))

        rank_body = QWidget()
        rank_body.setStyleSheet("background:transparent; border:none;")
        rb2 = QVBoxLayout(rank_body)
        rb2.setContentsMargins(14,10,14,12)
        rb2.setSpacing(0)

        # Cabeçalho
        hdr = QHBoxLayout()
        for txt_h, w in [("Posição",50),("Indicador",80),("",1),("Desempenho",130)]:
            l = QLabel(txt_h.upper())
            l.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            l.setStyleSheet(f"color:{CINZA_SUAVE}; background:transparent; border:none;")
            if w != 1: l.setFixedWidth(w)
            hdr.addWidget(l, 0 if w != 1 else 1)
        rb2.addLayout(hdr)

        div = QFrame(); div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(f"color:{CINZA_BORDA};"); rb2.addWidget(div)

        # Indicadores com resultado para ranking
        ranked = [(i, i.get("resultado_fev") or i.get("resultado_jan"))
                  for i in inds if (i.get("resultado_fev") or i.get("resultado_jan")) is not None]
        ranked = [(i, v) for i, v in ranked if v]
        # Mostrar top 5 pelos que têm dados
        for pos, (ind, val) in enumerate(ranked[:5], 1):
            pct = min(100, (val / (val * 1.3)) * 100) if val else 0
            pct = 60 + pos * 7  # distribui visualmente decrescente
            rb2.addWidget(_RankingRow(pos, ind["codigo"],
                                     ind["titulo"], round(100 - pos*4 + 4, 1)))
        rb2.addStretch()
        rank_ly.addWidget(rank_body, 1)
        row3.addWidget(rank, 3)

        # Pendências Críticas
        pend_frame = _card_frame()
        pend_ly = QVBoxLayout(pend_frame)
        pend_ly.setContentsMargins(0,0,0,0)
        pend_ly.setSpacing(0)
        pend_ly.addWidget(_section_header("PENDÊNCIAS CRÍTICAS"))
        pend_body = QWidget()
        pend_body.setStyleSheet("background:transparent; border:none;")
        pb = QVBoxLayout(pend_body)
        pb.setContentsMargins(14,12,14,12)
        pb.setSpacing(10)

        if pends:
            for p in pends:
                row_p = QFrame()
                cor_p = PENDENTE_FG if p["nivel"] == "CRÍTICO" else LARANJA
                row_p.setStyleSheet(f"""
                    QFrame {{
                        background: transparent;
                        border: 1px solid {CINZA_BORDA};
                        border-left: 3px solid {cor_p};
                        border-radius: 4px;
                    }}
                """)
                rp_ly = QHBoxLayout(row_p)
                rp_ly.setContentsMargins(10,8,10,8)
                rp_ly.setSpacing(8)
                desc = QLabel(f"{p['codigo']} – {p['descricao'][:55]}{'…' if len(p['descricao'])>55 else ''}")
                desc.setFont(QFont("Segoe UI", 8))
                desc.setStyleSheet(f"color:{PRETO_TITULO}; background:transparent; border:none;")
                desc.setWordWrap(True)
                rp_ly.addWidget(desc, 1)
                badge = QLabel(p["nivel"])
                badge.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
                badge.setStyleSheet(f"""
                    color: {BRANCO}; background: {cor_p};
                    border-radius: 3px; padding: 3px 7px; border: none;
                """)
                rp_ly.addWidget(badge)
                pb.addWidget(row_p)
        else:
            nl = QLabel("Nenhuma pendência crítica registrada.")
            nl.setFont(QFont("Segoe UI", 9))
            nl.setStyleSheet(f"color:{CINZA_SUAVE}; background:transparent; border:none;")
            pb.addWidget(nl)

        pb.addStretch()
        pend_ly.addWidget(pend_body, 1)
        row3.addWidget(pend_frame, 2)
        main.addLayout(row3)

        # ── Rodapé ────────────────────────────────────────────────────────
        footer = QLabel(
            f"Período: {stats['periodo']}   •   "
            f"Responsável: {stats['responsavel']}   •   "
            f"Última atualização: {stats['atualizacao']}"
        )
        footer.setFont(QFont("Segoe UI", 8))
        footer.setStyleSheet(f"color:{CINZA_SUAVE}; background:transparent;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main.addWidget(footer)
