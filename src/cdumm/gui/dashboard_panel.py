"""dashboard_panel.py — Aba "Painel" do Crimson Elite BR.

Baseado no DashboardPage do preview_new_ui_v2.py, adaptado para dados reais.

Performance:
 - ContentBackdrop escala a imagem UMA vez (no resize) e cacheia em _scaled_px.
 - StatCard usa paintEvent puro (sem objetos Python alocados on-paint).
 - ModMiniCard usa paintEvent incremental — apenas atualiza ao hover.
 - Scan de ASI é deferido 200ms e roda no main thread (é rápido).
"""

import time as _time
import os as _os
import sys as _sys
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QSize, QRectF, QRect, QPointF
from PySide6.QtGui import (
    QColor, QFont, QLinearGradient, QPainter, QPainterPath,
    QPen, QBrush, QRadialGradient, QPixmap,
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QSizePolicy, QScrollArea, QPushButton, QProgressBar,
)

# ── Localiza o hero bg relativo a este arquivo ──────────────────────────────
_HERE = Path(__file__).parent
if getattr(_sys, 'frozen', False):
    # PyInstaller copia conforme o spec: ('src/cdumm/gui/crimson_hero_bg.png', 'cdumm/gui')
    # Portanto no _MEIPASS o arquivo fica em: <MEIPASS>/cdumm/gui/crimson_hero_bg.png
    _HERO_BG_PATH = str(Path(_sys._MEIPASS) / "cdumm" / "gui" / "crimson_hero_bg.png")
    if not _os.path.exists(_HERO_BG_PATH):
        # Fallback: pode estar na raiz do MEIPASS
        _HERO_BG_PATH = str(Path(_sys._MEIPASS) / "crimson_hero_bg.png")
else:
    _HERO_BG_PATH = str(_HERE / "crimson_hero_bg.png")


# ─────────────────────────────────────────────────────────────────────────────
# BACKDROP — renderiza a imagem héri com overlays crimson
# Cacheia o pixmap escalado; só re-escala no resize (performance).
# ─────────────────────────────────────────────────────────────────────────────
class ContentBackdrop(QWidget):
    """Fundo com imagem + overlays gradientes."""
    _source_px: QPixmap | None = None   # pixmap original (lido uma vez)

    def __init__(self, parent=None):
        super().__init__(parent)
        if ContentBackdrop._source_px is None:
            ContentBackdrop._source_px = QPixmap(_HERO_BG_PATH)

    def paintEvent(self, _):
        p = QPainter(self)
        w, h = self.width(), self.height()
        
        # Guarda critica: sem dimensões válidas, não pintar
        if w <= 0 or h <= 0:
            p.end()
            return

        px = ContentBackdrop._source_px
        if px and not px.isNull():
            pw, ph = px.width(), px.height()
            
            # Keep Aspect Ratio by Expanding logic mapped directly to drawing rects
            ratio = max(w / pw, h / ph)
            if ratio <= 0:
                return
            
            x_off = ((pw * ratio) - w) / 2 / ratio
            y_off = ((ph * ratio) - h) / 2 / ratio
            sw, sh = w / ratio, h / ratio
            
            p.drawPixmap(QRectF(0, 0, w, h), px, QRectF(x_off, y_off, sw, sh))
        else:
            p.fillRect(0, 0, w, h, QColor("#09060C"))

        # Overlay vertical (escurece bordas)
        ov = QLinearGradient(0, 0, 0, h)
        ov.setColorAt(0.00, QColor(6, 4, 10, 155))
        ov.setColorAt(0.12, QColor(6, 4, 10,  90))
        ov.setColorAt(0.40, QColor(6, 4, 10, 115))
        ov.setColorAt(0.62, QColor(6, 4, 10, 175))
        ov.setColorAt(1.00, QColor(6, 4, 10, 230))
        p.fillRect(0, 0, w, h, QBrush(ov))

        # Leve bloom crimson no canto superior direito
        sky = QRadialGradient(w * 0.88, -h * 0.08, w * 0.85)
        sky.setColorAt(0.00, QColor(190, 42, 24, 52))
        sky.setColorAt(0.40, QColor(140, 24, 14, 22))
        sky.setColorAt(1.00, QColor(0, 0, 0, 0))
        p.fillRect(0, 0, w, h, QBrush(sky))

        # Vinheta final
        vig = QRadialGradient(w / 2, h / 2, max(w, h) * 0.82)
        vig.setColorAt(0.52, QColor(0, 0, 0, 0))
        vig.setColorAt(1.00, QColor(0, 0, 0, 75))
        p.fillRect(0, 0, w, h, QBrush(vig))

        # Grid Tático (Tactical Data Scanner)
        p.setPen(QPen(QColor(255, 255, 255, 5), 1))
        for x in range(0, int(w), 60):
            p.drawLine(x, 0, x, int(h))
        for y in range(0, int(h), 60):
            p.drawLine(0, y, int(w), y)

        p.end()


# ─────────────────────────────────────────────────────────────────────────────
# HERO AREA — sobreposição transparente com título + botão CTA
# ─────────────────────────────────────────────────────────────────────────────
class _HeroHeaderPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(700, 110)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
    def paintEvent(self, _):
        from PySide6.QtGui import QPainter, QFont, QPen, QColor, QFontMetrics
        from PySide6.QtCore import Qt, QRectF
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        
        w, h = self.width(), self.height()
        
        # Guarda critica: sem dimensões válidas, não pintar
        if w <= 0 or h <= 0:
            p.end()
            return
        
        cx, cy = w / 2.0, h / 2.0
        
        # ── Título Centralizer: CRIMSON ELITE ──
        font_main = QFont("Bahnschrift", 36, QFont.Weight.Black)
        font_main.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 5.0)
        p.setFont(font_main)
        
        text1 = "CRIMSON ELITE"
        fm1 = QFontMetrics(font_main)
        text1_rect = fm1.boundingRect(text1)
        
        # ── BR Tag ──
        font_br = QFont("Bahnschrift", 30, QFont.Weight.Bold)
        fm2 = QFontMetrics(font_br)
        text2 = " BR"
        text2_rect = fm2.boundingRect(text2)
        
        total_w = text1_rect.width() + text2_rect.width()
        start_x = cx - (total_w / 2.0)
        base_y = cy - 4
        
        # Glow Drop-shadow
        p.setPen(QColor(0, 0, 0, 180))
        p.drawText(int(start_x + 2), int(base_y + 2), text1)
        p.drawText(int(start_x + text1_rect.width() + 2), int(base_y + 2), text2)
        
        # Principal (Branco/Neve)
        p.setPen(QColor(255, 255, 255))
        p.drawText(int(start_x), int(base_y), text1)
        
        # BR Color (Laranja Neon para destaque)
        p.setFont(font_br)
        p.setPen(QColor(255, 110, 26)) # Laranja
        p.drawText(int(start_x + text1_rect.width()), int(base_y), text2)
        
        # ── Miras / Corners de Foco Sniper na extremidade ──
        p.setPen(QPen(QColor(255, 255, 255, 80), 2.0))
        # Esquerda Lateral
        p.drawLine(int(start_x - 30), int(base_y - 12), int(start_x - 15), int(base_y - 12))
        p.drawLine(int(start_x - 30), int(base_y - 12), int(start_x - 30), int(base_y - 22))
        # Direita Lateral
        end_str = start_x + total_w
        p.drawLine(int(end_str + 15), int(base_y - 12), int(end_str + 30), int(base_y - 12))
        p.drawLine(int(end_str + 30), int(base_y - 12), int(end_str + 30), int(base_y - 22))

        # ── Subtítulo de Terminal (Legível) ──
        sub_str = "ULTIMATE MOD MANAGER - PT BR"
        f_sub = QFont("Segoe UI", 12, QFont.Weight.Bold)
        f_sub.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3.0)
        p.setFont(f_sub)
        sub_w = QFontMetrics(f_sub).boundingRect(sub_str).width()
        
        p.setPen(QColor(230, 230, 240, 240)) # Quase branco, legível
        p.drawText(int(cx - (sub_w / 2.0)), int(cy + 32), sub_str)
        p.end()


class _HeroArea(QWidget):
    launch_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAutoFillBackground(False)
        self.setMinimumHeight(280)
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        inner = QWidget()
        inner.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        inner.setAutoFillBackground(False)
        iv = QVBoxLayout(inner)
        iv.setContentsMargins(0, 28, 0, 24)
        iv.setSpacing(6)
        iv.setAlignment(Qt.AlignmentFlag.AlignCenter)

        header = _HeroHeaderPanel()
        iv.addWidget(header, alignment=Qt.AlignmentFlag.AlignCenter)
        iv.addSpacing(12)

        btn = _CinemaLaunchButton()
        btn.clicked.connect(self.launch_requested)
        iv.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
        v.addWidget(inner)

    # paintEvent removido — o ContentBackdrop global pinta o fundo de toda a janela,
    # incluindo a área do hero. O overlay local anterior criava uma caixa retangular
    # com borda dura entre o hero e os stat cards abaixo.


# ─────────────────────────────────────────────────────────────────────────────
# BOTÃO "INICIAR JOGO" — Glassmorphism Neon Dark  (nível Riot/Blizzard)
# Borda neon: Âmbar/Laranja (esq) → Rosa/Lilás (dir)
# Glow via blobs radiais difusos — sem faixas concêntricas (sem stroke loops)
# ─────────────────────────────────────────────────────────────────────────────
class _CinemaLaunchButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__("INICIAR JOGO", parent)
        self.setFixedSize(432, 76)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._hovered = False
        self._pix_normal: QPixmap | None = None
        self._pix_hover:  QPixmap | None = None

    def enterEvent(self, e):
        self._hovered = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        self.update()
        super().leaveEvent(e)

    def resizeEvent(self, e):
        self._pix_normal = None
        self._pix_hover  = None
        super().resizeEvent(e)

    def _render_pixmap(self, is_hover: bool) -> QPixmap:
        w, h = self.width(), self.height()
        pix = QPixmap(w, h)
        pix.fill(Qt.GlobalColor.transparent)

        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        gm = 1.45 if is_hover else 1.0

        # Retângulo elegante — RADIUS fixo 12px, nunca proporcional à altura
        PAD    = 14
        RADIUS = 12.0
        rect   = QRectF(PAD, PAD, w - 2 * PAD, h - 2 * PAD)
        cx     = rect.center().x()
        cy     = rect.center().y()

        path = QPainterPath()
        path.addRoundedRect(rect, RADIUS, RADIUS)

        # ── 1) GLOW EXTERNO — linear horizontal + halo de borda (sem cortes) ──
        # Técnica: QLinearGradient de 0→w nunca ultrapassa a borda do pixmap.
        # Âmbar no extremo esquerdo · transparente no centro · Rosa/Lilás à direita.

        def _a(base: int) -> int:
            return min(255, int(base * gm))



        # Halo de borda: radial pequeno ancorado NA borda do botão (≤ PAD de raio)
        # → fica 100% dentro do pixmap, impossível de cortar
        halo_r = PAD * 1.35   # 14 * 1.35 ≈ 19 px — cabe dentro do padding
        lh = QRadialGradient(rect.left(), cy, halo_r)
        lh.setColorAt(0.00, QColor(255, 110, 26, _a(165))) # Fogo Âmbar
        lh.setColorAt(0.50, QColor(229,  20, 20, _a(60)))  # Vermelho
        lh.setColorAt(1.00, QColor(  0,   0,  0, 0))
        p.fillRect(QRectF(0, 0, rect.left() + halo_r, h), QBrush(lh))

        rh = QRadialGradient(rect.right(), cy, halo_r)
        rh.setColorAt(0.00, QColor(112,  11, 20, _a(165))) # Sangue/Borgonha
        rh.setColorAt(0.50, QColor( 80,   5, 12, _a(55)))
        rh.setColorAt(1.00, QColor(  0,   0,   0, 0))
        p.fillRect(QRectF(rect.right() - halo_r, 0, halo_r + PAD, h), QBrush(rh))

        # ── 2) CORPO — vidro escuro com calor âmbar interno ───────────────────
        # Fundo base escuro translúcido — não é "buraco negro"
        p.fillPath(path, QBrush(QColor(8, 4, 14, 180 if is_hover else 162)))

        # Calor central radiante: Crimson Forge core
        warm = QRadialGradient(cx, cy, rect.width() * 0.44)
        warm.setColorAt(0.00, QColor(255, 90, 20, 58 if is_hover else 40))
        warm.setColorAt(0.25, QColor(220, 25, 15, 28 if is_hover else 18))
        warm.setColorAt(0.55, QColor(140, 10, 15, 12 if is_hover else  7))
        warm.setColorAt(0.82, QColor( 70,  5, 10,  4))
        warm.setColorAt(1.00, QColor(  0,  0,  0,  0))
        p.fillPath(path, QBrush(warm))

        # Glass sheen sutil no topo
        sheen_p = QPainterPath()
        sheen_p.addRoundedRect(
            QRectF(rect.left(), rect.top(), rect.width(), rect.height() * 0.44),
            RADIUS, RADIUS
        )
        sheen = QLinearGradient(0, rect.top(), 0, rect.top() + rect.height() * 0.44)
        sheen.setColorAt(0.00, QColor(255, 255, 255, 22 if is_hover else 13))
        sheen.setColorAt(0.50, QColor(255, 255, 255,  4))
        sheen.setColorAt(1.00, QColor(255, 255, 255,  0))
        p.fillPath(sheen_p, QBrush(sheen))

        # ── 3) BORDA NEON — linha horizontal fina 1.5 px ─────────────────────
        # Gradiente horizontal puro Crimson Forge
        bg = QLinearGradient(rect.left(), 0, rect.right(), 0)
        bg.setColorAt(0.00, QColor(255, 110,  26, _a(255)))   # âmbar brilhante
        bg.setColorAt(0.35, QColor(229,  20,  20, _a(255)))   # rubi central
        bg.setColorAt(0.65, QColor(229,  20,  20, _a(255)))   # rubi central
        bg.setColorAt(1.00, QColor(112,  11,  20, _a(255)))   # borgonha / sangue

        p.setPen(QPen(QBrush(bg), 1.5,
                      Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap,
                      Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

        # Aresta interna de vidro (highlight top → invisible bottom)
        rim_p = QPainterPath()
        rim_p.addRoundedRect(
            rect.adjusted(1.2, 1.2, -1.2, -1.2), RADIUS - 1.2, RADIUS - 1.2
        )
        rim_g = QLinearGradient(0, rect.top(), 0, rect.bottom())
        rim_g.setColorAt(0.00, QColor(255, 255, 255, 48 if is_hover else 28))
        rim_g.setColorAt(0.22, QColor(255, 255, 255,  5))
        rim_g.setColorAt(1.00, QColor(  0,   0,   0,  0))
        p.setPen(QPen(QBrush(rim_g), 0.7))
        p.drawPath(rim_p)

        # ── 4) TEXTO ─────────────────────────────────────────────────────────
        # Black/Heavy, 18pt, kerning 4.0 — texto domina o botão
        font = QFont("Bahnschrift", 18, QFont.Weight.Black)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 4.0)
        p.setFont(font)
        txt_r = rect.toRect()

        # Drop shadow escuro (1px deslocamento limpo)
        shr = QRect(txt_r)
        shr.translate(0, 1)
        p.setPen(QColor(0, 0, 0, 145))
        p.drawText(shr, Qt.AlignmentFlag.AlignCenter, self.text())

        # Texto principal branco puro
        p.setPen(QColor(255, 255, 255, 255))
        p.drawText(txt_r, Qt.AlignmentFlag.AlignCenter, self.text())

        p.end()
        return pix

    def paintEvent(self, _):
        if self._pix_normal is None:
            self._pix_normal = self._render_pixmap(False)
            self._pix_hover  = self._render_pixmap(True)

        p = QPainter(self)
        p.drawPixmap(0, 0, self._pix_hover if self._hovered else self._pix_normal)
        p.end()




# ─────────────────────────────────────────────────────────────────────────────
# STAT CARD — Card com mini-barras de progresso
# ─────────────────────────────────────────────────────────────────────────────
class _StatCard(QWidget):
    clicked = Signal()

    def __init__(self, key_type: str, title: str, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(200)
        self.setFixedHeight(158)
        self._hovered = False
        self._key_type = key_type  # "mods", "plugins", "sys"
        self._is_error = False

        v = QVBoxLayout(self)
        v.setContentsMargins(20, 16, 20, 14)
        v.setSpacing(0)

        hr = QHBoxLayout()
        hr.setSpacing(8)
        
        ttl = QLabel(title.upper())
        ttl.setStyleSheet("color:#A09CA8; font-family:'Segoe UI'; font-size:11px; font-weight:800; letter-spacing:1px; background:transparent;")
        hr.addWidget(ttl)
        hr.addStretch()
        v.addLayout(hr)
        v.addSpacing(16)

        self._val_lbl = QLabel("—")
        self._val_lbl.setStyleSheet(
            "color:#FFFFFF; font-family:'Bahnschrift','Consolas'; font-size:24px; font-weight:800;"
            "letter-spacing:1px; background:transparent;"
        )
        v.addWidget(self._val_lbl)

        self._sub_lbl = QLabel("—")
        self._sub_lbl.setStyleSheet("color:#8A8AAC; font-family:'Segoe UI'; font-size:12px; font-weight:600; letter-spacing:0.5px; background:transparent;")
        v.addWidget(self._sub_lbl)
        v.addStretch()

    def set_value(self, main: str, sub: str, is_error: bool = False):
        self._is_error = is_error
        if self._val_lbl.text() != main:
            self._val_lbl.setText(main)
        if self._sub_lbl.text() != sub:
            self._sub_lbl.setText(sub)
        self.update()

    def paintEvent(self, _):
        from PySide6.QtGui import QPolygonF
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w, h = self.width(), self.height()
        
        # Guarda critica: widget sem dimensões válidas, não pintar
        if w < 32 or h < 32:
            p.end()
            return
        
        # ── Cut-Corners (Chapara Chanfrada HUD) ──
        # Tira quinas no topo esquero e base direita
        cut = 16.0
        poly = QPolygonF([
            QPointF(cut, 0),
            QPointF(w, 0),
            QPointF(w, h - cut),
            QPointF(w - cut, h),
            QPointF(0, h),
            QPointF(0, cut)
        ])

        # Corpo escuro translúcido com gradiente diagonal
        bg = QLinearGradient(0, 0, w, h)
        if self._is_error:
            bg.setColorAt(0.0, QColor(40, 10, 15, 230 if self._hovered else 190))
            bg.setColorAt(1.0, QColor(10, 2, 4, 255 if self._hovered else 220))
        else:
            bg.setColorAt(0.0, QColor(15, 10, 20, 210 if self._hovered else 185))
            bg.setColorAt(1.0, QColor(6, 4, 10, 240 if self._hovered else 215))

        path = QPainterPath()
        path.addPolygon(poly)
        p.fillPath(path, QBrush(bg))

        # Aura reacionária (Glow Bottom)
        bot_glow = QRadialGradient(w * 0.5, h, w * 0.7)
        if self._is_error:
            bot_glow.setColorAt(0.0, QColor(255, 30, 30, 60 if self._hovered else 20))
        else:
            bot_glow.setColorAt(0.0, QColor(229, 20, 20, 45 if self._hovered else 0))
        bot_glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(bot_glow))
        p.drawPolygon(poly)

        # ── Linha de acento de status no topo ──
        acc = QLinearGradient(0, 0, w, 0)
        c_prim = QColor(229, 20, 20, 255) if not self._is_error else QColor(255, 40, 40, 255)
        c_sec  = QColor(255, 110, 26, 200) if not self._is_error else QColor(255, 255, 255, 200)
        
        acc.setColorAt(0.00, QColor(0, 0, 0, 0))
        acc.setColorAt(0.15, c_sec)
        acc.setColorAt(0.50, c_prim)
        acc.setColorAt(0.85, c_sec)
        acc.setColorAt(1.00, QColor(0, 0, 0, 0))
        
        # Desenha a fita do acento no topo da caixa (respeitando o chanfro)
        p.fillRect(QRectF(cut + 4, 0, w - (cut * 2) - 8, 2), QBrush(acc))

        # Borda poligonal fina
        border_clr = QColor(255, 40, 40, 90) if self._is_error else QColor(255, 255, 255, 22 if self._hovered else 10)
        p.setPen(QPen(border_clr, 1.2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPolygon(poly)

        # ── Cyber-Glyph Dotted Decorativo ──
        p.save()
        p.translate(w - 38, 28)
        
        glyph_clr = QColor(229, 20, 20, 160) if not self._is_error else QColor(255, 40, 40, 200)
        if self._hovered:
            p.setPen(QPen(QColor(255, 255, 255, 80), 1.5))
        else:
            p.setPen(QPen(glyph_clr, 1.5))
            
        p.setBrush(Qt.BrushStyle.NoBrush)

        if self._key_type == "mods":
            # Hex Core
            from math import cos, sin, pi
            q_poly = QPolygonF()
            for i in range(6):
                ang = i * (pi / 3)
                q_poly.append(QPointF(12 * cos(ang), 12 * sin(ang)))
            p.drawPolygon(q_poly)
            p.drawEllipse(QPointF(0,0), 3, 3)
            
        elif self._key_type == "plugins":
            # Triangle Matrix
            t_poly = QPolygonF([QPointF(0, -10), QPointF(10, 8), QPointF(-10, 8)])
            p.drawPolygon(t_poly)
            p.drawLine(0, -10, 0, 8)
            p.drawLine(-10, 8, 10, 8)

        elif self._key_type == "sys":
            # Shield Lock
            s_poly = QPolygonF([QPointF(-10, -10), QPointF(10, -10), QPointF(10, 2), QPointF(0, 12), QPointF(-10, 2)])
            p.drawPolygon(s_poly)
            if self._is_error:
                p.drawLine(-3, -3, 3, 3); p.drawLine(3, -3, -3, 3) # X
            else:
                p.drawLine(-3, 0, -1, 3); p.drawLine(-1, 3, 4, -4) # Checkmark
                
        p.restore()
        p.end()

    def enterEvent(self, event):
        self._hovered = True
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.unsetCursor()
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


# ─────────────────────────────────────────────────────────────────────────────
# MOD MINI CARD — linha compacta por mod
# ─────────────────────────────────────────────────────────────────────────────
_STATUS_BAR_COLORS = {
    "active":   QColor("#D44000"),
    "conflict": QColor("#E53935"),
    "pending":  QColor("#E67E22"),
    "disabled": QColor("#2A2038"),
}


class DashboardPanel(QWidget):
    """Aba Painel — hero com fundo cinematográfico + stat cards + mini-lista de mods."""
    launch_requested   = Signal()
    navigate_requested = Signal(str)
    revert_requested = Signal()

    def __init__(self, main_window):
        super().__init__()
        self._main_window = main_window

        # ASI cache (deve ser definido ANTES de _build_ui)
        self._asi_cache_plugins = 0
        self._asi_cache_status  = "Nenhum Loader Detectado"

        # _build_ui vai setar _card_mods, _card_plugins, _card_sys, _mini_cards_container
        self._build_ui()

        from PySide6.QtCore import QTimer
        QTimer.singleShot(200, self._scan_asi_async)

    # ── Construção da UI ───────────────────────────────────────────────────
    def _build_ui(self):
        # DashboardPanel é transparente — o backdrop vem do main_window (todas as páginas)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAutoFillBackground(False)

        inner_layout = QVBoxLayout(self)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(0)

        # Scroll area transparente
        # WA_TranslucentBackground + WA_NoSystemBackground no viewport garante que
        # a cadeia de transparência chegue até o ContentBackdrop (central widget).
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setAutoFillBackground(False)
        scroll.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        vp = scroll.viewport()
        vp.setAutoFillBackground(False)
        vp.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        vp.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        scroll.setStyleSheet("""
            QScrollArea { background:transparent; border:none; }
            QAbstractScrollArea > QWidget > QWidget { background: transparent; }
            QScrollBar:vertical { background:transparent; width:4px; }
            QScrollBar::handle:vertical { background:#2A1018; border-radius:2px; min-height:24px; }
            QScrollBar::handle:vertical:hover { background:#C0392B; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
        """)

        scroll_inner = QWidget()
        scroll_inner.setAutoFillBackground(False)
        scroll_inner.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        scroll_inner.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        scroll_inner.setStyleSheet("background:transparent;")
        sv = QVBoxLayout(scroll_inner)
        sv.setContentsMargins(0, 0, 0, 0)
        sv.setSpacing(0)

        # ── Hero ──
        hero = _HeroArea()
        hero.launch_requested.connect(self.launch_requested)
        sv.addWidget(hero)

        # ── Conteúdo abaixo do hero ──
        below = QWidget()
        below.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        below.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        below.setAutoFillBackground(False)
        below.setStyleSheet("background:transparent;")
        bv = QVBoxLayout(below)
        bv.setContentsMargins(40, 32, 40, 36)
        bv.setSpacing(0)

        # Stat cards
        cards_h = QHBoxLayout()
        cards_h.setSpacing(20)

        self._card_mods    = _StatCard("mods", "Mods Ativos")
        self._card_mods.clicked.connect(lambda: self.navigate_requested.emit("PAZ Mods"))
        
        self._card_plugins = _StatCard("plugins", "Plugins Carregados")
        self._card_plugins.clicked.connect(lambda: self.navigate_requested.emit("ASI Mods"))
        
        self._card_sys     = _StatCard("sys", "Proteção de Arquivos")
        self._card_sys.clicked.connect(self.revert_requested.emit)

        self._card_profiles = _StatCard("sys", "Banco de Perfis")
        self._card_profiles.clicked.connect(self._main_window._on_profiles)

        for card in (self._card_mods, self._card_plugins, self._card_sys, self._card_profiles):
            cards_h.addWidget(card)

        bv.addLayout(cards_h)
        bv.addSpacing(28)


        bv.addStretch()
        sv.addWidget(below)

        scroll.setWidget(scroll_inner)
        inner_layout.addWidget(scroll)

    # ── Atualização de dados ────────────────────────────────────────────────
    def showEvent(self, event):
        self.update_stats()
        super().showEvent(event)

    def update_stats(self):
        """Atualiza números dos stat cards. Rápido — chamado a cada toggle."""
        # Sem guard de visibilidade: o card de Proteção precisa atualizar mesmo
        # quando o dashboard não está ativo (ex: backup concluído em outra aba).
        mw = self._main_window

        # Coleta os totais rápidos
        total_mods = 0
        enabled_mods = 0
        if getattr(mw, "_mod_list_model", None):
            mods_data = mw._mod_list_model._mods
            total_mods = len(mods_data)
            enabled_mods = sum(1 for m in mods_data if m.get("enabled"))

        # ── Card 1: Mods — atualiza só os labels (O(1), sem criar widgets) ──
        if self._card_mods:
            self._card_mods.set_value(
                f"{enabled_mods} Ativos",
                f"De {total_mods} instalados"
            )

        # ── Card 2: Plugins ──
        if self._card_plugins:
            self._card_plugins.set_value(
                f"{self._asi_cache_plugins} Carregado(s)",
                self._asi_cache_status
            )

        # ── Card 3: Sistema ──
        if self._card_sys:
            sys_status = "Proteção Ativa"
            snap_status = "Cópia de Segurança OK"
            is_err = False
            if getattr(mw, "_snapshot", None):
                if not mw._snapshot.has_snapshot():
                    sys_status = "Atenção Necessária"
                    snap_status = "Sem Cópia de Segurança"
                    is_err = True
                elif getattr(mw, "_startup_context", {}).get("game_updated"):
                    sys_status = "Atenção Necessária"
                    snap_status = "Cópia Desatualizada"
                    is_err = True
            self._card_sys.set_value(sys_status, snap_status, is_err)

        # ── Card 4: Perfis ──
        if getattr(self, '_card_profiles', None):
            try:
                if mw._db and mw._db.connection:
                    prof_qtd = len(mw._db.connection.execute("SELECT id FROM profiles").fetchall())
                    if prof_qtd > 0:
                        self._card_profiles.set_value(f"{prof_qtd} Perfis", "Salvos no Banco", is_error=False)
                    else:
                        self._card_profiles.set_value("Criar Perfil", "Gestão de Perfils", is_error=False)
                else:
                    self._card_profiles.set_value("Offline", "Banco não lido", is_error=True)
            except Exception:
                self._card_profiles.set_value("Erro", "Falha de Leitura", is_error=True)
    def _scan_asi_async(self):
        """Scan rápido de ASI — roda no main thread mas é O(1) (apenas stat de arquivos)."""
        plugins_loaded = 0
        asi_status = "Nenhum Loader Detectado"
        game_dir = getattr(self._main_window, "_game_dir", None)
        if game_dir:
            try:
                bin_dir = game_dir / "bin64"
                if (bin_dir / "winmm.dll").exists() or (bin_dir / "version.dll").exists():
                    asi_status = "Loader Detectado"
                    plugins_loaded = sum(1 for p in bin_dir.glob("*.asi") if p.is_file())
            except OSError:
                pass
        self._asi_cache_plugins = plugins_loaded
        self._asi_cache_status  = asi_status
        if self._card_plugins:
            self._card_plugins.set_value(
                f"{plugins_loaded} Carregado(s)",
                asi_status
            )

