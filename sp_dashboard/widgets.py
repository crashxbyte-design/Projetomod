"""
widgets.py - Widgets reutilizáveis: cards, badges, tabela de indicadores.
"""

from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame,
    QGraphicsDropShadowEffect, QSizePolicy, QScrollArea
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPainterPath

from styles import (
    VERMELHO, VERMELHO_ESC, VERMELHO_SOFT, BRANCO, CINZA_BG, CINZA_BORDA,
    CINZA_TEXTO, CINZA_SUAVE, PRETO_TITULO, VERDE, VERDE_SOFT,
    LARANJA, LARANJA_SOFT, CINZA_META, CINZA_META_BG,
    PENDENTE_FG, PENDENTE_BG, AZUL, STATUS_COLORS
)


def shadow(radius=12, offset=(0, 2), color=(0, 0, 0, 30)):
    eff = QGraphicsDropShadowEffect()
    eff.setBlurRadius(radius)
    eff.setOffset(*offset)
    eff.setColor(QColor(*color))
    return eff


class SectionTitle(QLabel):
    """Título de seção com barra vermelha à esquerda."""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        font = QFont("Segoe UI", 13)
        font.setWeight(QFont.Weight.Bold)
        font.setPixelSize(14)
        self.setFont(font)
        self.setStyleSheet(f"""
            QLabel {{
                color: {PRETO_TITULO};
                border-left: 4px solid {VERMELHO};
                padding-left: 12px;
                letter-spacing: 0.5px;
                background: transparent;
            }}
        """)


class KPICard(QFrame):
    """Card KPI executivo premium com ícone circular."""
    def __init__(self, label, value, subtitle="", color=None, icon=None, parent=None):
        super().__init__(parent)
        color = color or PRETO_TITULO
        self.setMinimumHeight(110)
        self.setMinimumWidth(150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        self.setStyleSheet(f"""
            QFrame {{
                background: {BRANCO};
                border: 1px solid {CINZA_BORDA};
                border-radius: 12px;
            }}
        """)
        self.setGraphicsEffect(shadow(12, (0, 3), (0, 0, 0, 8)))

        ly = QVBoxLayout(self)
        ly.setContentsMargins(0, 0, 0, 0)
        ly.setSpacing(0)

        # Icon Container (Right Side) / Values (Left)
        content = QWidget()
        content.setStyleSheet("background:transparent; border:none;")
        hl = QHBoxLayout(content)
        hl.setContentsMargins(4, 4, 4, 4)
        hl.setSpacing(12)

        # Texts
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        text_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl = QLabel(label.upper())
        lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: #64748B; background: transparent; border: none; letter-spacing: 0.8px;")
        lbl.setWordWrap(True)
        text_col.addWidget(lbl)

        val_lbl = QLabel(str(value))
        val_lbl.setFont(QFont("Segoe UI", 34, QFont.Weight.Bold))
        val_lbl.setStyleSheet(f"color: {color}; background: transparent; border: none;")
        text_col.addWidget(val_lbl)

        if subtitle:
            sub = QLabel(subtitle)
            sub.setFont(QFont("Segoe UI", 8))
            sub.setStyleSheet(f"color: #94A3B8; background: transparent; border: none;")
            sub.setWordWrap(True)
            text_col.addWidget(sub)

        hl.addLayout(text_col, 1)
        
        # Bottom accent
        ly.addWidget(content, 1)
        
        accent = QFrame()
        accent.setFixedHeight(3)
        accent.setStyleSheet(f"background: {color}; border: none; border-radius: 0px; "
                              f"border-bottom-left-radius: 12px; border-bottom-right-radius: 12px;")
        ly.addWidget(accent)


class StatusBadge(QLabel):
    """Badge de status com tipografia premium e borda suave."""
    def __init__(self, status, parent=None):
        super().__init__(status, parent)
        fg, bg, border = STATUS_COLORS.get(status, (CINZA_META, CINZA_META_BG, CINZA_BORDA))
        self.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(26)
        self.setContentsMargins(12, 0, 12, 0)
        self.setStyleSheet(f"""
            QLabel {{
                background: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 0px 12px;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }}
        """)


class Sparkline(QWidget):
    """Componente simples simulando um gráfico de barras (Tendência)."""
    def __init__(self, values, color, parent=None):
        super().__init__(parent)
        self.values = values
        self.color = color
        self.setFixedHeight(30)
        self.setFixedWidth(100)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.values:
            return
        w = self.width()
        h = self.height()
        bar_w = max(2, (w / len(self.values)) - 2)
        max_v = max(self.values) if max(self.values) > 0 else 1
        
        painter.setBrush(QColor(self.color))
        painter.setPen(Qt.PenStyle.NoPen)
        for i, v in enumerate(self.values):
            bar_h = (v / max_v) * h
            x = i * (bar_w + 2)
            y = h - bar_h
            painter.drawRect(int(x), int(y), int(bar_w), int(bar_h))


class IndicadorRow(QFrame):
    """Linha de indicador na tabela (9 colunas exatas)."""
    def __init__(self, ind_data, ano_selecionado=2026, parent=None):
        super().__init__(parent)
        self.ind_data = ind_data
        self.ano_selecionado = ano_selecionado
        self.setStyleSheet(f"""
            QFrame {{
                background: {BRANCO};
                border-bottom: 1px solid {CINZA_BORDA};
                border-radius: 0px;
            }}
            QFrame:hover {{
                background: #F9F9F9;
            }}
        """)
        self.setFixedHeight(60)

        ly = QHBoxLayout(self)
        ly.setContentsMargins(16, 0, 16, 0)
        ly.setSpacing(12)

        # 1. Código
        cod = QLabel(ind_data["codigo"])
        cod.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        cod.setStyleSheet(f"color: {PRETO_TITULO}; background: transparent; border: none;")
        cod.setFixedWidth(70)
        ly.addWidget(cod)

        # 2. Indicador
        tit = QLabel(ind_data["titulo"])
        tit.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        tit.setStyleSheet(f"color: {PRETO_TITULO}; background: transparent; border: none;")
        tit.setWordWrap(True)
        ly.addWidget(tit, 2)

        # 3. Tipo
        tipo = QLabel(ind_data["tipo"])
        tipo.setFont(QFont("Segoe UI", 9))
        tipo.setStyleSheet(f"color: {CINZA_SUAVE}; background: transparent; border: none;")
        tipo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tipo.setFixedWidth(90)
        ly.addWidget(tipo)

        # 4. Periodicidade
        per = QLabel(ind_data["periodicidade"])
        per.setFont(QFont("Segoe UI", 9))
        per.setStyleSheet(f"color: {CINZA_SUAVE}; background: transparent; border: none;")
        per.setAlignment(Qt.AlignmentFlag.AlignCenter)
        per.setFixedWidth(90)
        ly.addWidget(per)

        # 5. Meta
        meta_txt = ind_data["meta"]
        meta_val = QLabel(meta_txt)
        meta_val.setFont(QFont("Segoe UI", 9))
        meta_val.setStyleSheet(f"color: {PRETO_TITULO}; background: transparent; border: none;")
        meta_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        meta_val.setFixedWidth(90)
        ly.addWidget(meta_val)

        # 6. Resultado Atual
        # Pega o último resultado válido do ano selecionado
        hist_ano = ind_data.get("historicos", {}).get(ano_selecionado, {})
        res_text = "–"
        rc = CINZA_META
        
        # Encontra o último mês com dado para o ano selecionado
        from data_loader import MESES
        ultimo_valor = None
        for mes in reversed(MESES):
            if hist_ano.get(mes) is not None:
                ultimo_valor = hist_ano[mes]
                break
                
        if ultimo_valor is not None:
            res_text = str(ultimo_valor)
            if "95" in meta_txt and float(str(res_text).replace(",", ".")) >= 95:
                rc = VERDE
            else:
                rc = LARANJA
                
        res_lbl = QLabel(res_text)
        res_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        res_lbl.setStyleSheet(f"color: {rc}; background: transparent; border: none;")
        res_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        res_lbl.setFixedWidth(110)
        ly.addWidget(res_lbl)

        # 7. Tendência (Sparkline Real)
        tend_container = QWidget()
        tend_container.setFixedWidth(120)
        tend_ly = QVBoxLayout(tend_container)
        tend_ly.setContentsMargins(10, 10, 10, 10)
        
        # Pegar valores reais do histórico para o gráfico
        real_vals = []
        for mes in MESES:
            val = hist_ano.get(mes)
            if val is not None:
                try:
                    real_vals.append(float(str(val).replace(",", ".")))
                except:
                    pass
                    
        # Se não tiver dados suficientes, cria uma linha reta 0 ou omite
        if len(real_vals) < 2:
            real_vals = [0, 0]
            
        spark = Sparkline(real_vals, VERDE if rc == VERDE else LARANJA)
        tend_ly.addWidget(spark)
        ly.addWidget(tend_container)

        # 8. Status badge (extended width to fill removed column)
        badge_container = QWidget()
        badge_container.setFixedWidth(135)
        badge_ly = QVBoxLayout(badge_container)
        badge_ly.setContentsMargins(0, 0, 0, 0)
        badge_ly.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        badge = StatusBadge(ind_data["status"])
        badge.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        badge_ly.addWidget(badge)
        ly.addWidget(badge_container)
        ly.addSpacing(15)


class PendenciaCard(QFrame):
    """Card de pendência crítica."""
    def __init__(self, pendencia, parent=None):
        super().__init__(parent)
        nivel = pendencia["nivel"]
        if nivel == "CRÍTICO":
            accent, bg = PENDENTE_FG, PENDENTE_BG
        else:
            accent, bg = LARANJA, LARANJA_SOFT

        self.setStyleSheet(f"""
            QFrame {{
                background: {bg};
                border: 1px solid {accent}55;
                border-left: 5px solid {accent};
                border-radius: 10px;
            }}
        """)
        self.setGraphicsEffect(shadow(10, (0, 2), (0, 0, 0, 15)))

        ly = QVBoxLayout(self)
        ly.setContentsMargins(16, 14, 16, 14)
        ly.setSpacing(6)

        # Header row
        header = QHBoxLayout()
        cod = QLabel(pendencia["codigo"])
        cod.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        cod.setStyleSheet(f"color: {accent}; background: transparent; border: none;")
        header.addWidget(cod)
        header.addStretch()
        badge = QLabel(nivel)
        badge.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        badge.setStyleSheet(f"""
            color: {BRANCO};
            background: {accent};
            border-radius: 4px;
            padding: 2px 8px;
            border: none;
        """)
        header.addWidget(badge)
        ly.addLayout(header)

        tit = QLabel(pendencia["titulo"])
        tit.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        tit.setStyleSheet(f"color: {PRETO_TITULO}; background: transparent; border: none;")
        tit.setWordWrap(True)
        ly.addWidget(tit)

        desc = QLabel(pendencia["descricao"])
        desc.setFont(QFont("Segoe UI", 9))
        desc.setStyleSheet(f"color: {CINZA_TEXTO}; background: transparent; border: none;")
        desc.setWordWrap(True)
        ly.addWidget(desc)


class SubindicadorCard(QFrame):
    """Card compacto para subindicadores (Jan + Fev/2026)."""
    def __init__(self, titulo, jan_val, fev_val, meta_txt, unidade="", parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background: {BRANCO};
                border: 1px solid {CINZA_BORDA};
                border-radius: 10px;
            }}
        """)
        self.setGraphicsEffect(shadow(12, (0, 2), (0, 0, 0, 18)))

        ly = QVBoxLayout(self)
        ly.setContentsMargins(16, 14, 16, 14)
        ly.setSpacing(6)

        tit = QLabel(titulo)
        tit.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        tit.setStyleSheet(f"color: {PRETO_TITULO}; background: transparent; border: none;")
        tit.setWordWrap(True)
        ly.addWidget(tit)

        meta_lbl = QLabel(f"Meta: {meta_txt}")
        meta_lbl.setFont(QFont("Segoe UI", 9))
        meta_lbl.setStyleSheet(f"color: {CINZA_SUAVE}; background: transparent; border: none;")
        ly.addWidget(meta_lbl)

        ly.addSpacing(4)

        # Valores
        row = QHBoxLayout()
        for mes, val in [("Janeiro", jan_val), ("Fevereiro", fev_val)]:
            col = QVBoxLayout()
            col.setSpacing(2)
            m = QLabel(mes[:3].upper())
            m.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            m.setStyleSheet(f"color: {CINZA_SUAVE}; letter-spacing: 1px; background: transparent; border: none;")
            v_txt = str(val) + (f" {unidade}" if unidade and val is not None else "") if val is not None else "–"
            v = QLabel(v_txt)
            v.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
            v.setStyleSheet(f"color: {VERMELHO}; background: transparent; border: none;")
            col.addWidget(m)
            col.addWidget(v)
            row.addLayout(col)
            if mes == "Janeiro":
                row.addSpacing(20)
        ly.addLayout(row)
