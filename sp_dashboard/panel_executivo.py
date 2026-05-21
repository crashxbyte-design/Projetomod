"""
panel_executivo.py - Tela Painel Executivo (redesenhado).
Layout fiel ao print de referência:
  Linha 1: Resumo Executivo (esq) + KPI Cards (dir)
  Linha 2: Barras Desempenho | Linha Evolução | Donut Tipo
  Linha 3: Destaques | Ranking Top 5 | Pendências Críticas
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QSizePolicy, QComboBox
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont

from styles import (
    BRANCO, CINZA_BG, CINZA_SUAVE, COMBO_DROPDOWN_CSS
)
from widgets import shadow

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    HAS_MPL = True
    # ── Tema global Matplotlib (aplicado uma vez, vale para todos os gráficos) ──
    matplotlib.rcParams.update({
        "figure.facecolor":   "#FFFFFF",
        "axes.facecolor":     "#FFFFFF",
        "axes.grid":          True,
        "axes.grid.axis":     "y",
        "grid.color":         "#E2E8F0",
        "grid.linewidth":     0.6,
        "axes.spines.top":    False,
        "axes.spines.right":  False,
        "axes.spines.left":   False,
        "axes.spines.bottom": False,
        "xtick.bottom":       False,
        "ytick.left":         False,
        "xtick.color":        "#94A3B8",
        "ytick.color":        "#94A3B8",
        "xtick.labelsize":    8,
        "ytick.labelsize":    8,
        "axes.labelsize":     8,
        "axes.titlesize":     10,
        "axes.titleweight":   "bold",
        "axes.titlecolor":    "#0F172A",
        "legend.fontsize":    8,
        "legend.frameon":     False,
        "legend.labelcolor":  "#475569",
        "figure.dpi":         96,
    })
except ImportError:
    HAS_MPL = False

try:
    import qtawesome as qta
    HAS_QTA = True
except ImportError:
    HAS_QTA = False

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
            border: 1px solid #D1D9E6;
            border-radius: 14px;
        }}
    """)
    f.setGraphicsEffect(shadow(18, (0, 5), (0, 0, 0, 12)))
    return f

def _section_header(icon_name, text):
    f = QFrame()
    f.setStyleSheet("background:transparent;border:none;")
    hl = QHBoxLayout(f)
    hl.setContentsMargins(20, 14, 20, 12)
    hl.setSpacing(10)
    ico = QLabel()
    if HAS_QTA:
        px = qta.icon(icon_name, color="#B91C1C").pixmap(QSize(16, 16))
        ico.setPixmap(px)
    else:
        ico.setText("●")
        ico.setFont(QFont("Segoe UI", 10))
        ico.setStyleSheet("color:#B91C1C;")
    ico.setFixedWidth(20)
    ico.setAlignment(Qt.AlignmentFlag.AlignCenter)
    ico.setStyleSheet("background:transparent;border:none;")
    lbl = QLabel(text.upper())
    lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
    lbl.setStyleSheet("color:#1E293B;letter-spacing:1px;background:transparent;border:none;")
    hl.addWidget(ico)
    hl.addWidget(lbl)
    hl.addStretch()
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setStyleSheet("background:#E2E8F0; border:none; max-height:1px;")
    outer = QFrame()
    outer.setStyleSheet("background:transparent;border:none;")
    ol = QVBoxLayout(outer)
    ol.setContentsMargins(0, 0, 0, 0)
    ol.setSpacing(0)
    ol.addWidget(f)
    ol.addWidget(sep)
    return outer

# ─────────────────────────────────────────────────────────────────────────────
# Gráficos
# ─────────────────────────────────────────────────────────────────────────────

def _chart_desempenho(indicadores):
    """Barras horizontais – status por indicador (nova lógica 4 status)."""
    n = len(indicadores)
    if n == 0:
        fig, ax = plt.subplots(figsize=(5.0, 3.0), dpi=92)
        ax.text(0.5, 0.5, "Nenhum indicador cadastrado", ha="center", va="center",
                color="#94A3B8", fontsize=10)
        ax.axis("off")
        return fig

    fig, ax = plt.subplots(figsize=(5.0, max(3.2, n * 0.58)), dpi=92)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")

    STATUS_COR = {
        "Dentro da meta": "#10B981",
        "Em Atenção":   "#F59E0B",
        "Sem meta":       "#94A3B8",
        "A preencher":    "#E2E8F0",
    }
    STATUS_PCT = {
        "Dentro da meta": 1.0,
        "Em Atenção":   0.70,
        "Sem meta":       0.40,
        "A preencher":    0.0,
    }

    labels = [f" {i['codigo'][:12]}" for i in indicadores]
    for idx, ind in enumerate(indicadores):
        st  = ind["status"]
        cor = STATUS_COR.get(st, "#E2E8F0")
        pct = STATUS_PCT.get(st, 0.0)
        bg  = "#F8FAFC"
        ax.barh(idx, pct,       color=cor, height=0.48, edgecolor="none", zorder=3)
        ax.barh(idx, 1.0 - pct, left=pct, color=bg,    height=0.48, edgecolor="none", zorder=2)
        # Label de status à direita
        c_lbl = "#334155" if pct > 0.5 else "#94A3B8"
        ax.text(1.03, idx, st, va="center", ha="left",
                fontsize=7.5, color=c_lbl)

    ax.set_yticks(list(range(n)))
    ax.set_yticklabels(labels, fontsize=8.5, fontweight="bold", color="#1E293B")
    ax.set_xlim(0, 1.58)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"], fontsize=7, color="#94A3B8")
    ax.tick_params(axis="both", length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.xaxis.grid(True, color="#F1F5F9", linewidth=1.2, zorder=0)
    ax.set_axisbelow(True)
    ax.axvline(1.0, color="#CBD5E1", linewidth=1.5, linestyle=":", zorder=2)

    legenda = [
        mpatches.Patch(color="#10B981", label="Dentro da Meta"),
        mpatches.Patch(color="#F59E0B", label="Em Atenção"),
        mpatches.Patch(color="#94A3B8", label="Sem Meta"),
        mpatches.Patch(color="#E2E8F0", label="A Preencher"),
    ]
    ax.legend(handles=legenda, loc="lower center", fontsize=7.5,
              frameon=False, ncol=4, bbox_to_anchor=(0.5, -0.10), labelcolor="#475569")
    ax.set_title("STATUS DE DESEMPENHO — Por Indicador", fontsize=9.5,
                 fontweight="bold", color="#0F172A", pad=12, loc="left")
    fig.tight_layout(pad=0.6)
    return fig


def _chart_evolucao(sub_raw, ano_base=2025, ano_comp=2026):
    """Barras agrupadas — Dinâmico por ano. Layout executivo limpo."""
    import numpy as np

    def _total_mes(ano, mes):
        return sum(r["valor"] for r in sub_raw
                   if r["ano"] == ano and r["mes"] == mes and r["valor"] is not None)

    vals_base = [_total_mes(ano_base, m) for m in MESES_FULL]
    vals_comp = [_total_mes(ano_comp, m) for m in MESES_FULL]

    # Mostrar apenas até o último mês com dados (+ 1 buffer), no mínimo 2 meses
    indices_com_dados = [i for i in range(12) if vals_base[i] > 0 or vals_comp[i] > 0]
    cutoff = min(max(indices_com_dados) + 1, 11) if indices_com_dados else 1
    meses_exibir = list(range(cutoff + 1))
    abrevs  = [MESES_ABREV[i] for i in meses_exibir]
    v_base_flt = [vals_base[i] for i in meses_exibir]
    v_comp_flt = [vals_comp[i] for i in meses_exibir]

    n_meses = len(meses_exibir)
    fig, ax = plt.subplots(figsize=(6.4, 3.6), dpi=92)
    # facecolor já definido pelo rcParams global (#FFFFFF)

    x = np.arange(n_meses)
    w = 0.32

    # Barras Ano Base — cinza Slate suave
    ax.bar(x - w/2, v_base_flt, width=w,
           color="#CBD5E1", label=str(ano_base),
           edgecolor="none", zorder=3)
    # Barras Ano Comp — crimson
    ax.bar(x + w/2, v_comp_flt, width=w,
           color="#C8102E", label=str(ano_comp),
           edgecolor="none", zorder=3, alpha=0.92)

    # Eixos — spines/grid já configurados pelo rcParams; apenas customiza xticks
    ax.set_xticks(x)
    ax.set_xticklabels(abrevs, fontsize=8, color="#64748B")
    ax.tick_params(axis="both", length=0)
    ax.set_axisbelow(True)

    # Rótulos agrupados por mês: evita colisão quando as duas barras têm alturas parecidas.
    max_v = max(v_base_flt + v_comp_flt) if any(v_base_flt + v_comp_flt) else 1
    ax.set_ylim(0, max_v * 1.18)

    for idx, (base, comp) in enumerate(zip(v_base_flt, v_comp_flt)):
        top = max(base, comp)
        if top <= 0:
            continue

        if base > 0:
            ax.text(
                x[idx],
                top + max_v * 0.025,
                f"{int(base)}",
                ha="center",
                va="bottom",
                fontsize=6.0,
                fontweight="bold",
                color="#64748B",
                clip_on=False,
            )
        if comp > 0:
            ax.text(
                x[idx],
                top + max_v * (0.075 if base > 0 else 0.025),
                f"{int(comp)}",
                ha="center",
                va="bottom",
                fontsize=6.0,
                fontweight="bold",
                color="#991B1B",
                clip_on=False,
            )

    # Os seletores acima do gráfico já identificam os anos; manter a legenda fora da área
    # de plotagem evita conflito visual com Dezembro.

    # Variação acumulada
    total_base = sum(v_base_flt)
    total_comp = sum(v_comp_flt)
    if total_base > 0:
        var_pct = (total_comp - total_base) / total_base * 100
        seta    = "▼" if var_pct < 0 else "▲"
        var_cor = "#DC2626" if var_pct < 0 else "#059669"
        msg_cor = "#DC2626" if var_pct < 0 else "#059669"
        comp_msg = f"Desempenho {ano_comp} abaixo de {ano_base}" if var_pct < 0 else f"Desempenho {ano_comp} acima de {ano_base}"
        # Linha separadora
        ax.axhline(0, color="#E2E8F0", linewidth=0.8)
        ultimo_abrev = abrevs[[j for j,v in enumerate(v_comp_flt) if v>0][-1]] if any(v>0 for v in v_comp_flt) else abrevs[-1]
        ax.annotate(
            f"  Variação acumulada (Jan–{ultimo_abrev}):",
            xy=(0.0, -0.20), xycoords="axes fraction",
            fontsize=7, color="#64748B", ha="left"
        )
        ax.annotate(
            f"  {seta} {abs(var_pct):.0f}%",
            xy=(0.52, -0.20), xycoords="axes fraction",
            fontsize=7.5, color=var_cor, fontweight="bold", ha="left"
        )
        ax.annotate(
            comp_msg,
            xy=(1.0, -0.20), xycoords="axes fraction",
            fontsize=7, color=msg_cor, ha="right"
        )

    ax.set_title(f"COMPARAÇÃO MENSAL  –  {ano_base} × {ano_comp}", fontsize=9.5,
                 fontweight="bold", color="#0F172A", pad=12, loc="left")
    fig.tight_layout(pad=0.6)
    return fig


def _chart_donut(stats):
    """Donut executivo refinado — distribuição por status (nova lógica 4 status)."""
    fig, ax = plt.subplots(figsize=(4.4, 3.8), dpi=92)
    fig.patch.set_facecolor("#FFFFFF")

    labels = ["Dentro da Meta", "Em Atenção", "Sem Meta", "A Preencher"]
    values = [
        stats.get("atingidas", 0),
        stats.get("em_atencao", 0),
        stats.get("sem_meta", 0),
        stats.get("a_preencher", 0),
    ]
    colors = ["#10B981", "#F59E0B", "#94A3B8", "#E2E8F0"]

    pairs = [
        (label, value, color)
        for label, value, color in zip(labels, values, colors)
        if value > 0
    ]
    if not pairs:
        pairs = [("Sem dados", 1, "#CBD5E1")]
    ls, vs, cs = zip(*pairs)

    total = stats.get("total", sum(vs))

    wedges, _, autotexts = ax.pie(
        vs, labels=None, colors=cs, autopct="%1.0f%%",
        startangle=90,
        wedgeprops={"edgecolor": "#FFFFFF", "linewidth": 4, "antialiased": True},
        pctdistance=0.76
    )
    for t in autotexts:
        t.set_fontsize(9)
        t.set_fontweight("bold")
        t.set_color("#1E293B")

    # Buraco do donut mais largo
    ax.add_patch(plt.Circle((0, 0), 0.58, color="#FFFFFF"))

    # Texto central
    ax.text(0, 0.15, str(total), ha="center", va="center",
            fontsize=28, fontweight="bold", color="#0F172A")
    ax.text(0, -0.18, "Total de\nIndicadores", ha="center", va="center",
            fontsize=7, color="#94A3B8", multialignment="center",
            fontstyle="italic")

    ax.legend(
        wedges,
        [f"{label}  ({value})" for label, value in zip(ls, vs)],
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        fontsize=8, frameon=False, labelcolor="#334155",
        handlelength=1.0, handleheight=0.9,
        borderpad=0, labelspacing=0.8
    )
    ax.set_title("DISTRIBUIÇÃO POR STATUS", fontsize=9,
                 fontweight="bold", color="#0F172A", pad=14, loc="left")
    fig.subplots_adjust(left=0.02, right=0.56, top=0.88, bottom=0.05)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Sub-widgets
# ─────────────────────────────────────────────────────────────────────────────

class _KPICard(QFrame):
    def __init__(self, icon, label, value, sub, icon_color, icon_bg, val_color, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(180)
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setStyleSheet("""
            QFrame {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }
        """)
        self.setGraphicsEffect(shadow(14, (0, 4), (0, 0, 0, 8)))

        root_ly = QVBoxLayout(self)
        root_ly.setContentsMargins(0, 0, 0, 0)
        root_ly.setSpacing(0)

        # Conteúdo principal
        content = QWidget()
        content.setStyleSheet("background: transparent; border: none;")
        ly = QHBoxLayout(content)
        ly.setContentsMargins(20, 20, 20, 16)
        ly.setSpacing(16)

        # Lado esquerdo — ícone circular com qtawesome
        ico_container = QFrame()
        ico_container.setFixedSize(54, 54)
        ico_container.setStyleSheet(f"background: {icon_bg}; border-radius: 27px; border: none;")
        ico_ly = QVBoxLayout(ico_container)
        ico_ly.setContentsMargins(0, 0, 0, 0)
        ico_lbl = QLabel()
        if HAS_QTA:
            px = qta.icon(icon, color=icon_color).pixmap(QSize(24, 24))
            ico_lbl.setPixmap(px)
        else:
            ico_lbl.setText("●")
            ico_lbl.setFont(QFont("Segoe UI", 16))
            ico_lbl.setStyleSheet(f"color: {icon_color}; background: transparent; border: none;")
        ico_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ico_lbl.setStyleSheet("background: transparent; border: none;")
        ico_ly.addWidget(ico_lbl)
        ly.addWidget(ico_container)

        # Lado direito — textos
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        text_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        t = QLabel(label.upper().replace('\n', ' '))
        t.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        t.setStyleSheet("color: #6B7280; background: transparent; border: none; letter-spacing: 0.5px;")
        t.setWordWrap(True)
        text_col.addWidget(t)

        v = QLabel(str(value))
        v.setFont(QFont("Segoe UI", 44, QFont.Weight.Bold))
        v.setStyleSheet(f"color: {val_color}; background: transparent; border: none;")
        text_col.addWidget(v)

        if sub:
            s = QLabel(sub)
            s.setFont(QFont("Segoe UI", 8))
            s.setStyleSheet("color: #9CA3AF; background: transparent; border: none;")
            text_col.addWidget(s)

        ly.addLayout(text_col, 1)
        root_ly.addWidget(content, 1)

        # Linha accent colorida na base do card
        accent = QFrame()
        accent.setFixedHeight(3)
        accent.setStyleSheet(f"background: {val_color}; border: none; border-radius: 0px; "
                              f"border-bottom-left-radius: 12px; border-bottom-right-radius: 12px;")
        root_ly.addWidget(accent)


class _DestaqueItem(QWidget):
    def __init__(self, icon, text, color, parent=None):
        super().__init__(parent)
        ly = QHBoxLayout(self)
        ly.setContentsMargins(0, 8, 0, 8)
        ly.setSpacing(14)
        ico = QLabel(icon)
        ico.setFont(QFont("Segoe UI", 16))
        ico.setFixedWidth(28)
        ico.setStyleSheet(f"color:{color}; background:transparent; border:none;")
        ly.addWidget(ico)
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 10))
        lbl.setStyleSheet("color:#334155; background:transparent; border:none;")
        lbl.setWordWrap(True)
        ly.addWidget(lbl, 1)


class _RankingRow(QWidget):
    def __init__(self, pos, cod, nome, pct, bar_color="#10B981", parent=None):
        super().__init__(parent)
        ly = QHBoxLayout(self)
        ly.setContentsMargins(0, 6, 0, 6)
        ly.setSpacing(12)

        p = QLabel(f"{pos}º")
        p.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        p.setFixedWidth(24)
        p.setStyleSheet("color:#94A3B8; background:transparent; border:none;")
        ly.addWidget(p)

        c = QLabel(cod)
        c.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        c.setFixedWidth(84)
        c.setStyleSheet("color:#0F172A; background:transparent; border:none;")
        ly.addWidget(c)

        n = QLabel(nome[:28] + ("…" if len(nome) > 28 else ""))
        n.setFont(QFont("Segoe UI", 9))
        n.setStyleSheet("color:#64748B; background:transparent; border:none;")
        ly.addWidget(n, 1)

        bar_bg = QFrame()
        bar_bg.setFixedSize(100, 16)
        bar_bg.setStyleSheet("background:#F1F5F9; border-radius:4px; border:none;")
        bar_inner = QFrame(bar_bg)
        bar_inner.setStyleSheet(f"background:{bar_color}; border-radius:4px; border:none;")
        bar_inner.setGeometry(0, 0, max(2, int(100 * pct / 100)), 16)
        ly.addWidget(bar_bg)

        pc = QLabel(f"{pct:.1f}%")
        pc.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        pc.setFixedWidth(42)
        pc.setStyleSheet(f"color:{bar_color}; background:transparent; border:none;")
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

        # ── LINHA 1: KPI Cards ──────────────────────────────────────────────
        row1 = QHBoxLayout()
        row1.setSpacing(16)

        total       = stats["total"]
        com_meta    = stats["com_meta"]
        atingidas   = stats.get("atingidas", 0)
        em_atencao  = stats["em_atencao"]
        sem_meta    = stats.get("sem_meta", 0)
        a_preencher = stats.get("a_preencher", 0)

        kpi_data = [
            # (qta_icon, rótulo, valor, sublinha, cor_ícone, bg_ícone, cor_valor)
            ("fa5s.layer-group",          "Total de Indicadores",
             total, "monitorados no período",
             "#C8102E", "#FEF2F2", "#C8102E"),
            ("fa5s.bullseye",             "Com Meta Definida",
             com_meta,
             f"{com_meta/max(total,1)*100:.0f}% do total",
             "#334155", "#F1F5F9", "#0F172A"),
            ("fa5s.check-circle",         "Dentro da Meta",
             atingidas,
             f"{atingidas/max(com_meta,1)*100:.0f}% das metas",
             "#059669", "#DCFCE7", "#059669"),
            ("fa5s.exclamation-triangle", "Em Atenção",
             em_atencao,
             f"{em_atencao/max(com_meta,1)*100:.0f}% das metas",
             "#D97706", "#FEF3C7", "#D97706"),
            ("fa5s.minus-circle",         "Sem Meta",
             sem_meta,
             f"{sem_meta/max(total,1)*100:.0f}% do total",
             "#64748B", "#F8FAFC", "#475569"),
        ]
        for ico, lbl, val, sub, ico_c, ico_bg, val_c in kpi_data:
            c = _KPICard(ico, lbl, val, sub, ico_c, ico_bg, val_c)
            row1.addWidget(c)
        main.addLayout(row1)


        # ── LINHA 2: Resumo Executivo + Gráficos ───────────────────────────
        row2 = QHBoxLayout()
        row2.setSpacing(16)

        # Resumo
        resumo = _card_frame()
        resumo.setMinimumWidth(280)
        resumo.setMaximumWidth(320)
        
        r_ly = QVBoxLayout(resumo)
        r_ly.setContentsMargins(0,0,0,0)
        r_ly.setSpacing(0)
        
        rh_frame = QFrame()
        rh_frame.setStyleSheet("""
            background: #F8FAFC;
            border: none;
            border-bottom: 1px solid #E2E8F0;
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
        """)
        rh_ly = QHBoxLayout(rh_frame)
        rh_ly.setContentsMargins(20, 14, 20, 14)
        r_lbl = QLabel("RESUMO EXECUTIVO")
        r_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        r_lbl.setStyleSheet("""
            color: #0F172A;
            letter-spacing: 1.2px;
            background: transparent;
            border: none;
        """)
        rh_ly.addWidget(r_lbl)
        rh_ly.addStretch()
        # Badge do período
        periodo_badge = QLabel(stats.get("periodo", "Jan–Fev/2026"))
        periodo_badge.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        periodo_badge.setStyleSheet("""
            color: #C8102E;
            background: #FEF2F2;
            border: 1px solid #FECACA;
            border-radius: 10px;
            padding: 2px 10px;
        """)
        rh_ly.addWidget(periodo_badge)
        r_ly.addWidget(rh_frame)

        r_body = QWidget()
        r_body.setStyleSheet("background:transparent; border:none;")
        rb = QVBoxLayout(r_body)
        rb.setContentsMargins(20,16,20,20)
        rb.setSpacing(12)
        
        periodo = stats.get("periodo", "—")
        pct_ok      = atingidas / max(com_meta, 1) * 100 if com_meta else 0

        sumario = QLabel(
            f"Período: <b>{periodo}</b>. "
            f"<b>{com_meta}</b> de <b>{total}</b> indicadores possuem meta definida — "
            f"<b>{atingidas}</b> dentro da meta, <b>{em_atencao}</b> em atenção."
        )
        sumario.setFont(QFont("Segoe UI", 9))
        sumario.setStyleSheet("color:#475569; background:transparent; border:none; padding: 2px 0px;")
        sumario.setWordWrap(True)
        rb.addWidget(sumario)

        # Bullets com os 4 status da nova lógica
        def _bullet_row(color, bold_text, light_text):
            item = QWidget()
            item.setStyleSheet("background: transparent; border: none;")
            hl = QHBoxLayout(item)
            hl.setContentsMargins(0, 4, 0, 4)
            hl.setSpacing(12)
            dot = QLabel()
            dot.setFixedSize(20, 20)
            dot.setStyleSheet(f"""
                background: {color}18;
                border: 2px solid {color};
                border-radius: 10px;
            """)
            hl.addWidget(dot)
            txt_col = QVBoxLayout()
            txt_col.setSpacing(0)
            b = QLabel(bold_text)
            b.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            b.setStyleSheet("color: #1E293B; background:transparent; border:none;")
            secondary = QLabel(light_text)
            secondary.setFont(QFont("Segoe UI", 8))
            secondary.setStyleSheet("color: #64748B; background:transparent; border:none;")
            txt_col.addWidget(b)
            txt_col.addWidget(secondary)
            hl.addLayout(txt_col, 1)
            return item

        rb.addWidget(_bullet_row(
            "#059669",
            f"{atingidas} dentro da meta",
            f"{pct_ok:.0f}% dos indicadores com meta atingida"
        ))
        rb.addWidget(_bullet_row(
            "#D97706",
            f"{em_atencao} em atenção",
            "Requer acompanhamento imediato"
        ))
        if sem_meta > 0:
            rb.addWidget(_bullet_row(
                "#64748B",
                f"{sem_meta} sem meta definida",
                "Defina meta na Base de Dados"
            ))
        if a_preencher > 0:
            rb.addWidget(_bullet_row(
                "#94A3B8",
                f"{a_preencher} a preencher",
                "Nenhum valor registrado no período"
            ))

        rb.addStretch()
        r_ly.addWidget(r_body, 1)
        row2.addWidget(resumo)

        def _wrap_chart(fig, stretch=1):
            f = _card_frame()
            ly = QVBoxLayout(f)
            ly.setContentsMargins(4, 4, 4, 4)
            canvas = FigureCanvas(fig)
            canvas.setStyleSheet("background:transparent; border:none;")
            ly.addWidget(canvas)
            row2.addWidget(f, stretch)

        if HAS_MPL:
            # 3 colunas como na referência: Comparativo + Donut
            chart_container = self._build_dynamic_chart_frame()
            row2.addWidget(chart_container, 4)
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
        dest_ly.addWidget(_section_header("fa5s.star", "DESTAQUES DO PERÍODO"))
        dest_body = QWidget()
        dest_body.setStyleSheet("background:transparent; border:none;")
        db = QVBoxLayout(dest_body)
        db.setContentsMargins(20,12,20,20)
        db.setSpacing(4)
        _dest_items = [
            ("fa5s.check-circle",        "#059669", f"<b>{atingidas}</b> indicadores dentro da meta no período."),
            ("fa5s.exclamation-triangle", "#D97706", f"<b>{em_atencao}</b> indicador(es) em atenção — acompanhamento necessário."),
            ("fa5s.minus-circle",         "#3B82F6", f"<b>{sem_meta}</b> indicador(es) sem meta definida."),
            ("fa5s.clock",                "#94A3B8", f"<b>{a_preencher}</b> indicador(es) ainda a preencher (sem valor)."),
        ]
        for icon_n, icon_c, txt in _dest_items:
            it = QWidget()
            it.setStyleSheet("background:transparent;border:none;")
            hl = QHBoxLayout(it)
            hl.setContentsMargins(0, 6, 0, 6)
            hl.setSpacing(12)
            i_lbl = QLabel()
            if HAS_QTA:
                px = qta.icon(icon_n, color=icon_c).pixmap(QSize(16, 16))
                i_lbl.setPixmap(px)
            else:
                i_lbl.setText("●")
                i_lbl.setStyleSheet(f"color:{icon_c};font-size:10px;")
            i_lbl.setFixedWidth(22)
            i_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
            i_lbl.setStyleSheet("background:transparent;border:none;")
            t_lbl = QLabel(txt)
            t_lbl.setFont(QFont("Segoe UI", 10))
            t_lbl.setStyleSheet("color:#334155; background:transparent; border:none;")
            t_lbl.setWordWrap(True)
            hl.addWidget(i_lbl)
            hl.addWidget(t_lbl, 1)
            db.addWidget(it)
        db.addStretch()
        dest_ly.addWidget(dest_body, 1)
        row3.addWidget(dest, 2)

        # Ranking
        rank = _card_frame()
        rank_ly = QVBoxLayout(rank)
        rank_ly.setContentsMargins(0,0,0,0)
        rank_ly.setSpacing(0)
        rank_ly.addWidget(_section_header("fa5s.trophy", "RANKING DE DESEMPENHO (Top 5)"))

        rank_body = QWidget()
        rank_body.setStyleSheet("background:transparent; border:none;")
        rb2 = QVBoxLayout(rank_body)
        rb2.setContentsMargins(20,12,20,12)
        rb2.setSpacing(6)

        # Cabeçalho
        hdr = QHBoxLayout()
        for txt_h, w in [("Posição",52),("Indicador",90),("",1),("Desempenho",140)]:
            label = QLabel(txt_h.upper())
            label.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            label.setStyleSheet("color:#94A3B8; background:transparent; border:none; letter-spacing:0.5px;")
            if w != 1:
                label.setFixedWidth(w)
            hdr.addWidget(label, 0 if w != 1 else 1)
        rb2.addLayout(hdr)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("background:#E2E8F0; border:none;")
        rb2.addWidget(div)

        # Função para calcular desempenho real
        def _pct_real(ind):
            val = ind.get("resultado_fev") or ind.get("resultado_jan")
            meta = ind.get("meta_numero")
            op   = ind.get("meta_operador")
            st   = ind.get("status", "")
            if st == "Dentro da meta":
                return 100.0
            if val is None or meta is None or not op:
                return 0.0
            try:
                val = float(val)
                meta = float(meta)
                if meta == 0:
                    return 0.0
                if op in (">=", ">"):
                    return min(100.0, round(val / meta * 100, 1))
                elif op in ("<=", "<"):
                    return min(100.0, round(meta / val * 100, 1)) if val else 100.0
                else:
                    return 100.0 if val == meta else max(0.0, round((1 - abs(val-meta)/meta)*100, 1))
            except Exception:
                return 0.0

        # Ordenar por desempenho real descendente
        status_ord = {"Dentro da meta": 0, "Em Atenção": 1, "Sem meta": 2, "A preencher": 3}
        ranked_inds = sorted(
            [i for i in inds if i.get("resultado_fev") is not None or i.get("resultado_jan") is not None],
            key=lambda i: (status_ord.get(i.get("status", ""), 9), -_pct_real(i))
        )
        pcts_reais = []
        for pos, ind in enumerate(ranked_inds[:5], 1):
            pct_v = _pct_real(ind)
            pcts_reais.append(pct_v)
            bar_c = "#10B981" if ind.get("status") == "Dentro da meta" else "#F59E0B"
            rb2.addWidget(_RankingRow(pos, ind["codigo"], ind["titulo"], pct_v, bar_c))
        rb2.addStretch()

        # Footer: Média real
        if pcts_reais:
            media_pct = sum(pcts_reais) / len(pcts_reais)
            footer_row = QFrame()
            footer_row.setStyleSheet("background:#FFF1F2; border: none; border-top: 1px solid #E2E8F0; border-radius: 0px;")
            fr_ly = QHBoxLayout(footer_row)
            fr_ly.setContentsMargins(0,10,0,10)
            fr_lbl = QLabel("  Média de desempenho dos indicadores")
            fr_lbl.setFont(QFont("Segoe UI", 9))
            fr_lbl.setStyleSheet("color:#475569; background:transparent; border:none;")
            fr_val = QLabel(f"{media_pct:.0f}%")
            fr_val.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            fr_val.setStyleSheet("color:#B91C1C; background:transparent; border:none;")
            fr_ly.addSpacing(20)
            fr_ly.addWidget(fr_lbl, 1)
            fr_ly.addWidget(fr_val)
            fr_ly.addSpacing(20)
            rank_ly.addWidget(rank_body, 1)
            rank_ly.addWidget(footer_row)
        else:
            rank_ly.addWidget(rank_body, 1)
        row3.addWidget(rank, 3)

        # Pendências Críticas
        pend_frame = _card_frame()
        pend_ly = QVBoxLayout(pend_frame)
        pend_ly.setContentsMargins(0,0,0,0)
        pend_ly.setSpacing(0)
        pend_ly.addWidget(_section_header("fa5s.bell", "PENDÊNCIAS CRÍTICAS"))
        pend_body = QWidget()
        pend_body.setStyleSheet("background:transparent; border:none;")
        pb = QVBoxLayout(pend_body)
        pb.setContentsMargins(20,12,20,16)
        pb.setSpacing(10)

        # Filtrar apenas pendências com conteúdo útil
        pends_uteis = [
            p for p in pends
            if (p.get("descricao") or "").strip() or (p.get("causa") or "").strip() or (p.get("acao") or "").strip()
        ]

        if pends_uteis:
            for p in pends_uteis:
                row_p = QFrame()
                cor_p = "#B91C1C" if p["nivel"] == "CRÍTICO" else "#F59E0B"
                nivel_txt = "CRÍTICO" if p["nivel"] == "CRÍTICO" else "ATENÇÃO"
                row_p.setStyleSheet(f"""
                    QFrame {{
                        background: #FFFFFF;
                        border: 1px solid #E2E8F0;
                        border-left: 4px solid {cor_p};
                        border-radius: 6px;
                    }}
                """)
                rp_ly = QVBoxLayout(row_p)
                rp_ly.setContentsMargins(14, 10, 14, 10)
                rp_ly.setSpacing(4)
                # Linha 1: código + badge
                top_row = QHBoxLayout()
                top_row.setSpacing(8)
                cod_lbl = QLabel(f"{p['codigo']} — {p['titulo'][:40]}{'...' if len(p['titulo'])>40 else ''}")
                cod_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                cod_lbl.setStyleSheet("color:#1E293B; background:transparent; border:none;")
                top_row.addWidget(cod_lbl, 1)
                badge = QLabel(nivel_txt)
                badge.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                badge.setStyleSheet(f"""
                    color: #FFFFFF; background: {cor_p};
                    border-radius: 4px; padding: 3px 8px; border: none;
                """)
                top_row.addWidget(badge)
                rp_ly.addLayout(top_row)
                # Linha 2: descrição (se houver)
                desc_txt = (p.get("descricao") or "").strip()
                if desc_txt:
                    desc = QLabel(desc_txt[:80] + ("..." if len(desc_txt) > 80 else ""))
                    desc.setFont(QFont("Segoe UI", 8))
                    desc.setStyleSheet("color:#64748B; background:transparent; border:none;")
                    desc.setWordWrap(True)
                    rp_ly.addWidget(desc)
                pb.addWidget(row_p)
        else:
            empty_w = QWidget()
            empty_w.setStyleSheet("background:transparent; border:none;")
            ev = QVBoxLayout(empty_w)
            ev.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ev.setSpacing(8)
            ico_empty = QLabel()
            if HAS_QTA:
                px = qta.icon("fa5s.check-circle", color="#10B981").pixmap(QSize(28, 28))
                ico_empty.setPixmap(px)
            ico_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ico_empty.setStyleSheet("background:transparent; border:none;")
            txt_empty = QLabel("Nenhuma pendência crítica registrada.")
            txt_empty.setFont(QFont("Segoe UI", 10))
            txt_empty.setStyleSheet("color:#10B981; background:transparent; border:none;")
            txt_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ev.addWidget(ico_empty)
            ev.addWidget(txt_empty)
            pb.addWidget(empty_w)

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

    def _build_dynamic_chart_frame(self):
        f = _card_frame()
        ly = QVBoxLayout(f)
        ly.setContentsMargins(10, 10, 10, 10)
        ly.setSpacing(4)

        # Header com seletores
        hdr = QHBoxLayout()
        hdr.setContentsMargins(10, 0, 10, 0)
        
        lbl = QLabel("Análise Anual:")
        lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #475569; background:transparent; border:none;")
        hdr.addWidget(lbl)

        anos = self.data.get("anos_disponiveis", [2024, 2025, 2026])
        if not anos:
            anos = [2025, 2026]

        # Container do canvas precisa existir ANTES de conectar os sinais
        self.chart_canvas_container = QVBoxLayout()

        self.cb_base = QComboBox()
        self.cb_comp = QComboBox()
        for cb in [self.cb_base, self.cb_comp]:
            cb.addItems([str(a) for a in anos])
            cb.setStyleSheet(f"""
                QComboBox {{
                    border: 1px solid #CBD5E1; border-radius: 4px; padding: 2px 8px;
                    color: #1E293B; background: #FFFFFF; font-size: 11px;
                }}
                {COMBO_DROPDOWN_CSS}
            """)
            cb.currentIndexChanged.connect(self._update_dynamic_chart)

        # Default: base=penúltimo, comp=último
        if len(anos) >= 2:
            self.cb_base.setCurrentText(str(anos[-2]))
            self.cb_comp.setCurrentText(str(anos[-1]))
        elif anos:
            self.cb_base.setCurrentText(str(anos[-1]))
            self.cb_comp.setCurrentText(str(anos[-1]))

        hdr.addWidget(QLabel("Base:"))
        hdr.addWidget(self.cb_base)
        hdr.addSpacing(10)
        hdr.addWidget(QLabel("vs."))
        hdr.addSpacing(10)
        hdr.addWidget(QLabel("Comp:"))
        hdr.addWidget(self.cb_comp)
        hdr.addStretch()

        ly.addLayout(hdr)
        ly.addLayout(self.chart_canvas_container, 1)
        
        self._update_dynamic_chart()
        return f

    def _update_dynamic_chart(self):
        # Limpa o layout antigo do canvas
        while self.chart_canvas_container.count():
            item = self.chart_canvas_container.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        sub_raw = self.data.get("sub_raw", [])
        try:
            a_base = int(self.cb_base.currentText())
            a_comp = int(self.cb_comp.currentText())
        except ValueError:
            a_base, a_comp = 2025, 2026

        fig = _chart_evolucao(sub_raw, a_base, a_comp)
        canvas = FigureCanvas(fig)
        canvas.setStyleSheet("background:transparent; border:none;")
        self.chart_canvas_container.addWidget(canvas)
