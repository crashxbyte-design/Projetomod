"""Qt Model for the mod list table view."""
import logging
from pathlib import Path

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QThread, Qt, Signal, QObject
from PySide6.QtGui import QColor

from cdumm.engine.conflict_detector import ConflictDetector
from cdumm.engine.mod_manager import ModManager

logger = logging.getLogger(__name__)

COLUMNS = ["☐", "#", "Name", "Author", "Version", "Status", "Files", "Notes", "Import Date"]
COL_ENABLED = 0
COL_ORDER = 1
COL_NAME = 2
COL_AUTHOR = 3
COL_VERSION = 4
COL_STATUS = 5
COL_FILES = 6
COL_NOTES = 7
COL_DATE = 8

STATUS_COLORS = {
    "active": QColor(76, 175, 80),       # green
    "not applied": QColor(255, 152, 0),   # orange
    "no data": QColor(244, 67, 54),       # red
    "outdated": QColor(255, 193, 7),      # amber
    "active (outdated)": QColor(255, 193, 7),    # amber
    "not applied (outdated)": QColor(255, 193, 7), # amber
    "disabled": QColor(158, 158, 158),    # gray
    "disabled (outdated)": QColor(255, 193, 7),  # amber
    "checking...": QColor(158, 158, 158), # gray
    "disabled (crash)": QColor(244, 67, 54),    # red
    "active (crash)": QColor(244, 67, 54),      # red
    "not applied (crash)": QColor(244, 67, 54), # red
}


class _StatusWorker(QObject):
    """Background worker to compute mod game statuses without blocking UI."""
    finished = Signal(object)  # {mod_id: status_str}

    def __init__(self, mod_ids: list[int], db_path: Path, game_dir: Path,
                 deltas_dir: Path) -> None:
        super().__init__()
        self._mod_ids = mod_ids
        self._db_path = db_path
        self._game_dir = game_dir
        self._deltas_dir = deltas_dir

    def run(self) -> None:
        try:
            from cdumm.storage.database import Database
            db = Database(self._db_path)
            db.initialize()
            mgr = ModManager(db, self._deltas_dir)
            results = {}
            for mid in self._mod_ids:
                try:
                    results[mid] = mgr.get_mod_game_status(mid, self._game_dir)
                except Exception as e:
                    logger.warning("Status check failed for mod %d: %s", mid, e)
                    results[mid] = "disabled"
            db.close()
            self.finished.emit(results)
        except Exception as e:
            logger.error("StatusWorker crashed: %s", e, exc_info=True)
            # Emit fallback so UI doesn't stay stuck on "checking..."
            self.finished.emit({mid: "disabled" for mid in self._mod_ids})


class ModListModel(QAbstractTableModel):
    """Table model backed by SQLite mod registry."""

    mod_toggled = Signal()  # emitted when a mod is enabled/disabled via checkbox

    def __init__(self, mod_manager: ModManager, conflict_detector: ConflictDetector,
                 game_dir: Path | None = None, db_path: Path | None = None,
                 deltas_dir: Path | None = None, parent=None) -> None:
        super().__init__(parent)
        self._mod_manager = mod_manager
        self._conflict_detector = conflict_detector
        self._game_dir = game_dir
        self._db_path = db_path
        self._deltas_dir = deltas_dir
        self._mods: list[dict] = []
        self._status_cache: dict[int, str] = {}
        self._file_count_cache: dict[int, int] = {}
        self._conflict_status_cache: dict[int, str] = {}
        self._status_thread: QThread | None = None
        self.refresh()

    def refresh(self, preserve_statuses: bool = True) -> None:
        """Refresh mod list from DB. Preserves status cache by default to avoid flicker."""
        self.beginResetModel()
        self._mods = self._mod_manager.list_mods()
        # Preserve existing status cache — only new mods get "checking..."
        # (Resetting to checking... on every refresh caused all cards to flicker after toggle)
        if preserve_statuses:
            old_cache = dict(self._status_cache)
            self._status_cache = {
                mod["id"]: old_cache.get(mod["id"], "checking...")
                for mod in self._mods
            }
        else:
            # Full reset — on initial load or explicit hard refresh
            self._status_cache = {mod["id"]: "checking..." for mod in self._mods}
        self._file_count_cache = self._mod_manager.get_file_counts()
        self._conflict_status_cache = self._conflict_detector.get_all_mod_statuses()
        self.endResetModel()

    def refresh_statuses(self) -> None:
        """Trigger background status computation. Call after window is visible."""
        self._refresh_statuses_async()

    def _refresh_statuses_async(self) -> None:
        """Compute mod game statuses on a background thread."""
        if not self._game_dir or not self._db_path or not self._deltas_dir:
            return
        if not self._mods:
            return

        # Clean up previous thread
        old_thread = self._status_thread
        if old_thread is not None:
            try:
                if old_thread.isRunning():
                    old_thread.quit()
                    old_thread.wait(2000)
            except RuntimeError:
                pass
        self._status_thread = None
        self._status_worker = None

        mod_ids = [m["id"] for m in self._mods]
        worker = _StatusWorker(mod_ids, self._db_path, self._game_dir, self._deltas_dir)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_statuses_ready)
        worker.finished.connect(thread.quit)
        self._status_thread = thread
        self._status_worker = worker
        thread.start()

    def _on_statuses_ready(self, results: dict) -> None:
        self._status_cache.update(results)
        # Overlay crash flags from crash registry
        try:
            crash_flags = self._mod_manager.get_crash_flags()
            for mod_id, info in crash_flags.items():
                if mod_id in self._status_cache:
                    base = self._status_cache[mod_id]
                    if "crash" not in base:
                        self._status_cache[mod_id] = f"{base} (crash)"
        except Exception:
            pass
        # Emit dataChanged for column 0 (UserRole used by FastModCardDelegate/QListView)
        # AND for COL_STATUS (used by any TableView consumers)
        if self._mods:
            top0 = self.index(0, 0)
            bottom0 = self.index(len(self._mods) - 1, 0)
            self.dataChanged.emit(top0, bottom0)
            top = self.index(0, COL_STATUS)
            bottom = self.index(len(self._mods) - 1, COL_STATUS)
            self.dataChanged.emit(top, bottom)

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._mods)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(COLUMNS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return COLUMNS[section]
        return None

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._mods):
            return None

        mod = self._mods[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == COL_ORDER:
                return str(index.row() + 1)
            if col == COL_NAME:
                if mod.get("configurable"):
                    return f"⚙ {mod['name']}"
                return mod["name"]
            if col == COL_AUTHOR:
                return mod.get("author") or ""
            if col == COL_VERSION:
                return mod.get("version") or ""
            if col == COL_STATUS:
                status = self._status_cache.get(mod["id"], "")
                conflict = self._conflict_status_cache.get(mod["id"], "clean")
                if conflict in ("conflict", "resolved"):
                    return f"{status} ({conflict})"
                return status
            if col == COL_FILES:
                return str(self._file_count_cache.get(mod["id"], 0))
            if col == COL_NOTES:
                return mod.get("notes") or ""
            if col == COL_DATE:
                return mod["import_date"][:16] if mod["import_date"] else ""

        if role == Qt.ItemDataRole.ForegroundRole:
            if col == COL_STATUS:
                status = self._status_cache.get(mod["id"], "")
                color = STATUS_COLORS.get(status)
                if color is None and "(crash)" in status:
                    color = QColor(244, 67, 54)  # red for any crash-flagged status
                return color
            if col == COL_NOTES and mod.get("notes"):
                from cdumm.gui.theme import get_color
                return QColor(get_color("text_bright"))

        if role == Qt.ItemDataRole.CheckStateRole and col == COL_ENABLED:
            return Qt.CheckState.Checked if mod["enabled"] else Qt.CheckState.Unchecked

        if role == Qt.ItemDataRole.ToolTipRole:
            if col == COL_NAME and mod.get("notes"):
                return f"Notes: {mod['notes']}"
            if col == COL_STATUS:
                status = self._status_cache.get(mod["id"], "")
                if "outdated" in status and mod.get("notes") and "Broken by game update" in mod["notes"]:
                    return mod["notes"]
                if "outdated" in status:
                    return "This mod was made for an older game version. The mod author needs to update it."

        if role == Qt.ItemDataRole.UserRole:
            # FastModCardDelegate (QListView) reads this role to paint cards.
            # Must return a dict with all fields the delegate needs.
            status = self._status_cache.get(mod["id"], "checking...")
            if not mod["enabled"]:
                status = "disabled"
            conflict = self._conflict_status_cache.get(mod["id"], "clean")
            if conflict in ("conflict", "resolved"):
                status = f"{status} ({conflict})"
            return {
                "id": mod["id"],
                "name": mod.get("name") or "",
                "enabled": bool(mod["enabled"]),
                "status": status,
                "author": mod.get("author") or "",
                "version": mod.get("version") or "",
                "mod_type": mod.get("mod_type") or "",
                "desc": mod.get("desc") or "",
            }

        return None

    def setData(self, index: QModelIndex, value, role=Qt.ItemDataRole.EditRole) -> bool:
        if index.column() == COL_ENABLED and role == Qt.ItemDataRole.CheckStateRole:
            mod = self._mods[index.row()]
            # Robust comparison — handles enum, int value (2), and bool
            enabled = value in (Qt.CheckState.Checked, 2, True)
            self._mod_manager.set_enabled(mod["id"], enabled)
            # Atualização cirúrgica: só notifica a linha alterada, sem resetar toda a lista
            mod["enabled"] = enabled
            # Emit with explicit roles so QListView re-renders UserRole (card paint)
            self.dataChanged.emit(
                index, index,
                [Qt.ItemDataRole.CheckStateRole, Qt.ItemDataRole.UserRole]
            )
            self.mod_toggled.emit()
            return True
        return False

    def update_mod_state(self, mod_id: int, enabled: bool) -> None:
        """Atualiza o estado ativo/inativo de um mod sem resetar o modelo inteiro.

        Use este método sempre que o toggle vier de fora do modelo (ex: botão Alternar
        Todos, menu de contexto). Emite dataChanged só na linha afetada.
        """
        for row, mod in enumerate(self._mods):
            if mod["id"] == mod_id:
                mod["enabled"] = enabled
                self.dataChanged.emit(
                    self.index(row, 0),
                    self.index(row, len(COLUMNS) - 1),
                    [Qt.ItemDataRole.CheckStateRole, Qt.ItemDataRole.UserRole,
                     Qt.ItemDataRole.DisplayRole]
                )
                return

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        flags = super().flags(index)
        if index.column() == COL_ENABLED:
            flags |= Qt.ItemFlag.ItemIsUserCheckable
        if index.isValid():
            flags |= Qt.ItemFlag.ItemIsDragEnabled
        flags |= Qt.ItemFlag.ItemIsDropEnabled
        return flags

    def supportedDropActions(self):
        return Qt.DropAction.MoveAction

    def mimeTypes(self):
        return ["application/x-cdumm-mod-row"]

    def mimeData(self, indexes):
        from PySide6.QtCore import QMimeData
        data = QMimeData()
        rows = sorted(set(idx.row() for idx in indexes if idx.isValid()))
        data.setData("application/x-cdumm-mod-row", ",".join(str(r) for r in rows).encode())
        return data

    def canDropMimeData(self, data, action, row, column, parent):
        return data.hasFormat("application/x-cdumm-mod-row")

    def dropMimeData(self, data, action, row, column, parent):
        if not data.hasFormat("application/x-cdumm-mod-row"):
            return False
        raw = bytes(data.data("application/x-cdumm-mod-row")).decode()
        if not raw:
            return False
        source_rows = [int(r) for r in raw.split(",")]
        if not source_rows:
            return False

        # When dropping ON a row (not between), row is -1 and parent is valid
        if row < 0 and parent.isValid():
            row = parent.row()
        elif row < 0:
            row = len(self._mods)

        # Reorder: move source rows to target position
        ids = [m["id"] for m in self._mods]
        moved = [ids[r] for r in source_rows if r < len(ids)]
        remaining = [mid for mid in ids if mid not in moved]
        # Adjust target: account for removed items above the drop point
        target = row
        for r in sorted(source_rows):
            if r < row:
                target -= 1
        target = max(0, min(target, len(remaining)))
        new_order = remaining[:target] + moved + remaining[target:]

        self._mod_manager.reorder_mods(new_order)
        self.refresh()
        self.refresh_statuses()
        self.mod_toggled.emit()
        return True

    def refresh_conflict_cache(self) -> None:
        """Update conflict status cache from database. Call after detect_all()."""
        self._conflict_status_cache = self._conflict_detector.get_all_mod_statuses()
        if self._mods:
            top = self.index(0, COL_STATUS)
            bottom = self.index(len(self._mods) - 1, COL_STATUS)
            self.dataChanged.emit(top, bottom)

    def get_mod_at_row(self, row: int) -> dict | None:
        if 0 <= row < len(self._mods):
            return self._mods[row]
        return None
