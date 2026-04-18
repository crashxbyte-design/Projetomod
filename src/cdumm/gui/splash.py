"""Splash screen shown during app startup."""
import importlib.resources
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import QSplashScreen, QLabel

from cdumm import __version__


def _get_logo_pixmap(size: int = 160) -> QPixmap | None:
    """Carrega o logo.png empacotado no bundle, compatível com PyInstaller."""
    try:
        # importlib.resources funciona tanto em desenvolvimento como no .exe
        pkg = importlib.resources.files("cdumm.gui").joinpath("logo.png")
        with importlib.resources.as_file(pkg) as path:
            pix = QPixmap(str(path))
            if pix.isNull():
                return None
            return pix.scaled(
                size, size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
    except Exception:
        return None


def show_splash(icon_path: str = None) -> QSplashScreen:
    """Cria e exibe a tela de splash."""
    W, H = 540, 270
    pixmap = QPixmap(W, H)

    painter = QPainter(pixmap)

    # Fundo escuro com gradiente
    grad = QLinearGradient(0, 0, W, H)
    grad.setColorAt(0, QColor(14, 8, 12))
    grad.setColorAt(1, QColor(26, 15, 18))
    painter.fillRect(pixmap.rect(), grad)

    # Linha de acento superior (laranja neon)
    painter.setPen(Qt.PenStyle.NoPen)
    accent_grad = QLinearGradient(0, 0, W, 0)
    accent_grad.setColorAt(0,   QColor(255, 110, 26, 0))
    accent_grad.setColorAt(0.5, QColor(255, 110, 26, 220))
    accent_grad.setColorAt(1,   QColor(255, 110, 26, 0))
    painter.setBrush(accent_grad)
    painter.drawRect(0, 0, W, 3)

    # Logo à esquerda (se conseguir carregar via importlib)
    logo_pix = _get_logo_pixmap(160)
    logo_x = 24
    if logo_pix:
        painter.drawPixmap(logo_x, (H - logo_pix.height()) // 2 - 12, logo_pix)
        text_x = logo_x + logo_pix.width() + 18
    else:
        text_x = 30

    # Título "CRIMSON ELITE BR"
    painter.setPen(QColor(255, 110, 26))
    f_title = QFont("Bahnschrift", 26)
    f_title.setBold(True)
    painter.setFont(f_title)
    painter.drawText(text_x, 110, "CRIMSON ELITE BR")

    # Subtítulo BR / versão
    painter.setPen(QColor(214, 214, 224))
    painter.setFont(QFont("Bahnschrift", 12))
    painter.drawText(text_x, 140, f"Gerenciador de Mods  •  v{__version__}")

    # Linha separadora fina
    painter.setPen(QColor(38, 24, 26))
    painter.drawLine(text_x, 156, W - 24, 156)

    # Texto de carregamento em baixo
    painter.setPen(QColor(255, 110, 26, 170))
    painter.setFont(QFont("Bahnschrift", 10))
    painter.drawText(
        pixmap.rect().adjusted(0, 0, -16, -14),
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
        "Carregando Sistemas Elite...",
    )

    painter.end()

    splash = QSplashScreen(pixmap)
    splash.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
    splash.show()
    return splash
