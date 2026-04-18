from PySide6.QtWidgets import QPushButton
from PySide6.QtGui import (
    QPainter, QPainterPath, QColor, QRadialGradient, 
    QLinearGradient, QBrush, QPen, QFont
)
from PySide6.QtCore import Qt, QRectF, QRect

class PremiumNeonButton(QPushButton):
    """
    Botão 'Glass Neon' com a paleta Crimson Forge.
    Destinado para janelas/paneis translúcidos ou com background vazado.
    """
    def __init__(self, text, par=None):
        super().__init__(text, par)
        self.setFixedHeight(36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.0)
        self.setFont(font)
        
        # Adiciona margem horizontal extra via stylesheet fake 
        self.setStyleSheet("padding: 0px 18px;")

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        w, h = self.width(), self.height()
        
        is_hover = self.underMouse()
        radius = 6.0
        rect = QRectF(2, 2, w - 4, h - 4)
        
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        
        # Corpo de vidro
        bg_alpha = 180 if is_hover else 140
        p.fillPath(path, QBrush(QColor(10, 5, 15, bg_alpha)))
        
        # Calor interno (fogo âmbar -> carmesim escuro)
        warm = QRadialGradient(w/2, h/2, w*0.6)
        warm.setColorAt(0, QColor(255, 60, 10, 50 if is_hover else 20))
        warm.setColorAt(0.6, QColor(200,  15, 15, 25 if is_hover else 8))
        warm.setColorAt(1, QColor(0, 0, 0, 0))
        p.fillPath(path, QBrush(warm))
        
        # Reflexo superior de vidro
        sheen = QLinearGradient(0, rect.top(), 0, rect.top() + rect.height() * 0.45)
        sheen.setColorAt(0, QColor(255, 255, 255, 30 if is_hover else 15))
        sheen.setColorAt(1, QColor(255, 255, 255, 0))
        sheen_p = QPainterPath()
        sheen_p.addRoundedRect(QRectF(rect.x(), rect.y(), rect.width(), rect.height() * 0.45), radius, radius)
        p.fillPath(sheen_p, QBrush(sheen))
        
        # Borda neon "Crimson Forge"
        border = QLinearGradient(rect.left(), 0, rect.right(), 0)
        if is_hover:
            border.setColorAt(0.00, QColor(255, 110, 26, 255))
            border.setColorAt(0.50, QColor(229,  20, 20, 255))
            border.setColorAt(1.00, QColor(112,  11, 20, 255))
        else:
            border.setColorAt(0.00, QColor(255, 110, 26, 170))
            border.setColorAt(0.50, QColor(229,  20, 20, 170))
            border.setColorAt(1.00, QColor(112,  11, 20, 170))
            
        p.setPen(QPen(QBrush(border), 1.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        
        # Aresta interna branca (luz de topo no vidro)
        rim = QPainterPath()
        rim.addRoundedRect(rect.adjusted(1.2, 1.2, -1.2, -1.2), radius - 1.2, radius - 1.2)
        rim_g = QLinearGradient(0, rect.top(), 0, rect.bottom())
        rim_g.setColorAt(0, QColor(255, 255, 255, 45 if is_hover else 25))
        rim_g.setColorAt(0.4, QColor(255, 255, 255, 5))
        rim_g.setColorAt(1, QColor(255, 255, 255, 0))
        p.setPen(QPen(QBrush(rim_g), 0.8))
        p.drawPath(rim)
        
        # Texto limpo
        text_rect = rect.toRect()
        shadow_rect = QRect(text_rect)
        shadow_rect.translate(0, 1)
        p.setPen(QColor(0, 0, 0, 190))
        p.drawText(shadow_rect, Qt.AlignmentFlag.AlignCenter, self.text())
        
        p.setPen(QColor(255, 255, 255, 255))
        p.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.text())
        p.end()

class SolidCrimsonButton(QPushButton):
    """
    Botão 'Sólido' para caixas de diálogo e QWidgets de base opaca.
    Não tenta vazar background para evitar clashing em pop-ups.
    """
    def __init__(self, text, par=None):
        super().__init__(text, par)
        self.setFixedHeight(34)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        
        font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.5)
        self.setFont(font)
        
        self.setStyleSheet("padding: 0px 16px;")

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        w, h = self.width(), self.height()
        
        is_hover = self.underMouse()
        radius = 5.0
        rect = QRectF(1, 1, w - 2, h - 2)
        
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        
        # Corpo Vermelho Crimson
        bg_col = QColor(210, 28, 28) if is_hover else QColor(185, 20, 20)
        p.fillPath(path, QBrush(bg_col))
        
        # Sombra sutil interna base
        inner_shadow = QLinearGradient(0, rect.top(), 0, rect.bottom())
        inner_shadow.setColorAt(0.00, QColor(0, 0, 0, 0))
        inner_shadow.setColorAt(1.00, QColor(0, 0, 0, 60))
        p.fillPath(path, QBrush(inner_shadow))

        # Borda sutil escurecida
        p.setPen(QPen(QColor(130, 10, 10), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        
        # Reflexo leve no topo (sheen)
        sheen_line = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.top()+5)
        sheen_line.setColorAt(0, QColor(255, 255, 255, 50))
        sheen_line.setColorAt(1, QColor(255, 255, 255, 0))
        rim = QPainterPath()
        rim.addRoundedRect(rect.adjusted(1,1,-1,-1), radius-1, radius-1)
        p.setPen(QPen(QBrush(sheen_line), 0.8))
        p.drawPath(rim)

        # Texto visível
        text_rect = rect.toRect()
        shadow_rect = QRect(text_rect)
        shadow_rect.translate(0, 1)
        p.setPen(QColor(0, 0, 0, 120))
        p.drawText(shadow_rect, Qt.AlignmentFlag.AlignCenter, self.text())
        
        p.setPen(QColor(255, 255, 255, 255))
        p.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.text())
        p.end()
