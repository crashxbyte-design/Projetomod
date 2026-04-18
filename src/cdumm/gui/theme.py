"""CDUMM Application Theme — Elite Dark Crimson."""

# ── Colour Palette ─────────────────────────────────────────────────────────────
BG_DEEP      = "#080A0C"       # deepest background
BG_DARK      = "#0C0E10"       # main content bg
BG_MID       = "#0E0A09"       # sidebar, headers
BG_ELEVATED  = "#151213"       # cards, elevated surfaces
BG_HOVER     = "#1C1518"       # hover states
BORDER       = "#26181A"       # strong borders
BORDER_DIM   = "#1A1012"       # subtle borders
TEXT_BRIGHT  = "#F4F4FC"       # headings, important text
TEXT_PRIMARY = "#9898B0"       # body text
TEXT_SECONDARY = "#565668"     # labels
TEXT_MUTED   = "#303240"       # disabled
ACCENT       = "#C0392B"       # crimson primary
ACCENT_HOVER = "#E53935"
ACCENT_DIM   = "#7D2A22"
GREEN        = "#27AE60"
GREEN_HOVER  = "#2ECC71"
RED          = "#E53935"
RED_HOVER    = "#FF5252"
ORANGE       = "#E67E22"
SELECTION    = "#3B1010"       # list/table selection bg

STYLESHEET = f"""
/* ── Base ── */
QMainWindow {{
    background-color: {BG_DARK};
}}
/* ── Global base — sem background para não bloquear o ContentBackdrop ── */
QWidget {{
    color: {TEXT_PRIMARY};
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}}
QPushButton {{
    background: rgba(255,255,255,0.04);
    border: 1px solid {BORDER};
    border-radius: 6px;
    color: {TEXT_PRIMARY};
    font-size: 12px;
    font-weight: 600;
    padding: 5px 14px;
}}
QPushButton:hover {{
    background: rgba(255,255,255,0.07);
    border-color: #3A2020;
    color: {TEXT_BRIGHT};
}}
QPushButton:pressed {{
    background: rgba(255,255,255,0.02);
}}
QLineEdit {{
    background: {BG_DARK};
    border: 1px solid {BORDER};
    border-radius: 6px;
    color: {TEXT_PRIMARY};
    padding: 4px 10px;
    font-size: 12px;
    selection-background-color: {ACCENT_DIM};
}}
QLineEdit:focus {{
    border-color: {ACCENT};
}}
QComboBox {{
    background: {BG_DARK};
    border: 1px solid {BORDER};
    border-radius: 6px;
    color: {TEXT_PRIMARY};
    padding: 4px 10px;
    font-size: 12px;
}}
QComboBox:focus {{
    border-color: {ACCENT};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

/* ── Sidebar ── */
QFrame#sidebar {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {BG_MID}, stop:1 #060406);
    border-right: 1px solid {BORDER};
}}
QFrame#sidebar QLabel#sidebarTitle {{
    color: {TEXT_BRIGHT};
    font-size: 16px;
    font-weight: 800;
    padding: 4px;
    letter-spacing: 1px;
}}
QFrame#sidebar QPushButton {{
    background: transparent;
    border: none;
    border-radius: 0;
    color: #8A8A9E;
    padding: 10px 18px; /* Compacted left indent to match logo */
    font-size: 11px;
    font-weight: 500;
    min-height: 34px; /* Reduced massiveness */
    text-align: left;
    letter-spacing: 0.2px;
}}
QFrame#sidebar QPushButton:hover {{
    background: rgba(255,255,255,0.03); /* very soft glow */
    color: {TEXT_BRIGHT};
}}
QFrame#sidebar QPushButton:checked {{
    background: rgba(192, 57, 43, 0.10);
    color: #FFFFFF;
    border: none;
    border-left: 3px solid {ACCENT};
    border-radius: 0;
    margin: 0;
    padding-left: 15px;  /* compensate for 3px border */
    font-weight: 800;
    letter-spacing: 0px;
}}
QFrame#sidebar QPushButton:checked:hover {{
    background: rgba(192, 57, 43, 0.16);
    color: #FFFFFF;
    border: none;
    border-left: 3px solid {ACCENT_HOVER};
    border-radius: 0;
    margin: 0;
    padding-left: 15px;
    font-weight: 800;
}}
/* navActive dynamic property (same as :checked, for unpolish/polish cycle) */
QFrame#sidebar QPushButton[navActive="true"] {{
    background: rgba(192, 57, 43, 0.10);
    border-left: 3px solid {ACCENT};
    padding-left: 15px;
}}
QFrame#sidebarSep {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 transparent,
        stop:0.2 {ACCENT_DIM},
        stop:0.5 {ACCENT},
        stop:0.8 {ACCENT_DIM},
        stop:1 transparent);
    border: none;
}}
/* ── Sidebar/content vertical separator ── */
QFrame#contentSep {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 transparent,
        stop:0.3 {ACCENT_DIM},
        stop:0.7 {ACCENT_DIM},
        stop:1 transparent);
    border: none;
    min-width: 1px;
    max-width: 1px;
}}
/* ── Sidebar bottom launch button ── */
QPushButton#sidebarLaunchBtn {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {ACCENT}, stop:1 {ACCENT_DIM});
    color: #FFFFFF;
    border: none;
    border-top: 1px solid rgba(255,100,80,0.25);
    border-radius: 0;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 1.5px;
    padding: 0 18px;
    margin: 0 12px;
    border-radius: 8px;
}}
QPushButton#sidebarLaunchBtn:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {ACCENT_HOVER}, stop:1 {ACCENT});
}}
QPushButton#sidebarLaunchBtn:pressed {{
    background: {ACCENT_DIM};
}}

QLabel#sidebarVersion {{
    color: #686878;
    font-size: 10px;
    font-weight: 600;
    background: #16121A;
    border: 1px solid #22162A;
    border-radius: 12px;
    padding: 4px 12px;
    margin: 0 18px 0 18px;
}}

/* ── Status Bar ── */
QStatusBar {{
    background: {BG_MID};
    color: {TEXT_MUTED};
    font-size: 11px;
    border-top: 1px solid {BORDER};
    padding: 0 10px;
}}
QStatusBar::item {{
    border: none;
}}

/* ── Secondary page titles (Tools, About, etc.) ── */
QLabel#toolsHeader {{
    color: {TEXT_BRIGHT};
    font-size: 15px;
    font-weight: 800;
    letter-spacing: 0.5px;
    padding-bottom: 6px;
    border-bottom: 1px solid {BORDER};
    margin-bottom: 4px;
}}

/* ── Section Header ── */
QFrame#sectionHeader {{
    background: rgba(8, 6, 12, 0.82);
    border-bottom: 1px solid {BORDER};
    border-top: 2px solid {ACCENT};
}}
QLabel#headerTitle {{
    color: {TEXT_BRIGHT};
    font-family: "Bahnschrift", "Segoe UI", sans-serif;
    font-size: 20px;
    font-weight: 800;
    letter-spacing: 2px;
    background: transparent;
}}
QLabel#headerStats {{
    color: {TEXT_MUTED};
    font-size: 11px;
    letter-spacing: 0.3px;
    background: transparent;
}}
/* ── Header stat badges ── */
QLabel#statBadge {{
    background: rgba(192,57,43,0.10);
    border: 1px solid rgba(192,57,43,0.25);
    border-radius: 9px;
    color: {TEXT_PRIMARY};
    font-size: 10px;
    font-weight: 700;
    padding: 1px 8px;
    letter-spacing: 0.3px;
}}

/* ── Header action buttons (Etapa 2) ── */
QPushButton#btnImportar {{
    background: rgba(255,255,255,0.05);
    border: 1px solid {BORDER};
    border-radius: 8px;
    color: {TEXT_PRIMARY};
    font-size: 12px;
    font-weight: 600;
    padding: 0 16px;
    min-width: 90px;
}}
QPushButton#btnImportar:hover {{
    background: rgba(255,255,255,0.09);
    border-color: {TEXT_SECONDARY};
    color: {TEXT_BRIGHT};
}}
QPushButton#btnImportar:pressed {{
    background: rgba(255,255,255,0.04);
}}
QPushButton#btnSincronizar {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {ACCENT}, stop:1 {ACCENT_DIM});
    border: none;
    border-radius: 8px;
    color: {TEXT_BRIGHT};
    font-size: 12px;
    font-weight: 700;
    padding: 0 18px;
    min-width: 90px;
}}
QPushButton#btnSincronizar:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {ACCENT_HOVER}, stop:1 {ACCENT});
}}
QPushButton#btnSincronizar:pressed {{
    background: {ACCENT_DIM};
}}
QPushButton#btnJogar {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {GREEN}, stop:1 #1A6E3C);
    border: none;
    border-radius: 8px;
    color: white;
    font-size: 12px;
    font-weight: 700;
    padding: 0 18px;
    min-width: 120px;
}}
QPushButton#btnJogar:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {GREEN_HOVER}, stop:1 {GREEN});
}}
QPushButton#btnJogar:pressed {{
    background: #1A6E3C;
}}

/* ── Action Bar (revert zone) ── */
QFrame#actionBar {{
    background: rgba(5, 3, 8, 0.88);
    border-top: none;
}}
QFrame#actionBarSep {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 transparent,
        stop:0.15 {BORDER},
        stop:0.5 {ACCENT_DIM},
        stop:0.85 {BORDER},
        stop:1 transparent);
    border: none;
    min-height: 1px;
    max-height: 1px;
}}
QLabel#actionBarHint {{
    color: {TEXT_MUTED};
    font-size: 10px;
    letter-spacing: 0.2px;
    background: transparent;
}}
QPushButton#applyBtn {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {ACCENT}, stop:1 {ACCENT_DIM});
    border: none;
    border-radius: 8px;
    color: {TEXT_BRIGHT};
    font-weight: 700;
    font-size: 14px;
    padding: 10px 32px;
}}
QPushButton#applyBtn:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {ACCENT_HOVER}, stop:1 {ACCENT});
}}
QPushButton#launchBtn {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {GREEN}, stop:1 #1A6E3C);
    border: none;
    border-radius: 8px;
    color: white;
    font-weight: 700;
    font-size: 14px;
    padding: 10px 32px;
}}
QPushButton#launchBtn:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {GREEN_HOVER}, stop:1 {GREEN});
}}
QPushButton#revertBtn {{
    background: transparent;
    border: 1px solid {ACCENT};
    border-radius: 8px;
    color: {ACCENT};
    padding: 8px 18px;
    font-size: 12px;
    font-weight: 700;
}}
QPushButton#revertBtn:hover {{
    background: rgba(192, 57, 43, 0.18);
    color: {ACCENT_HOVER};
    border-color: {ACCENT_HOVER};
}}
QPushButton#revertBtn:pressed {{
    background: rgba(192, 57, 43, 0.30);
}}

/* ── Table — Elite Neon Design ── */
QTableView#modTable, QTableView {{
    background-color: #0D0B0E;
    alternate-background-color: #111015;
    border: 1px solid {BORDER};
    border-radius: 10px;
    gridline-color: transparent;
    selection-background-color: transparent;
    selection-color: {TEXT_BRIGHT};
    outline: none;
    show-decoration-selected: 1;
}}
QTableView#modTable::item, QTableView::item {{
    padding: 10px 14px;
    border-bottom: 1px solid rgba(255,255,255,0.025);
    color: {TEXT_PRIMARY};
}}
QTableView#modTable::item:alternate, QTableView::item:alternate {{
    background: #111015;
}}
QTableView#modTable::item:hover, QTableView::item:hover {{
    background: #1A161E;
    color: {TEXT_BRIGHT};
    border-left: 2px solid rgba(192,57,43,0.35);
}}
QTableView#modTable::item:selected, QTableView::item:selected {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(192,57,43,0.30), stop:1 rgba(192,57,43,0.08));
    color: #F5D0CC;
    border-left: 2px solid {ACCENT};
    border-bottom: 1px solid rgba(192,57,43,0.20);
}}
QTableView#modTable::item:selected:hover, QTableView::item:selected:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(229,57,53,0.38), stop:1 rgba(192,57,43,0.12));
    color: #FFFFFF;
    border-left: 2px solid {ACCENT_HOVER};
}}
/* ── Header — Dark Minimal with Accent Line ── */
QHeaderView {{
    background: transparent;
}}
QHeaderView::section {{
    background: #0A0809;
    color: #5C5C7A;
    border: none;
    border-bottom: 2px solid {ACCENT_DIM};
    border-right: 1px solid rgba(255,255,255,0.03);
    padding: 10px 14px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.2px;
    text-transform: uppercase;
}}
QHeaderView::section:first {{
    border-top-left-radius: 10px;
}}
QHeaderView::section:last {{
    border-top-right-radius: 10px;
    border-right: none;
}}
QHeaderView::section:hover {{
    background: #110D10;
    color: {TEXT_BRIGHT};
    border-bottom: 2px solid {ACCENT};
}}
QHeaderView::section:checked {{
    background: rgba(192,57,43,0.12);
    color: #FF8070;
}}

/* ── Buttons (general) ── */
QPushButton {{
    background: {BG_ELEVATED};
    border: 1px solid {BORDER};
    border-radius: 8px;
    color: {TEXT_PRIMARY};
    padding: 8px 18px;
    font-size: 12px;
    font-weight: 500;
}}
QPushButton:hover {{
    background: {BG_HOVER};
    border-color: {BORDER};
    color: {TEXT_BRIGHT};
}}
QPushButton:pressed {{
    background: {SELECTION};
}}
QPushButton:disabled {{
    background: {BG_DARK};
    color: {TEXT_MUTED};
    border-color: {BORDER_DIM};
}}

/* ── Splitter ── */
QSplitter::handle {{
    background: {BORDER};
    height: 3px;
}}
QSplitter::handle:hover {{
    background: {ACCENT};
}}

/* ── ScrollBar ── */
QScrollBar:vertical {{
    background: {BG_DARK};
    width: 6px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {ACCENT};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: {BG_DARK};
    height: 6px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER};
    border-radius: 3px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {ACCENT};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ── Status Bar ── */
QStatusBar {{
    background: {BG_DEEP};
    border-top: 1px solid {BORDER_DIM};
    color: {TEXT_SECONDARY};
    font-size: 11px;
}}
QStatusBar QLabel {{
    color: {TEXT_SECONDARY};
    font-size: 11px;
    padding: 0 6px;
}}

/* ── Dialog / MessageBox ── */
QDialog {{
    background: {BG_DARK};
}}
QMessageBox {{
    background: {BG_MID};
}}
QMessageBox QLabel {{
    color: {TEXT_BRIGHT};
    font-size: 13px;
}}
QMessageBox QPushButton {{
    min-width: 80px;
}}

/* ── Input ── */
QLineEdit, QTextEdit {{
    background: {BG_DEEP};
    border: 1px solid {BORDER};
    border-radius: 8px;
    color: {TEXT_BRIGHT};
    padding: 7px 10px;
    selection-background-color: {SELECTION};
}}
QLineEdit:focus, QTextEdit:focus {{
    border-color: {ACCENT};
}}

/* ── Menu ── */
QMenu {{
    background: {BG_MID};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 6px;
}}
QMenu::item {{
    padding: 8px 28px 8px 16px;
    border-radius: 6px;
    color: {TEXT_PRIMARY};
}}
QMenu::item:selected {{
    background: {SELECTION};
    color: {TEXT_BRIGHT};
}}
QMenu::separator {{
    height: 1px;
    background: {BORDER};
    margin: 4px 8px;
}}

/* ── ToolTip ── */
QToolTip {{
    background: {BG_ELEVATED};
    border: 1px solid {BORDER};
    border-radius: 4px;
    color: {TEXT_BRIGHT};
    padding: 6px 10px;
    font-size: 12px;
}}

/* ── Progress ── */
QProgressBar {{
    background: {BG_DEEP};
    border: none;
    border-radius: 4px;
    height: 6px;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {ACCENT}, stop:1 {ACCENT_HOVER});
    border-radius: 4px;
}}

/* ── List / Tree (generic) ── */
QListWidget, QTreeWidget {{
    background: {BG_DARK};
    border: 1px solid {BORDER};
    border-radius: 8px;
    outline: none;
}}
QListWidget::item, QTreeWidget::item {{
    padding: 7px 12px;
    border-bottom: 1px solid {BORDER_DIM};
    color: {TEXT_PRIMARY};
}}
QListWidget::item:hover, QTreeWidget::item:hover {{
    background: {BG_ELEVATED};
}}
QListWidget::item:selected, QTreeWidget::item:selected {{
    background: {SELECTION};
    color: {TEXT_BRIGHT};
}}

/* ── GroupBox ── */
QGroupBox {{
    background: {BG_ELEVATED};
    border: 1px solid {BORDER};
    border-radius: 8px;
    margin-top: 16px;
    padding-top: 20px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 8px;
    color: {TEXT_SECONDARY};
    font-weight: 600;
}}

/* ── ComboBox ── */
QComboBox {{
    background: {BG_ELEVATED};
    border: 1px solid {BORDER};
    border-radius: 8px;
    color: {TEXT_BRIGHT};
    padding: 6px 10px;
}}
QComboBox QAbstractItemView {{
    background: {BG_MID};
    border: 1px solid {BORDER};
    selection-background-color: {SELECTION};
}}

/* ── CheckBox ── */
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {BORDER};
    border-radius: 5px;
    background: {BG_DEEP};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
}}
QCheckBox::indicator:hover {{
    border-color: {ACCENT};
}}

/* ── Tools page label ── */
QLabel#toolsHeader {{
    color: {TEXT_BRIGHT};
    font-size: 18px;
    font-weight: 700;
    padding-bottom: 8px;
    min-height: 28px;
}}

QPushButton#btnImportar {{
    background: transparent;
    color: {TEXT_SECONDARY};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.3px;
}}
QPushButton#btnImportar:hover {{
    background: rgba(255,255,255,0.04);
    border-color: #3A2828;
    color: {TEXT_BRIGHT};
}}
QPushButton#btnSincronizar {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {ACCENT}, stop:1 {ACCENT_DIM});
    color: #FFFFFF;
    border: none;
    border-top: 1px solid rgba(255,100,80,0.30);
    border-radius: 8px;
    padding: 6px 20px;
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 0.8px;
}}
QPushButton#btnSincronizar:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {ACCENT_HOVER}, stop:1 {ACCENT});
}}
QPushButton#btnSincronizar:pressed {{
    background: {ACCENT_DIM};
}}
QPushButton#btnJogar {{
    background: transparent;
    color: {TEXT_BRIGHT};
    border: 1px solid {ACCENT_DIM};
    border-radius: 8px;
    padding: 6px 20px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1.2px;
}}
QPushButton#btnJogar:hover {{
    background: rgba(192,57,43,0.12);
    border-color: {ACCENT};
    color: #FFFFFF;
}}
QPushButton#btnJogar:pressed {{
    background: rgba(192,57,43,0.20);
}}

/* ── Mod card list override — Etapa 3 ── */
QListWidget#modCardList {{
    background: transparent;
    border: none;
    outline: none;
}}
QListWidget#modCardList::item {{
    background: transparent;
    border: none;
    padding: 0;
}}
QListWidget#modCardList::item:selected {{
    background: transparent;
}}

/* ── Conflict tree ── */
QTreeView#conflictTree {{
    background: {BG_DARK};
    alternate-background-color: {BG_ELEVATED};
    border: none;
    border-top: 1px solid {BORDER};
    outline: none;
    color: {TEXT_PRIMARY};
    font-size: 12px;
}}
QTreeView#conflictTree::item {{
    padding: 5px 8px;
    border: none;
}}
QTreeView#conflictTree::item:hover {{
    background: {BG_ELEVATED};
    color: {TEXT_BRIGHT};
}}
QTreeView#conflictTree::item:selected {{
    background: {SELECTION};
    color: {TEXT_BRIGHT};
}}
QTreeView#conflictTree QHeaderView::section {{
    background: {BG_MID};
    color: {TEXT_SECONDARY};
    border: none;
    border-bottom: 1px solid {BORDER};
    border-right: 1px solid {BORDER_DIM};
    padding: 7px 10px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.5px;
}}
QTreeView#conflictTree::branch {{
    background: transparent;
}}
QTreeView#conflictTree::branch:has-children:!has-siblings:closed,
QTreeView#conflictTree::branch:closed:has-children:has-siblings {{
    color: {TEXT_SECONDARY};
}}

/* ── Mod list hint ── */
QLabel#modHint {{
    color: {TEXT_MUTED};
    font-size: 11px;
    padding: 5px 12px;
    background: {BG_DEEP};
    border-top: 1px solid {BORDER_DIM};
    letter-spacing: 0.2px;
}}

/* ── Mod list container (QListView area) ── */
QListView {{
    background: transparent;
    border: none;
    outline: none;
}}

/* ── Toggle All — botão de destaque (estilo outlined crimson) ── */
QPushButton#btnToggleAll {{
    background: transparent;
    color: {ACCENT};
    border: 1.5px solid {ACCENT};
    border-radius: 8px;
    padding: 0 18px;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 1px;
}}
QPushButton#btnToggleAll:hover {{
    background: rgba(192,57,43,0.14);
    border-color: {ACCENT_HOVER};
    color: {ACCENT_HOVER};
}}
QPushButton#btnToggleAll:pressed {{
    background: rgba(192,57,43,0.28);
    border-color: {ACCENT};
}}

/* ── QScrollBar Global Protection ── */
QScrollBar:vertical {{
    border: none;
    background: transparent;
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: rgba(255,255,255,0.06);
    min-height: 20px;
    border-radius: 5px;
    margin: 2px;
}}
QScrollBar::handle:vertical:hover {{
    background: rgba(192,57,43,0.40); /* Crimson glow on hover */
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    border: none;
    background: none;
    height: 0px;
}}
QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical, QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

QScrollBar:horizontal {{
    border: none;
    background: transparent;
    height: 10px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: rgba(255,255,255,0.06);
    min-width: 20px;
    border-radius: 5px;
    margin: 2px;
}}
QScrollBar::handle:horizontal:hover {{
    background: rgba(192,57,43,0.40);
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    border: none;
    background: none;
    width: 0px;
}}
QScrollBar::left-arrow:horizontal, QScrollBar::right-arrow:horizontal, QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
}}

/* ── QToolTip Global Protection ── */
QToolTip {{
    background-color: {BG_DEEP};
    color: {TEXT_BRIGHT};
    border: 1px solid rgba(192,57,43,0.4);
    border-radius: 4px;
    padding: 6px 8px;
    font-size: 11px;
}}

/* ── OS Dialog Fallback Protection (QMessageBox) ── */
QDialog, QMessageBox {{
    background-color: {BG_MID};
    color: {TEXT_PRIMARY};
}}
QMessageBox QLabel {{
    color: {TEXT_BRIGHT};
    font-size: 12px;
}}
QMessageBox QPushButton {{
    background: {BG_ELEVATED};
    color: {TEXT_BRIGHT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 16px;
    font-size: 11px;
    min-width: 60px;
}}
QMessageBox QPushButton:hover {{
    background: {SELECTION};
    border: 1px solid rgba(192,57,43,0.5);
}}
"""
