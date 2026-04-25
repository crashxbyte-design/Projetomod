"""
styles.py - Paleta de cores e estilos institucionais Mackenzie / Segurança Patrimonial.
Design System v2 – Slate Premium.
"""

# ─── Paleta Institucional ────────────────────────────────────────────────────
VERMELHO       = "#B91C1C"   # Crimson principal
VERMELHO_ESC   = "#991B1B"   # Tom escuro para destaques
VERMELHO_SOFT  = "#FEF2F2"   # Fundo suave vermelho

CINZA_BG       = "#F1F5F9"   # Fundo geral – Slate 100
BRANCO         = "#FFFFFF"
CINZA_SIDEBAR  = "#FFFFFF"
CINZA_BORDA    = "#E2E8F0"   # Slate 200
CINZA_TEXTO    = "#334155"   # Slate 700
CINZA_SUAVE    = "#64748B"   # Slate 500
PRETO_TITULO   = "#0F172A"   # Slate 900

VERDE          = "#059669"   # Emerald 600 – Atingido
VERDE_SOFT     = "#D1FAE5"   # Emerald 100
LARANJA        = "#D97706"   # Amber 600 – Em atenção
LARANJA_SOFT   = "#FEF3C7"   # Amber 100
AZUL           = "#2563EB"   # Blue 600
CINZA_META     = "#94A3B8"   # Slate 400
CINZA_META_BG  = "#F8FAFC"   # Slate 50
PENDENTE_BG    = "#FFF1F2"   # Rose 50
PENDENTE_FG    = "#E11D48"   # Rose 600 – Crítico

# ─── Status colors (Texto, Fundo, Borda) ─────────────────────────────────────
STATUS_COLORS = {
    "Atingido":              (VERDE,       VERDE_SOFT,   VERDE),
    "Em Atenção":            (LARANJA,     LARANJA_SOFT, LARANJA),
    "Acima da meta":         (PENDENTE_FG, PENDENTE_BG,  PENDENTE_FG),
    "Pendente de processo":  (PENDENTE_FG, PENDENTE_BG,  PENDENTE_FG),
    "Pendente de controle":  (LARANJA,     LARANJA_SOFT, LARANJA),
    "Meta a definir":        (CINZA_META,  CINZA_META_BG, CINZA_BORDA),
    "A preencher":           (CINZA_META,  CINZA_META_BG, CINZA_BORDA),
    "Dentro da meta":        (VERDE,       VERDE_SOFT,   VERDE),
    "Abaixo da meta":        (PENDENTE_FG, PENDENTE_BG,  PENDENTE_FG),
}

# ─── Global QSS ─────────────────────────────────────────────────────────────
GLOBAL_STYLE = f"""
* {{
    font-family: 'Segoe UI', 'Arial', sans-serif;
    font-size: 10px;
    outline: none;
    margin: 0;
    padding: 0;
}}
QMainWindow, QDialog {{
    background: {CINZA_BG};
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollBar:vertical {{
    background: {CINZA_BG};
    width: 6px;
    border-radius: 3px;
    margin: 2px 0;
}}
QScrollBar::handle:vertical {{
    background: {CINZA_BORDA};
    border-radius: 3px;
    min-height: 28px;
}}
QScrollBar::handle:vertical:hover {{
    background: {CINZA_META};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background: {CINZA_BG};
    height: 6px;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal {{
    background: {CINZA_BORDA};
    border-radius: 3px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
QToolTip {{
    background: {PRETO_TITULO};
    color: {BRANCO};
    border: 1px solid {VERMELHO};
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 500;
}}
QLabel {{
    color: {CINZA_TEXTO};
    background: transparent;
}}
QPushButton {{
    font-weight: 600;
    border-radius: 6px;
    padding: 6px 14px;
}}
QPushButton:focus {{
    outline: none;
}}
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {BRANCO};
    border: 1.5px solid {CINZA_BORDA};
    border-radius: 6px;
    padding: 6px 10px;
    color: {PRETO_TITULO};
    font-size: 10px;
    selection-background-color: {VERMELHO_SOFT};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border-color: {VERMELHO};
    background: {BRANCO};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background: {BRANCO};
    border: 1px solid {CINZA_BORDA};
    selection-background-color: {VERMELHO_SOFT};
    selection-color: {PRETO_TITULO};
    outline: none;
}}
QTabWidget::pane {{
    border: 1px solid {CINZA_BORDA};
    border-radius: 0px;
    background: {BRANCO};
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {CINZA_SUAVE};
    padding: 10px 20px;
    font-size: 10px;
    font-weight: 600;
    border: none;
    border-bottom: 3px solid transparent;
    margin-right: 2px;
    letter-spacing: 0.3px;
}}
QTabBar::tab:selected {{
    color: {VERMELHO};
    border-bottom: 3px solid {VERMELHO};
    background: transparent;
}}
QTabBar::tab:hover:!selected {{
    color: {PRETO_TITULO};
    background: {CINZA_BG};
}}
QHeaderView::section {{
    background: {CINZA_META_BG};
    color: {CINZA_SUAVE};
    font-size: 8px;
    font-weight: 700;
    letter-spacing: 0.8px;
    padding: 8px 12px;
    border: none;
    border-bottom: 1px solid {CINZA_BORDA};
    border-right: 1px solid {CINZA_BORDA};
    text-transform: uppercase;
}}
QTableWidget {{
    background: {BRANCO};
    border: none;
    gridline-color: {CINZA_BORDA};
    font-size: 10px;
    color: {CINZA_TEXTO};
    selection-background-color: {VERMELHO_SOFT};
    selection-color: {PRETO_TITULO};
    outline: none;
}}
QTableWidget::item {{
    padding: 6px 12px;
    border-bottom: 1px solid {CINZA_BG};
}}
QTableWidget::item:selected {{
    background: {VERMELHO_SOFT};
    color: {PRETO_TITULO};
}}
"""
