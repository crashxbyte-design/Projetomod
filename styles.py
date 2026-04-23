"""
styles.py - Paleta de cores e estilos institucionais Mackenzie / Segurança Patrimonial.
"""

# ─── Paleta Institucional ────────────────────────────────────────────────────
VERMELHO       = "#C8102E"   # Mackenzie vermelho principal
VERMELHO_ESC   = "#A00000"   # Tom mais escuro para cabeçalhos de tabela
VERMELHO_SOFT  = "#FFF0F2"   # Fundo suave
CINZA_BG       = "#F4F6F9"   # Fundo geral do app (cinza bem claro)
BRANCO         = "#FFFFFF"
CINZA_SIDEBAR  = "#FFFFFF"   # Sidebar branca na referência
CINZA_BORDA    = "#E0E0E0"
CINZA_TEXTO    = "#333333"
CINZA_SUAVE    = "#666666"
PRETO_TITULO   = "#000000"

VERDE          = "#2E7D32"   # Atingido (verde escuro)
VERDE_SOFT     = "#E8F5E9"
LARANJA        = "#E65100"   # Em atenção / Laranja
LARANJA_SOFT   = "#FFF3E0"
AZUL           = "#1565C0"   # Eficiência / Azul (gráfico)
CINZA_META     = "#9E9E9E"   # Sem meta
CINZA_META_BG  = "#F5F5F5"
PENDENTE_BG    = "#FFF3F3"
PENDENTE_FG    = "#D32F2F"   # Crítico / Vermelho

# ─── Status colors (Texto, Fundo, Borda) ─────────────────────────────────────
STATUS_COLORS = {
    "Atingido":           (VERDE, BRANCO, VERDE),
    "Em Atenção":         (LARANJA, BRANCO, LARANJA),
    "Acima da meta":      (PENDENTE_FG, BRANCO, PENDENTE_FG),
    "Pendente de processo": (PENDENTE_FG, BRANCO, PENDENTE_FG),
    "Pendente de controle": (LARANJA, BRANCO, LARANJA),
    "Meta a definir":     (CINZA_META, CINZA_META_BG, CINZA_BORDA),
    "A preencher":        (CINZA_META, CINZA_META_BG, CINZA_BORDA),
}

# ─── Global QSS ─────────────────────────────────────────────────────────────
GLOBAL_STYLE = f"""
* {{
    font-family: 'Segoe UI', 'Arial', sans-serif;
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
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: #C4C9D4;
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: #A0A8B8;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background: {CINZA_BG};
    height: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: #C4C9D4;
    border-radius: 4px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
QToolTip {{
    background: {CINZA_TEXTO};
    color: white;
    border: 1px solid {VERMELHO};
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 12px;
}}
"""
