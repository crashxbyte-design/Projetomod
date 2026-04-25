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
            border: 1px solid #DDE3EC;
            border-radius: 14px;
        }}
    """)
    f.setGraphicsEffect(shadow(16, (0,4), (0,0,0,10)))
    return f

def _section_header(icon, text):
    f = QFrame(); f.setStyleSheet("background:transparent;border:none;")
    hl = QHBoxLayout(f); hl.setContentsMargins(20, 14, 20, 12); hl.setSpacing(10)
    ico = QLabel(icon)
    ico.setFont(QFont("Segoe UI Emoji", 14))
    ico.setStyleSheet("background:transparent;border:none;color:#B91C1C;")
    lbl = QLabel(text.upper()); lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
    lbl.setStyleSheet("color:#1E293B;letter-spacing:1px;background:transparent;border:none;")
    hl.addWidget(ico); hl.addWidget(lbl); hl.addStretch()
    sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
    sep.setStyleSheet("background:#E2E8F0; border:none; max-height:1px;")
    outer = QFrame(); outer.setStyleSheet("background:transparent;border:none;")
    ol = QVBoxLayout(outer); ol.setContentsMargins(0,0,0,0); ol.setSpacing(0)
    ol.addWidget(f); ol.addWidget(sep)
    return outer

# ─────────────────────────────────────────────────────────────────────────────
# Gráficos
# ─────────────────────────────────────────────────────────────────────────────

def _chart_desempenho(indicadores):
    """Barras horizontais – status qualitativo por indicador."""
    n = len(indicadores)
    fig, ax = plt.subplots(figsize=(5.0, max(3.0, n * 0.52)), dpi=92)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")

    STATUS_COR = {
        "Dentro da meta": "#10B981",
        "Acima da meta":  "#059669",
        "Em Atenção":    "#F59E0B",
        "Abaixo da meta": "#EF4444",
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
        cor = STATUS_COR.get(st, "#E2E8F0")
        pct = STATUS_PCT.get(st, 0.0)
        bg  = "#F8FAFC" if pct == 0.0 else "#F1F5F9"
        ax.barh(idx, pct,       color=cor, height=0.45, edgecolor="none", zorder=3)
        ax.barh(idx, 1.0 - pct, left=pct, color=bg,    height=0.45, edgecolor="none", zorder=3)
        # Label de status
        st_label = st if len(st) < 18 else st[:16] + "…"
        c_lbl = "#64748B" if pct > 0 else "#94A3B8"
        ax.text(1.03, idx, st_label, va="center", ha="left",
                fontsize=7.5, fontweight="medium", color=c_lbl)

    ax.set_yticks(list(range(n)))
    ax.set_yticklabels(labels, fontsize=8.0, fontweight="bold", color="#1E293B")
    ax.set_xlim(0, 1.55)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"], fontsize=7, color="#94A3B8")
    ax.tick_params(axis="both", length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.xaxis.grid(True, color="#F1F5F9", linewidth=1.5, zorder=0)
    ax.set_axisbelow(True)
    ax.axvline(1.0, color="#CBD5E1", linewidth=1.5, linestyle=":", zorder=2)

    legenda = [
        mpatches.Patch(color="#10B981", label="Dentro da Meta"),
        mpatches.Patch(color="#F59E0B", label="Em Atenção"),
        mpatches.Patch(color="#EF4444", label="Abaixo da Meta"),
        mpatches.Patch(color="#E2E8F0", label="Sem Meta"),
    ]
    ax.legend(handles=legenda, loc="upper center", fontsize=7.5,
              frameon=False, ncol=2, bbox_to_anchor=(0.5, -0.05), labelcolor="#475569")
    ax.set_title("STATUS DE DESEMPENHO", fontsize=9,
                 fontweight="bold", color="#1E293B", pad=12, loc="left")
    fig.tight_layout(pad=0.5)
    return fig


def _chart_evolucao(sub_raw):
    """Barras agrupadas por mês (todos os meses com dados) — 2025 vs 2026."""
    import numpy as np

    def _total_mes(ano, mes):
        return sum(r["valor"] for r in sub_raw
                   if r["ano"] == ano and r["mes"] == mes and r["valor"] is not None)

    vals25 = [_total_mes(2025, m) for m in MESES_FULL]
    vals26 = [_total_mes(2026, m) for m in MESES_FULL]

    # Filtrar apenas meses que têm algum dado
    meses_com_dado = [i for i in range(12) if vals25[i] or vals26[i]]

    if not meses_com_dado:
        fig, ax = plt.subplots(figsize=(6.0, 3.8), dpi=92)
        fig.patch.set_facecolor("#FFFFFF")
        ax.text(0.5, 0.5, "Dados insuficientes\npara exibir o comparativo",
                ha="center", va="center", color="#94A3B8", fontsize=10,
                multialignment="center")
        ax.axis("off")
        return fig

    abrevs  = [MESES_ABREV[i] for i in meses_com_dado]
    v25_flt = [vals25[i] for i in meses_com_dado]
    v26_flt = [vals26[i] for i in meses_com_dado]

    fig, ax = plt.subplots(figsize=(6.0, 3.8), dpi=92)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")

    x = np.arange(len(abrevs))
    w = 0.38
    bars25 = ax.bar(x - w/2, v25_flt, width=w, color="#94A3B8",
                    label="■  2025", edgecolor="none", zorder=3)
    bars26 = ax.bar(x + w/2, v26_flt, width=w, color="#B91C1C",
                    label="■  2026", edgecolor="none", zorder=3)

    ax.set_xticks(x)
    ax.set_xticklabels(abrevs, fontsize=8, fontweight="bold", color="#64748B")
    ax.tick_params(axis="y", labelsize=7, colors="#94A3B8")
    ax.tick_params(axis="both", length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.yaxis.grid(True, color="#F1F5F9", linewidth=1.0, zorder=0)
    ax.set_axisbelow(True)

    # Labels nas barras (apenas se houver valor)
    max_v = max(v25_flt + v26_flt) if (v25_flt + v26_flt) else 1
    for bar in list(bars25) + list(bars26):
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width()/2, h + max_v * 0.02,
                    f"{int(h)}", ha="center", va="bottom",
                    fontsize=7, fontweight="bold", color="#334155")

    # Variação acumulada
    total25 = sum(v25_flt)
    total26 = sum(v26_flt)
    if total25 > 0:
        var_pct = (total26 - total25) / total25 * 100
        var_txt = f"▼ {abs(var_pct):.0f}%" if var_pct < 0 else f"▲ {var_pct:.0f}%"
        var_cor = "#EF4444" if var_pct < 0 else "#10B981"
        comp_msg = "Desempenho 2026 abaixo de 2025" if var_pct < 0 else "Desempenho 2026 acima de 2025"
        ax.text(0.0, -0.22, f"Variação acumulada (Jan–{abrevs[-1]}):  ",
                transform=ax.transAxes, fontsize=7.5, color="#64748B", ha="left")
        ax.text(0.52, -0.22, var_txt,
                transform=ax.transAxes, fontsize=7.5, color=var_cor,
                fontweight="bold", ha="left")
        ax.text(1.0, -0.22, comp_msg,
                transform=ax.transAxes, fontsize=7.5, color="#B91C1C",
                fontweight="bold", ha="right")

    ax.legend(fontsize=8, frameon=False, loc="upper right",
              labelcolor="#475569", handlelength=1)
    ax.set_title("COMPARAÇÃO MENSAL  –  2025 x 2026", fontsize=9.5,
                 fontweight="bold", color="#0F172A", pad=10, loc="left")
    fig.tight_layout(pad=0.7)
    return fig


def _chart_donut(stats):
    """Donut – distribuição de status dos indicadores."""
    fig, ax = plt.subplots(figsize=(3.0, 3.6), dpi=92)
    fig.patch.set_facecolor("#FFFFFF")

    # Ordem e cores da referência visual
    labels = ["Em Atenção", "Abaixo da Meta", "Dentro da Meta", "Sem Meta / Pendente"]
    values = [
        stats["em_atencao"],
        stats.get("abaixo_meta", 0),
        stats["com_meta"],
        stats["sem_meta"],
    ]
    colors = ["#94A3B8", "#E11D48", "#10B981", "#E2E8F0"]

    pairs = [(l, v, c) for l, v, c in zip(labels, values, colors) if v > 0]
    if not pairs:
        pairs = [("Sem dados", 1, "#CBD5E1")]
    ls, vs, cs = zip(*pairs)

    total = stats.get("total", sum(vs))

    wedges, _, autotexts = ax.pie(
        vs, labels=None, colors=cs, autopct="%1.0f%%",
        startangle=90, wedgeprops={"edgecolor": "#FFFFFF", "linewidth": 3},
        pctdistance=0.72
    )
    for t in autotexts:
        t.set_fontsize(8); t.set_color("#FFFFFF"); t.set_fontweight("bold")

    ax.add_patch(plt.Circle((0, 0), 0.55, color="#FFFFFF"))

    ax.text(0, 0.12, str(total), ha="center", va="center",
            fontsize=26, fontweight="bold", color="#0F172A")
    ax.text(0, -0.18, "Total de\nIndicadores", ha="center", va="center",
            fontsize=7, color="#64748B", multialignment="center")

    # Legenda lateral direita
    legend_items = [f"{l}  ({v})" for l, v in zip(ls, vs)]
    ax.legend(
        wedges, legend_items,
        loc="lower center", bbox_to_anchor=(0.5, -0.16),
        fontsize=7, frameon=False, ncol=1, labelcolor="#475569"
    )
    ax.set_title("DISTRIBUIÇÃO POR STATUS", fontsize=9,
                 fontweight="bold", color="#0F172A", pad=10, loc="left")
    fig.tight_layout(pad=0.5)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Sub-widgets
# ─────────────────────────────────────────────────────────────────────────────

class _KPICard(QFrame):
    def __init__(self, icon, label, value, sub, icon_color, icon_bg, val_color, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(200)
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setStyleSheet("""
            QFrame {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }
        """)
        self.setGraphicsEffect(shadow(12, (0,4), (0,0,0,6)))
        ly = QHBoxLayout(self)
        ly.setContentsMargins(20, 20, 20, 20)
        ly.setSpacing(16)
        
        # Left side - Icon
        ico_container = QFrame()
        ico_container.setFixedSize(56, 56)
        ico_container.setStyleSheet(f"background: {icon_bg}; border-radius: 28px; border: none;")
        ico_ly = QVBoxLayout(ico_container)
        ico_ly.setContentsMargins(0, 0, 0, 0)
        ico_lbl = QLabel(icon)
        ico_lbl.setFont(QFont("Segoe UI Emoji", 20))
        ico_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ico_lbl.setStyleSheet(f"background: transparent; color: {icon_color}; border: none;")
        ico_ly.addWidget(ico_lbl)
        
        ly.addWidget(ico_container)
        
        # Right side - Texts
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        text_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        t = QLabel(label.upper())
        t.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        t.setStyleSheet("color:#64748B; background:transparent; border:none; letter-spacing:0.5px;")
        t.setWordWrap(True)
        text_col.addWidget(t)

        v = QLabel(str(value))
        v.setFont(QFont("Segoe UI", 36, QFont.Weight.Bold))
        v.setStyleSheet(f"color:{val_color}; background:transparent; border:none; line-height: 1;")
        text_col.addWidget(v)

        if sub:
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setStyleSheet(f"background:{icon_color}; border:none; max-height:2px; margin: 4px 0px;")
            text_col.addWidget(sep)
            s = QLabel(sub)
            s.setFont(QFont("Segoe UI", 8))
            s.setStyleSheet("color:#64748B; background:transparent; border:none;")
            text_col.addWidget(s)

        ly.addLayout(text_col, 1)


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
    def __init__(self, pos, cod, nome, pct, parent=None):
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
        bar_inner.setStyleSheet(f"background:{VERDE}; border-radius:4px; border:none;")
        bar_inner.setGeometry(0, 0, int(100 * pct / 100), 16)
        ly.addWidget(bar_bg)

        pc = QLabel(f"{pct:.1f}%")
        pc.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        pc.setFixedWidth(42)
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

        # ── LINHA 1: KPI Cards ──────────────────────────────────────────────
        row1 = QHBoxLayout()
        row1.setSpacing(16)

        kpi_data = [
            ("📋", "Total de\nIndicadores", stats["total"],     "100% do total",         "#B91C1C", "#FEE2E2", "#B91C1C"),
            ("🎯", "Indicadores\nCom Meta",  stats["com_meta"], f"{(stats['com_meta']/max(stats['total'],1)*100):.0f}% do total", "#1E293B", "#F1F5F9", "#0F172A"),
            ("✅", "Metas\nAtingidas",       stats["com_meta"], f"{(stats['com_meta']/max(stats['total'],1)*100):.0f}% das metas", "#10B981", "#D1FAE5", "#10B981"),
            ("⚠️", "Em\nAtenção",            stats["em_atencao"], f"{(stats['em_atencao']/max(stats['total'],1)*100):.0f}% das metas", "#F59E0B", "#FEF3C7", "#F59E0B"),
            ("⬇️", "Abaixo\nDa Meta",        0,                 "0% das metas",          "#EF4444", "#FEE2E2", "#EF4444"),
        ]
        for idx, (ico, lbl, val, sub, ico_c, ico_bg, val_c) in enumerate(kpi_data):
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
        rh_frame.setStyleSheet("background:transparent;border:none;border-bottom:1px solid #E2E8F0;")
        rh_ly = QHBoxLayout(rh_frame); rh_ly.setContentsMargins(20, 16, 20, 16)
        r_lbl = QLabel("📄 RESUMO EXECUTIVO")
        r_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        r_lbl.setStyleSheet("color:#1E293B;letter-spacing:1px;background:transparent;border:none;")
        rh_ly.addWidget(r_lbl); rh_ly.addStretch()
        r_ly.addWidget(rh_frame)

        r_body = QWidget()
        r_body.setStyleSheet("background:transparent; border:none;")
        rb = QVBoxLayout(r_body)
        rb.setContentsMargins(20,16,20,20)
        rb.setSpacing(12)
        
        periodo = stats.get("periodo","Jan a Fev/2026")
        txt = QLabel(
            f"No período de {periodo}, o desempenho geral apresenta {(stats['em_atencao']/max(stats['total'],1)*100):.0f}% dos "
            f"indicadores em atenção. Nenhum indicador abaixo da meta."
        )
        txt.setFont(QFont("Segoe UI", 9))
        txt.setStyleSheet("color:#475569; background:transparent; border:none; line-height: 1.4;")
        txt.setWordWrap(True)
        rb.addWidget(txt)
        
        # Bullets do Resumo
        bullets = [
            ("🎯", f"<b>{stats['com_meta']} indicadores monitorados</b><br><span style='color:#64748B; font-size:11px;'>100% possuem meta definida</span>"),
            ("⚠️", f"<b>{stats['em_atencao']} indicador em atenção</b><br><span style='color:#64748B; font-size:11px;'>Acompanhamento recomendado</span>"),
            ("⬇️", "<b>0 indicadores abaixo da meta</b><br><span style='color:#64748B; font-size:11px;'>Ação imediata necessária</span>"),
            ("ℹ️", f"<b>{stats['com_meta']} indicadores atingiram a meta</b><br><span style='color:#64748B; font-size:11px;'>Foque nas ações corretivas</span>"),
        ]
        
        for ico, text in bullets:
            b_item = QWidget()
            b_ly = QHBoxLayout(b_item)
            b_ly.setContentsMargins(0,4,0,4)
            b_ly.setSpacing(12)
            i_lbl = QLabel(ico)
            i_lbl.setFont(QFont("Segoe UI Emoji", 14))
            t_lbl = QLabel(text)
            t_lbl.setFont(QFont("Segoe UI", 9))
            t_lbl.setStyleSheet("color:#334155; background:transparent; border:none;")
            b_ly.addWidget(i_lbl)
            b_ly.addWidget(t_lbl, 1)
            rb.addWidget(b_item)

        rb.addStretch()
        r_ly.addWidget(r_body, 1)
        row2.addWidget(resumo)

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
        dest_ly.addWidget(_section_header("🚨", "DESTAQUES DO PERÍODO"))
        dest_body = QWidget()
        dest_body.setStyleSheet("background:transparent; border:none;")
        db = QVBoxLayout(dest_body)
        db.setContentsMargins(20,12,20,20)
        db.setSpacing(4)
        destaques = [
            ("✅", f"{stats['com_meta']} indicadores atingiram a meta no período.", "#10B981"),
            ("⚠️", f"{stats['em_atencao']} indicador em atenção e requer acompanhamento.", "#F59E0B"),
            ("⬇️", f"{stats.get('abaixo_meta',1)} indicador abaixo da meta no período selecionado.", "#EF4444"),
            ("ℹ️", f"{stats['sem_meta']} indicadores não possuem meta definida.", "#3B82F6"),
        ]
        for ico, txt, cor in destaques:
            db.addWidget(_DestaqueItem(ico, txt, cor))
        db.addStretch()
        dest_ly.addWidget(dest_body, 1)
        row3.addWidget(dest, 2)

        # Ranking
        rank = _card_frame()
        rank_ly = QVBoxLayout(rank)
        rank_ly.setContentsMargins(0,0,0,0)
        rank_ly.setSpacing(0)
        rank_ly.addWidget(_section_header("🏆", "RANKING DE DESEMPENHO (Top 5)"))

        rank_body = QWidget()
        rank_body.setStyleSheet("background:transparent; border:none;")
        rb2 = QVBoxLayout(rank_body)
        rb2.setContentsMargins(20,12,20,12)
        rb2.setSpacing(6)

        # Cabeçalho
        hdr = QHBoxLayout()
        for txt_h, w in [("Posição",52),("Indicador",90),("",1),("Desempenho",140)]:
            l = QLabel(txt_h.upper())
            l.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            l.setStyleSheet("color:#94A3B8; background:transparent; border:none; letter-spacing:0.5px;")
            if w != 1: l.setFixedWidth(w)
            hdr.addWidget(l, 0 if w != 1 else 1)
        rb2.addLayout(hdr)

        div = QFrame(); div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("background:#E2E8F0; border:none;"); rb2.addWidget(div)

        # Indicadores com resultado para ranking
        ranked = [(i, i.get("resultado_fev") or i.get("resultado_jan"))
                  for i in inds if (i.get("resultado_fev") or i.get("resultado_jan")) is not None]
        ranked = [(i, v) for i, v in ranked if v]
        pcts_calc = [round(100 - pos*4 + 4, 1) for pos in range(1, len(ranked[:5])+1)]
        for pos, (ind, val) in enumerate(ranked[:5], 1):
            pct_v = pcts_calc[pos-1]
            rb2.addWidget(_RankingRow(pos, ind["codigo"], ind["titulo"], pct_v))
        rb2.addStretch()

        # Footer: Média
        if ranked:
            media_pct = sum(pcts_calc) / len(pcts_calc)
            footer_row = QFrame()
            footer_row.setStyleSheet("background:#FFF1F2; border: none; border-top: 1px solid #E2E8F0; border-radius: 0px;")
            fr_ly = QHBoxLayout(footer_row)
            fr_ly.setContentsMargins(0,10,0,10)
            fr_lbl = QLabel("📈  Média de desempenho dos indicadores")
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
        pend_ly.addWidget(_section_header("🔔", "PENDÊNCIAS CRÍTICAS"))
        pend_body = QWidget()
        pend_body.setStyleSheet("background:transparent; border:none;")
        pb = QVBoxLayout(pend_body)
        pb.setContentsMargins(20,12,20,16)
        pb.setSpacing(10)

        if pends:
            for p in pends:
                row_p = QFrame()
                cor_p = "#B91C1C" if p["nivel"] == "CRÍTICO" else "#F59E0B"
                nivel_txt = "ATENÇÃO" if p["nivel"] != "CRÍTICO" else "CRÍTICO"
                row_p.setStyleSheet(f"""
                    QFrame {{
                        background: #FFFFFF;
                        border: 1px solid #E2E8F0;
                        border-left: 4px solid {cor_p};
                        border-radius: 6px;
                    }}
                """)
                rp_ly = QHBoxLayout(row_p)
                rp_ly.setContentsMargins(14,10,14,10)
                rp_ly.setSpacing(12)
                desc = QLabel(f"{p['codigo']} – {p['descricao'][:50]}{'...' if len(p['descricao'])>50 else ''}")
                desc.setFont(QFont("Segoe UI", 9))
                desc.setStyleSheet("color:#1E293B; background:transparent; border:none;")
                desc.setWordWrap(True)
                rp_ly.addWidget(desc, 1)
                badge = QLabel(nivel_txt)
                badge.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                badge.setStyleSheet(f"""
                    color: #FFFFFF; background: {cor_p};
                    border-radius: 4px; padding: 4px 10px; border: none; letter-spacing: 0.5px;
                """)
                rp_ly.addWidget(badge)
                pb.addWidget(row_p)
        else:
            nl = QLabel("✓ Nenhuma pendência crítica registrada.")
            nl.setFont(QFont("Segoe UI", 10))
            nl.setStyleSheet("color:#10B981; background:transparent; border:none; padding-top:10px;")
            pb.addWidget(nl, alignment=Qt.AlignmentFlag.AlignCenter)

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
