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
    ("📊", "Painel Executivo",          "painel"),
    ("📌", "Indicadores",                "indicadores"),
    ("📈", "Gráficos e Subindicadores",  "subindicadores"),
    ("⚠️",  "Pendências / Observações", "pendencias"),
    ("🗄️", "Base de Dados",             "base_dados"),
    ("📖", "Instruções",                "instrucoes"),
]


class SidebarButton(QPushButton):
    def __init__(self, icon_txt, label, key, parent=None):
        super().__init__(parent)
        self.key = key
        self._active = False
        self.setCheckable(True)
        self.setFixedHeight(52)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        ly = QHBoxLayout(self)
        ly.setContentsMargins(16, 0, 12, 0)
        ly.setSpacing(14)

        self.ico_lbl = QLabel(icon_txt)
        self.ico_lbl.setFont(QFont("Segoe UI Emoji", 13))
        self.ico_lbl.setFixedWidth(22)
        self.ico_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ico_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        ly.addWidget(self.ico_lbl)

        self.txt_lbl = QLabel(label)
        self.txt_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        self.txt_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.txt_lbl.setWordWrap(False)
        ly.addWidget(self.txt_lbl, 1)

        self._update_style(False)

    def _update_style(self, active):
        self._active = active
        if active:
            bg  = "#B91C1C"
            fg  = "#FFFFFF"
            hov = "#991B1B"
        else:
            bg  = "transparent"
            fg  = "#475569"
            hov = "#F1F5F9"

        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                border: none;
                border-radius: 8px;
                margin: 2px 10px;
                padding: 0px;
            }}
            QPushButton:hover {{ background: {hov}; }}
        """)
        transparent = "background: transparent; border: none;"
        self.ico_lbl.setStyleSheet(f"color: {fg}; {transparent}")
        self.txt_lbl.setStyleSheet(f"color: {fg}; {transparent}; font-weight: {'700' if active else '500'};")

    def setActive(self, v):
        self._update_style(v)
        self.setChecked(v)


class Sidebar(QFrame):
    """Sidebar vertical com navegação — fiel ao print de referência."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(260)
        self.setStyleSheet(f"background: #FFFFFF; border-right: 1px solid #E2E8F0;")

        self._buttons = []
        self._callbacks = []

        ly = QVBoxLayout(self)
        ly.setContentsMargins(0, 16, 0, 0)
        ly.setSpacing(4)

        # ── Botões de navegação ────────────────────────────────────────────
        for icon_txt, label, key in NAV_ITEMS:
            btn = SidebarButton(icon_txt, label, key)
            btn.clicked.connect(lambda checked, b=btn: self._on_click(b))
            self._buttons.append(btn)
            ly.addWidget(btn)

        ly.addStretch()

        # ── Botão Recarregar ───────────────────────────────────────────────
        self.btn_reload = QPushButton("🔄  Recarregar Dados")
        self.btn_reload.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.btn_reload.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reload.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                color: #475569;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 10px;
                margin: 0px 16px;
                text-align: center;
            }
            QPushButton:hover {
                background: #F8FAFC;
                border-color: #94A3B8;
                color: #0F172A;
            }
        """)
        ly.addWidget(self.btn_reload)

        # ── Versão ────────────────────────────────────────────────────────
        ver = QLabel("v1.0 – Fase 1")
        ver.setFont(QFont("Segoe UI", 8))
        ver.setStyleSheet("color: #94A3B8; background: transparent; border: none; padding: 16px 16px 20px 16px;")
        ver.setAlignment(Qt.AlignmentFlag.AlignRight)
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


class MackenzieLogo(QLabel):
    """Componente visual que carrega a logo a partir do arquivo logo.png."""
    def __init__(self, parent=None):
        super().__init__(parent)
        import os
        from PySide6.QtGui import QPixmap
        from PySide6.QtCore import Qt
        
        logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logo.png'))
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            # Escala a imagem para caber bem no bloco esquerdo (max 240x80)
            pixmap = pixmap.scaled(240, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.setPixmap(pixmap)
            self.setFixedSize(pixmap.size())
        else:
            # Fallback se a imagem não existir
            self.setFixedSize(54, 54)
            self.setText("M")
            self.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setStyleSheet("color: #B91C1C; font-size: 26px; font-weight: bold; background: white; border-radius: 27px;")

class TopHeader(QFrame):
    """Cabeçalho superior com título da tela e bloco de logo do Mackenzie alinhado ao sidebar."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(100)
        self.setStyleSheet(f"""
            QFrame {{
                background: #FFFFFF;
                border-bottom: 1px solid #E2E8F0;
                border-top: none;
                border-left: none;
                border-right: none;
            }}
        """)

        ly = QHBoxLayout(self)
        ly.setContentsMargins(0, 0, 32, 0)
        ly.setSpacing(0)
        
        # Bloco Vermelho com Logo, largura igual ao sidebar
        logo_block = QFrame()
        logo_block.setFixedWidth(260)
        logo_block.setStyleSheet("background: #B91C1C; border: none; border-bottom: 1px solid #991B1B;")
        lb_ly = QHBoxLayout(logo_block)
        lb_ly.setContentsMargins(10, 10, 10, 10)
        
        logo = MackenzieLogo()
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lb_ly.addWidget(logo)
        
        ly.addWidget(logo_block)
        
        # Espaçamento após o bloco vermelho
        ly.addSpacing(32)

        # Título principal centralizado na área restante
        self.title_col = QVBoxLayout()
        self.title_col.setSpacing(2)
        self.title_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.page_title = QLabel("BOOK DE INDICADORES")
        self.page_title.setFont(QFont("Segoe UI", 24, QFont.Weight.Black))
        self.page_title.setStyleSheet("color: #0F172A; background: transparent; border: none; letter-spacing: 1px;")
        self.page_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_col.addWidget(self.page_title)

        self.page_sub = QLabel("PAINEL EXECUTIVO")
        self.page_sub.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.page_sub.setStyleSheet("color: #B91C1C; background: transparent; border: none; letter-spacing: 1.5px;")
        self.page_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_col.addWidget(self.page_sub)

        ly.addLayout(self.title_col, 1)

        # Metadados à direita
        meta_frame = QFrame()
        meta_frame.setStyleSheet("""
            QFrame {
                background: #F8FAFC; 
                border: 1px solid #E2E8F0; 
                border-radius: 8px;
            }
        """)
        meta_ly = QVBoxLayout(meta_frame)
        meta_ly.setContentsMargins(16, 12, 16, 12)
        meta_ly.setSpacing(6)
        
        for icon, label, value in [
            ("📅", "Data de Atualização:", "05/11/2026"),
            ("📅", "Período Selecionado:", "Jan a Fev/2026"),
            ("👤", "Responsável:", "Segurança Patrimonial"),
        ]:
            row = QHBoxLayout()
            row.setSpacing(10)
            ico = QLabel(icon)
            ico.setFont(QFont("Segoe UI Emoji", 10))
            ico.setStyleSheet("background:transparent; border:none;")
            lbl = QLabel(label)
            lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            lbl.setStyleSheet("color: #1E293B; background: transparent; border: none;")
            val = QLabel(value)
            val.setFont(QFont("Segoe UI", 9))
            val.setStyleSheet("color: #64748B; background: transparent; border: none;")
            row.addWidget(ico)
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
