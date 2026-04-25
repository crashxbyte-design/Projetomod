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
    ("◈", "Painel Executivo",          "painel"),
    ("≡", "Indicadores",               "indicadores"),
    ("∿", "Gráficos e Subindicadores", "subindicadores"),
    ("◬", "Pendências / Observações",  "pendencias"),
    ("▤", "Base de Dados",             "base_dados"),
    ("○", "Instruções",                "instrucoes"),
]


class SidebarButton(QPushButton):
    def __init__(self, icon_txt, label, key, parent=None):
        super().__init__(parent)
        self.key = key
        self._active = False
        self.setCheckable(True)
        self.setMinimumHeight(52)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        ly = QHBoxLayout(self)
        ly.setContentsMargins(18, 10, 14, 10)
        ly.setSpacing(14)

        self.ico_lbl = QLabel(icon_txt)
        self.ico_lbl.setFont(QFont("Segoe UI", 16))
        self.ico_lbl.setFixedWidth(24)
        self.ico_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ico_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        ly.addWidget(self.ico_lbl)

        self.txt_lbl = QLabel(label)
        self.txt_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.txt_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.txt_lbl.setWordWrap(True)
        ly.addWidget(self.txt_lbl, 1)

        self._update_style(False)

    def _update_style(self, active):
        self._active = active
        if active:
            bg  = "#C8102E"
            fg  = "#FFFFFF"
            hov = "#A00000"
        else:
            bg  = "transparent"
            fg  = "#1E293B"
            hov = "#F1F5F9"

        # Item ativo ocupa largura total (sem border-radius, sem margem) como na referência
        if active:
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
        else:
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
        transparent = "background: transparent; border: none;"
        ico_color = "#FFFFFF" if active else "#374151"
        txt_color = "#FFFFFF" if active else "#1E293B"
        self.ico_lbl.setStyleSheet(f"color: {ico_color}; {transparent}")
        self.txt_lbl.setStyleSheet(f"color: {txt_color}; {transparent}; font-weight: {'700' if active else '500'};")

    def setActive(self, v):
        self._update_style(v)
        self.setChecked(v)


class Sidebar(QFrame):
    """Sidebar vertical com navegação."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(230)
        self.setStyleSheet("background: #FFFFFF; border-right: 1px solid #E2E8F0;")

        self._buttons = []
        self._callbacks = []

        ly = QVBoxLayout(self)
        ly.setContentsMargins(0, 8, 0, 0)
        ly.setSpacing(2)

        for icon_txt, label, key in NAV_ITEMS:
            btn = SidebarButton(icon_txt, label, key)
            btn.clicked.connect(lambda checked, b=btn: self._on_click(b))
            self._buttons.append(btn)
            ly.addWidget(btn)

        ly.addStretch()

        self.btn_reload = QPushButton("Recarregar Dados")
        self.btn_reload.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.btn_reload.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reload.setStyleSheet("""
            QPushButton {
                background: #FFFFFF;
                color: #374151;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 9px;
                margin: 0px 16px;
                text-align: center;
            }
            QPushButton:hover {
                background: #F9FAFB;
                border-color: #9CA3AF;
            }
        """)
        ly.addWidget(self.btn_reload)

        ver = QLabel("v1.0 – Fase 1")
        ver.setFont(QFont("Segoe UI", 8))
        ver.setStyleSheet("color: #9CA3AF; background: transparent; border: none; padding: 10px 20px 16px 20px;")
        ver.setAlignment(Qt.AlignmentFlag.AlignLeft)
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
    """Círculo vermelho com 'M' + texto Mackenzie, fiel à referência."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(46, 46)

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QColor, QFont
        from PySide6.QtCore import Qt
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Fundo branco do círculo
        painter.setBrush(QColor("#FFFFFF"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, 46, 46)
        # Borda vermelha
        from PySide6.QtGui import QPen
        pen = QPen(QColor("#C8102E"))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(2, 2, 42, 42)
        # Letra M
        painter.setPen(QColor("#C8102E"))
        f = QFont("Arial", 20, QFont.Weight.Bold)
        painter.setFont(f)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "M")

class TopHeader(QFrame):
    """Cabeçalho superior."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(100)
        self.setStyleSheet("""
            QFrame {
                background: #FFFFFF;
                border-bottom: 1px solid #E2E8F0;
                border-top: none; border-left: none; border-right: none;
            }
        """)

        ly = QHBoxLayout(self)
        ly.setContentsMargins(0, 0, 28, 0)
        ly.setSpacing(0)

        # ── Bloco vermelho esquerdo (alinhado ao sidebar)
        logo_block = QFrame()
        logo_block.setFixedWidth(230)
        logo_block.setStyleSheet("background: #C8102E; border: none;")
        lb_ly = QHBoxLayout(logo_block)
        lb_ly.setContentsMargins(16, 0, 12, 0)
        lb_ly.setSpacing(12)

        logo = MackenzieLogo()
        lb_ly.addWidget(logo)

        mack_col = QVBoxLayout()
        mack_col.setSpacing(1)
        mack_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        uni_lbl = QLabel("Universidade Presbiteriana")
        uni_lbl.setFont(QFont("Segoe UI", 8))
        uni_lbl.setStyleSheet("color: #FECACA; background: transparent; border: none;")
        mack_lbl = QLabel("Mackenzie")
        mack_lbl.setFont(QFont("Segoe UI", 17, QFont.Weight.Bold))
        mack_lbl.setStyleSheet("color: #FFFFFF; background: transparent; border: none;")
        mack_col.addWidget(uni_lbl)
        mack_col.addWidget(mack_lbl)
        lb_ly.addLayout(mack_col)
        lb_ly.addStretch()

        ly.addWidget(logo_block)
        ly.addSpacing(28)

        # ── Título central
        self.title_col = QVBoxLayout()
        self.title_col.setSpacing(2)
        self.title_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.page_title = QLabel("BOOK DE INDICADORES")
        self.page_title.setFont(QFont("Segoe UI", 24, QFont.Weight.Black))
        self.page_title.setStyleSheet("color: #0F172A; background: transparent; border: none;")
        self.page_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_col.addWidget(self.page_title)
        self.page_sub = QLabel("PAINEL EXECUTIVO")
        self.page_sub.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.page_sub.setStyleSheet("color: #C8102E; background: transparent; border: none; letter-spacing: 1.5px;")
        self.page_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_col.addWidget(self.page_sub)
        ly.addLayout(self.title_col, 1)

        # ── Metadados direita
        meta_frame = QFrame()
        meta_frame.setStyleSheet("""
            QFrame { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; }
        """)
        meta_ly = QVBoxLayout(meta_frame)
        meta_ly.setContentsMargins(16, 10, 16, 10)
        meta_ly.setSpacing(6)
        for label, value in [
            ("Data de Atualização:",  "05/11/2026"),
            ("Período Selecionado:",  "Jan a Fev/2026"),
            ("Responsável:",           "Segurança Patrimonial"),
        ]:
            row = QHBoxLayout()
            row.setSpacing(8)
            lbl = QLabel(label)
            lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            lbl.setStyleSheet("color: #1E293B; background: transparent; border: none;")
            val = QLabel(value)
            val.setFont(QFont("Segoe UI", 9))
            val.setStyleSheet("color: #64748B; background: transparent; border: none;")
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
