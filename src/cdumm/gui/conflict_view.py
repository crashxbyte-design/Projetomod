import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QColor, QStandardItem, QStandardItemModel, QPainter, QPainterPath, QFont, QPen
from PySide6.QtWidgets import QHeaderView, QMenu, QTreeView, QVBoxLayout, QWidget, QStyledItemDelegate, QStyle

from cdumm.engine.conflict_detector import Conflict

logger = logging.getLogger(__name__)

LEVEL_COLORS = {
    "papgt": QColor("#B08B7A"),     # Amber-cinzento — seguro / auto-gerenciado
    "paz": QColor("#FF6E1A"),       # Laranja Neon — alerta / compatível
    "byte_range": QColor("#E51414"),  # Carmesim brilhante — conflito real
}

LEVEL_LABELS = {
    "papgt": "Gerenciado automaticamente (PAPGT)",
    "paz": "Compatível (intervalos de bytes diferentes)",
    "byte_range": "Resolvido (ordem de carregamento)",
}

# Data role for storing mod IDs on tree items
MOD_A_ID_ROLE = Qt.ItemDataRole.UserRole + 1
MOD_B_ID_ROLE = Qt.ItemDataRole.UserRole + 2
WINNER_ID_ROLE = Qt.ItemDataRole.UserRole + 3


class ConflictDelegate(QStyledItemDelegate):
    """Custom delegate para pintar os emblemas visuais na tabela de árvore e remover o cinza padrão."""
    
    def paint(self, painter: QPainter, option, index) -> None:
        text = index.data(Qt.ItemDataRole.DisplayRole)
        
        # 1. Background Hover / Selection
        is_sel = bool(option.state & QStyle.StateFlag.State_Selected)
        if is_sel:
            painter.fillRect(option.rect, QColor(229, 20, 20, 30)) # Crimson Faint
            
        # 2. Desenhar a Pílula de "Vencedor" se for a string mestre
        if text and isinstance(text, str) and text.startswith("Vencedor: "):
            winner_name = text.replace("Vencedor: ", "").strip()
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            rect = option.rect.adjusted(4, 4, -4, -4)
            # Proteção crítica: Se as dimensões forem negativas (painel contraído ou calculando),
            # o QPainterPath.addRoundedRect dá crash C++ (assert exception).
            if rect.width() > 0 and rect.height() > 0:
                badge_path = QPainterPath()
                badge_path.addRoundedRect(rect, rect.height() / 2, rect.height() / 2)
                
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(255, 110, 26, 35)) # Amber fumaça
                painter.drawPath(badge_path)
                
                painter.setPen(QColor(255, 110, 26, 120))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPath(badge_path)
                
                painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                painter.setPen(QColor("#FF8B3D")) # Neon Orange
                painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter, f"🏆 VENCEDOR: {winner_name.upper()}")
            
            painter.restore()
            return
            
        super().paint(painter, option, index)


class ConflictView(QWidget):
    """Tree view displaying mod conflicts grouped by mod pair → file → details."""

    winner_changed = Signal(int)  # emits mod_id that was set as winner
    collapse_toggled = Signal(bool) # Emite True quando retraído, False quando expandido

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── HEADER COLLAPSIBLE OTIMIZADO ──
        self._header = QWidget()
        self._header.setStyleSheet("""
            QWidget { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(28, 12, 14, 255), stop:1 rgba(18, 8, 10, 255));
                border-top: 2px solid #E51414;
                border-bottom: 1px solid rgba(229, 20, 20, 0.4);
            }
        """)
        from PySide6.QtWidgets import QHBoxLayout
        h_layout = QHBoxLayout(self._header)
        h_layout.setContentsMargins(12, 4, 12, 4)
        
        from PySide6.QtWidgets import QLabel
        title = QLabel("CONFLITOS NA ÁRVORE DE MODS")
        title.setStyleSheet("color: #FF6E1A; font-family: 'Bahnschrift'; font-size: 10px; font-weight: bold; letter-spacing: 0.5px; background: transparent; border: none;")
        h_layout.addWidget(title)
        
        h_layout.addStretch()
        
        from cdumm.gui.premium_buttons import PremiumNeonButton
        self._btn_toggle = PremiumNeonButton("MOSTRAR PAINEL")
        self._btn_toggle.setFixedHeight(22)
        self._btn_toggle.clicked.connect(self._toggle_collapse)
        h_layout.addWidget(self._btn_toggle)
        
        layout.addWidget(self._header)

        self._tree = QTreeView()
        self._tree.setObjectName("conflictTree")
        self._tree.setHeaderHidden(False)
        self._tree.setAlternatingRowColors(False) # Turn off generic alternating colours
        
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)
        
        # Apply the layout CSS for Crimson Forge framework
        self._tree.setStyleSheet("""
            QTreeView {
                background-color: #110A0C;
                color: #D6D6E0;
                border: none;
                outline: none;
            }
            QTreeView::item {
                padding: 6px;
                border-bottom: 1px solid #1E1214;
            }
            QTreeView::item:hover {
                background-color: rgba(229, 20, 20, 0.05);
            }
            QHeaderView::section {
                background-color: #160D10;
                color: #FFFFFF;
                border: none;
                border-bottom: 2px solid #E51414;
                padding: 8px;
                font-weight: bold;
                text-transform: uppercase;
            }
            QScrollBar:horizontal {
                height: 10px;
                background: #110A0C;
            }
            QScrollBar::handle:horizontal {
                background: #2E1B1F;
                border-radius: 4px;
            }
            QScrollBar:vertical {
                width: 10px;
                background: #110A0C;
            }
            QScrollBar::handle:vertical {
                background: #2E1B1F;
                border-radius: 4px;
            }
        """)

        # Injecting the Custom Display Painter
        self._delegate = ConflictDelegate(self._tree)
        self._tree.setItemDelegate(self._delegate)

        self._model = QStandardItemModel()
        self._model.setHorizontalHeaderLabels(["Grupos em Conflito", "Severidade", "Condição de Resolução"])
        self._tree.setModel(self._model)
        self._tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self._tree)
        
        # Padrão: Painel oculto na inicialização
        self._tree.hide()

    def update_conflicts(self, conflicts: list[Conflict]) -> None:
        """Rebuild the tree with the current conflict list."""
        self._model.removeRows(0, self._model.rowCount())

        if not conflicts:
            empty = QStandardItem("  Nenhum conflito letal detectado nesta listagem de mods")
            empty.setForeground(QColor("#B08B7A")) # Faded alert
            self._model.appendRow([empty, QStandardItem(""), QStandardItem("")])
            return

        # Group by mod pair
        pairs: dict[tuple[int, int], list[Conflict]] = {}
        for c in conflicts:
            key = (min(c.mod_a_id, c.mod_b_id), max(c.mod_a_id, c.mod_b_id))
            pairs.setdefault(key, []).append(c)

        for (_, _), pair_conflicts in pairs.items():
            first = pair_conflicts[0]
            # Determine worst level for this pair
            worst = "papgt"
            for c in pair_conflicts:
                if c.level == "byte_range":
                    worst = "byte_range"
                    break
                if c.level == "paz":
                    worst = "paz"

            # Node 1: Main conflict folder summary (The thick root node)
            pair_item = QStandardItem(f"  {first.mod_a_name}  ↔  {first.mod_b_name}")
            
            # Using custom UI font for clarity
            font_title = QFont("Segoe UI", 10, QFont.Weight.Bold)
            pair_item.setFont(font_title)
            
            pair_item.setForeground(LEVEL_COLORS.get(worst, QColor("#E51414")))
            pair_item.setData(first.mod_a_id, MOD_A_ID_ROLE)
            pair_item.setData(first.mod_b_id, MOD_B_ID_ROLE)
            
            level_item = QStandardItem(LEVEL_LABELS.get(worst, worst))
            level_item.setFont(QFont("Segoe UI", 9))
            
            # Show winner in the detail column for byte_range conflicts
            winner = first.winner_name if worst == "byte_range" and first.winner_name else ""
            detail_text = f"Vencedor: {winner}" if winner else f"  {len(pair_conflicts)} intervalo(s) de arquivo analisado"
            detail_item = QStandardItem(detail_text)
            
            if winner:
                detail_item.setForeground(QColor("#FF6E1A")) # Fallback
            else:
                detail_item.setForeground(QColor("#7A7890"))

            for c in pair_conflicts:
                file_item = QStandardItem(c.file_path)
                file_item.setData(c.mod_a_id, MOD_A_ID_ROLE)
                file_item.setData(c.mod_b_id, MOD_B_ID_ROLE)
                file_item.setData(c.winner_id, WINNER_ID_ROLE)
                
                file_level = QStandardItem(LEVEL_LABELS.get(c.level, c.level))
                file_level.setForeground(LEVEL_COLORS.get(c.level, QColor("#999")))
                
                file_detail = QStandardItem(c.explanation)
                file_detail.setForeground(QColor("#A09CA8")) # Subtle child detail color
                
                pair_item.appendRow([file_item, file_level, file_detail])

            self._model.appendRow([pair_item, level_item, detail_item])

        self._tree.expandAll()

    def _toggle_collapse(self):
        is_hiding = self._tree.isVisible()
        if is_hiding:
            self._tree.hide()
            self._btn_toggle.setText("MOSTRAR PAINEL")
        else:
            self._tree.show()
            self._btn_toggle.setText("ESCONDER PAINEL")
            
        self.collapse_toggled.emit(is_hiding)

    def _show_context_menu(self, pos) -> None:
        """Show right-click menu with Set Winner options."""
        index = self._tree.indexAt(pos)
        if not index.isValid():
            return

        # Get the first column item (where mod IDs are stored)
        item = self._model.itemFromIndex(index.siblingAtColumn(0))
        if not item:
            return

        mod_a_id = item.data(MOD_A_ID_ROLE)
        mod_b_id = item.data(MOD_B_ID_ROLE)
        if mod_a_id is None or mod_b_id is None:
            return

        # Look up mod names from the tree
        mod_a_name = None
        mod_b_name = None
        # Walk up to pair level to get names
        parent = item.parent() or item
        text = parent.text().replace("  ", "").strip() # Removed padded spaces for title
        if "↔" in text:
            parts = text.split("↔")
            mod_a_name = parts[0].strip()
            mod_b_name = parts[1].strip() if len(parts) > 1 else None

        menu = QMenu(self)
        
        menu.setStyleSheet("""
            QMenu {
                background-color: #110A0C;
                border: 1px solid #E51414;
                color: #FFFFFF;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 24px;
                font-family: 'Segoe UI', sans-serif;
                font-weight: bold;
            }
            QMenu::item:selected {
                background-color: #E51414;
                color: #FFFFFF;
            }
        """)

        if mod_a_name:
            action_a = QAction(f"★ Definir \"{mod_a_name}\" como vencedor máximo", self)
            action_a.triggered.connect(lambda: self.winner_changed.emit(mod_a_id))
            menu.addAction(action_a)
        if mod_b_name:
            action_b = QAction(f"★ Definir \"{mod_b_name}\" como vencedor máximo", self)
            action_b.triggered.connect(lambda: self.winner_changed.emit(mod_b_id))
            menu.addAction(action_b)

        if not menu.isEmpty():
            menu.exec(self._tree.viewport().mapToGlobal(pos))
