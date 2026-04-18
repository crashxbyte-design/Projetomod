# -*- coding: utf-8 -*-
"""Proper progress dialog that reliably shows percentage and status text."""
import logging

from PySide6.QtCore import Qt, QTimer, QRectF, Slot
from PySide6.QtGui import QColor, QPainter, QPen, QConicalGradient
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class _SpinnerWidget(QWidget):
    """Custom circular spinner drawn via QPainter — tamanho e espessura livres."""

    def __init__(self, size: int = 40, thickness: int = 5, parent=None) -> None:
        super().__init__(parent)
        self._size = size
        self._thickness = thickness
        self._angle = 0
        self._done = False
        self._error = False
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._timer = QTimer(self)
        self._timer.setInterval(18)          # ~55 fps
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self) -> None:
        self._angle = (self._angle - 6) % 360   # sentido anti-horário
        self.update()

    def stop(self, error: bool = False) -> None:
        self._timer.stop()
        self._done = True
        self._error = error
        self.update()

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        s = self._size
        t = self._thickness
        margin = t // 2 + 1
        rect = QRectF(margin, margin, s - 2 * margin, s - 2 * margin)

        if self._done:
            # Circulo completo + simbolo
            color = QColor("#E51414") if self._error else QColor("#2ECC71")
            pen = QPen(color, t, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawEllipse(rect)

            # Desenha check ou X no centro
            cx, cy = s / 2, s / 2
            inner = s * 0.20
            pen2 = QPen(color, t - 1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                        Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen2)
            if not self._error:
                # Check mark
                from PySide6.QtCore import QPointF
                p.drawPolyline([
                    QPointF(cx - inner * 0.9, cy),
                    QPointF(cx - inner * 0.2, cy + inner * 0.8),
                    QPointF(cx + inner * 1.1, cy - inner * 0.9),
                ])
            else:
                # X
                from PySide6.QtCore import QPointF
                p.drawLine(QPointF(cx - inner, cy - inner), QPointF(cx + inner, cy + inner))
                p.drawLine(QPointF(cx + inner, cy - inner), QPointF(cx - inner, cy + inner))
        else:
            # Trilha de fundo
            pen_bg = QPen(QColor(255, 255, 255, 22), t,
                          Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            p.setPen(pen_bg)
            p.drawEllipse(rect)

            # Arco animado com gradiente laranja → vermelho
            pen_arc = QPen(QColor("#FF6E1A"), t,
                           Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            p.setPen(pen_arc)
            # Qt usa 1/16 de grau, sentido anti-horário = positivo
            span = 270 * 16
            start = self._angle * 16
            p.drawArc(rect, start, span)

        p.end()


class ProgressDialog(QDialog):
    """Modal progress dialog with percentage bar, status message and spinner.

    Unlike QProgressDialog, this always shows immediately and reliably
    updates from worker thread signals via proper Slot decorators.
    """

    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(560)
        self.setModal(False)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.CustomizeWindowHint
        )

        self.setStyleSheet("""
            QDialog {
                background-color: #0E080C;
            }
            QLabel {
                color: #D6D6E0;
                font-family: 'Segoe UI';
                font-size: 13px;
                font-weight: 500;
            }
            QProgressBar {
                background-color: rgba(14, 8, 12, 0.6);
                border: 1px solid #1A0F12;
                border-radius: 4px;
                color: #FFFFFF;
                text-align: center;
                font-family: 'Bahnschrift';
                font-weight: bold;
                min-height: 24px;
            }
            QProgressBar::chunk {
                background-color: #FF6E1A;
                border-radius: 4px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(18, 18, 18, 16)

        # ── Linha de status: spinner + texto ──────────────────────────────────
        status_row = QHBoxLayout()
        status_row.setSpacing(14)

        self._spinner = _SpinnerWidget(size=44, thickness=5)
        status_row.addWidget(self._spinner, 0, Qt.AlignmentFlag.AlignVCenter)

        self._status_label = QLabel("INICIANDO ENGRENAGENS...")
        self._status_label.setStyleSheet(
            "font-family: 'Bahnschrift'; font-weight: bold;"
            " color: #FF6E1A; font-size: 14px; letter-spacing: 1px;"
        )
        self._status_label.setWordWrap(True)
        status_row.addWidget(self._status_label, 1)

        layout.addLayout(status_row)

        # ── Barra de progresso ────────────────────────────────────────────────
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFormat("%p%  concluido")
        layout.addWidget(self._progress_bar)

        # ── Detalhe secundario ────────────────────────────────────────────────
        self._detail_label = QLabel("")
        self._detail_label.setStyleSheet("color: #8A8298; font-size: 11px;")
        self._detail_label.setWordWrap(True)
        layout.addWidget(self._detail_label)

    # ── Slots de progresso ────────────────────────────────────────────────────
    @Slot(int, str)
    def update_progress(self, percent: int, message: str) -> None:
        """Thread-safe progress update via Qt signal/slot."""
        self._progress_bar.setValue(percent)
        self._status_label.setText(message)
        self._detail_label.setText(f"{percent}% finalizado")

    set_progress = update_progress

    @Slot()
    def on_finished(self) -> None:
        self._spinner.stop(error=False)
        self._progress_bar.setValue(100)
        self._status_label.setText("OPERACAO CONCLUIDA COM SUCESSO!")
        self._status_label.setStyleSheet(
            "color: #2ECC71; font-family: 'Bahnschrift';"
            " font-weight: bold; font-size: 14px; letter-spacing: 1px;"
        )
        self.accept()

    @Slot(str)
    def on_error(self, error: str) -> None:
        self._spinner.stop(error=True)
        self._status_label.setText(f"ERRO DETECTADO: {error}")
        self._status_label.setStyleSheet(
            "color: #E51414; font-family: 'Bahnschrift';"
            " font-weight: bold; font-size: 14px; letter-spacing: 1px;"
        )
        self._detail_label.setText("Processo Abortado.")
        # Don't auto-close — let user read the error
