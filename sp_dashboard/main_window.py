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
    CINZA_BORDA, CINZA_SUAVE, PRETO_TITULO, GLOBAL_STYLE, LOGO_PATH
)


NAV_ITEMS = [
    ("fa5s.tachometer-alt",  "Painel Executivo",         "painel"),
    ("fa5s.chart-bar",       "Indicadores",               "indicadores"),
    ("fa5s.chart-line",      "Gráficos e Subindicadores", "subindicadores"),
    ("fa5s.clipboard-list",  "Pendências / Observações", "pendencias"),
    ("fa5s.database",        "Base de Dados",             "base_dados"),
    ("fa5s.book",            "Instruções",               "instrucoes"),
]


class SidebarButton(QPushButton):
    def __init__(self, icon_name, label, key, parent=None):
        super().__init__(parent)
        self.key = key
        self._icon_name = icon_name
        self._active = False
        self.setCheckable(True)
        self.setFixedHeight(54)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        ly = QHBoxLayout(self)
        ly.setContentsMargins(18, 0, 10, 0)
        ly.setSpacing(14)

        self.ico_lbl = QLabel()
        self.ico_lbl.setFixedWidth(22)
        self.ico_lbl.setFixedHeight(22)
        self.ico_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ico_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        ly.addWidget(self.ico_lbl)

        self.txt_lbl = QLabel(label)
        self.txt_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.txt_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.txt_lbl.setWordWrap(False)
        ly.addWidget(self.txt_lbl, 1)

        self._update_style(False)

    def _update_style(self, active):
        self._active = active
        bg  = "#B91C1C" if active else "transparent"
        fg  = "#FFFFFF"  if active else "#334155"
        hov = "#DC2626"  if active else "#F1F5F9"

        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                border: none;
                border-radius: 8px;
                margin: 3px 10px;
                padding: 0px;
            }}
            QPushButton:hover {{ background: {hov}; }}
        """)
        try:
            import qtawesome as qta
            from PySide6.QtCore import QSize
            px = qta.icon(self._icon_name, color=fg).pixmap(QSize(18, 18))
            self.ico_lbl.setPixmap(px)
            self.ico_lbl.setStyleSheet("background:transparent;border:none;")
        except Exception:
            self.ico_lbl.setText("●")
            self.ico_lbl.setStyleSheet(f"color:{fg};background:transparent;border:none;font-size:10px;")
        self.txt_lbl.setStyleSheet(f"color:{fg};background:transparent;border:none;")

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


# Logo removida, usando imagem

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
        lb_ly.setContentsMargins(16, 0, 16, 0)
        lb_ly.setSpacing(12)

        from PySide6.QtGui import QPixmap
        from PySide6.QtCore import Qt
        from styles import LOGO_PATH
        
        logo_lbl = QLabel()
        pixmap = QPixmap(LOGO_PATH)
        pixmap = pixmap.scaled(200, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        logo_lbl.setPixmap(pixmap)
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lb_ly.addWidget(logo_lbl)

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

        # Labels de valor — guardadas para atualização dinâmica
        self._val_atualizacao = QLabel("—")
        self._val_periodo     = QLabel("—")
        self._val_responsavel = QLabel("—")

        for label, val_lbl in [
            ("Data de Atualização:",  self._val_atualizacao),
            ("Período Selecionado:",  self._val_periodo),
            ("Responsável:",           self._val_responsavel),
        ]:
            row = QHBoxLayout()
            row.setSpacing(8)
            lbl = QLabel(label)
            lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            lbl.setStyleSheet("color: #1E293B; background: transparent; border: none;")
            val_lbl.setFont(QFont("Segoe UI", 9))
            val_lbl.setStyleSheet("color: #64748B; background: transparent; border: none;")
            row.addWidget(lbl)
            row.addWidget(val_lbl)
            row.addStretch()
            meta_ly.addLayout(row)
        ly.addWidget(meta_frame)

    def set_page(self, title, subtitle="SEGURANÇA PATRIMONIAL"):
        self.page_title.setText(title)
        self.page_sub.setText(subtitle)

    def set_meta(self, stats: dict):
        """Atualiza os metadados do cabeçalho com dados reais do banco."""
        self._val_atualizacao.setText(stats.get("atualizacao") or "—")
        self._val_periodo.setText(stats.get("periodo")     or "—")
        self._val_responsavel.setText(stats.get("responsavel")  or "—")


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
