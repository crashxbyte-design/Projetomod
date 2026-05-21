"""
panel_subindicadores.py - Tela Gráficos e Subindicadores (Análise Detalhada).
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QComboBox, QSizePolicy, QSpacerItem, QGridLayout
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont

from styles import (
    VERMELHO, VERMELHO_ESC, BRANCO, CINZA_BG, CINZA_BORDA,
    CINZA_SUAVE, PRETO_TITULO, VERDE, LARANJA, CINZA_META,
    AZUL, COMBO_DROPDOWN_CSS
)
from widgets import SectionTitle, shadow
import database as db

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

MESES = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
         "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
MESES_ABREV = [m[:3] for m in MESES]


def _card_frame():
    f = QFrame()
    f.setStyleSheet(f"""
        QFrame {{
            background: {BRANCO};
            border: 1px solid {CINZA_BORDA};
            border-radius: 12px;
        }}
    """)
    f.setGraphicsEffect(shadow(12, (0, 3), (0, 0, 0, 10)))
    return f


def _setup_hover(fig, ax, lines=None, bars=None):
    """Configura o hover (tooltip) para linhas e barras no matplotlib."""
    annot = ax.annotate("", xy=(0,0), xytext=(0, 10), textcoords="offset points",
                        bbox=dict(boxstyle="round4,pad=0.5", fc=BRANCO, ec=CINZA_BORDA, lw=1),
                        arrowprops=dict(arrowstyle="-|>", connectionstyle="arc3,rad=0", color=PRETO_TITULO))
    annot.set_visible(False)
    annot.set_zorder(99)
    annot.set_fontfamily("sans-serif")
    annot.set_fontsize(9)

    def update_annot_line(line, ind):
        x, y = line.get_data()
        idx = ind["ind"][0]
        annot.xy = (x[idx], y[idx])
        val = y[idx]
        lbl = line.get_label()
        mes = MESES_ABREV[int(x[idx])] if isinstance(x[idx], (int, float)) else x[idx]
        annot.set_text(f"{lbl} ({mes})\n{val:g}")
        annot.get_bbox_patch().set_alpha(0.9)

    def update_annot_bar(bar, lbl, mes_idx):
        x = bar.get_x() + bar.get_width() / 2.
        y = bar.get_height()
        annot.xy = (x, y)
        mes = MESES_ABREV[mes_idx]
        annot.set_text(f"{lbl} ({mes})\n{y:g}")
        annot.get_bbox_patch().set_alpha(0.9)

    def hover(event):
        vis = annot.get_visible()
        if event.inaxes == ax:
            # Lines
            if lines:
                for line in lines:
                    cont, ind = line.contains(event)
                    if cont:
                        update_annot_line(line, ind)
                        annot.set_visible(True)
                        fig.canvas.draw_idle()
                        return
            # Bars
            if bars:
                for container, lbl in bars:
                    for i, bar in enumerate(container):
                        cont, _ = bar.contains(event)
                        if cont:
                            update_annot_bar(bar, lbl, i)
                            annot.set_visible(True)
                            fig.canvas.draw_idle()
                            return
        if vis:
            annot.set_visible(False)
            fig.canvas.draw_idle()

    fig.canvas.mpl_connect("motion_notify_event", hover)


def _make_line_chart(dados_base, dados_comp, ano_base, ano_comp, titulo, meses_mostrar):
    """Gera o gráfico comparativo em linhas."""
    fig, ax = plt.subplots(figsize=(8.0, 3.5), dpi=100)
    fig.patch.set_facecolor(BRANCO)
    ax.set_facecolor(BRANCO)

    if not dados_base and not dados_comp:
        ax.text(0.5, 0.5, "Sem dados suficientes para gerar o gráfico.", 
                ha='center', va='center', color=CINZA_SUAVE, fontsize=11)
        ax.axis('off')
        fig.tight_layout()
        return fig

    # Use all months for x-axis, but only plot values for meses_mostrar
    vals_base = [dados_base.get(m, None) if m in meses_mostrar else None for m in MESES]
    vals_comp = [dados_comp.get(m, None) if m in meses_mostrar else None for m in MESES]

    # Plot
    l1, = ax.plot(MESES_ABREV, vals_base, marker='o', color=CINZA_SUAVE, linewidth=2, markersize=6, label=f"Ano {ano_base}")
    l2, = ax.plot(MESES_ABREV, vals_comp, marker='o', color=VERMELHO_ESC, linewidth=2.5, markersize=7, label=f"Ano {ano_comp}")

    # Estilização
    ax.set_title(titulo.upper(), fontsize=10, fontweight='bold', color=PRETO_TITULO, pad=15)
    ax.set_ylabel("")
    ax.tick_params(axis="y", labelsize=8, colors=CINZA_SUAVE)
    ax.tick_params(axis="x", labelsize=9, colors=PRETO_TITULO)
    
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color(CINZA_BORDA)
    ax.yaxis.grid(True, color=CINZA_BORDA, linewidth=0.5, linestyle='--')
    ax.set_axisbelow(True)

    ax.legend(frameon=False, loc="upper right", fontsize=9, labelcolor=PRETO_TITULO)

    _setup_hover(fig, ax, lines=[l1, l2])

    fig.tight_layout()
    return fig

def _make_bar_chart(dados_base, dados_comp, ano_base, ano_comp, titulo, meses_mostrar):
    """Gera o gráfico comparativo em barras agrupadas."""
    fig, ax = plt.subplots(figsize=(8.0, 3.5), dpi=100)
    fig.patch.set_facecolor(BRANCO)
    ax.set_facecolor(BRANCO)

    if not dados_base and not dados_comp:
        ax.text(0.5, 0.5, "Sem dados suficientes para gerar o gráfico.", 
                ha='center', va='center', color=CINZA_SUAVE, fontsize=11)
        ax.axis('off')
        fig.tight_layout()
        return fig

    x = np.arange(len(MESES))
    width = 0.35

    vals_base = [dados_base.get(m, 0) if (m in meses_mostrar and dados_base.get(m) is not None) else 0 for m in MESES]
    vals_comp = [dados_comp.get(m, 0) if (m in meses_mostrar and dados_comp.get(m) is not None) else 0 for m in MESES]

    b1 = ax.bar(x - width/2, vals_base, width, label=f"Ano {ano_base}", color=CINZA_SUAVE)
    b2 = ax.bar(x + width/2, vals_comp, width, label=f"Ano {ano_comp}", color=VERMELHO_ESC)

    # Estilização
    ax.set_title(titulo.upper(), fontsize=10, fontweight='bold', color=PRETO_TITULO, pad=15)
    ax.set_ylabel("")
    ax.set_xticks(x)
    ax.set_xticklabels(MESES_ABREV)
    ax.tick_params(axis="y", labelsize=8, colors=CINZA_SUAVE)
    ax.tick_params(axis="x", labelsize=9, colors=PRETO_TITULO)
    
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color(CINZA_BORDA)
    ax.yaxis.grid(True, color=CINZA_BORDA, linewidth=0.5, linestyle='--')
    ax.set_axisbelow(True)

    ax.legend(frameon=False, loc="upper right", fontsize=9, labelcolor=PRETO_TITULO)

    _setup_hover(fig, ax, bars=[(b1, f"Ano {ano_base}"), (b2, f"Ano {ano_comp}")])

    fig.tight_layout()
    return fig


class SubindicadoresPanel(QWidget):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self.sub_raw = self.data.get("sub_raw", [])
        
        # Map Indicador Principal (Codigo - Titulo) -> Subindicadores
        self.mapa_ind_sub = {}
        for s in self.sub_raw:
            cod_ind = s.get("codigo_indicador")
            nome_sub = s.get("nome_subindicador")
            if cod_ind and nome_sub:
                # Find title in indicadores
                titulo_ind = cod_ind
                for i in self.data.get("indicadores", []):
                    if i["codigo"] == cod_ind:
                        titulo_ind = f"{cod_ind} - {i['titulo']}"
                        break
                        
                if titulo_ind not in self.mapa_ind_sub:
                    self.mapa_ind_sub[titulo_ind] = set()
                self.mapa_ind_sub[titulo_ind].add(nome_sub)
                
        # Lista de indicadores ordenados
        self.lista_inds = sorted(list(self.mapa_ind_sub.keys()))
        
        # Anos disponíveis
        self.anos_disponiveis = self.data.get("anos_disponiveis", [2025, 2026])
        if len(self.anos_disponiveis) < 2 and 2026 not in self.anos_disponiveis:
            self.anos_disponiveis.append(self.anos_disponiveis[0] + 1 if self.anos_disponiveis else 2026)
            self.anos_disponiveis.sort()

        # Mapa de modo e id por subindicador: (cod_ind, nome_sub) -> modo / id
        self.mapa_modo_sub = {}
        self.mapa_sub_id   = {}
        try:
            for sub in db.get_all_subindicadores():
                key = (sub["codigo_indicador"], sub["nome_subindicador"])
                self.mapa_modo_sub[key] = sub.get("modo_lancamento") or "mensal"
                self.mapa_sub_id[key]   = sub["id"]
        except Exception:
            pass


        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root.addWidget(scroll)

        self.container = QWidget()
        self.container.setStyleSheet(f"background: {CINZA_BG};")
        scroll.setWidget(self.container)

        self.main_ly = QVBoxLayout(self.container)
        self.main_ly.setContentsMargins(28, 24, 28, 32)
        self.main_ly.setSpacing(24)

        # ── Cabeçalho e Título ─────────────────────────────────────────────
        header_ly = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        title_col.addWidget(SectionTitle("ANÁLISE DE SUBINDICADORES"))
        
        info = QLabel("Acompanhamento gerencial e comparativo evolutivo dos subindicadores da operação.")
        info.setFont(QFont("Segoe UI", 10))
        info.setStyleSheet(f"color: {CINZA_SUAVE};")
        title_col.addWidget(info)
        
        header_ly.addLayout(title_col)
        header_ly.addStretch()
        self.main_ly.addLayout(header_ly)

        # ── Controles de Filtro (Premium) ──────────────────────────────────
        filter_frame = _card_frame()
        filter_frame.setStyleSheet(filter_frame.styleSheet().replace(f"background: {BRANCO};", "background: #F8FAFC; border: 1px dashed #CBD5E1;"))
        filter_main_ly = QVBoxLayout(filter_frame)
        filter_main_ly.setContentsMargins(20, 16, 20, 16)
        filter_main_ly.setSpacing(16)
        
        row1_ly = QHBoxLayout()
        row1_ly.setSpacing(20)
        row2_ly = QHBoxLayout()
        row2_ly.setSpacing(20)

        # Função auxiliar para combo
        def _make_combo(label_text, parent_ly, min_width=0):
            col = QVBoxLayout()
            col.setSpacing(4)
            lbl = QLabel(label_text)
            lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            lbl.setStyleSheet(f"color: {CINZA_SUAVE}; text-transform: uppercase;")
            col.addWidget(lbl)
            from PySide6.QtWidgets import QSizePolicy, QComboBox
            cb = QComboBox()
            if min_width > 0:
                cb.setMinimumWidth(min_width)
            cb.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
            cb.setStyleSheet(f"""
                QComboBox {{
                    border: 1px solid {CINZA_BORDA}; border-radius: 6px; padding: 6px 35px 6px 10px;
                    color: {PRETO_TITULO}; background: {BRANCO}; font-size: 13px; font-weight: 500;
                }}
                {COMBO_DROPDOWN_CSS}
                QComboBox:disabled {{ background: #E2E8F0; color: #94A3B8; }}
            """)
            col.addWidget(cb)
            parent_ly.addLayout(col)
            return cb

        self.cb_ind = _make_combo("Indicador Principal", row1_ly, 380)
        self.cb_sub = _make_combo("Subindicador Analisado", row1_ly, 280)

        # Badge de modo de lançamento — atualiza com a seleção de subindicador
        self.lbl_modo_badge = QLabel("")
        self.lbl_modo_badge.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.lbl_modo_badge.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.lbl_modo_badge.setFixedHeight(24)
        self.lbl_modo_badge.setContentsMargins(0, 0, 0, 0)
        row1_ly.addWidget(self.lbl_modo_badge)
        self.cb_grafico = _make_combo("Tipo de Gráfico", row1_ly, 180)
        self.cb_grafico.addItems(["Linha", "Barras Agrupadas", "Grade Mensal"])
        self.cb_grafico.setCurrentText("Barras Agrupadas")
        
        row1_ly.addStretch()
        
        self.cb_ab = _make_combo("Ano Base", row2_ly, 120)
        self.cb_ac = _make_combo("Ano Comparativo", row2_ly, 120)
        self.cb_modo = _make_combo("Modo de Recorte", row2_ly, 140)
        self.cb_modo.addItems(["Automático", "Manual"])
        self.cb_mes_ini = _make_combo("Mês Inicial", row2_ly, 140)
        self.cb_mes_ini.addItems(MESES)
        self.cb_mes_fim = _make_combo("Mês Final", row2_ly, 140)
        self.cb_mes_fim.addItems(MESES)
        
        row2_ly.addStretch()

        filter_main_ly.addLayout(row1_ly)
        filter_main_ly.addLayout(row2_ly)

        self.main_ly.addWidget(filter_frame)

        # ── Dashboard Body (Será recriado dinamicamente) ───────────────────
        self.body_container = QWidget()
        self.body_ly = QVBoxLayout(self.body_container)
        self.body_ly.setContentsMargins(0,0,0,0)
        self.body_ly.setSpacing(24)
        self.main_ly.addWidget(self.body_container, 1)

        # Popula combos iniciais
        self._populate_combos()

        # Sinais
        self.cb_ind.currentIndexChanged.connect(self._on_ind_changed)
        self.cb_sub.currentIndexChanged.connect(self._update_dashboard)
        self.cb_ab.currentIndexChanged.connect(self._update_dashboard)
        self.cb_ac.currentIndexChanged.connect(self._update_dashboard)
        self.cb_grafico.currentIndexChanged.connect(self._update_dashboard)
        
        self.cb_modo.currentIndexChanged.connect(self._on_modo_changed)
        self.cb_mes_ini.currentIndexChanged.connect(self._on_mes_manual_changed)
        self.cb_mes_fim.currentIndexChanged.connect(self._on_mes_manual_changed)

        self.cb_sub.currentIndexChanged.connect(self._update_modo_badge)
        # Trigger inicial
        self._on_modo_changed()
        if self.lista_inds:
            self._on_ind_changed()

    def _populate_combos(self):
        self.cb_ind.blockSignals(True)
        self.cb_ind.clear()
        self.cb_ind.addItems(self.lista_inds)
        self.cb_ind.blockSignals(False)

        self.cb_ab.blockSignals(True)
        self.cb_ac.blockSignals(True)
        self.cb_ab.clear()
        self.cb_ac.clear()
        
        str_anos = [str(a) for a in self.anos_disponiveis]
        self.cb_ab.addItems(str_anos)
        self.cb_ac.addItems(str_anos)
        
        if len(str_anos) >= 2:
            self.cb_ab.setCurrentText(str_anos[-2])
            self.cb_ac.setCurrentText(str_anos[-1])
        elif len(str_anos) == 1:
            self.cb_ab.setCurrentText(str_anos[0])
            self.cb_ac.setCurrentText(str_anos[0])
            
        self.cb_ab.blockSignals(False)
        self.cb_ac.blockSignals(False)

    def _on_ind_changed(self):
        ind_sel = self.cb_ind.currentText()
        subs = sorted(list(self.mapa_ind_sub.get(ind_sel, [])))
        
        if subs:
            subs.insert(0, "GERAL (Todos)")
            
        self.cb_sub.blockSignals(True)
        self.cb_sub.clear()
        self.cb_sub.addItems(subs)
        self.cb_sub.blockSignals(False)
        
        self._update_modo_badge()
        self._update_dashboard()
        
    def _update_modo_badge(self):
        """Atualiza o badge de modo de lançamento conforme o subindicador selecionado."""
        ind_sel = self.cb_ind.currentText()
        sub_sel = self.cb_sub.currentText()
        if not sub_sel or sub_sel == "GERAL (Todos)" or not ind_sel:
            self.lbl_modo_badge.setText("")
            self.lbl_modo_badge.setStyleSheet("")
            return
        # Extrai codigo_indicador do texto "COD - Titulo"
        cod = ind_sel.split(" - ")[0] if " - " in ind_sel else ind_sel
        modo = self.mapa_modo_sub.get((cod, sub_sel), "mensal")
        if modo == "por_horario":
            self.lbl_modo_badge.setText("  Lancamento por Horario  ")
            self.lbl_modo_badge.setStyleSheet(
                "color:#1D4ED8;background:#DBEAFE;"
                "border:1px solid #93C5FD;border-radius:10px;"
                "padding:0px 8px;"
            )
        else:
            self.lbl_modo_badge.setText("  Mensal  ")
            self.lbl_modo_badge.setStyleSheet(
                "color:#065F46;background:#D1FAE5;"
                "border:1px solid #6EE7B7;border-radius:10px;"
                "padding:0px 8px;"
            )

    def _on_modo_changed(self):
        is_manual = (self.cb_modo.currentText() == "Manual")
        self.cb_mes_ini.setEnabled(is_manual)
        self.cb_mes_fim.setEnabled(is_manual)
        self._update_dashboard()
        
    def _on_mes_manual_changed(self):
        if self.cb_modo.currentText() == "Manual":
            idx_ini = self.cb_mes_ini.currentIndex()
            idx_fim = self.cb_mes_fim.currentIndex()
            # Ensure logical range
            if idx_ini > idx_fim:
                self.cb_mes_fim.blockSignals(True)
                self.cb_mes_fim.setCurrentIndex(idx_ini)
                self.cb_mes_fim.blockSignals(False)
            self._update_dashboard()

    def _update_dashboard(self):
        # Limpar body atual
        while self.body_ly.count():
            item = self.body_ly.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

        ind_sel = self.cb_ind.currentText()
        sub_sel = self.cb_sub.currentText()
        ano_b = self.cb_ab.currentText()
        ano_c = self.cb_ac.currentText()
        modo = self.cb_modo.currentText()
        tipo_grafico = self.cb_grafico.currentText()

        if not sub_sel or not ano_b or not ano_c:
            return

        try:
            ano_b = int(ano_b)
            ano_c = int(ano_c)
        except:
            return

        # Filtrar dados para os anos e subindicador selecionado
        dados_base = {}
        dados_comp = {}

        is_geral = (sub_sel == "GERAL (Todos)")

        for s in self.sub_raw:
            # We match the indicator title by checking if it starts with the codigo_indicador
            # since ind_sel is in the format "COD - Titulo"
            if ind_sel.startswith(s.get("codigo_indicador", "")):
                if is_geral or s.get("nome_subindicador") == sub_sel:
                    a = s.get("ano")
                    m = s.get("mes")
                    v = s.get("valor")
                    if v is not None:
                        if a == ano_b:
                            dados_base[m] = dados_base.get(m, 0.0) + float(v)
                        if a == ano_c:
                            dados_comp[m] = dados_comp.get(m, 0.0) + float(v)

        # Calcular o intervalo de meses comparáveis baseados no modo
        meses_comparaveis = []
        if modo == "Automático":
            for m in MESES:
                if m in dados_comp and m in dados_base:
                    meses_comparaveis.append(m)
            
            # Atualiza os combos manuais visualmente para refletir o recorte detectado
            if meses_comparaveis:
                self.cb_mes_ini.blockSignals(True)
                self.cb_mes_fim.blockSignals(True)
                self.cb_mes_ini.setCurrentText(meses_comparaveis[0])
                self.cb_mes_fim.setCurrentText(meses_comparaveis[-1])
                self.cb_mes_ini.blockSignals(False)
                self.cb_mes_fim.blockSignals(False)
        else:
            idx_ini = self.cb_mes_ini.currentIndex()
            idx_fim = self.cb_mes_fim.currentIndex()
            meses_comparaveis = MESES[idx_ini:idx_fim+1]
                
        soma_base = sum([dados_base[m] for m in meses_comparaveis if dados_base.get(m) is not None])
        soma_comp = sum([dados_comp[m] for m in meses_comparaveis if dados_comp.get(m) is not None])
        
        if soma_base > 0:
            var_pct = ((soma_comp - soma_base) / soma_base) * 100
        else:
            var_pct = 0.0
            
        # Determinar string do período comparável
        if modo == "Automático":
            periodo_txt = "(recorte comparável)"
        else:
            if len(meses_comparaveis) == 12:
                periodo_txt = "(Jan–Dez)"
            elif len(meses_comparaveis) > 1:
                periodo_txt = f"({meses_comparaveis[0][:3]}–{meses_comparaveis[-1][:3]})"
            elif len(meses_comparaveis) == 1:
                periodo_txt = f"({meses_comparaveis[0][:3]})"
            else:
                periodo_txt = "(Sem meses)"

        # ── Resumo Analítico (KPIs) ────────────────────────────────────────
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(16)
        
        from widgets import KPICard
        c1 = KPICard(f"Acumulado Base {periodo_txt}", f"{soma_base:g}", f"Em {ano_b} no mesmo recorte", CINZA_SUAVE)
        c2 = KPICard(f"Acumulado Atual {periodo_txt}", f"{soma_comp:g}", f"Em {ano_c} no mesmo recorte", VERMELHO_ESC)
        
        cor_var = VERDE if var_pct >= 0 else VERMELHO
        sinal = "+" if var_pct > 0 else ""
        c3 = KPICard("Variação do Recorte", f"{sinal}{var_pct:.1f}%", f"Modo {modo}", cor_var)
        
        c1.setFixedHeight(105); c2.setFixedHeight(105); c3.setFixedHeight(105)
        kpi_row.addWidget(c1); kpi_row.addWidget(c2); kpi_row.addWidget(c3)
        self.body_ly.addLayout(kpi_row)
        
        # ── Bloco Analítico Textual ────────────────────────────────────────
        if meses_comparaveis:
            analise_frame = QFrame()
            analise_frame.setStyleSheet(f"""
                QFrame {{
                    background: #F8FAFC; border: 1px dashed {CINZA_BORDA}; border-radius: 8px;
                }}
            """)
            analise_ly = QHBoxLayout(analise_frame)
            analise_ly.setContentsMargins(16, 12, 16, 12)
            analise_ly.setSpacing(12)
            
            ico_an = QLabel("📈")
            ico_an.setFont(QFont("Segoe UI", 12))
            ico_an.setStyleSheet("background:transparent; border:none;")
            analise_ly.addWidget(ico_an)
            
            # Achar o melhor mês no ano comparativo (dentre os selecionados)
            comp_vals_validos = {m: dados_comp[m] for m in meses_comparaveis if m in dados_comp}
            melhor_mes = max(comp_vals_validos.items(), key=lambda x: x[1])[0] if comp_vals_validos else "—"
            
            media_comp = soma_comp / len(meses_comparaveis) if meses_comparaveis else 0
            
            txt_an = QLabel(
                f"Comparação em {len(meses_comparaveis)} meses. "
                f"O pico do ano atual ocorreu em {melhor_mes}. "
                f"A média mensal em {ano_c} é de {media_comp:.1f}. "
                f"A variação acumulada de {sinal}{var_pct:.1f}% indica uma tendência de {'alta' if var_pct > 0 else 'baixa'} em relação à base."
            )
            txt_an.setFont(QFont("Segoe UI", 9))
            txt_an.setStyleSheet(f"color: {CINZA_SUAVE}; background: transparent; border: none;")
            analise_ly.addWidget(txt_an, 1)
            self.body_ly.addWidget(analise_frame)

        # ── Visualização (Gráfico ou Grade) ────────────────────────────────
        viz_card = _card_frame()
        viz_ly = QVBoxLayout(viz_card)
        viz_ly.setContentsMargins(16, 20, 16, 16)
        
        # Detectar modo do subindicador para título e info
        cod_sel = ind_sel.split(" - ")[0] if " - " in ind_sel else ind_sel
        modo_sub = self.mapa_modo_sub.get((cod_sel, sub_sel), "mensal") if sub_sel != "GERAL (Todos)" else "mensal"
        modo_tag = " [Consolidado por Horário]" if modo_sub == "por_horario" else ""
        titulo_grafico = f"Evolução Mensal{modo_tag} — {sub_sel} ({ano_b} vs {ano_c})"
        
        if tipo_grafico in ["Linha", "Barras Agrupadas"] and HAS_MPL:
            if tipo_grafico == "Linha":
                fig = _make_line_chart(dados_base, dados_comp, ano_b, ano_c, titulo_grafico, meses_comparaveis)
            else:
                fig = _make_bar_chart(dados_base, dados_comp, ano_b, ano_c, titulo_grafico, meses_comparaveis)
            
            canvas = FigureCanvas(fig)
            canvas.setStyleSheet("border: none; background: transparent;")
            viz_ly.addWidget(canvas)
            
        elif tipo_grafico == "Grade Mensal":
            lbl_title = QLabel(titulo_grafico.upper())
            lbl_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            lbl_title.setStyleSheet(f"color: {PRETO_TITULO}; background: transparent; border: none;")
            lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            viz_ly.addWidget(lbl_title)
            viz_ly.addSpacing(16)
            
            grid_w = QWidget()
            grid_ly = QGridLayout(grid_w)
            grid_ly.setSpacing(16)
            grid_ly.setContentsMargins(10, 10, 10, 10)
            
            for i, m in enumerate(MESES):
                row = i // 4
                col = i % 4
                
                v_base = dados_base.get(m)
                v_comp = dados_comp.get(m)
                is_valid = m in meses_comparaveis
                
                f = QFrame()
                # Tratamento visual sutil para meses fora do recorte ou sem dado
                if not is_valid:
                    f.setStyleSheet(f"background: #F8FAFC; border-radius: 8px; border: 1px solid #E2E8F0;")
                else:
                    f.setStyleSheet(f"background: {BRANCO}; border-radius: 8px; border: 1px solid {CINZA_BORDA};")
                    
                f_ly = QVBoxLayout(f)
                f_ly.setContentsMargins(16, 12, 16, 12)
                f_ly.setSpacing(8)
                
                l_mes = QLabel(m.upper())
                l_mes.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                l_mes.setStyleSheet("color: #475569; border: none;")
                l_mes.setAlignment(Qt.AlignmentFlag.AlignCenter)
                f_ly.addWidget(l_mes)
                
                div = QFrame()
                div.setFixedHeight(1)
                div.setStyleSheet("background: #E2E8F0;")
                f_ly.addWidget(div)
                
                # Valores Comparativos (Duas Colunas)
                vals_ly = QHBoxLayout()
                vals_ly.setSpacing(16)
                
                def _val_lbl(ano_lbl, v_val, color):
                    ly_v = QVBoxLayout()
                    ly_v.setSpacing(2)
                    la = QLabel(str(ano_lbl))
                    la.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                    la.setStyleSheet("color: #94A3B8; border: none;")
                    la.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    lv = QLabel(f"{v_val if v_val is not None else '—'}")
                    lv.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
                    lv.setStyleSheet(f"color: {color}; border: none;")
                    lv.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    ly_v.addWidget(la)
                    ly_v.addWidget(lv)
                    return ly_v
                    
                color_b = CINZA_SUAVE if is_valid and v_base is not None else "#CBD5E1"
                color_c = VERMELHO_ESC if is_valid and v_comp is not None else "#CBD5E1"
                
                vals_ly.addLayout(_val_lbl(ano_b, v_base, color_b))
                vals_ly.addLayout(_val_lbl(ano_c, v_comp, color_c))
                f_ly.addLayout(vals_ly)
                
                # Comparativo / Delta
                if is_valid and v_base is not None and v_comp is not None and v_base > 0:
                    delta = ((v_comp - v_base) / v_base) * 100
                    d_color = VERDE if delta >= 0 else VERMELHO
                    d_bg = "rgba(5, 150, 105, 0.15)" if delta >= 0 else "rgba(200, 16, 46, 0.15)"
                    d_txt = f"Δ {('+' if delta > 0 else '')}{delta:.1f}%"
                else:
                    d_color = "#94A3B8"
                    d_bg = "transparent"
                    d_txt = "Δ —"
                    
                l_delta = QLabel(d_txt)
                l_delta.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                l_delta.setStyleSheet(f"color: {d_color}; background: {d_bg}; border-radius: 4px; padding: 4px 6px; border: none;")
                l_delta.setAlignment(Qt.AlignmentFlag.AlignCenter)
                f_ly.addWidget(l_delta)
                
                grid_ly.addWidget(f, row, col)
                
            viz_ly.addWidget(grid_w)
            viz_ly.addStretch()
        else:
            lbl = QLabel("Gráfico indisponível (Matplotlib ausente)")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            viz_ly.addWidget(lbl)
            
        self.body_ly.addWidget(viz_card, 1)

        # ── Seção de análise por horário (só para por_horario) ────────────────
        if modo_sub == "por_horario" and sub_sel != "GERAL (Todos)":
            sub_id_h = self.mapa_sub_id.get((cod_sel, sub_sel))
            if sub_id_h:
                self._build_horario_section(sub_id_h)

    # ═══════════════════════════════════════════════════════════════════════
    #  ANÁLISE POR HORÁRIO — métodos dedicados
    # ═══════════════════════════════════════════════════════════════════════

    def _build_horario_section(self, sub_id: int):
        """Monta a seção de análise detalhada por horário abaixo do gráfico principal."""
        import re as _re

        anos_h = db.get_anos_horario(sub_id)
        if not anos_h:
            ano_def, mes_def = None, None
        else:
            ano_def = anos_h[-1]
            meses_h = db.get_meses_horario(sub_id, ano_def)
            mes_def = meses_h[-1] if meses_h else None

        # ── Card container ──────────────────────────────────────────────
        card = _card_frame()
        card.setStyleSheet(card.styleSheet() + "QFrame{border-top:3px solid #3B82F6;}")
        ly = QVBoxLayout(card)
        ly.setContentsMargins(22, 18, 22, 22)
        ly.setSpacing(14)

        # Header
        hdr = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        t1 = QLabel("ANÁLISE DETALHADA · LANÇAMENTOS POR HORÁRIO")
        t1.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        t1.setStyleSheet(f"color:{PRETO_TITULO};letter-spacing:1px;")
        t2 = QLabel("Distribuição dos lançamentos que compõem o valor mensal consolidado")
        t2.setFont(QFont("Segoe UI", 8))
        t2.setStyleSheet(f"color:{CINZA_SUAVE};")
        title_col.addWidget(t1); title_col.addWidget(t2)
        hdr.addLayout(title_col)

        badge = QLabel("  ⏰ Por Horário  ")
        badge.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        badge.setStyleSheet("color:#1D4ED8;background:#DBEAFE;border:1px solid #93C5FD;"
                            "border-radius:10px;padding:2px 8px;")
        hdr.addWidget(badge)
        hdr.addStretch()

        # Combos
        def _mini_combo(lbl_txt, width):
            col = QVBoxLayout(); col.setSpacing(2)
            lb = QLabel(lbl_txt)
            lb.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            lb.setStyleSheet(f"color:{CINZA_SUAVE};")
            cb = QComboBox(); cb.setFixedWidth(width)
            cb.setStyleSheet(COMBO_DROPDOWN_CSS)
            col.addWidget(lb); col.addWidget(cb)
            hdr.addLayout(col)
            return cb

        self._h_cb_ano = _mini_combo("Ano", 90)
        self._h_cb_mes = _mini_combo("Mês", 120)

        # Populate ano
        self._h_cb_ano.addItems([str(a) for a in anos_h])
        if ano_def:
            self._h_cb_ano.setCurrentText(str(ano_def))

        ly.addLayout(hdr)

        div = QFrame(); div.setFixedHeight(1)
        div.setStyleSheet("background:#E2E8F0;")
        ly.addWidget(div)

        # Content area (rebuilt on filter change)
        self._h_body = QWidget()
        self._h_body_ly = QVBoxLayout(self._h_body)
        self._h_body_ly.setContentsMargins(0,0,0,0)
        self._h_body_ly.setSpacing(14)
        ly.addWidget(self._h_body)

        # Signals — must capture sub_id
        def _on_ano():
            a_txt = self._h_cb_ano.currentText()
            if not a_txt:
                return
            meses = db.get_meses_horario(sub_id, int(a_txt))
            self._h_cb_mes.blockSignals(True)
            self._h_cb_mes.clear()
            self._h_cb_mes.addItems(meses)
            if meses:
                self._h_cb_mes.setCurrentText(meses[-1])
            self._h_cb_mes.blockSignals(False)
            _refresh()

        def _refresh():
            a = self._h_cb_ano.currentText()
            m = self._h_cb_mes.currentText()
            if a and m:
                self._refresh_horario_content(sub_id, int(a), m)

        self._h_cb_ano.currentIndexChanged.connect(_on_ano)
        self._h_cb_mes.currentIndexChanged.connect(_refresh)

        # Initial
        _on_ano()

        self.body_ly.addWidget(card)

    def _refresh_horario_content(self, sub_id: int, ano: int, mes: str):
        """Reconstrói o corpo da seção horária para o (ano, mês) selecionado."""
        import re as _re
        RE_HORA = _re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")

        # Clear
        while self._h_body_ly.count():
            it = self._h_body_ly.takeAt(0)
            if it.widget(): it.widget().deleteLater()
            elif it.layout(): self._clear_layout(it.layout())

        dados = db.get_lancamentos_horario(sub_id, ano, mes)

        # ── Estado vazio ────────────────────────────────────────────────
        if not dados:
            empty = QFrame()
            empty.setStyleSheet("background:#F8FAFC;border:1px dashed #CBD5E1;"
                                "border-radius:10px;")
            e_ly = QVBoxLayout(empty)
            e_ly.setContentsMargins(0, 36, 0, 36)
            e_ly.setSpacing(6)
            for txt, fnt, col in [
                ("📭", 28, "#94A3B8"),
                (f"Nenhum lançamento em {mes} de {ano}", 10, CINZA_SUAVE),
                ("Use a aba Histórico Mensal para adicionar lançamentos", 8, "#CBD5E1"),
            ]:
                lb = QLabel(txt); lb.setFont(QFont("Segoe UI", fnt))
                lb.setStyleSheet(f"color:{col};background:transparent;border:none;")
                lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
                e_ly.addWidget(lb)
            self._h_body_ly.addWidget(empty)
            return

        # Flatten
        lancamentos = []
        for dia, faixas in dados.items():
            for faixa, rec in faixas.items():
                val = rec.get("valor") if isinstance(rec, dict) else rec
                obs = rec.get("obs", "") if isinstance(rec, dict) else ""
                if val is not None:
                    tipo = "horario" if RE_HORA.match(str(faixa).strip()) else "periodo"
                    lancamentos.append({"dia": int(dia), "faixa": faixa,
                                        "valor": float(val), "obs": obs, "tipo": tipo})

        if not lancamentos:
            return

        has_h = any(l["tipo"] == "horario" for l in lancamentos)
        has_p = any(l["tipo"] == "periodo" for l in lancamentos)
        is_mixed = has_h and has_p

        if is_mixed:
            note = QLabel("ℹ️  Mês com mistura de Horário Pontual e Período — "
                          "identificados por cor no gráfico de faixas")
            note.setFont(QFont("Segoe UI", 8))
            note.setStyleSheet("color:#92400E;background:#FFFBEB;border:1px solid #FDE68A;"
                               "border-radius:6px;padding:6px 10px;")
            self._h_body_ly.addWidget(note)

        # ── Gráficos lado a lado ─────────────────────────────────────────
        if HAS_MPL:
            row_w = QWidget()
            row_ly = QHBoxLayout(row_w)
            row_ly.setContentsMargins(0,0,0,0)
            row_ly.setSpacing(16)

            fig1 = self._h_chart_faixa(lancamentos, mes, ano, is_mixed)
            c1 = FigureCanvas(fig1)
            c1.setStyleSheet("border:none;background:transparent;")
            c1.setMinimumHeight(260)
            row_ly.addWidget(c1, 6)

            fig2 = self._h_chart_daily(lancamentos, mes, ano)
            c2 = FigureCanvas(fig2)
            c2.setStyleSheet("border:none;background:transparent;")
            c2.setMinimumHeight(260)
            row_ly.addWidget(c2, 4)

            self._h_body_ly.addWidget(row_w)

        # ── Tabela bruta ─────────────────────────────────────────────────
        self._h_body_ly.addWidget(self._h_raw_table(lancamentos, is_mixed))

    def _h_chart_faixa(self, lancamentos, mes, ano, is_mixed):
        """Barras por faixa horária/período — totais do mês."""
        from collections import defaultdict
        import matplotlib.pyplot as plt
        import numpy as np

        totais = defaultdict(float)
        tipos  = {}
        for l in lancamentos:
            totais[l["faixa"]] += l["valor"]
            tipos[l["faixa"]]   = l["tipo"]

        # Sort: horario chronological, period by value desc
        def sort_key(f):
            import re as _re
            m = _re.match(r"^(\d{2}):(\d{2})$", f)
            if m: return (0, int(m.group(1))*60 + int(m.group(2)))
            order = {"Manhã":1,"Tarde":2,"Noite":3,"Madrugada":0}
            return (1, order.get(f, 99))

        faixas = sorted(totais.keys(), key=sort_key)
        vals   = [totais[f] for f in faixas]
        cores  = ["#3B82F6" if tipos.get(f) == "horario" else "#F59E0B" for f in faixas]

        fig, ax = plt.subplots(figsize=(7, 3.5))
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")

        n = len(faixas)
        use_h = n > 7  # horizontal se muitas faixas
        if use_h:
            bars = ax.barh(range(n), vals, color=cores, height=0.6)
            ax.set_yticks(range(n)); ax.set_yticklabels(faixas, fontsize=8)
            ax.set_xlabel("Valor", fontsize=8)
            for bar, v in zip(bars, vals):
                ax.text(bar.get_width() + max(vals)*0.01, bar.get_y() + bar.get_height()/2,
                        f"{v:g}", va="center", fontsize=8, color="#374151")
        else:
            bars = ax.bar(range(n), vals, color=cores, width=0.6)
            ax.set_xticks(range(n))
            ax.set_xticklabels(faixas, rotation=30 if n > 4 else 0,
                                ha="right" if n > 4 else "center", fontsize=8)
            for bar, v in zip(bars, vals):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(vals)*0.02,
                        f"{v:g}", ha="center", fontsize=8, color="#374151")

        ax.set_title(f"Por Faixa Horária · {mes}/{ano}", fontsize=9,
                     color="#374151", loc="left", pad=8)
        ax.spines[["top","right"]].set_visible(False)
        ax.tick_params(colors="#94A3B8")
        ax.set_ylabel("")
        ax.yaxis.set_tick_params(length=0)
        ax.xaxis.set_tick_params(length=0)
        ax.set_axisbelow(True)
        ax.yaxis.grid(True, color="#F1F5F9", linewidth=0.8) if not use_h else \
            ax.xaxis.grid(True, color="#F1F5F9", linewidth=0.8)

        if is_mixed:
            from matplotlib.patches import Patch
            ax.legend(handles=[Patch(color="#3B82F6", label="Horário Pontual"),
                                Patch(color="#F59E0B", label="Período")],
                      fontsize=7, framealpha=0.8, loc="upper right")

        fig.tight_layout(pad=1.2)
        return fig

    def _h_chart_daily(self, lancamentos, mes, ano):
        """Barras por dia do mês — soma diária."""
        import matplotlib.pyplot as plt
        from collections import defaultdict

        por_dia = defaultdict(float)
        for l in lancamentos:
            por_dia[l["dia"]] += l["valor"]

        dias = sorted(por_dia.keys())
        vals = [por_dia[d] for d in dias]
        media = sum(vals) / len(vals) if vals else 0

        fig, ax = plt.subplots(figsize=(5, 3.5))
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")

        ax.bar(dias, vals, color="#6366F1", width=0.7, alpha=0.85)
        if len(dias) > 1:
            ax.axhline(media, color="#94A3B8", linewidth=1, linestyle="--")
            ax.text(max(dias) + 0.3, media, f"  méd {media:.1f}",
                    fontsize=7, va="center", color="#94A3B8")

        ax.set_title(f"Evolução Diária · {mes}/{ano}", fontsize=9,
                     color="#374151", loc="left", pad=8)
        ax.set_xlabel("Dia", fontsize=8)
        ax.spines[["top","right"]].set_visible(False)
        ax.tick_params(colors="#94A3B8")
        ax.xaxis.set_tick_params(length=0)
        ax.yaxis.set_tick_params(length=0)
        ax.yaxis.grid(True, color="#F1F5F9", linewidth=0.8)
        ax.set_axisbelow(True)

        fig.tight_layout(pad=1.2)
        return fig

    def _h_raw_table(self, lancamentos, is_mixed):
        """Tabela compacta dos lançamentos brutos do mês."""
        frame = QFrame()
        frame.setStyleSheet(f"background:{BRANCO};border:1px solid #E2E8F0;border-radius:8px;")
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(14, 12, 14, 12)
        fl.setSpacing(6)

        # Título
        t = QLabel("LANÇAMENTOS DO MÊS")
        t.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        t.setStyleSheet(f"color:{CINZA_SUAVE};letter-spacing:1px;border:none;background:transparent;")
        fl.addWidget(t)

        div = QFrame(); div.setFixedHeight(1)
        div.setStyleSheet("background:#F1F5F9;")
        fl.addWidget(div)

        # Grid header
        grid = QGridLayout(); grid.setSpacing(0); grid.setContentsMargins(0,0,0,0)
        for ci, hdr in enumerate(["Dia", "Faixa / Horário",
                                   "Tipo" if is_mixed else "", "Valor", "Obs."]):
            if not hdr: continue
            lh = QLabel(hdr.upper())
            lh.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            lh.setStyleSheet(f"color:#94A3B8;padding:4px 8px;background:#F8FAFC;"
                              f"border-bottom:1px solid #E2E8F0;")
            grid.addWidget(lh, 0, ci)

        srt = sorted(lancamentos, key=lambda l: (l["dia"], l["faixa"]))
        for ri, l in enumerate(srt, 1):
            bg = "#FFFFFF" if ri % 2 == 0 else "#F8FAFC"
            def _cell(txt, bold=False, color=PRETO_TITULO):
                lb = QLabel(str(txt))
                lb.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold if bold else QFont.Weight.Normal))
                lb.setStyleSheet(f"color:{color};padding:5px 8px;background:{bg};border:none;")
                return lb
            grid.addWidget(_cell(l["dia"], bold=True), ri, 0)
            grid.addWidget(_cell(l["faixa"]), ri, 1)
            if is_mixed:
                tipo_txt  = "⏰ Horário" if l["tipo"] == "horario" else "☀️ Período"
                tipo_cor  = "#1D4ED8"    if l["tipo"] == "horario" else "#92400E"
                grid.addWidget(_cell(tipo_txt, color=tipo_cor), ri, 2)
            v_txt = str(int(l["valor"])) if l["valor"] == int(l["valor"]) else f"{l['valor']:g}"
            grid.addWidget(_cell(v_txt, bold=True), ri, 3)
            grid.addWidget(_cell(l["obs"] or "—", color=CINZA_SUAVE), ri, 4)

        fl.addLayout(grid)
        return frame

    def _clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self._clear_layout(item.layout())
