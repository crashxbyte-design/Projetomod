"""
gui/mod_card_delegate.py
─────────────────────────────────────────────────────────────────────────────
Custom QStyledItemDelegate that renders each mod as a premium dark card.

STATUS: Ready for Etapa 3 integration — NOT imported anywhere yet.

Usage (Etapa 3):
    from cdumm.gui.mod_card_delegate import ModCardDelegate, build_mod_card_dict

    delegate = ModCardDelegate()
    delegate.toggle_requested.connect(lambda mod_id: ...)

    list_widget = QListWidget()
    list_widget.setObjectName("modCardList")
    list_widget.setItemDelegate(delegate)

    # Populate items:
    for mod in mod_manager.list_mods():
        item = QListWidgetItem()
        card = build_mod_card_dict(mod, model._status_cache, model._conflict_status_cache)
        item.setData(Qt.ItemDataRole.UserRole, card)
        item.setSizeHint(QSize(0, ModCardDelegate.CARD_H + 14))
        list_widget.addItem(item)

Card data dict schema (Qt.UserRole):
    {
        "id":       int,      # mod database id
        "name":     str,      # display name
        "desc":     str,      # short description / author
        "version":  str,      # version string
        "enabled":  bool,     # current enabled state
        "status":   str,      # "active" | "not applied" | "no data" | "disabled" | "checking..."
        "conflict": str,      # "clean" | "conflict" | "resolved"
    }
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from PySide6.QtCore import (
    QEvent, QPointF, QRect, QRectF, QSize, Qt, Signal,
)
from PySide6.QtGui import (
    QBrush, QColor, QFont, QFontMetrics, QLinearGradient,
    QPainter, QPainterPath, QPen, QPolygonF, QRadialGradient,
)
from PySide6.QtWidgets import QStyle, QStyledItemDelegate

# ── Card status display config ────────────────────────────────────────────────

# Maps ModListModel status strings to (border_colour, badge_label, badge_colour)
_STATUS_MAP = {
    "active":      (QColor("#FF6E1A"), "✓  Ativo",        QColor("#FF6E1A")),
    "not applied": (QColor("#D4A43C"), "⚠  Pendente",     QColor("#D4A43C")),
    "no data":     (QColor("#E51414"), "✗  Sem dados",    QColor("#E51414")),
    "disabled":    (QColor("#363648"), "◌  Desativado", QColor("#565668")),
    "checking...": (QColor("#2A2A3A"), "◌",               QColor("#38384A")),
    # injected by conflict_cache override:
    "conflict":    (QColor("#E51414"), "⚠  Conflito",     QColor("#FF4040")),
}
_STATUS_DEFAULT = (QColor("#363648"), "◌  Desconhecido", QColor("#565668"))

# Thumb hue assigned per mod_id for stable palette (cycles through 8 values)
_THUMB_HUES = [12, 215, 195, 275, 30, 160, 340, 55]


def _thumb_hue(mod_id: int) -> int:
    return _THUMB_HUES[mod_id % len(_THUMB_HUES)]


# ── Public helper ─────────────────────────────────────────────────────────────

def build_mod_card_dict(
    mod: dict,
    status_cache: dict[int, str] | None = None,
    conflict_cache: dict[int, str] | None = None,
) -> dict:
    """
    Convert a ModManager.list_mods() row dict into a card data dict
    ready to be stored as Qt.UserRole on a QListWidgetItem.

    Args:
        mod:            Dict from ModManager.list_mods()
        status_cache:   ModListModel._status_cache   {mod_id: status_str}
        conflict_cache: ModListModel._conflict_status_cache {mod_id: str}
    """
    mid = mod.get("id", 0)
    status = (status_cache or {}).get(mid, "checking...")
    conflict = (conflict_cache or {}).get(mid, "clean")

    # Conflict overrides status display
    effective_status = "conflict" if conflict == "conflict" else status

    return {
        "id":       mid,
        "name":     mod.get("name") or "Unknown",
        "desc":     mod.get("author") or "",
        "version":  mod.get("version") or "",
        "enabled":  bool(mod.get("enabled", False)),
        "status":   effective_status,
        "conflict": conflict,
        "thumb_hue": _thumb_hue(mid),
    }


# ── Delegate ──────────────────────────────────────────────────────────────────

class ModCardDelegate(QStyledItemDelegate):
    """
    Renders a mod list item as a premium dark card.

    Signals:
        toggle_requested(int):  Emitted with mod_id when the toggle pill is clicked.
                                Connect to: lambda mid: mod_manager.set_enabled(mid, not cur)
    """

    CARD_H: int = 90  # inner card height (px) — item height = CARD_H + 14

    toggle_requested = Signal(int)  # mod_id

    # ── Size hint ─────────────────────────────────────────────────────────────

    def sizeHint(self, _option, _index) -> QSize:
        return QSize(0, self.CARD_H + 14)

    # ── Event — toggle click detection ────────────────────────────────────────

    def editorEvent(self, event, model, option, index) -> bool:
        """Intercept mouse clicks on the toggle pill area."""
        if event.type() != QEvent.Type.MouseButtonRelease:
            return False
        mod = index.data(Qt.ItemDataRole.UserRole)
        if not mod:
            return False
        tr = self._toggle_rect(option.rect)
        if tr.contains(event.pos()):
            self.toggle_requested.emit(mod["id"])
            return True
        return False

    def _toggle_rect(self, item_rect: QRect) -> QRect:
        """Returns the QRect of the toggle pill for hit-testing."""
        rect = QRectF(item_rect).adjusted(14, 7, -14, -7)
        TW, TH = 52, 26
        MID_Y = int(rect.top()) + self.CARD_H // 2
        TX2 = int(rect.right()) - TW - 14
        TY2 = MID_Y - TH // 2
        return QRect(TX2, TY2, TW, TH)

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paint(self, painter: QPainter, option, index) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        mod = index.data(Qt.ItemDataRole.UserRole)
        if not mod:
            painter.restore()
            return

        is_hovered  = bool(option.state & QStyle.StateFlag.State_MouseOver)
        is_selected = bool(option.state & QStyle.StateFlag.State_Selected)
        status      = mod.get("status", "disabled")
        enabled     = mod.get("enabled", False)

        border_col, badge_label, badge_fg = _STATUS_MAP.get(status, _STATUS_DEFAULT)
        if not enabled and status not in ("conflict",):
            border_col = QColor("#363648")

        rect = QRectF(option.rect).adjusted(14, 7, -14, -7)

        # ── Shadow ────────────────────────────────────────────────────────────
        for off, alpha, spread in [(5, 75, 2), (2, 45, 0)]:
            sh = QPainterPath()
            sh.addRoundedRect(rect.adjusted(-spread, off, spread, off + spread), 10, 10)
            painter.fillPath(sh, QBrush(QColor(0, 0, 0, alpha)))

        # ── Card fill (Blood Glass) ───────────────────────────────────────────
        card_path = QPainterPath()
        card_path.addRoundedRect(rect, 8, 8)

        if is_selected:
            CARD_BG = QColor(26, 10, 10, 240)  # Dark burgundy tint
        elif is_hovered:
            CARD_BG = QColor(22, 12, 12, 220)
        else:
            CARD_BG = QColor(16, 12, 12, 200)
        painter.fillPath(card_path, QBrush(CARD_BG))

        # Depth gradient top → bottom
        dg = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
        dg.setColorAt(0.00, QColor(255, 255, 255, 9 if is_hovered else 3))
        dg.setColorAt(0.25, QColor(255, 255, 255, 0))
        dg.setColorAt(1.00, QColor(0, 0, 0, 48))
        painter.fillPath(card_path, QBrush(dg))

        # Status colour bleed from left
        bleed = QPainterPath()
        bleed.addRoundedRect(rect, 8, 8)
        bg = QLinearGradient(rect.left(), 0, rect.left() + 100, 0)
        c0 = QColor(border_col); c0.setAlpha(40 if enabled else 15)
        bg.setColorAt(0.0, c0); bg.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillPath(bleed, QBrush(bg))

        # ── Outer Ambient Glow (Neon Aura) ────────────────────────────────────
        if is_selected or is_hovered:
            rx, ry = rect.center().x(), rect.center().y()
            glow_rad = QRadialGradient(rx, ry, rect.width() * 0.6)
            base_glow = QColor("#FF6E1A") if is_selected else QColor("#AA3311")
            base_glow.setAlpha(35 if is_selected else 15)
            glow_rad.setColorAt(0.0, base_glow)
            glow_rad.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.fillRect(rect.adjusted(-20, -20, 20, 20), QBrush(glow_rad))

        # Card border (Gradient Neon)
        if is_selected or is_hovered:
            outline_g = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
            if is_selected:
                outline_g.setColorAt(0.0, QColor("#FF6E1A"))
                outline_g.setColorAt(1.0, QColor("#E51414"))
            else:
                outline_g.setColorAt(0.0, QColor(229, 20, 20, 180))
                outline_g.setColorAt(1.0, QColor(112, 11, 20, 80))
            painter.setPen(QPen(QBrush(outline_g), 1.5))
        else:
            painter.setPen(QPen(QColor("#26181A"), 0.9))
        painter.drawPath(card_path)

        # ── Glass Cut-out / Beveling ──────────────────────────────────────────
        # Top inner edge (light)
        painter.setPen(QPen(QColor(255, 255, 255, 18), 1.0))
        tp = QPainterPath()
        tp.moveTo(rect.left() + 12, rect.top() + 1)
        tp.lineTo(rect.right() - 12, rect.top() + 1)
        painter.drawPath(tp)

        # Bottom inner shadow 
        painter.setPen(QPen(QColor(0, 0, 0, 120), 1.0))
        bp = QPainterPath()
        bp.moveTo(rect.left() + 12, rect.bottom() - 1)
        bp.lineTo(rect.right() - 12, rect.bottom() - 1)
        painter.drawPath(bp)

        # ── Left status bar (Glowing line) ────────────────────────────────────
        lb = QPainterPath()
        lb.addRoundedRect(rect.left(), rect.top(), 3, rect.height(), 2, 2)
        painter.setPen(Qt.PenStyle.NoPen)
        lb_g = QLinearGradient(0, rect.top(), 0, rect.bottom())
        if is_selected:
            lb_g.setColorAt(0.0, QColor(border_col).lighter(145))
            lb_g.setColorAt(1.0, QColor(border_col).lighter(118))
        else:
            lb_g.setColorAt(0.0, QColor(border_col).lighter(115))
            lb_g.setColorAt(1.0, border_col)
        painter.fillPath(lb, QBrush(lb_g))

        # ── Thumbnail / Avatar ────────────────────────────────────────────────
        TH = 62
        TX = int(rect.left()) + 16
        TY = int(rect.top()) + (self.CARD_H - TH) // 2
        th_r = QRectF(TX, TY, TH, TH)
        th_p = QPainterPath()
        th_p.addRoundedRect(th_r, 6, 6)

        hue = mod.get("thumb_hue", 0)
        sky = QLinearGradient(th_r.left(), th_r.top(), th_r.left(), th_r.bottom())
        
        # Ghost Thumbnail when disabled
        if not enabled:
            sky.setColorAt(0.0, QColor(40, 42, 48))
            sky.setColorAt(0.5, QColor(25, 27, 30))
            sky.setColorAt(1.0, QColor(15, 16, 20))
        else:
            sky.setColorAt(0.0, QColor.fromHsl(hue, 90, 28))
            sky.setColorAt(0.5, QColor.fromHsl(hue, 70, 16))
            sky.setColorAt(1.0, QColor.fromHsl(hue, 50,  8))
        painter.fillPath(th_p, QBrush(sky))

        if enabled:
            # Active landscape
            hrz = QLinearGradient(th_r.left(), th_r.top() + TH * 0.45,
                                  th_r.left(), th_r.top() + TH * 0.65)
            hrz.setColorAt(0.0, QColor(0, 0, 0, 0))
            hrz.setColorAt(0.5, QColor.fromHsl(hue, 100, 32, 70))
            hrz.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.fillPath(th_p, QBrush(hrz))

            vig = QRadialGradient(TX + TH / 2, TY + TH / 2, TH * 0.58)
            vig.setColorAt(0.0, QColor(0, 0, 0,   0))
            vig.setColorAt(0.7, QColor(0, 0, 0,  60))
            vig.setColorAt(1.0, QColor(0, 0, 0, 140))
            painter.fillPath(th_p, QBrush(vig))
        else:
            # Inactive avatar ghost
            alpha = mod.get("name", "M").strip()
            first_l = alpha[0].upper() if alpha else "M"
            painter.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
            painter.setPen(QColor(255, 255, 255, 25))
            painter.drawText(th_r, Qt.AlignmentFlag.AlignCenter, first_l)

        # Border for thumbnail
        painter.setPen(QPen(QColor(255, 255, 255, 40 if enabled else 15), 1.0))
        painter.drawPath(th_p)

        # ── Text ──────────────────────────────────────────────────────────────
        TEXT_X  = TX + TH + 16
        RIGHT_W = 240
        TEXT_W  = int(rect.right()) - TEXT_X - RIGHT_W - 4

        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        painter.setPen(QColor("#FFFFFF"))  # Bright White for Impact
        painter.drawText(
            QRect(TEXT_X, int(rect.top()) + 20, TEXT_W, 22),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            mod.get("name", ""),
        )

        desc_f = QFont("Segoe UI", 8)
        painter.setFont(desc_f)
        painter.setPen(QColor("#B08B7A")) # Golden Amber tone for desc
        desc = QFontMetrics(desc_f).elidedText(
            mod.get("desc", ""), Qt.TextElideMode.ElideRight, TEXT_W)
        painter.drawText(
            QRect(TEXT_X, int(rect.top()) + 48, TEXT_W, 18),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            desc,
        )

        # ── Right elements ────────────────────────────────────────────────────
        MID_Y = int(rect.top()) + self.CARD_H // 2

        # == Toggle pill ==
        TW2, TH2 = 52, 26
        TX2 = int(rect.right()) - TW2 - 14
        TY2 = MID_Y - TH2 // 2

        if enabled:
            glow = QRadialGradient(TX2 + TW2 // 2, TY2 + TH2 // 2, TW2 * 0.85)
            # Radiant Crimson glow
            glow.setColorAt(0.0, QColor(229, 20, 20, 90))
            glow.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.fillRect(QRect(TX2 - 10, TY2 - 10, TW2 + 20, TH2 + 20), QBrush(glow))

        tg_p = QPainterPath()
        tg_p.addRoundedRect(TX2, TY2, TW2, TH2, TH2 // 2, TH2 // 2)

        if enabled:
            tf = QLinearGradient(TX2, TY2, TX2, TY2 + TH2)
            # Crimson / Blood Fill
            tf.setColorAt(0.0, QColor("#FF3B1A"))
            tf.setColorAt(1.0, QColor("#A50C0C"))
        else:
            tf = QLinearGradient(TX2, TY2, TX2, TY2 + TH2)
            tf.setColorAt(0.0, QColor("#303042"))
            tf.setColorAt(1.0, QColor("#232336"))

        painter.fillPath(tg_p, QBrush(tf))
        painter.setPen(QPen(QColor(255, 255, 255, 28 if enabled else 12), 0.8))
        painter.drawPath(tg_p)

        KS = TH2 - 6
        KX = (TX2 + TW2 - KS - 3) if enabled else (TX2 + 3)
        KY = TY2 + 3

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 60)))
        painter.drawEllipse(QRect(KX + 1, KY + 1, KS, KS))

        kg = QRadialGradient(KX + KS * 0.35, KY + KS * 0.3, KS * 0.6)
        kg.setColorAt(0.0, QColor("#FFFFFF"))
        kg.setColorAt(1.0, QColor("#F4F4FC") if enabled else QColor("#A0A0B0"))
        painter.setBrush(QBrush(kg))
        painter.drawEllipse(QRect(KX, KY, KS, KS))

        painter.setFont(QFont("Segoe UI", 6, QFont.Weight.Bold))
        painter.setPen(QColor(255, 255, 255, 180 if enabled else 100))
        if enabled:
            painter.drawText(
                QRect(TX2 + 5, TY2, KX - TX2 - 1, TH2),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "LIG")
        else:
            painter.drawText(
                QRect(KX + KS + 2, TY2, TX2 + TW2 - KX - KS - 3, TH2),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "DESL")

        # == Version ==
        VW = 50
        VX = TX2 - VW - 14
        painter.setFont(QFont("Segoe UI", 9))
        painter.setPen(QColor("#A88B7D"))
        painter.drawText(
            QRect(VX, MID_Y - 10, VW, 20),
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
            mod.get("version", ""),
        )

        # == Status badge ==
        bf = QFont("Segoe UI", 8, QFont.Weight.Bold)
        painter.setFont(bf)
        BW = QFontMetrics(bf).horizontalAdvance(badge_label) + 24
        BH = 24
        BX = VX - BW - 12
        BY = MID_Y - BH // 2

        badge_path = QPainterPath()
        badge_path.addRoundedRect(BX, BY, BW, BH, BH // 2, BH // 2)

        fill = QColor(badge_fg); fill.setAlpha(38)
        painter.fillPath(badge_path, QBrush(fill))
        border_c = QColor(badge_fg); border_c.setAlpha(180)
        painter.setPen(QPen(border_c, 1.2))
        painter.drawPath(badge_path)
        painter.setPen(badge_fg)
        painter.drawText(QRect(BX, BY, BW, BH), Qt.AlignmentFlag.AlignCenter, badge_label)

        painter.restore()
