"""Dialog para alternar patches individuais de um mod JSON — Elite BR.

Reescrito com PySide6 puro (sem qfluentwidgets), visual Crimson Elite.
Permite ativar/desativar alterações byte-a-byte individuais de um mod JSON.
"""

import json
import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QFrame, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QScrollArea, QSizePolicy,
    QVBoxLayout, QWidget,
)

from cdumm.engine.mod_manager import ModManager

logger = logging.getLogger(__name__)

# ── Estilo Elite BR ──────────────────────────────────────────────────────────
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
QCheckBox {
    color: #D0C8CC;
    font-family: 'Segoe UI';
    font-size: 12px;
    padding: 6px 4px;
    spacing: 10px;
    background: transparent;
}
QCheckBox:hover { color: #FFFFFF; }
QCheckBox::indicator {
    width: 15px;
    height: 15px;
    border: 1px solid rgba(192, 57, 43, 0.5);
    border-radius: 3px;
    background: rgba(10, 6, 12, 0.8);
}
QCheckBox::indicator:checked {
    background: #C0392B;
    border-color: #C0392B;
}
QToolTip {
    background: #1A0E10;
    color: #E0D8DC;
    border: 1px solid rgba(192, 57, 43, 0.4);
    font-family: 'Segoe UI';
    font-size: 11px;
    padding: 4px 8px;
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
    border: none;
    border-radius: 5px;
    padding: 8px 22px;
    min-width: 110px;
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
    padding: 8px 16px;
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
    background: rgba(192, 57, 43, 0.10);
    color: #C0392B;
    font-family: 'Segoe UI';
    font-size: 11px;
    font-weight: 600;
    border: 1px solid rgba(192, 57, 43, 0.3);
    border-radius: 4px;
    padding: 5px 12px;
}
QPushButton:hover {
    background: rgba(192, 57, 43, 0.22);
    border-color: rgba(192, 57, 43, 0.6);
    color: #FFFFFF;
}
"""


def has_patch_data(mod: dict, mod_manager: ModManager) -> bool:
    """Retorna True se o mod possui dados de patch individual (JSON source)."""
    try:
        return bool(mod_manager.get_json_source(mod["id"]))
    except Exception:
        return False


class PatchToggleDialog(QDialog):
    """Dialog para alternar patches individuais de um mod JSON.

    Mostra cada alteração byte-a-byte do mod com um checkbox, permitindo
    desativar alterações específicas que serão ignoradas ao Aplicar.
    """

    def __init__(self, mod: dict, mod_manager: ModManager, parent=None) -> None:
        super().__init__(parent)
        self._mod = mod
        self._mm = mod_manager
        self._checkboxes: list[tuple[int, QCheckBox]] = []
        self._changed = False

        self.setStyleSheet(_DIALOG_STYLE)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
        )
        self.setMinimumWidth(680)
        self.setWindowTitle(f"Alternar Patches — {mod['name']}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        # Título
        title = QLabel(f"Alternar Patches Individuais")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #FFFFFF; background: transparent; margin-bottom: 2px;")
        layout.addWidget(title)

        mod_lbl = QLabel(mod["name"])
        mod_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        mod_lbl.setStyleSheet("color: #E0D8DC; background: transparent;")
        layout.addWidget(mod_lbl)

        desc_lbl = QLabel(
            "Alterações desativadas são ignoradas ao clicar em Aplicar. "
            "Útil para desativar partes específicas de um mod sem removê-lo."
        )
        desc_lbl.setFont(QFont("Segoe UI", 10))
        desc_lbl.setStyleSheet("color: #9A8E92; background: transparent;")
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)

        layout.addSpacing(4)

        # Carregar JSON source
        json_source = self._load_json_source(mod["id"])
        if json_source is None:
            no_data = QLabel(
                "Este mod não possui dados de patch individual configuráveis.\n"
                "Apenas mods JSON com patches byte-a-byte suportam esta função."
            )
            no_data.setFont(QFont("Segoe UI", 11))
            no_data.setStyleSheet("color: #9A8E92; background: transparent;")
            no_data.setWordWrap(True)
            layout.addWidget(no_data)

            layout.addSpacing(8)
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setStyleSheet("background: rgba(192,57,43,0.25); max-height: 1px; border: none;")
            layout.addWidget(sep)

            row = QHBoxLayout()
            row.addStretch()
            close_btn = QPushButton("Fechar")
            close_btn.setStyleSheet(_BTN_PRIMARY)
            close_btn.clicked.connect(self.accept)
            row.addWidget(close_btn)
            layout.addLayout(row)
            return

        # Patches desativados atualmente
        disabled = set(mod_manager.get_disabled_patches(mod["id"]))

        # ── Scroll area com patches ──────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setMinimumHeight(300)
        scroll.setMaximumHeight(420)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        patch_layout = QVBoxLayout(container)
        patch_layout.setContentsMargins(10, 10, 10, 10)
        patch_layout.setSpacing(2)

        flat_idx = 0
        patches = json_source.get("patches", [])

        for patch in patches:
            game_file = patch.get("game_file", "unknown")
            changes = patch.get("changes", [])
            if not changes:
                continue

            # Cabeçalho do arquivo-alvo
            file_lbl = QLabel(f"📄  {game_file}")
            file_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            file_lbl.setStyleSheet(
                "color: #FF8C5A; background: transparent; padding-top: 8px;"
            )
            patch_layout.addWidget(file_lbl)

            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setStyleSheet(
                "background: rgba(192,57,43,0.3); max-height: 1px; border: none; margin-bottom: 4px;"
            )
            patch_layout.addWidget(sep)

            for change in changes:
                cb = QCheckBox()
                cb.setChecked(flat_idx not in disabled)

                label_text = change.get("label", "")
                offset = change.get("offset", "?")
                original = change.get("original", "")
                patched = change.get("patched", "")
                ctype = change.get("type", "replace")

                if label_text:
                    desc = f"[{ctype}]  {label_text}  @ offset {offset}"
                else:
                    orig_preview = original[:20] + ("…" if len(original) > 20 else "")
                    pat_preview = patched[:20] + ("…" if len(patched) > 20 else "")
                    desc = f"[{ctype}]  offset {offset}:  {orig_preview} → {pat_preview}"

                cb.setText(desc)
                cb.setToolTip(
                    f"Offset: {offset}\n"
                    f"Original: {original}\n"
                    f"Aplicado: {patched}\n"
                    f"Tipo: {ctype}"
                )

                idx = flat_idx
                cb.toggled.connect(lambda checked, i=idx: self._on_toggle(i, checked))
                self._checkboxes.append((flat_idx, cb))
                patch_layout.addWidget(cb)
                flat_idx += 1

        patch_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

        # Status
        total = flat_idx
        enabled_count = total - len(disabled & set(range(total)))
        self._status_lbl = QLabel(f"{enabled_count} de {total} patches ativados")
        self._status_lbl.setFont(QFont("Segoe UI", 10))
        self._status_lbl.setStyleSheet("color: #9A8E92; background: transparent;")
        layout.addWidget(self._status_lbl)

        # Botões de massa
        bulk_row = QHBoxLayout()
        enable_all = QPushButton("Ativar Todos")
        enable_all.setStyleSheet(_BTN_SMALL)
        enable_all.clicked.connect(self._enable_all)
        bulk_row.addWidget(enable_all)

        bulk_row.addSpacing(6)

        disable_all = QPushButton("Desativar Todos")
        disable_all.setStyleSheet(_BTN_SMALL)
        disable_all.clicked.connect(self._disable_all)
        bulk_row.addWidget(disable_all)

        bulk_row.addStretch()
        layout.addLayout(bulk_row)

        # Separador
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("background: rgba(192,57,43,0.25); max-height: 1px; border: none;")
        layout.addWidget(sep2)

        # Botões de ação
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setStyleSheet(_BTN_SECONDARY)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        btn_row.addSpacing(8)

        save_btn = QPushButton("Salvar e Fechar")
        save_btn.setStyleSheet(_BTN_PRIMARY)
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save_and_close)
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)

    # ── Métodos internos ────────────────────────────────────────────────────

    def _load_json_source(self, mod_id: int) -> dict | None:
        """Carrega o JSON source do mod para exibir os patches."""
        json_path = self._mm.get_json_source(mod_id)
        if not json_path:
            return None
        path = Path(json_path)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _on_toggle(self, idx: int, checked: bool) -> None:
        self._changed = True
        self._update_status()

    def _update_status(self) -> None:
        total = len(self._checkboxes)
        enabled = sum(1 for _, cb in self._checkboxes if cb.isChecked())
        self._status_lbl.setText(f"{enabled} de {total} patches ativados")

    def _enable_all(self) -> None:
        for _, cb in self._checkboxes:
            cb.setChecked(True)
        self._changed = True

    def _disable_all(self) -> None:
        for _, cb in self._checkboxes:
            cb.setChecked(False)
        self._changed = True

    def _save_and_close(self) -> None:
        disabled = [idx for idx, cb in self._checkboxes if not cb.isChecked()]
        self._mm.set_disabled_patches(self._mod["id"], disabled)
        self._changed = False
        self.accept()

    def reject(self) -> None:
        """Avisa sobre alterações não salvas ao fechar."""
        if self._changed:
            msg = QMessageBox(self)
            msg.setWindowTitle("Alterações não salvas")
            msg.setText("Você tem alterações de patches não salvas.")
            msg.setInformativeText("Deseja salvar antes de fechar?")
            # Botões em PT-BR — StandardButton mostra inglês no Windows
            btn_salvar   = msg.addButton("Salvar",    QMessageBox.ButtonRole.AcceptRole)
            btn_descartar = msg.addButton("Descartar", QMessageBox.ButtonRole.DestructiveRole)
            msg.addButton("Cancelar",  QMessageBox.ButtonRole.RejectRole)
            msg.setDefaultButton(btn_salvar)
            msg.setStyleSheet("""
                QMessageBox {
                    background: #0A060C;
                    color: #E8E0E4;
                    font-family: 'Segoe UI';
                }
                QMessageBox QLabel { color: #E8E0E4; }
                QPushButton {
                    background: rgba(192,57,43,0.2);
                    color: #E8E0E4;
                    border: 1px solid rgba(192,57,43,0.4);
                    border-radius: 4px;
                    padding: 5px 14px;
                    font-family: 'Segoe UI';
                }
                QPushButton:hover { background: rgba(192,57,43,0.4); }
            """)
            msg.exec()
            clicked = msg.clickedButton()
            if clicked is btn_salvar:
                self._save_and_close()
                return
            elif clicked is btn_descartar:
                pass  # Fecha sem salvar
            else:
                return  # Cancelar — não fecha
        super().reject()
