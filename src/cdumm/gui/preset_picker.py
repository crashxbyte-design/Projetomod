"""Dialogs de seleção de preset e toggle para mods JSON — Elite BR.

Reescrito com PySide6 puro (sem qfluentwidgets), visual Crimson Elite.
"""

import json
import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QButtonGroup, QDialog, QVBoxLayout, QHBoxLayout, QListWidget,
    QListWidgetItem, QCheckBox, QRadioButton, QWidget, QFrame,
    QLabel, QPushButton, QScrollArea, QSizePolicy,
)

logger = logging.getLogger(__name__)

# ── Estilo Elite BR comum ────────────────────────────────────────────────────
_DIALOG_STYLE = """
QDialog {
    background-color: #0A060C;
    border: 1px solid rgba(192, 57, 43, 0.6);
    border-radius: 10px;
}
QLabel {
    color: #E8E0E4;
    background: transparent;
}
QScrollArea {
    background: rgba(14, 8, 12, 0.85);
    border: 1px solid rgba(192, 57, 43, 0.3);
    border-radius: 6px;
}
QScrollArea > QWidget > QWidget {
    background: transparent;
}
QCheckBox, QRadioButton {
    color: #D0C8CC;
    font-family: 'Segoe UI';
    font-size: 13px;
    padding: 8px 4px;
    spacing: 10px;
    background: transparent;
}
QCheckBox:hover, QRadioButton:hover {
    color: #FFFFFF;
}
QCheckBox::indicator, QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid rgba(192, 57, 43, 0.6);
    border-radius: 3px;
    background: rgba(10, 6, 12, 0.8);
}
QCheckBox::indicator:checked {
    background: #C0392B;
    border-color: #C0392B;
}
QRadioButton::indicator {
    border-radius: 8px;
}
QRadioButton::indicator:checked {
    background: #C0392B;
    border-color: #C0392B;
}
"""

_BTN_PRIMARY = """
QPushButton {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #C0392B, stop:1 #922B21);
    color: #FFFFFF;
    font-family: 'Segoe UI';
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
    border: none;
    border-radius: 5px;
    padding: 8px 22px;
    min-width: 90px;
}
QPushButton:hover {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #E74C3C, stop:1 #C0392B);
}
QPushButton:pressed { background: #922B21; }
"""

_BTN_SECONDARY = """
QPushButton {
    background: rgba(255,255,255,0.04);
    color: #A0989C;
    font-family: 'Segoe UI';
    font-size: 12px;
    font-weight: 500;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 5px;
    padding: 8px 18px;
    min-width: 80px;
}
QPushButton:hover {
    background: rgba(255,255,255,0.08);
    color: #CECECE;
    border-color: rgba(255,255,255,0.15);
}
QPushButton:pressed { background: rgba(0,0,0,0.2); }
"""

_BTN_SMALL = """
QPushButton {
    background: rgba(192, 57, 43, 0.12);
    color: #C0392B;
    font-family: 'Segoe UI';
    font-size: 11px;
    font-weight: 600;
    border: 1px solid rgba(192, 57, 43, 0.3);
    border-radius: 4px;
    padding: 5px 12px;
}
QPushButton:hover {
    background: rgba(192, 57, 43, 0.25);
    border-color: rgba(192, 57, 43, 0.6);
    color: #FFFFFF;
}
"""


def _make_title(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
    lbl.setStyleSheet("color: #FFFFFF; background: transparent; margin-bottom: 4px;")
    return lbl


def _make_caption(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(QFont("Segoe UI", 10))
    lbl.setStyleSheet("color: #9A8E92; background: transparent;")
    lbl.setWordWrap(True)
    return lbl


def _make_scroll_container() -> tuple[QScrollArea, QWidget, QVBoxLayout]:
    """Returns (scroll_area, inner_widget, inner_layout)."""
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QScrollArea.Shape.NoFrame)
    scroll.setMinimumHeight(220)
    scroll.setMaximumHeight(360)

    inner = QWidget()
    inner.setStyleSheet("background: transparent;")
    layout = QVBoxLayout(inner)
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(2)
    scroll.setWidget(inner)
    return scroll, inner, layout


# ── Helpers funcionais (sem mudança) ─────────────────────────────────────────

def find_json_presets(path: Path) -> list[tuple[Path, dict]]:
    """Find all valid JSON patch files in a path.

    Returns list of (file_path, parsed_json) for each valid preset.
    """
    candidates = []

    if path.is_file() and path.suffix.lower() == ".json":
        candidates = [path]
    elif path.is_dir():
        candidates = sorted(path.glob("*.json"))
        if not candidates:
            candidates = sorted(path.glob("*/*.json"))

    presets = []
    for f in candidates:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if (isinstance(data, dict)
                    and "patches" in data
                    and isinstance(data["patches"], list)
                    and len(data["patches"]) > 0
                    and "game_file" in data["patches"][0]
                    and "changes" in data["patches"][0]):
                presets.append((f, data))
        except Exception:
            continue

    return presets


def find_folder_variants(path: Path) -> list[Path]:
    """Find folder-based mod variants (subdirectories that each contain a mod).

    Detects patterns like:
        ModName/
            VariantA/   (contains .paz, .pamt, .json, or numbered dirs)
            VariantB/

    Returns list of variant folder paths, or empty if not a variant mod.
    Ignores numbered PAZ directories (0001/, 0036/) — those are game data, not variants.
    """
    if not path.is_dir():
        return []

    subdirs = sorted([
        d for d in path.iterdir()
        if d.is_dir() and not d.name.startswith('.') and not d.name.startswith('_')
    ])

    if len(subdirs) < 2:
        return []

    # Check if ALL subdirs are numbered PAZ dirs (like 0002/, 0012/) — not variants
    import re
    if all(re.match(r'^\d{4}$', d.name) for d in subdirs):
        return []

    # Check if subdirs look like mod variants (contain game files)
    variants = []
    for d in subdirs:
        has_content = False
        for f in d.rglob("*"):
            if f.is_file() and f.suffix.lower() in ('.paz', '.pamt', '.json', '.bsdiff'):
                has_content = True
                break
            if f.is_dir() and re.match(r'^\d{4}$', f.name):
                has_content = True
                break
        if has_content:
            variants.append(d)

    return variants if len(variants) >= 2 else []


def has_labeled_changes(data: dict) -> bool:
    """Check if a JSON patch mod has configurable options.

    Returns True for:
    1. Grouped presets with [BracketPrefix] pattern (radio buttons)
    2. Mods with 2+ labeled changes that represent independent options

    Does NOT trigger for mods where all changes share the same bracket
    prefix (like [Trust] Talk Gain x2, [Trust] Talk Gain x2). Those are
    parts of one feature, not separate toggles.
    """
    import re
    if _detect_preset_groups(data) is not None:
        return True
    # Collect all labels across all patches
    labels = []
    for patch in data.get("patches", []):
        for change in patch.get("changes", []):
            if "label" in change:
                labels.append(change["label"])
    if len(labels) < 2:
        return False
    # Check bracket prefixes
    prefixes = set()
    has_any_bracket = False
    for label in labels:
        match = re.match(r'\[([^\]]+)\]', label)
        if match:
            prefixes.add(match.group(1))
            has_any_bracket = True
    # All same bracket prefix = one feature, not toggleable
    if has_any_bracket and len(prefixes) <= 1:
        return False
    # Multiple distinct bracket groups, but only if all patches target
    # the SAME game file. Different game files = different components
    # that need to be installed together (like LET ME SLEEP's sleep_left
    # + sleep_right), not independent options.
    if has_any_bracket and len(prefixes) >= 2:
        game_files = set()
        for patch in data.get("patches", []):
            gf = patch.get("game_file")
            if gf:
                game_files.add(gf)
        if len(game_files) <= 1:
            return True
        return False  # multiple game files = not configurable
    # Plain labels (no brackets): only show toggle for mods with many
    # changes (10+), suggesting a mod with lots of independent options.
    # Small numbers of plain labels are just descriptions, not toggles.
    if len(labels) >= 10:
        return True
    return False


def _detect_preset_groups(data: dict) -> dict[str, list[int]] | None:
    """Detect if patches represent mutually exclusive preset groups.

    Returns {group_name: [patch_indices]} if grouped presets found, None if
    independent toggles.
    """
    import re
    patches = data.get("patches", [])
    if not patches:
        return None

    # Pattern 1: multiple patches with bracket prefixes
    if len(patches) >= 2:
        files = [p.get("game_file") for p in patches]
        if len(set(files)) == 1:
            groups: dict[str, list[int]] = {}
            all_have_prefix = True
            for i, patch in enumerate(patches):
                changes = patch.get("changes", [])
                if not changes or "label" not in changes[0]:
                    all_have_prefix = False
                    break
                label = changes[0].get("label", "")
                match = re.match(r'\[([^\]]+)\]', label)
                if match:
                    groups.setdefault(match.group(1), []).append(i)
                else:
                    all_have_prefix = False
                    break
            if all_have_prefix and len(groups) >= 2:
                return groups

    return None


# ── Dialogs Elite BR ─────────────────────────────────────────────────────────

class _EliteDialog(QDialog):
    """Base dialog com estilo Elite BR."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(_DIALOG_STYLE)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(24, 20, 24, 20)
        self._main_layout.setSpacing(10)

    def _add_buttons(self, ok_text: str, cancel_text: str = "Cancelar") -> tuple[QPushButton, QPushButton]:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background: rgba(192,57,43,0.25); max-height: 1px; border: none;")
        self._main_layout.addWidget(sep)

        row = QHBoxLayout()
        row.addStretch()

        cancel = QPushButton(cancel_text)
        cancel.setStyleSheet(_BTN_SECONDARY)
        cancel.clicked.connect(self.reject)
        row.addWidget(cancel)
        row.addSpacing(8)

        ok = QPushButton(ok_text)
        ok.setStyleSheet(_BTN_PRIMARY)
        ok.setDefault(True)
        row.addWidget(ok)

        self._main_layout.addLayout(row)
        return ok, cancel


class FolderVariantDialog(_EliteDialog):
    """Dialog para escolher qual variante de pasta importar."""

    def __init__(self, variants: list[Path], parent=None):
        super().__init__(parent)
        self._variants = variants
        self.selected_path: Path | None = None
        self.setMinimumWidth(420)
        self.setWindowTitle("Escolher Variante")

        self._main_layout.addWidget(_make_title("Escolher Variante de Mod"))
        self._main_layout.addWidget(_make_caption("Selecione a variante que deseja importar:"))
        self._main_layout.addSpacing(8)

        from cdumm.engine.import_handler import prettify_mod_name
        self._group = QButtonGroup(self)
        for i, v in enumerate(variants):
            radio = QRadioButton(prettify_mod_name(v.name))
            radio.setFont(QFont("Segoe UI", 12))
            if i == 0:
                radio.setChecked(True)
            self._group.addButton(radio, i)
            self._main_layout.addWidget(radio)

        self._main_layout.addSpacing(4)
        ok, _ = self._add_buttons("Instalar")
        ok.clicked.connect(self._on_accept)

    def _on_accept(self) -> None:
        idx = self._group.checkedId()
        if 0 <= idx < len(self._variants):
            self.selected_path = self._variants[idx]
        self.accept()


class PresetPickerDialog(_EliteDialog):
    """Dialog para escolher quais presets JSON importar (multi-seleção)."""

    def __init__(self, presets: list[tuple[Path, dict]], parent=None):
        super().__init__(parent)
        self._presets = presets
        # Legacy single-select compat
        self.selected_path: Path | None = None
        self.selected_data: dict | None = None
        # Multi-select results
        self.selected_presets: list[tuple[Path, dict]] = []

        self.setMinimumWidth(520)
        self.setWindowTitle("Escolher Preset(s)")

        self._main_layout.addWidget(_make_title("Escolher Preset(s) de Mod"))
        self._main_layout.addWidget(
            _make_caption("Selecione os presets que deseja importar. "
                          "Vários presets podem ser selecionados ao mesmo tempo.")
        )
        self._main_layout.addSpacing(6)

        scroll, inner, cb_layout = _make_scroll_container()
        self._main_layout.addWidget(scroll)

        self._checkboxes: list[QCheckBox] = []
        for i, (file_path, data) in enumerate(presets):
            name = data.get("name", file_path.stem)
            desc = data.get("description", "")
            patch_count = sum(len(p.get("changes", [])) for p in data.get("patches", []))

            label = name
            if desc:
                label += f"\n{desc[:80]}"
            label += f"\n{patch_count} alterações"

            cb = QCheckBox(label)
            cb.setFont(QFont("Segoe UI", 12))
            cb.setChecked(i == 0)  # primeiro marcado por padrão
            self._checkboxes.append(cb)
            cb_layout.addWidget(cb)

        cb_layout.addStretch()

        ok, _ = self._add_buttons("Instalar")
        ok.clicked.connect(self._on_accept)

    def _on_accept(self) -> None:
        self.selected_presets = []
        for i, cb in enumerate(self._checkboxes):
            if cb.isChecked() and i < len(self._presets):
                fp, data = self._presets[i]
                self.selected_presets.append((fp, data))
        # Legacy compat: set first selected as primary
        if self.selected_presets:
            self.selected_path = self.selected_presets[0][0]
            self.selected_data = self.selected_presets[0][1]
        self.accept()


class TogglePickerDialog(_EliteDialog):
    """Dialog para escolher quais alterações aplicar de um mod JSON.

    Suporta dois modos:
    - Toggles independentes: checkboxes para cada alteração
    - Presets agrupados: radio buttons para grupos mutuamente exclusivos
    """

    def __init__(self, data: dict, parent=None, previous_labels: list[str] | None = None):
        super().__init__(parent)
        self._data = data
        self._previous = set(previous_labels) if previous_labels else None
        self.selected_data: dict | None = None

        self.setMinimumWidth(520)
        self.setWindowTitle("Escolher o que Aplicar")

        self._main_layout.addWidget(_make_title("Escolher o que Aplicar"))

        name = data.get("name", "Mod")
        desc = data.get("description", "")

        name_lbl = QLabel(name)
        name_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        name_lbl.setStyleSheet("color: #E0D8DC; background: transparent;")
        self._main_layout.addWidget(name_lbl)

        if desc:
            self._main_layout.addWidget(_make_caption(desc))

        if self._previous:
            self._main_layout.addWidget(
                _make_caption(f"Selecionados anteriormente: {len(self._previous)} items")
            )

        # Detect which mode to use
        self._groups = _detect_preset_groups(data)

        if self._groups:
            self._build_preset_mode()
        else:
            self._build_toggle_mode()

        ok, _ = self._add_buttons("Aplicar Selecionados")
        ok.clicked.connect(self._on_accept)

    def _build_preset_mode(self) -> None:
        """Presets mutuamente exclusivos — radio buttons."""
        self._main_layout.addWidget(_make_caption("Escolha um preset:"))
        self._main_layout.addSpacing(4)

        scroll, inner, scroll_layout = _make_scroll_container()

        self._radio_buttons: list[tuple] = []  # (radio, group_name, indices)
        first = True
        for group_name, indices in self._groups.items():
            patches = self._data["patches"]
            detail_parts = []
            group_labels = []
            for idx in indices:
                for c in patches[idx].get("changes", []):
                    label = c.get("label", "")
                    group_labels.append(label)
                    import re
                    clean = re.sub(r'^\[[^\]]+\]\s*', '', label)
                    if clean:
                        detail_parts.append(clean)

            radio = QRadioButton(group_name)
            radio.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            if self._previous and any(l in self._previous for l in group_labels):
                radio.setChecked(True)
                first = False
            elif first:
                radio.setChecked(True)
                first = False
            scroll_layout.addWidget(radio)

            if detail_parts:
                MAX_SHOWN = 3
                summary = (", ".join(detail_parts[:MAX_SHOWN])
                           + (f"  (+{len(detail_parts) - MAX_SHOWN} mais)" if len(detail_parts) > MAX_SHOWN else ""))
                detail = _make_caption("  " + summary)
                scroll_layout.addWidget(detail)

            self._radio_buttons.append((radio, group_name, indices))

        scroll_layout.addStretch()
        self._main_layout.addWidget(scroll)

    def _build_toggle_mode(self) -> None:
        """Toggles independentes — checkboxes."""
        self._main_layout.addWidget(_make_caption("Marque os itens que deseja aplicar:"))
        self._main_layout.addSpacing(4)

        # Select all / Deselect all row
        sel_row = QHBoxLayout()
        sel_all = QPushButton("Selecionar Tudo")
        sel_all.setStyleSheet(_BTN_SMALL)
        sel_all.clicked.connect(self._select_all)
        sel_row.addWidget(sel_all)
        sel_row.addSpacing(6)
        desel_all = QPushButton("Desmarcar Tudo")
        desel_all.setStyleSheet(_BTN_SMALL)
        desel_all.clicked.connect(self._deselect_all)
        sel_row.addWidget(desel_all)
        sel_row.addStretch()
        self._main_layout.addLayout(sel_row)

        scroll, inner, scroll_layout = _make_scroll_container()

        self._checkboxes: list[tuple[QCheckBox, dict]] = []
        for patch in self._data.get("patches", []):
            for change in patch.get("changes", []):
                label = change.get("label", f"offset {change.get('offset', '?')}")
                cb = QCheckBox(label)
                cb.setFont(QFont("Segoe UI", 11))
                if self._previous is not None:
                    cb.setChecked(label in self._previous)
                else:
                    cb.setChecked(True)
                scroll_layout.addWidget(cb)
                self._checkboxes.append((cb, change))

        scroll_layout.addStretch()
        self._main_layout.addWidget(scroll)

        self._count_label = _make_caption(f"{len(self._checkboxes)} itens selecionados")
        self._main_layout.addWidget(self._count_label)
        for cb, _ in self._checkboxes:
            cb.toggled.connect(self._update_count)

    def _select_all(self) -> None:
        for cb, _ in self._checkboxes:
            cb.setChecked(True)

    def _deselect_all(self) -> None:
        for cb, _ in self._checkboxes:
            cb.setChecked(False)

    def _update_count(self) -> None:
        count = sum(1 for cb, _ in self._checkboxes if cb.isChecked())
        self._count_label.setText(f"{count} de {len(self._checkboxes)} itens selecionados")

    def _on_accept(self) -> None:
        import copy
        filtered = copy.deepcopy(self._data)

        if self._groups:
            # Preset mode — keep only the selected group's patches
            selected_indices = set()
            for radio, group_name, indices in self._radio_buttons:
                if radio.isChecked():
                    selected_indices.update(indices)
            filtered["patches"] = [
                p for i, p in enumerate(filtered["patches"])
                if i in selected_indices
            ]
        else:
            # Toggle mode — keep only checked changes
            selected_changes = [change for cb, change in self._checkboxes if cb.isChecked()]
            if not selected_changes:
                return
            selected_keys = {(c.get("offset"), c.get("label")) for c in selected_changes}
            for patch in filtered["patches"]:
                patch["changes"] = [
                    c for c in patch.get("changes", [])
                    if (c.get("offset"), c.get("label")) in selected_keys
                ]

        self.selected_data = filtered
        self.accept()
