"""
Fast Mod Card Delegate — Crimson Elite V5.

Cards premium com design crimson consistente com o tema global.
Barra de status lateral colorida, tipografia melhorada, toggle switch
atualizado e hover effect suave. Otimizado para 60FPS sem sombras pesadas.
"""

from PySide6.QtCore  import QSize, Qt, QRect, QRectF, QEvent, QPoint, Signal
from PySide6.QtGui   import (QPainter, QColor, QFont, QPen, QBrush, QFontMetrics,
                              QLinearGradient, QMouseEvent, QPainterPath)
from PySide6.QtWidgets import QStyledItemDelegate, QStyle, QApplication

# ── Paleta Crimson Elite ─────────────────────────────────────────────────────
_BG_NORMAL     = QColor(16, 12, 12, 200)   # fundo do card (glass)
_BG_HOVER      = QColor(22, 12, 12, 220)   # hover
_BG_SELECTED   = QColor(26, 10, 10, 240)   # selecionado 
_BG_DISABLED   = QColor(12, 8, 8, 180)     # desativado

_BORDER_NORMAL = QColor("#26181A")   # borda standard

_TEXT_ON       = QColor("#FFFFFF")   # nome ativo — puro cristal
_TEXT_OFF      = QColor("#4E4A58")   # nome desativado — apagado
_TEXT_SUB      = QColor("#565668")   # subtítulo desativado
_TEXT_SUB_ON   = QColor("#B08B7A")   # subtítulo ativo - Âmbar Ouro

# Toggle switch
_SW_OFF_TRACK  = QColor("#1E1A1E")   
_SW_KNOB       = QColor("#FFFFFF")   
_SW_OFF_KNOB   = QColor("#3A3840")   

# Barra lateral de status
_STATUS_BAR_COLORS = {
    "active":       QColor("#FF6E1A"),   # Amber Fire
    "not applied":  QColor("#D4A43C"),   # Amarelo Pendente
    "no data":      QColor("#E51414"),   # Crimson
    "disabled":     QColor("#2A2830"),   # quase invisível
    "checking...":  QColor("#2A2830"),
    "conflict":     QColor("#E51414"),   # Crimson
}

# Badge de status
_STATUS_COLORS = {
    "active":       QColor("#FF6E1A"),
    "not applied":  QColor("#D4A43C"),
    "no data":      QColor("#E51414"),
    "disabled":     QColor("#3A3848"),
    "checking...":  QColor("#3A3848"),
    "conflict":     QColor("#E51414"),
}
_STATUS_LABELS = {
    "active":       "✓ Ativo",
    "not applied":  "⚡ Pendente",
    "no data":      "✗ Sem dados",
    "disabled":     "○ Desativado",
    "checking...":  "○ Verificando",
    "conflict":     "⚠ Conflito",
}

# Fontes
_FONT_NAME   = QFont("Segoe UI", 11, QFont.Weight.Bold)
_FONT_SUB    = QFont("Segoe UI", 9)
_FONT_BADGE  = QFont("Segoe UI", 8, QFont.Weight.Bold)
_FONT_PRIO   = QFont("Segoe UI", 10, QFont.Weight.Bold)   # "Prioridade X"
_FONT_ICON   = QFont("Segoe UI", 16, QFont.Weight.Bold)

# Cores botões ▲▼
_BTN_NORMAL  = QColor(60, 40, 40, 160)
_BTN_HOVER   = QColor("#FF6E1A")
_BTN_TEXT    = QColor("#FFFFFF")
_BTN_W, _BTN_H = 18, 16  # compact size to fit right-margin zone


class FastModCardDelegate(QStyledItemDelegate):
    """Delegate de cards Premium Crimson Elite para QListView."""

    CARD_H = 48   # altura do card (densidade extrema)

    def sizeHint(self, option, index) -> QSize:
        return QSize(0, self.CARD_H)

    def __init__(self, parent=None):
        super().__init__(parent)
        # Track hover state for ▲▼ buttons: index row → 'up' | 'down' | None
        self._hovered_btn: dict[int, str | None] = {}

    def _btn_rects(self, card: QRect, data: dict, row: int) -> tuple[QRect, QRect]:
        """Return (up_rect, down_rect) for the ▲▼ buttons.

        Botões alinhados à esquerda do texto de Prioridade.
        """
        sw_w = 56
        sw_x = card.right() - sw_w - 16
        badge_w = 104
        badge_left = sw_x - badge_w - 8
        
        p_text = f"Prioridade {row}"
        pm = QFontMetrics(_FONT_PRIO)
        p_w = pm.horizontalAdvance(p_text) + 20
            
        p_x = badge_left - p_w - 8
        bx = p_x - _BTN_W - 8
        
        gap = 2
        total_h = _BTN_H * 2 + gap
        by  = card.top() + (card.height() - total_h) // 2
        
        up   = QRect(bx, by,             _BTN_W, _BTN_H)
        down = QRect(bx, by + _BTN_H + gap, _BTN_W, _BTN_H)
        return up, down

    def _draw_arrow_btn(self, painter: QPainter, rect: QRect,
                        symbol: str, hovered: bool) -> None:
        """Draw a small ▲ or ▼ button with neon hover effect."""
        rf = QRectF(rect)
        bg = _BTN_HOVER if hovered else _BTN_NORMAL
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(rf, 4.0, 4.0)
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.setPen(_BTN_TEXT)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, symbol)

    # ── Paint principal ──────────────────────────────────────────────────────
    def paint(self, painter: QPainter, option, index) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        data = index.data(Qt.ItemDataRole.UserRole)
        if not isinstance(data, dict):
            painter.restore()
            return

        is_sel   = bool(option.state & QStyle.StateFlag.State_Selected)
        is_hover = bool(option.state & QStyle.StateFlag.State_MouseOver)
        is_on    = data.get("enabled", False)
        status   = data.get("status", "disabled" if not is_on else "active")
        
        # Card com margem ZERADA (Grudados)
        card = option.rect.adjusted(10, 0, -10, 0)
        rf   = QRectF(card)

        # ── 1. Fundo do card (Blood Glass) ──────────────────────────────────
        if is_sel:
            bg = _BG_SELECTED
        elif is_hover:
            bg = _BG_HOVER
        elif not is_on:
            bg = _BG_DISABLED
        else:
            bg = _BG_NORMAL

        path = QPainterPath()
        path.addRoundedRect(rf, 9.0, 9.0)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg))
        painter.drawPath(path)

        # Gradient shading on top for glass dimension
        dg = QLinearGradient(rf.left(), rf.top(), rf.left(), rf.bottom())
        dg.setColorAt(0.00, QColor(255, 255, 255, 9 if is_hover else 3))
        dg.setColorAt(0.25, QColor(255, 255, 255, 0))
        dg.setColorAt(1.00, QColor(0, 0, 0, 48))
        painter.setBrush(QBrush(dg))
        painter.drawPath(path)

        # ── 2. Barra de status lateral ──────────────────────────────────────
        status_color = _STATUS_BAR_COLORS.get(status, _STATUS_BAR_COLORS["disabled"])
        bar_rf = QRectF(card.left(), card.top() + 6,
                        3.5, card.height() - 12)
        bar_path = QPainterPath()
        bar_path.addRoundedRect(bar_rf, 2.0, 2.0)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(status_color)
        painter.drawPath(bar_path)

        # ── 3. Borda do card (Gradient Neon Effect) ─────────────────────────
        if is_sel or is_hover:
            outline_g = QLinearGradient(card.left(), card.top(), card.left(), card.bottom())
            if is_sel:
                outline_g.setColorAt(0.0, QColor("#FF6E1A"))
                outline_g.setColorAt(1.0, QColor("#E51414"))
                border_w = 1.5
            else:
                outline_g.setColorAt(0.0, QColor(229, 20, 20, 180))
                outline_g.setColorAt(1.0, QColor(112, 11, 20, 80))
                border_w = 1.2
            painter.setPen(QPen(QBrush(outline_g), border_w))
        else:
            painter.setPen(QPen(_BORDER_NORMAL, 1.0))
            
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

        # Beveling (Glass Refraction)
        painter.setPen(QPen(QColor(255, 255, 255, 15), 1.0))
        painter.drawLine(card.left() + 12, card.top() + 1, card.right() - 12, card.top() + 1)
        painter.setPen(QPen(QColor(0, 0, 0, 100), 1.0))
        painter.drawLine(card.left() + 12, card.bottom() - 1, card.right() - 12, card.bottom() - 1)

        # ── 4. Thumbnail / Avatar Cativante ─────────────────────────────────
        icon_size = 32
        icon_x = card.left() + 16
        icon_y = card.top() + (card.height() - icon_size) // 2
        icon_rf   = QRectF(icon_x, icon_y, icon_size, icon_size)
        mod_name = str(data.get("name", "?")).strip()
        if len(mod_name) > 80:
            mod_name = mod_name[:77] + "..."
        icon_char = str(index.row() + 1)

        if is_on:
            # Active landscape / warm gradient based on ID
            h_hue = (data.get("id", 0) * 45) % 360
            sky = QLinearGradient(icon_rf.left(), icon_rf.top(), icon_rf.left(), icon_rf.bottom())
            sky.setColorAt(0.0, QColor.fromHsl(h_hue, 90, 28))
            sky.setColorAt(0.5, QColor.fromHsl(h_hue, 70, 16))
            sky.setColorAt(1.0, QColor.fromHsl(h_hue, 50,  8))
            
            painter.setPen(QPen(QColor(255, 255, 255, 30), 1.0))
            painter.setBrush(QBrush(sky))
            painter.drawRoundedRect(icon_rf, 8.0, 8.0)
            
            hrz = QLinearGradient(icon_rf.left(), icon_rf.top() + icon_size * 0.45,
                                  icon_rf.left(), icon_rf.top() + icon_size * 0.65)
            hrz.setColorAt(0.0, QColor(0, 0, 0, 0))
            hrz.setColorAt(0.5, QColor.fromHsl(h_hue, 100, 32, 70))
            hrz.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(hrz))
            painter.drawRoundedRect(icon_rf, 8.0, 8.0)
        else:
            # Inactive Ghost avatar
            icon_bg = QColor("#141214")
            icon_border = QColor("#1E1A1E")
            painter.setPen(QPen(icon_border, 1.0))
            painter.setBrush(icon_bg)
            painter.drawRoundedRect(icon_rf, 8.0, 8.0)
            
        # Draw Priority Number inside the Avatar
        painter.setFont(_FONT_ICON)
        painter.setPen(QColor(255, 255, 255, 180) if is_on else QColor(255, 255, 255, 40))
        painter.drawText(icon_rf, Qt.AlignmentFlag.AlignCenter, icon_char)

        # ── 5. Toggle switch (Bloco Tático Cyberpunk: ATIVO/OFF) ──────────────
        sw_w, sw_h = 56, 22
        sw_x = card.right() - sw_w - 16
        sw_y = card.top() + (card.height() - sw_h) // 2
        
        path = QPainterPath()
        path.moveTo(sw_x + 6, sw_y)
        path.lineTo(sw_x + sw_w, sw_y)
        path.lineTo(sw_x + sw_w, sw_y + sw_h)
        path.lineTo(sw_x, sw_y + sw_h)
        path.lineTo(sw_x, sw_y + 6)
        path.closeSubpath()

        if is_on:
            tf = QLinearGradient(sw_x, sw_y, sw_x, sw_y + sw_h)
            tf.setColorAt(0.0, QColor("#FF6E1A"))
            tf.setColorAt(1.0, QColor("#A50C0C"))
            painter.setBrush(QBrush(tf))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(path)
            
            painter.setPen(QColor("#FFFFFF"))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.drawText(QRectF(sw_x, sw_y, sw_w, sw_h), Qt.AlignmentFlag.AlignCenter, "ATIVO")
        else:
            painter.setBrush(QColor(10, 6, 8, 180))
            painter.setPen(QPen(QColor(255, 110, 26, 60), 1.0))
            painter.drawPath(path)
            
            painter.setPen(QColor(255, 110, 26, 110))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Medium))
            painter.drawText(QRectF(sw_x, sw_y, sw_w, sw_h), Qt.AlignmentFlag.AlignCenter, "OFF")

        # ── 6. Textos: Nome e Subtítulo ─────────────────────────────────────
        text_x = icon_x + icon_size + 14
        badge_w = 104
        text_w  = sw_x - text_x - badge_w - 16

        name_rect = QRect(text_x, card.top() + 4, text_w, 20)
        painter.setFont(_FONT_NAME)
        painter.setPen(_TEXT_ON if is_on else _TEXT_OFF)
        painter.drawText(name_rect,
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         mod_name)

        author   = data.get("author") or data.get("desc") or ""
        version  = data.get("version") or ""
        mod_type = data.get("mod_type") or ""
        parts    = [p for p in [author, version, mod_type.upper()] if p]
        sub_str  = "  ·  ".join(parts) if parts else "—"

        sub_rect = QRect(text_x, card.top() + 24, text_w + badge_w + 16, 18)
        painter.setFont(_FONT_SUB)
        painter.setPen(_TEXT_SUB_ON if is_on else _TEXT_SUB)
        painter.drawText(sub_rect,
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         sub_str)

        # ── 7. Badge de status ──────────────────────────────────────────────
        badge_color = _STATUS_COLORS.get(status, QColor("#3A3848"))
        badge_label = _STATUS_LABELS.get(status, status)

        badge_rect = QRect(sw_x - badge_w - 8,
                           card.top() + (card.height() - 22) // 2,
                           badge_w, 22)
        badge_bg = QColor(badge_color.red(), badge_color.green(),
                          badge_color.blue(), 26)
        badge_border = QColor(badge_color.red(), badge_color.green(),
                              badge_color.blue(), 120)
        painter.setBrush(badge_bg)
        painter.setPen(QPen(badge_border, 1.2))
        painter.drawRoundedRect(QRectF(badge_rect), 11.0, 11.0)
        painter.setFont(_FONT_BADGE)
        painter.setPen(badge_color)
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, badge_label)

        # ── 8. Prioridade (Visual Positional Order) ───────────────────────────
        row = index.row()
        p_text = f"Prioridade {row}"
        painter.setFont(_FONT_PRIO)
        pm = QFontMetrics(painter.font())
        p_w = pm.horizontalAdvance(p_text) + 26
        p_h = 24
        p_x = badge_rect.left() - p_w - 8
        p_y = card.top() + (card.height() - p_h) // 2

        p_rectf = QRectF(p_x, p_y, p_w, p_h)

        # Badge Glassmorphism
        painter.setPen(QPen(QColor(255, 255, 255, 20), 1.0))
        if is_on:
            painter.setBrush(QColor(229, 20, 20, 40))  # Crimson glass
            painter.drawRoundedRect(p_rectf, p_h / 2, p_h / 2)
            painter.setPen(QColor("#FF6E1A"))
        else:
            painter.setBrush(QColor(0, 0, 0, 80))      # Dark glass
            painter.drawRoundedRect(p_rectf, p_h / 2, p_h / 2)
            painter.setPen(QColor("#7A7890"))

        painter.drawText(QRect(p_x, p_y, p_w, p_h), Qt.AlignmentFlag.AlignCenter, p_text)

        # ── 9. Botões ▲▼ (dentro do card, ao lado da prioridade) ───────────
        up_rect, down_rect = self._btn_rects(card, data, row)
        hov = self._hovered_btn.get(row)
        self._draw_arrow_btn(painter, up_rect,   "▲", hov == "up")
        self._draw_arrow_btn(painter, down_rect, "▼", hov == "down")

        painter.restore()

    # ── Editor de eventos (clique no toggle) ─────────────────────────────────
    def editorEvent(self, event: QEvent, model, option, index) -> bool:
        if event.type() == QEvent.Type.MouseMove:
            data = index.data(Qt.ItemDataRole.UserRole)
            if not isinstance(data, dict): return False
            card = option.rect.adjusted(10, 0, -10, 0)
            row = index.row()
            up, down = self._btn_rects(card, data, row)
            pos = event.position().toPoint()
            if up.contains(pos): self._hovered_btn[row] = "up"
            elif down.contains(pos): self._hovered_btn[row] = "down"
            else: self._hovered_btn[row] = None
            return False

        if event.type() != QEvent.Type.MouseButtonRelease:
            return False
        if not isinstance(event, QMouseEvent):
            return False
        if event.button() != Qt.MouseButton.LeftButton:
            return False

        data = index.data(Qt.ItemDataRole.UserRole)
        if not isinstance(data, dict):
            return False

        pos = event.position().toPoint()

        # ── Hit zones do clique ───────────────────────────────────────────
        card = option.rect.adjusted(10, 0, -10, 0)
        sw_w, sw_h = 56, 22
        sw_x = card.right() - sw_w - 16
        sw_y = card.top() + (card.height() - sw_h) // 2
        sw_rect = QRect(sw_x, sw_y, sw_w, sw_h)
        
        row = index.row()
        up_rect, down_rect = self._btn_rects(card, data, row)

        if sw_rect.contains(pos):
            current = data.get("enabled", False)
            new_val = Qt.CheckState.Unchecked if current else Qt.CheckState.Checked
            model.setData(index.siblingAtColumn(0), new_val,
                          Qt.ItemDataRole.CheckStateRole)
            return True

        # ── ▲ Up button ───────────────────────────────────────────────────
        if up_rect.contains(pos):
            view = self.parent()
            if view and hasattr(view, 'parent') and callable(view.parent):
                mw = view.parent()
                while mw is not None:
                    if hasattr(mw, '_mod_manager'):
                        mw._mod_manager.move_up(data["id"])
                        if hasattr(mw, '_refresh_all'):
                            mw._refresh_all()
                        break
                    mw = mw.parent() if hasattr(mw, 'parent') else None
            return True

        # ── ▼ Down button ─────────────────────────────────────────────────
        if down_rect.contains(pos):
            view = self.parent()
            if view and hasattr(view, 'parent') and callable(view.parent):
                mw = view.parent()
                while mw is not None:
                    if hasattr(mw, '_mod_manager'):
                        mw._mod_manager.move_down(data["id"])
                        if hasattr(mw, '_refresh_all'):
                            mw._refresh_all()
                        break
                    mw = mw.parent() if hasattr(mw, 'parent') else None
            return True

        return False
