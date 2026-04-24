"""
main_window.py - Janela principal com sidebar de navegação.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget,
    QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QColor, QIcon, QPainter, QLinearGradient, QPixmap

from styles import (
    VERMELHO, VERMELHO_ESC, BRANCO, CINZA_BG,
    CINZA_BORDA, CINZA_SUAVE, PRETO_TITULO, GLOBAL_STYLE
)


NAV_ITEMS = [
    ("🏠", "Painel\nExecutivo",        "painel"),
    ("📊", "Indicadores",               "indicadores"),
    ("📈", "Gráficos e\nSubindicadores","subindicadores"),
    ("📋", "Pendências /\nObservações", "pendencias"),
    ("📅", "Histórico\nMensal",         "historico"),
    ("📝", "Análise\nCrítica",          "analise"),
    ("🗄️", "Base de Dados",             "base_dados"),
    ("⚙️", "Configurações",             "config"),
    ("ℹ️", "Instruções",               "instrucoes"),
]


class SidebarButton(QPushButton):
    def __init__(self, icon_txt, label, key, parent=None):
        super().__init__(parent)
        self.key = key
        self._active = False
        self.setCheckable(True)
        self.setFixedHeight(58)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        ly = QHBoxLayout(self)
        ly.setContentsMargins(14, 0, 10, 0)
        ly.setSpacing(10)

        self.ico_lbl = QLabel(icon_txt)
        self.ico_lbl.setFont(QFont("Segoe UI Emoji", 15))
        self.ico_lbl.setFixedWidth(24)
        self.ico_lbl.setFixedHeight(24)
        self.ico_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ico_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        ly.addWidget(self.ico_lbl)

        self.txt_lbl = QLabel(label)
        self.txt_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.txt_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.txt_lbl.setWordWrap(True)
        ly.addWidget(self.txt_lbl, 1)

        self._update_style(False)

    def _update_style(self, active):
        self._active = active
        bg  = VERMELHO_ESC if active else "transparent"
        fg  = BRANCO       if active else "#333333"
        hov = "#6B0000"    if active else "#F0F0F0"

        # Sem border-radius — barra selecionada ocupa largura total como no print
        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                border: none;
                border-radius: 0px;
                margin: 0px;
                padding: 0px;
            }}
            QPushButton:hover {{ background: {hov}; }}
        """)
        # Fundo completamente transparente nas labels para não criar caixas brancas
        transparent = "background: transparent; border: none;"
        self.ico_lbl.setStyleSheet(f"color: {fg}; {transparent}")
        self.txt_lbl.setStyleSheet(f"color: {fg}; {transparent}")

    def setActive(self, v):
        self._update_style(v)
        self.setChecked(v)


class Sidebar(QFrame):
    """Sidebar vertical com navegação — fiel ao print de referência."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(190)
        self.setStyleSheet(f"background: {BRANCO}; border-right: 1px solid {CINZA_BORDA};")

        self._buttons = []
        self._callbacks = []

        ly = QVBoxLayout(self)
        ly.setContentsMargins(0, 8, 0, 0)
        ly.setSpacing(0)

        # ── Botões de navegação ────────────────────────────────────────────
        for icon_txt, label, key in NAV_ITEMS:
            btn = SidebarButton(icon_txt, label, key)
            btn.clicked.connect(lambda checked, b=btn: self._on_click(b))
            self._buttons.append(btn)
            ly.addWidget(btn)

        ly.addStretch()

        # ── Botão Recarregar ───────────────────────────────────────────────
        self.btn_reload = QPushButton("🔄 Recarregar Dados")
        self.btn_reload.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.btn_reload.setStyleSheet("""
            QPushButton {
                background: #F5F5F5;
                color: #333333;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                padding: 8px;
                margin: 0px 16px;
                text-align: left;
            }
            QPushButton:hover {
                background: #E0E0E0;
            }
        """)
        ly.addWidget(self.btn_reload)

        # ── Versão ────────────────────────────────────────────────────────
        ver = QLabel("v1.0 – Fase 1")
        ver.setFont(QFont("Segoe UI", 8))
        ver.setStyleSheet("color: #999999; background: transparent; border: none; padding: 10px 16px;")
        ver.setWordWrap(True)
        ly.addWidget(ver)

    def _on_click(self, clicked_btn):
        for btn in self._buttons:
            btn.setActive(btn is clicked_btn)
        for cb in self._callbacks:
            cb(clicked_btn.key)

    def set_active(self, key):
        for btn in self._buttons:
            btn.setActive(btn.key == key)

    def on_navigate(self, callback):
        self._callbacks.append(callback)


class MackenzieLogo(QWidget):
    """Componente visual imitando a logo do Mackenzie (círculo vermelho com 'M')."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 50)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Círculo vermelho
        painter.setBrush(QColor(VERMELHO))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, 50, 50)
        
        # Borda interna (círculo branco)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QColor(BRANCO))
        painter.drawEllipse(3, 3, 44, 44)
        
        # Letra M
        painter.setPen(QColor(BRANCO))
        font = QFont("Arial", 22, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "M")

class TopHeader(QFrame):
    """Cabeçalho superior com título da tela e logo Mackenzie."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)
        self.setStyleSheet(f"""
            QFrame {{
                background: {BRANCO};
                border-bottom: 2px solid {VERMELHO_ESC};
                border-top: none;
                border-left: none;
                border-right: none;
            }}
        """)

        ly = QHBoxLayout(self)
        ly.setContentsMargins(28, 0, 28, 0)
        ly.setSpacing(20)
        
        # Logo
        logo = MackenzieLogo()
        ly.addWidget(logo)
        
        # Textos Mackenzie
        mack_col = QVBoxLayout()
        mack_col.setSpacing(0)
        mack_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        uni_lbl = QLabel("Universidade Presbiteriana")
        uni_lbl.setFont(QFont("Segoe UI", 9))
        uni_lbl.setStyleSheet(f"color: {PRETO_TITULO}; background: transparent; border: none;")
        mack_lbl = QLabel("Mackenzie")
        mack_lbl.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        mack_lbl.setStyleSheet(f"color: {VERMELHO}; background: transparent; border: none;")
        mack_col.addWidget(uni_lbl)
        mack_col.addWidget(mack_lbl)
        ly.addLayout(mack_col)
        
        ly.addStretch()

        # Título principal centralizado
        self.title_col = QVBoxLayout()
        self.title_col.setSpacing(0)
        self.title_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.page_title = QLabel("BOOK DE INDICADORES")
        self.page_title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self.page_title.setStyleSheet(f"color: {PRETO_TITULO}; background: transparent; border: none;")
        self.page_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_col.addWidget(self.page_title)

        self.page_sub = QLabel("SEGURANÇA PATRIMONIAL")
        self.page_sub.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.page_sub.setStyleSheet(f"color: {VERMELHO}; background: transparent; border: none;")
        self.page_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_col.addWidget(self.page_sub)

        ly.addLayout(self.title_col)
        ly.addStretch()

        # Metadados à direita com fonte menor e bordas na Grid
        meta_frame = QFrame()
        meta_frame.setStyleSheet(f"border: 1px solid {CINZA_BORDA}; border-radius: 4px; background: transparent;")
        meta_ly = QVBoxLayout(meta_frame)
        meta_ly.setContentsMargins(8, 6, 8, 6)
        meta_ly.setSpacing(4)
        
        for label, value in [
            ("Data de Atualização:", "05/11/2026"),
            ("Período Selecionado:", "Jan a Fev/2026"),
            ("Responsável:", "Segurança Patrimonial"),
        ]:
            row = QHBoxLayout()
            row.setSpacing(10)
            lbl = QLabel(label)
            lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            lbl.setStyleSheet(f"color: {PRETO_TITULO}; background: transparent; border: none;")
            val = QLabel(value)
            val.setFont(QFont("Segoe UI", 8))
            val.setStyleSheet(f"color: {CINZA_SUAVE}; background: transparent; border: none;")
            row.addWidget(lbl)
            row.addWidget(val)
            row.addStretch()
            meta_ly.addLayout(row)
        ly.addWidget(meta_frame)

    def set_page(self, title, subtitle="SEGURANÇA PATRIMONIAL"):
        self.page_title.setText(title)
        self.page_sub.setText(subtitle)


class PlaceholderPanel(QWidget):
    """Painel placeholder para telas ainda não implementadas."""
    def __init__(self, titulo, msg, parent=None):
        super().__init__(parent)
        ly = QVBoxLayout(self)
        ly.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("🚧")
        icon.setFont(QFont("Segoe UI Emoji", 52))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("border: none; background: transparent;")
        ly.addWidget(icon)

        t = QLabel(titulo)
        t.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        t.setStyleSheet(f"color: {PRETO_TITULO}; background: transparent; border: none;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ly.addWidget(t)

        m = QLabel(msg)
        m.setFont(QFont("Segoe UI", 11))
        m.setStyleSheet(f"color: {CINZA_SUAVE}; background: transparent; border: none;")
        m.setAlignment(Qt.AlignmentFlag.AlignCenter)
        m.setWordWrap(True)
        ly.addWidget(m)
