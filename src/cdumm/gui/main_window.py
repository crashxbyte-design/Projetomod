from cdumm.gui.msg_box_br import _pergunta_br, _info_br, _warning_br, _critical_br
"""Main application window — wires all components together."""
import logging
from datetime import datetime, timedelta
from pathlib import Path
from cdumm import __version__
from PySide6.QtCore import QObject, QThread, QTimer, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QTableView,
    QListView,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from cdumm.engine.apply_engine import ApplyWorker, RevertWorker
from cdumm.engine.conflict_detector import ConflictDetector
from cdumm.engine.mod_manager import ModManager
from cdumm.engine.snapshot_manager import SnapshotManager, SnapshotWorker
from cdumm.gui.asi_panel import AsiPanel
from cdumm.gui.conflict_view import ConflictView
from cdumm.gui.changelog import PatchNotesDialog, CHANGELOG
from cdumm.gui.import_widget import ImportWidget
from cdumm.gui.mod_list_model import ModListModel
from cdumm.gui.progress_dialog import ProgressDialog
from cdumm.gui.workers import ImportWorker
from cdumm.storage.config import Config
from cdumm.storage.database import Database

logger = logging.getLogger(__name__)


def _is_standalone_paz_mod(path: Path) -> bool:
    """Check if path is a standalone PAZ mod (0.paz + 0.pamt, not in a numbered dir).

    These mods add a new PAZ directory and don't need a vanilla snapshot.
    """
    import zipfile
    if path.is_dir():
        # Check folder: has 0.paz + 0.pamt at root or one level deep
        if (path / "0.paz").exists() and (path / "0.pamt").exists():
            return True
        for sub in path.iterdir():
            if sub.is_dir() and (sub / "0.paz").exists() and (sub / "0.pamt").exists():
                # But NOT if it's a numbered directory (those are regular mods)
                if not (sub.name.isdigit() and len(sub.name) == 4):
                    return True
        return False
    if path.suffix.lower() == ".zip":
        try:
            with zipfile.ZipFile(path) as zf:
                names = zf.namelist()
                has_paz = any(n.endswith("/0.paz") or n == "0.paz" for n in names)
                has_pamt = any(n.endswith("/0.pamt") or n == "0.pamt" for n in names)
                return has_paz and has_pamt
        except Exception:
            return False
    return False


class MainThreadDispatcher(QObject):
    """Routes callbacks from worker threads to the main thread.

    PySide6 lambdas connected to signals execute on the emitter's thread,
    ignoring QueuedConnection. This QObject lives on the main thread with
    @Slot methods, so Qt's auto-connection correctly queues cross-thread calls.
    """
    _dispatch = Signal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dispatch.connect(self._execute)

    @Slot(object, object)
    def _execute(self, func, args):
        func(*args)

    def call(self, func, *args):
        """Emit from any thread — func will execute on the main thread."""
        self._dispatch.emit(func, args)


class MainWindow(QMainWindow):
    def __init__(self, db: Database | None = None, game_dir: Path | None = None,
                 app_data_dir: Path | None = None,
                 startup_context: dict | None = None) -> None:
        super().__init__()
        # Branding & Title
        self.setWindowTitle(f"Crimson Desert Elite BR - {__version__}")
        self.setMinimumSize(1000, 700)

        # Set window icon
        import sys
        from PySide6.QtGui import QIcon
        if getattr(sys, 'frozen', False):
            icon_path = Path(sys._MEIPASS) / "cdumm.ico"
        else:
            icon_path = Path(__file__).resolve().parents[3] / "cdumm.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # ── Enable Dark Titlebar on Windows 11/10 ──
        if sys.platform == "win32":
            import ctypes
            try:
                hwnd = self.winId()
                # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                ctypes.windll.dwmapi.DwmSetWindowAttribute(int(hwnd), 20, ctypes.byref(ctypes.c_int(2)), ctypes.sizeof(ctypes.c_int(2)))
            except Exception:
                pass

        self._db = db
        self._game_dir = game_dir
        self._app_data_dir = app_data_dir or Path.home() / "AppData" / "Local" / "CDMod_Elite"
        # Store vanilla backups and deltas on the game drive (CDMods folder)
        # so we can use hard links instead of copies for multi-GB PAZ files.
        self._cdmods_dir = game_dir / "CDModsElite" if game_dir else self._app_data_dir
        self._cdmods_dir.mkdir(parents=True, exist_ok=True)
        self._deltas_dir = self._cdmods_dir / "deltas"
        self._vanilla_dir = self._cdmods_dir / "vanilla"
        self._migrate_from_appdata()
        self._worker_thread: QThread | None = None
        self._active_progress: ProgressDialog | None = None
        self._needs_apply = False
        self._applied_state: dict[int, bool] = {}  # {mod_id: enabled} snapshot after last apply
        self._snapshot_in_progress = False
        self._dispatcher = MainThreadDispatcher(parent=self)

        # Clean up stale staging directory from previous crash.
        # Only clean if no other CDUMM instance is running (check lock file age).
        if game_dir:
            staging = game_dir / ".cdumm_staging"
            if staging.exists():
                lock_file = (Path.home() / "AppData" / "Local" / "CDMod_Elite" / ".running")
                lock_is_stale = True
                if lock_file.exists():
                    try:
                        lock_time = datetime.fromisoformat(
                            lock_file.read_text(encoding="utf-8").strip())
                        if datetime.now() - lock_time < timedelta(seconds=30):
                            lock_is_stale = False  # another instance may be active
                    except Exception:
                        pass
                if lock_is_stale:
                    try:
                        import shutil
                        shutil.rmtree(staging, ignore_errors=True)
                        logger.info("Cleaned up stale staging directory")
                    except Exception:
                        pass

        # Clear stale import state from previous session
        from cdumm.engine.import_handler import clear_assigned_dirs
        clear_assigned_dirs()

        # Initialize managers if database is available
        if db:
            self._snapshot = SnapshotManager(db)
            self._mod_manager = ModManager(db, self._deltas_dir)
            self._conflict_detector = ConflictDetector(db)
            self._mod_manager.cleanup_orphaned_deltas()
        else:
            self._snapshot = None
            self._mod_manager = None
            self._conflict_detector = None

        self._build_ui()
        self._build_toolbar()
        self._build_status_bar()
        # Diferir o _refresh_all pesado para depois do showEvent (janela visível)
        # Evita o 'Not Responding' de 4 segundos na inicialização
        self._startup_refresh_pending = True
        self._snapshot_applied_state()
        self.setAcceptDrops(True)
        self._startup_context = startup_context or {}

        self._has_pending_changes = False
        self._launch_after_apply = False

        # Crash detection — lock file
        self._lock_file = self._app_data_dir / ".running"
        crashed_last_time = self._lock_file.exists()
        self._lock_file.write_text(str(datetime.now()), encoding="utf-8")

        # Deferred startup tasks (after window is visible)
        QTimer.singleShot(500, self._deferred_startup)
        QTimer.singleShot(2000, self._heavy_background_checks)

        # Update check suppressed — update UI removed from interface
        # QTimer.singleShot(5000, self._check_for_updates)  # disabled
        self._update_timer = QTimer(self)  # kept inert (no connect, no start)

        # Auto-snapshot is handled by _deferred_startup

        # If previous session didn't close cleanly — crash report suppressed from UI
        # (method _offer_crash_report is intact; re-enable by uncommenting)
        # if crashed_last_time:
        #     QTimer.singleShot(1000, self._offer_crash_report)



    def closeEvent(self, event) -> None:
        super().closeEvent(event)

    def _migrate_from_appdata(self) -> None:
        """One-time migration: move vanilla/deltas from old AppData locations to CDMods on game drive."""
        import shutil
        # Check both old (cdmm) and current (cdumm) AppData paths
        old_appdata = Path.home() / "AppData" / "Local" / "cdmm"
        migrated_deltas_from: list[str] = []

        for appdata in [old_appdata, self._app_data_dir]:
            for sub in ("vanilla", "deltas"):
                old_dir = appdata / sub
                new_dir = self._vanilla_dir if sub == "vanilla" else self._deltas_dir
                if old_dir.exists() and not new_dir.exists() and old_dir != new_dir:
                    try:
                        shutil.move(str(old_dir), str(new_dir))
                        logger.info("Migrated %s -> %s", old_dir, new_dir)
                        if sub == "deltas":
                            migrated_deltas_from.append(str(old_dir))
                    except Exception as e:
                        logger.warning("Migration failed for %s: %s (will copy instead)", old_dir, e)
                        try:
                            shutil.copytree(str(old_dir), str(new_dir))
                            shutil.rmtree(old_dir, ignore_errors=True)
                            if sub == "deltas":
                                migrated_deltas_from.append(str(old_dir))
                        except Exception as e2:
                            logger.error("Copy fallback also failed: %s", e2)

        # Update delta_path references in the database to point to the new location
        if migrated_deltas_from:
            for old_path in migrated_deltas_from:
                new_path = str(self._deltas_dir)
                try:
                    count = self._db.connection.execute(
                        "UPDATE mod_deltas SET delta_path = REPLACE(delta_path, ?, ?)",
                        (old_path, new_path),
                    ).rowcount
                    self._db.connection.commit()
                    logger.info("Updated %d delta paths: %s -> %s", count, old_path, new_path)
                except Exception as e:
                    logger.error("Failed to update delta paths in DB: %s", e)

    def showEvent(self, event) -> None:
        """Disparado quando a janela fica visível pela primeira vez.
        Executa o refresh pesado aqui para que a janela já esteja renderizada
        (evita o 'Not Responding' do Windows na abertura).
        """
        super().showEvent(event)
        if getattr(self, "_startup_refresh_pending", False):
            self._startup_refresh_pending = False
            from PySide6.QtCore import QTimer
            # singleShot(200) dá tempo ao OS para desenhar a interface inteira
            # e não classificar o app como "Não está respondendo" durante I/O pesado.
            QTimer.singleShot(200, lambda: self._refresh_all(update_statuses=False))

    def _deferred_startup(self) -> None:
        """Run after window is visible. Only fast checks here — no file I/O."""
        if self._game_dir and self._db:
            if self._check_one_time_reset():
                return
            if self._check_game_updated():
                return
        if self._game_dir and self._snapshot and not self._snapshot.has_snapshot():
            reply = _pergunta_br(
                self, "Verificação de Arquivos Necessária",
                "Antes de usar o gerenciador de mods, os arquivos do jogo precisam ser verificados.\n\n"
                "Para melhores resultados, por favor verifique seus arquivos pela Steam primeiro:\n"
                "  Steam → Clique com botão direito em Crimson Desert → Propriedades\n"
                "  → Arquivos Instalados → Verificar integridade dos arquivos\n\n"
                "Você já verificou (ou é uma instalação nova)?"
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self._on_refresh_snapshot(skip_verify_prompt=True)
            else:
                self.statusBar().showMessage(
                    "Por favor verifique os arquivos do jogo (Steam: Verificar Integridade / Xbox: Reparar), depois reinicie.", 0)
            return


        self._check_program_files_warning()
        self._check_bad_standalone_imports()
        self._check_show_update_notes()

        # Check if main.py detected a game update during splash
        if self._startup_context.get("game_updated"):
            self._check_game_updated()

        # Check if game version fingerprint changed (Steam verify or update)
        # This is a fast check — just compares a config string, no file hashing
        elif self._game_dir and self._snapshot and self._snapshot.has_snapshot():
            try:
                from cdumm.engine.version_detector import detect_game_version
                from cdumm.storage.config import Config
                config = Config(self._db)
                current_fp = detect_game_version(self._game_dir)
                stored_fp = config.get("game_version_fingerprint")
                if current_fp and stored_fp and current_fp != stored_fp:
                    reply = _pergunta_br(
                        self, "Mudança no Jogo Detectada",
                        "Mudança detectada nos arquivos do jogo. Para evitar crashes, o sistema precisa re-sincronizar os mods com a nova versão da Steam. Prosseguir?",
                        icon=QMessageBox.Icon.Critical
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        self._on_refresh_snapshot(skip_verify_prompt=True)
            except Exception:
                pass



        # Verificação silenciosa de integridade — corrige estado sujo automaticamente
        self._startup_health_check()

        # Trigger background status check for mod list
        if hasattr(self, "_mod_list_model"):
            self._mod_list_model.refresh_statuses()

        # Trigger background conflict check
        self._schedule_conflict_check()

    def _heavy_background_checks(self) -> None:
        # Não rodar checks pesados enquanto o snapshot/backup estiver em progresso.
        # _check_stale_appdata pode mostrar um dialog modal bloqueante que colide
        # com o ProgressDialog do backup quando o usuário clica "Sim" rapidamente
        # (antes dos 2s do timer). Adia 10s e tenta de novo.
        if getattr(self, '_snapshot_in_progress', False):
            QTimer.singleShot(10000, self._heavy_background_checks)
            return

        self._check_stale_appdata()
        self._check_pamt_backups()
        self._check_missing_sources()


    def _startup_health_check(self) -> None:
        """Verificação silenciosa do estado do jogo ao iniciar.

        Se nenhum mod está habilitado mas os arquivos do jogo estão
        diferentes do vanilla, corrige o estado automaticamente.
        """
        try:
            if not self._db or not self._game_dir or not self._snapshot:
                return
            if not self._snapshot.has_snapshot():
                return

            # Só verifica se nenhum mod está habilitado
            enabled = self._db.connection.execute(
                "SELECT COUNT(*) FROM mods WHERE enabled = 1").fetchone()[0]
            if enabled > 0:
                return

            # Verificação rápida: tamanho do PAPGT vs snapshot
            papgt_path = self._game_dir / "meta" / "0.papgt"
            if not papgt_path.exists():
                return
            snap = self._db.connection.execute(
                "SELECT file_size FROM snapshots WHERE file_path = 'meta/0.papgt'"
            ).fetchone()
            if not snap:
                return
            actual_size = papgt_path.stat().st_size
            if actual_size == snap[0]:
                # PAPGT confere — verificar também diretórios órfãos
                has_orphans = False
                for d in self._game_dir.iterdir():
                    if (d.is_dir() and d.name.isdigit() and len(d.name) == 4
                            and int(d.name) >= 36):
                        orphan_check = self._db.connection.execute(
                            "SELECT COUNT(*) FROM snapshots WHERE file_path LIKE ?",
                            (d.name + "/%",)).fetchone()[0]
                        if orphan_check == 0:
                            has_orphans = True
                            break
                if not has_orphans:
                    return  # tudo parece limpo

            # Arquivos do jogo sujos sem mods habilitados — corrigir automaticamente
            logger.info("Verificação de integridade: arquivos do jogo sujos, corrigindo...")
            import shutil

            # Limpar diretórios órfãos
            for d in sorted(self._game_dir.iterdir()):
                if not d.is_dir() or not d.name.isdigit() or len(d.name) != 4:
                    continue
                if int(d.name) < 36:
                    continue
                orphan_check = self._db.connection.execute(
                    "SELECT COUNT(*) FROM snapshots WHERE file_path LIKE ?",
                    (d.name + "/%",)).fetchone()[0]
                if orphan_check == 0:
                    shutil.rmtree(d, ignore_errors=True)
                    logger.info("Integridade: removido diretório órfão %s", d.name)

            # Restaurar PAPGT vanilla se o backup existe e confere com o snapshot
            vanilla_papgt = self._vanilla_dir / "meta" / "0.papgt"
            if vanilla_papgt.exists() and snap:
                if vanilla_papgt.stat().st_size == snap[0]:
                    shutil.copy2(vanilla_papgt, papgt_path)
                    logger.info("Integridade: PAPGT vanilla restaurado do backup")

            self._log_activity("health", "Estado do jogo restaurado automaticamente na inicialização")
        except Exception as e:
            logger.debug("Verificação de integridade ao iniciar falhou: %s", e)
        finally:
            pass

    def _check_missing_sources(self) -> None:
        """Notifica o usuário sobre mods sem arquivos-fonte armazenados.

        Mods importados antes do sistema de sources não podem ser
        reimportados ou reconfigurados automaticamente.
        O usuário precisa arrastá-los novamente uma única vez.
        """
        try:
            if not self._db or not self._mod_manager:
                return
            from cdumm.storage.config import Config
            config = Config(self._db)
            if config.get("missing_sources_checked"):
                return

            sources_dir = self._cdmods_dir / "sources"
            mods = self._db.connection.execute(
                "SELECT id, name, source_path FROM mods").fetchall()
            missing = []
            for mod_id, name, source_path in mods:
                has_source = False
                src_dir = sources_dir / str(mod_id)
                if src_dir.exists():
                    try:
                        if any(src_dir.iterdir()):
                            has_source = True
                    except Exception:
                        pass
                if not has_source and source_path and Path(source_path).exists():
                    has_source = True
                if not has_source:
                    missing.append(name)

            if missing:
                names = "\n".join(f"  \u2022 {n}" for n in missing[:10])
                extra = f"\n  ...e mais {len(missing) - 10}" if len(missing) > 10 else ""
                QMessageBox.information(
                    self, "Mods Precisam Ser Reimportados",
                    f"Esses mods foram importados em uma versão mais antiga e não possuem\n"
                    f"arquivos-fonte salvos. Eles não podem ser atualizados ou reconfigurados\n"
                    f"automaticamente.\n\n"
                    f"{names}{extra}\n\n"
                    f"Para corrigir, remova cada mod e arraste o arquivo original novamente.\n"
                    f"Você só precisa fazer isso uma vez por mod."
                )

            config.set("missing_sources_checked", "1")
        except Exception as e:
            logger.debug("Verificação de fontes ausentes falhou: %s", e)

    def _on_fix_everything(self) -> None:
        """Correção com 1 clique: reverter, limpar backups, remover órfãos e re-escanear.

        Para usuários com estado corrompido que querem resolver de uma vez.
        """
        reply = QMessageBox.question(
            self, "Corrigir Estado do Jogo",
            "Antes de continuar, é altamente recomendado que você\n"
            "verifique seus arquivos pela Steam primeiro:\n\n"
            "  Steam > Clique direito em Crimson Desert > Propriedades\n"
            "  > Arquivos Instalados > Verificar integridade dos arquivos\n\n"
            "Após verificar, isso irá:\n"
            "1. Reverter todos os arquivos do jogo para o vanilla\n"
            "2. Limpar backups antigos\n"
            "3. Remover diretórios de mods órfãos\n"
            "4. Fazer uma nova varredura dos arquivos\n"
            "5. Reimportar todos os mods dos arquivos-fonte salvos\n\n"
            "Sua lista de mods é preservada.\n"
            "Você já verificou pela Steam?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        import shutil

        # Passo 1: Reverter
        self.statusBar().showMessage("Correção: revertendo para o vanilla...", 0)
        try:
            from cdumm.engine.apply_engine import RevertWorker
            from cdumm.storage.database import Database
            revert_db = Database(self._db.db_path)
            revert_db.initialize()
            rw = RevertWorker.__new__(RevertWorker)
            rw._game_dir = self._game_dir
            rw._vanilla_dir = self._vanilla_dir
            rw._db = revert_db
            rw._revert()
            revert_db.close()
        except Exception as e:
            logger.warning("Correção: falha ao reverter: %s", e)

        # Passo 2: Limpar backups
        if self._vanilla_dir and self._vanilla_dir.exists():
            shutil.rmtree(self._vanilla_dir, ignore_errors=True)
            self._vanilla_dir.mkdir(parents=True, exist_ok=True)

        # Passo 3: Remover diretórios órfãos
        for d in sorted(self._game_dir.iterdir()):
            if (d.is_dir() and d.name.isdigit() and len(d.name) == 4
                    and int(d.name) >= 36):
                snap_check = self._db.connection.execute(
                    "SELECT COUNT(*) FROM snapshots WHERE file_path LIKE ?",
                    (d.name + "/%",)).fetchone()[0]
                if snap_check == 0:
                    shutil.rmtree(d, ignore_errors=True)

        # Passo 4: Verificar se os arquivos estão realmente limpos antes de re-escanear
        files_clean = True
        try:
            papgt = self._game_dir / "meta" / "0.papgt"
            snap = self._db.connection.execute(
                "SELECT file_size FROM snapshots WHERE file_path = 'meta/0.papgt'"
            ).fetchone()
            if snap and papgt.exists() and papgt.stat().st_size != snap[0]:
                files_clean = False
        except Exception:
            pass

        if files_clean:
            self._on_refresh_snapshot(skip_verify_prompt=True)
            self._log_activity("fix",
                               "Corrigir Tudo: revertido, backups limpos, re-escaneando")
            self.statusBar().showMessage("Correção em andamento: re-escaneando arquivos do jogo...", 0)
        else:
            self._log_activity("fix",
                               "Corrigir Tudo: revertido e limpo, mas arquivos ainda modificados. "
                               "Verificação Steam necessária.")
            QMessageBox.warning(
                self, "Verificação Steam Necessária",
                "Os arquivos do jogo ainda estão modificados após a reversão.\n\n"
                "Isso significa que algumas alterações não puderam ser desfeitas automaticamente.\n"
                "Por favor verifique os arquivos do jogo pela Steam, depois volte aqui\n"
                "e clique em Corrigir Tudo novamente.\n\n"
                "Steam: Clique direito em Crimson Desert, Propriedades,\n"
                "Arquivos Instalados, Verificar integridade dos arquivos.")
            self.statusBar().showMessage(
                "Correção incompleta: Verificação Steam necessária, depois execute Corrigir Tudo.", 0)

    def _on_migrate_finished(self, reimported: int, failed: int) -> None:
        """Chamado após a migração em background ser concluída."""
        self._sync_db()

        # Restaurar estado enabled/priority dos mods
        mod_states = getattr(self, '_migrate_mod_states', [])
        for state in mod_states:
            try:
                row = self._db.connection.execute(
                    "SELECT id FROM mods WHERE name = ?",
                    (state["name"],)).fetchone()
                if row:
                    self._db.connection.execute(
                        "UPDATE mods SET enabled = ?, priority = ? WHERE id = ?",
                        (1 if state["enabled"] else 0, state["priority"], row[0]))
            except Exception:
                pass
        self._db.connection.commit()

        self._refresh_all()
        msg = f"Migração concluída: {reimported} mod(s) reimportados no novo formato."
        if failed:
            msg += f" {failed} mod(s) precisam de reimportação manual."
        self._log_activity("migrate", msg)
        self.statusBar().showMessage(msg, 15000)

    def _check_stale_appdata(self) -> None:
        """Detect stale data in %LocalAppData%/CDMod_Elite from old versions.

        Since v1.7.0, CDUMM stores everything in CDModsElite/ inside the game
        directory. Old %LocalAppData%/CDMod_Elite data can conflict or confuse
        users. Offer to clean it up.
        """
        try:
            from cdumm.storage.config import Config
            config = Config(self._db)
            if config.get("stale_appdata_checked"):
                return

            appdata_dir = Path.home() / "AppData" / "Local" / "CDMod_Elite"
            if not appdata_dir.exists():
                config.set("stale_appdata_checked", "1")
                return

            # Check if there's actual mod data (deltas, vanilla backups)
            has_stale = False
            for name in ["deltas", "vanilla", "cdumm.db"]:
                if (appdata_dir / name).exists():
                    has_stale = True
                    break

            if not has_stale:
                config.set("stale_appdata_checked", "1")
                return

            # NOTA: Não calculamos o tamanho via rglob — iterar sobre backups
            # grandes de arquivos de jogo pode bloquear o main thread por 5+ segundos.
            # A exibição do MB é puramente cosmética e foi removida por ser a causa
            # do stall identificado no frame_stalls.log (5032ms).

            # Marca como verificado ANTES de mostrar o diálogo.
            # Se o processo for encerrado durante o diálogo, o flag já foi salvo
            # e o diálogo não volta a aparecer na próxima execução.
            config.set("stale_appdata_checked", "1")
            try:
                self._db.connection.commit()
            except Exception:
                pass

            reply = _pergunta_br(
                self, "Dados Antigos Encontrados",
                f"Encontrados dados antigos de uma versão anterior do CDUMM em:\n"
                f"{appdata_dir}\n\n"
                f"Desde a v1.7.0, todos os dados de mods são armazenados na pasta CDModsElite\n"
                f"dentro do diretório do jogo. Estes dados antigos não são mais necessários.\n\n"
                f"Apagar para liberar espaço?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                import shutil
                for name in ["deltas", "vanilla", "cdumm.db"]:
                    target = appdata_dir / name
                    if target.is_dir():
                        shutil.rmtree(target, ignore_errors=True)
                    elif target.is_file():
                        target.unlink(missing_ok=True)
                self.statusBar().showMessage(
                    "Dados antigos removidos com sucesso.", 10000)
                self._log_activity("cleanup", "Removed stale AppData (old version)")


        except Exception as e:
            logger.debug("Stale appdata check failed: %s", e)

    def _check_program_files_warning(self) -> None:
        """Warn if game is installed under Program Files (admin restrictions). One-shot only."""
        try:
            if not self._game_dir:
                return

            game_path = str(self._game_dir).lower()
            if "program files" not in game_path:
                return

            # Sentinel file fallback — persists even if DB is not yet accessible
            _sentinel = self._app_data_dir / ".program_files_warned"
            if _sentinel.exists():
                return

            from cdumm.storage.config import Config
            config = Config(self._db)
            if config.get("program_files_warned"):
                _sentinel.touch()  # sync sentinel with DB flag
                return

            _warning_br(
                self, "Aviso de Local do Jogo",
                "Seu jogo está instalado em Arquivos de Programas, que possui\n"
                "permissões restritas de escrita no Windows.\n\n"
                "Isso pode causar problemas com backups de mods e configuração.\n"
                "Se enfrentar problemas, considere mover sua biblioteca Steam\n"
                "para outro local (ex. C:\\SteamLibrary).\n\n"
                "Steam → Configurações → Armazenamento → Adicionar nova pasta"
            )
            config.set("program_files_warned", "1")
            _sentinel.touch()  # persist sentinel regardless of DB success
        except Exception as e:
            logger.debug("Program Files warning check failed: %s", e)

    def _check_pamt_backups(self) -> None:
        """Detect missing full PAMT backups and create them or prompt for Steam verify.

        Older versions used range backups for PAMTs which can't fully restore
        vanilla. This checks every PAMT that mods touch and ensures a full
        backup exists. If the game file is currently vanilla (matches snapshot),
        the backup is created silently. If it's modded, the user is prompted.
        """
        if not self._db or not self._game_dir or not self._vanilla_dir:
            return
        if not self._snapshot or not self._snapshot.has_snapshot():
            return

        try:
            from cdumm.storage.config import Config
            config = Config(self._db)
            if config.get("pamt_backups_checked") == "1":
                return  # Already checked this install

            # Find all PAMT files that mods touch
            cursor = self._db.connection.execute(
                "SELECT DISTINCT file_path FROM mod_deltas "
                "WHERE file_path LIKE '%.pamt'")
            mod_pamts = [row[0] for row in cursor.fetchall()]
            if not mod_pamts:
                config.set("pamt_backups_checked", "1")
                return

            missing = []
            for pamt_path in mod_pamts:
                full_backup = self._vanilla_dir / pamt_path.replace("/", "\\")
                if not full_backup.exists():
                    missing.append(pamt_path)

            if not missing:
                config.set("pamt_backups_checked", "1")
                return

            # Try to create backups from current game files if they match snapshot
            from cdumm.engine.snapshot_manager import hash_file
            created = 0
            still_missing = []
            for pamt_path in missing:
                game_file = self._game_dir / pamt_path.replace("/", "\\")
                if not game_file.exists():
                    continue
                snap = self._db.connection.execute(
                    "SELECT file_hash, file_size FROM snapshots WHERE file_path = ?",
                    (pamt_path,)).fetchone()
                if not snap:
                    continue

                # Quick size check
                try:
                    if game_file.stat().st_size != snap[1]:
                        still_missing.append(pamt_path)
                        continue
                except OSError:
                    still_missing.append(pamt_path)
                    continue

                # Full hash check (PAMTs are small, <14MB)
                current_hash, _ = hash_file(game_file)
                if current_hash == snap[0]:
                    # Game file IS vanilla — create backup silently
                    backup_path = self._vanilla_dir / pamt_path.replace("/", "\\")
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    import shutil
                    shutil.copy2(game_file, backup_path)
                    created += 1
                    logger.info("Created missing PAMT backup: %s", pamt_path)
                else:
                    still_missing.append(pamt_path)

            if created:
                self._log_activity("backup",
                    f"Created {created} missing PAMT backup(s)",
                    "Upgraded from range backups to full backups")

            if still_missing:
                _info_br(
                    self, "Backup Original Incompleto",
                    f"{len(still_missing)} arquivo(s) PAMT estão atualmente modificados e têm "
                    f"nenhum backup original completo:\n\n"
                    + "\n".join(f"  {p}" for p in still_missing[:5])
                    + ("\n  ..." if len(still_missing) > 5 else "")
                    + "\n\nPara consertar isso:\n"
                    "1. Steam → Clique com botão direito em Crimson Desert → Propriedades\n"
                    "   → Arquivos Instalados → Verificar integridade dos arquivos\n"
                    "2. Reinicie o CDUMM — ele criará os backups ausentes\n\n"
                    "Até lá, a opção Reverter para Original pode não restaurar totalmente esses arquivos.",
                )
            else:
                config.set("pamt_backups_checked", "1")

        except Exception as e:
            logger.debug("PAMT backup check failed: %s", e)

    def _check_one_time_reset(self) -> bool:
        """One-time migrations when upgrading to a new major version.

        Each migration version is checked independently so users who skip
        versions still get all necessary migrations applied.
        """
        try:
            from cdumm.storage.config import Config
            config = Config(self._db)
            last_reset = config.get("last_reset_version") or ""

            # v1.0.7 migration: full reset (old format incompatible)
            if last_reset < "1.0.7":
                has_data = self._db.connection.execute(
                    "SELECT COUNT(*) FROM snapshots").fetchone()[0] > 0
                if not has_data:
                    config.set("last_reset_version", "1.3.0")
                    return False  # fresh install, nothing to reset

                from cdumm import __version__
                _info_br(
                    self, f"Elite BR v{__version__}",
                    "Esta atualização inclui correções importantes para o armazenamento de mods.\n\n"
                    "Antes de continuar, por favor verifique seus arquivos do jogo pela Steam:\n\n"
                    "  Steam → Clique com botão direito em Crimson Desert → Propriedades\n"
                    "  → Arquivos Instalados → Verificar integridade dos arquivos\n\n"
                    "Isto garante que seu jogo esteja em um estado limpo antes de escanear novamente.",
                )
                reply = _pergunta_br(
                    self, "Pronto para continuar?",
                    "Você verificou seus arquivos do jogo pela Steam?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    self.statusBar().showMessage(
                        "Por favor verifique os arquivos do jogo (Steam: Verificar Integridade / Xbox: Reparar), depois reinicie.", 0)
                    return True

                from cdumm.engine.version_detector import detect_game_version
                fp = detect_game_version(self._game_dir) or ""
                self._reset_for_game_update(fp)
                config.set("last_reset_version", "1.3.0")
                return True

            # v1.3.0 migration: purge stale vanilla backups
            if last_reset < "1.3.0":
                return self._migrate_v130(config)

            return False
        except Exception as e:
            logger.debug("One-time reset check failed: %s", e)
            return False

    def _migrate_v130(self, config) -> bool:
        """v1.3.0 migration: clean vanilla backups and rebuild from scratch.

        Previous versions could create dirty vanilla backups (taken from
        modded files) and stale PAPGT entries. This migration:
        1. Asks user to verify game files through Steam
        2. Deletes the vanilla backup folder (will be recreated clean)
        3. Cleans orphan mod directories (0036+)
        4. Clears snapshot (forces fresh rescan)
        5. Disables all mods (safe starting state)
        """
        import shutil
        from cdumm import __version__

        has_backups = self._vanilla_dir and self._vanilla_dir.exists()
        has_mods = self._db.connection.execute(
            "SELECT COUNT(*) FROM mods").fetchone()[0] > 0

        if not has_backups and not has_mods:
            config.set("last_reset_version", "1.3.0")
            return False  # nothing to migrate

        _info_br(
            self, f"Elite BR v{__version__} — Atualização Importante",
            "Esta atualização corrige como os backups originais são gerenciados.\n\n"
            "Seus backups existentes precisam ser reconstruídos do zero para\n"
            "garantir que a Reversão funcione corretamente.\n\n"
            "Por favor verifique seus arquivos do jogo pela Steam primeiro:\n\n"
            "  Steam → Clique com botão direito em Crimson Desert → Propriedades\n"
            "  → Arquivos Instalados → Verificar integridade dos arquivos\n\n"
            "Sua lista de mods será mantida — você apenas precisará aplicá-los novamente.",
        )
        reply = _pergunta_br(
            self, "Pronto para continuar?",
            "Você verificou seus arquivos do jogo pela Steam?\n\n"
            "Clique Sim para prosseguir com a limpeza.\n"
            "Clique Não para fazer depois (sugeriremos no próximo uso).",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            self.statusBar().showMessage(
                "Por favor verifique os arquivos do jogo (Steam: Verificar Integridade / Xbox: Reparar), depois reinicie.", 0)
            return True  # block startup but don't mark as done

        logger.info("v1.3.0 migration: cleaning vanilla backups")

        # Delete vanilla backup folder entirely
        if self._vanilla_dir and self._vanilla_dir.exists():
            shutil.rmtree(self._vanilla_dir, ignore_errors=True)
            logger.info("Deleted vanilla backup folder")

        # Clean orphan mod directories (0036+)
        if self._game_dir:
            for d in sorted(self._game_dir.iterdir()):
                if not d.is_dir() or not d.name.isdigit() or len(d.name) != 4:
                    continue
                if int(d.name) >= 36:
                    shutil.rmtree(d, ignore_errors=True)
                    logger.info("Removed orphan directory: %s", d.name)

        # Clear snapshot (forces fresh scan from verified files)
        try:
            self._db.connection.execute("DELETE FROM snapshots")
            self._db.connection.commit()
        except Exception:
            pass

        # Disable all mods (they'll be re-applied after rescan)
        try:
            self._db.connection.execute("UPDATE mods SET enabled = 0")
            self._db.connection.commit()
        except Exception:
            pass

        config.set("last_reset_version", "1.3.0")

        # Trigger fresh snapshot (user already confirmed Steam verify)
        self._refresh_all()
        self._on_refresh_snapshot(skip_verify_prompt=True)

        _info_br(
            self, "Limpeza Concluída",
            "Os backups originais foram redefinidos.\n\n"
            "Seus mods ainda estão listados, mas desativados.\n"
            "Ative-os e clique em Aplicar para reconstruir as pastas.",
        )
        return True

    def _check_game_updated(self) -> bool:
        """Detect if the game was updated since last launch.

        Compares PAMT fingerprints. If changed, wipes all mod data
        (backups, deltas, snapshot, database) and forces a fresh start.
        Returns True if a reset was triggered.
        """
        try:
            from cdumm.engine.version_detector import detect_game_version
            from cdumm.storage.config import Config
            config = Config(self._db)

            current = detect_game_version(self._game_dir)
            if not current:
                return False

            stored = config.get("game_version_fingerprint")
            game_changed = False

            if stored is None:
                # First time with this feature — save fingerprint.
                config.set("game_version_fingerprint", current)
                return False
            elif stored == current:
                return False
            else:
                logger.info("Game fingerprint changed: %s -> %s", stored, current)

            # Try to get the Steam build ID for a more informative message
            from cdumm.engine.version_detector import get_steam_build_id
            build_id = get_steam_build_id(self._game_dir)
            build_info = f" (Steam build {build_id})" if build_id else ""

            from cdumm.gui.msg_box_br import _warning_br
            _warning_br(
                self, "⚠️ Verificação de Sistemas",
                f"Atualização do Crimson Desert Detectada{build_info}.\n\n"
                "Os sistemas do Elite BR precisarão ser recalibrados para a nova versão.\n"
                "Para evitar corrompimento de Saves, sua lista de Mods foi temporariamente suspensa.\n\n"
                "Aviso Tático: Grandes atualizações e Hotfixes oficiais podem alterar as chaves da Engine. "
                "Caso seus mods voltem a falhar, aguarde até que os autores atualizem as matrizes no NexusMods.",
            )
            self._reset_for_game_update(current)
            return True
        except Exception as e:
            logger.debug("Game update check failed: %s", e)
            return False

    def _snapshot_stale(self) -> bool:
        """Check if stored snapshot hashes match actual game files.

        Skips files modified by enabled mods (those are expected to differ).
        Checks PAMT files and samples PAZ files from unmodded directories.

        IMPORTANT: If a mismatched file has a vanilla backup, it was
        previously modified by a mod — NOT by a Steam update. Don't
        count these as stale (they'll be fixed by the apply safety net).
        """
        try:
            from cdumm.engine.snapshot_manager import hash_file
            import os

            # Get files that enabled mods modify — these are expected to differ
            modded = self._db.connection.execute(
                "SELECT DISTINCT md.file_path FROM mod_deltas md "
                "JOIN mods m ON md.mod_id = m.id WHERE m.enabled = 1"
            ).fetchall()
            modded_set = {row[0] for row in modded}
            modded_set.add("meta/0.papgt")

            # Build set of files that have vanilla backups (previously modded)
            backed_up = set()
            if self._vanilla_dir and self._vanilla_dir.exists():
                for f in self._vanilla_dir.rglob("*"):
                    if not f.is_file():
                        continue
                    if f.name.endswith(".vranges"):
                        rel = f.name[:-len(".vranges")].replace("_", "/")
                    else:
                        rel = str(f.relative_to(self._vanilla_dir)).replace("\\", "/")
                    backed_up.add(rel)

            cursor = self._db.connection.execute(
                "SELECT file_path, file_hash FROM snapshots ORDER BY file_path")
            all_rows = cursor.fetchall()
            if not all_rows:
                return False

            priority = []
            others = []
            for row in all_rows:
                if row[0] in modded_set:
                    continue
                if row[0].endswith(".pamt"):
                    priority.append(row)
                else:
                    others.append(row)

            step = max(1, len(others) // 10)
            to_check = priority + others[::step]

            if not to_check:
                return False

            for file_path, snap_hash in to_check:
                game_file = self._game_dir / file_path.replace("/", os.sep)
                if not game_file.exists():
                    logger.info("Stale snapshot: %s missing", file_path)
                    return True
                current_hash, _ = hash_file(game_file)
                if current_hash != snap_hash:
                    # If this file has a vanilla backup, it was modded by a
                    # removed mod — NOT a game update. Don't trigger refresh.
                    if file_path in backed_up:
                        logger.info("Snapshot mismatch for %s but backup exists "
                                    "— orphaned mod file, not stale", file_path)
                        continue
                    logger.info("Stale snapshot: %s hash mismatch", file_path)
                    return True
            return False
        except Exception as e:
            logger.debug("Snapshot stale check failed: %s", e)
            return False

    def _reset_for_game_update(self, new_fingerprint: str) -> None:
        """Reset for a new game version while KEEPING mod data.

        Mod deltas and DB entries are preserved — users just need to
        re-enable and Apply after the rescan. Only vanilla backups and
        snapshot are cleared (they're version-specific).
        """
        import shutil
        from cdumm.storage.config import Config

        # Step 1: Clean up orphan mod directories (0036+) from game dir
        # These were created by mods — the new game version won't have them
        for d in self._game_dir.iterdir():
            if not d.is_dir() or not d.name.isdigit() or len(d.name) != 4:
                continue
            if int(d.name) >= 36:
                shutil.rmtree(d, ignore_errors=True)
                logger.info("Removed orphan mod directory: %s", d.name)

        # Step 2: Clear vanilla backups (they're for the old game version)
        if self._vanilla_dir.exists():
            shutil.rmtree(self._vanilla_dir, ignore_errors=True)
            logger.info("Cleared vanilla backups (old game version)")

        # Step 3: Clear snapshot (needs fresh rescan against new game files)
        self._db.connection.execute("DELETE FROM snapshots")
        try:
            self._db.connection.execute("DELETE FROM conflicts")
        except Exception:
            pass

        # Step 4: Clear old deltas (they're against the old vanilla)
        if self._deltas_dir.exists():
            shutil.rmtree(self._deltas_dir, ignore_errors=True)
            self._deltas_dir.mkdir(parents=True, exist_ok=True)
        self._db.connection.execute("DELETE FROM mod_deltas")

        # Step 5: Disable all mods
        self._db.connection.execute("UPDATE mods SET enabled = 0")
        self._db.connection.commit()
        logger.info("Game update: cleared backups/deltas/snapshot, disabled mods")

        # Step 6: Auto-reimport mods from stored sources (after rescan completes).
        # This is deferred — the rescan callback will trigger _auto_reimport_mods.
        sources_dir = self._cdmods_dir / "sources"
        if sources_dir.exists() and any(sources_dir.iterdir()):
            self._pending_auto_reimport = True
            logger.info("Auto-reimport scheduled: %d mod sources found",
                        sum(1 for _ in sources_dir.iterdir()))

        # Save new fingerprint
        config = Config(self._db)
        config.set("game_version_fingerprint", new_fingerprint)
        config.set("backups_verified", "0")

        # Refresh UI
        self._snapshot = SnapshotManager(self._db)
        self._refresh_all()
        self._snapshot_applied_state()

        # Automatically take a fresh snapshot
        self._on_refresh_snapshot_for_update()

    def _on_refresh_snapshot_for_update(self) -> None:
        """Take a snapshot automatically after game update reset."""
        if not self._db or not self._game_dir:
            return
        if self._snapshot_in_progress:
            return
        self._snapshot_in_progress = True
        progress = ProgressDialog("Buscando novos arquivos do jogo...", self)
        worker = SnapshotWorker(self._game_dir, self._db.db_path)
        worker.activity.connect(self._log_activity)
        thread = QThread()
        self._run_worker(worker, thread, progress,
                         on_finished=self._on_update_snapshot_finished)

    def _on_update_snapshot_finished(self, count: int) -> None:
        """Snapshot after game update is done."""
        self._on_snapshot_finished(count)
        # Count mods that need re-importing
        mod_count = 0
        mod_names = []
        if self._mod_manager:
            mods = self._mod_manager.list_mods()
            mod_count = len(mods)
            mod_names = [m["name"] for m in mods[:10]]
        if mod_count:
            names_str = "\n".join(f"  - {n}" for n in mod_names)
            if mod_count > 10:
                names_str += f"\n  ... and {mod_count - 10} more"
            _info_br(
                self, "Pronto",
                f"Arquivos do jogo verificados ({count} arquivos).\n\n"
                f"Você tem {mod_count} mod(s) que precisam ser reimportados:\n\n"
                f"{names_str}\n\n"
                "Arraste cada mod para o aplicativo para reimportá-lo."
            )
        else:
            _info_br(
                self, "Pronto",
                f"Arquivos do jogo verificados ({count} arquivos).\n\n"
                "Agora você pode importar mods arrastando-os para o aplicativo."
            )

    def _check_bad_standalone_imports(self) -> None:
        """Detect mods imported by v1.0.0 as broken standalone PAZ copies.

        v1.0.0 stored JSON patch mods as full 954MB PAZ copies in new directories
        instead of small byte-level deltas. These cause game crashes.
        Telltale: is_new=1 delta for a .paz file >100MB.
        """
        if getattr(self, "_legacy_checked", False):
            return
        self._legacy_checked = True
        
        if not self._db:
            return
        try:
            cursor = self._db.connection.execute("""
                SELECT DISTINCT m.id, m.name, md.file_path
                FROM mod_deltas md JOIN mods m ON md.mod_id = m.id
                WHERE md.is_new = 1 AND md.file_path LIKE '%%.paz'
                  AND md.byte_end > 100000000
            """)
            bad_mods = {}
            for mid, name, fpath in cursor.fetchall():
                bad_mods[mid] = name

            if not bad_mods:
                return

            # Legacy check: just log, no status bar message shown
            names = ", ".join(bad_mods.values())
            logger.warning("Legacy v1.0.0 bad imports detected: %s", names)
        except Exception as e:
            logger.debug("Bad standalone check failed: %s", e)

    def _on_bad_import_cleanup(self) -> None:
        """After revert completes, remove bad mods and disable all."""
        if hasattr(self, '_bad_import_ids'):
            names = []
            for mid in self._bad_import_ids:
                try:
                    details = self._mod_manager.get_mod_details(mid)
                    names.append(details["name"] if details else str(mid))
                except Exception:
                    names.append(str(mid))
                self._mod_manager.remove_mod(mid)
                logger.info("Removed bad standalone import: id=%d", mid)
            count = len(self._bad_import_ids)
            del self._bad_import_ids
            # Disable all mods since we reverted to vanilla
            for m in self._mod_manager.list_mods():
                if m["enabled"]:
                    self._mod_manager.set_enabled(m["id"], False)
            self._refresh_all()
            self._snapshot_applied_state()
            _info_br(
                self, "Limpeza Concluída",
                f"Removidos {count} mod(s) quebrado(s):\n"
                + "\n".join(f"  - {n}" for n in names) +
                "\n\nTodos os mods foram desativados. Ative seus mods, "
                "clique em Aplicar e então reimporte os mods removidos."
            )

    def _check_game_version_mismatches(self) -> None:
        """Warn about mods imported for a different game version."""
        try:
            from cdumm.engine.version_detector import detect_game_version
            current = detect_game_version(self._game_dir)
            if not current:
                return
            cursor = self._db.connection.execute(
                "SELECT name, game_version_hash FROM mods WHERE game_version_hash IS NOT NULL AND enabled = 1")
            mismatched = [name for name, ver in cursor.fetchall() if ver and ver != current]
            if mismatched:
                self.statusBar().showMessage(
                    f"Aviso: {len(mismatched)} mod(s) importados para uma versão diferente do jogo: "
                    + ", ".join(mismatched[:3])
                    + ("..." if len(mismatched) > 3 else ""), 15000)
        except Exception as e:
            logger.debug("Version mismatch check failed: %s", e)

    def _purge_corrupted_backups(self) -> None:
        """One-time check: run background worker to verify and purge corrupted backups."""
        config = Config(self._db)
        if config.get("backups_verified") == "1":
            return
        if not self._vanilla_dir.exists():
            config.set("backups_verified", "1")
            return

        from cdumm.gui.workers import BackupVerifyWorker
        progress = ProgressDialog("Verificando backups originais...", self)
        worker = BackupVerifyWorker(self._vanilla_dir, self._db.db_path)
        thread = QThread()
        self._run_worker(worker, thread, progress,
                         on_finished=self._on_backup_verify_done)

    def _on_backup_verify_done(self, purged_count: int) -> None:
        self._sync_db()
        config = Config(self._db)
        config.set("backups_verified", "1")
        if purged_count and purged_count > 0:
            self.statusBar().showMessage(
                f"Removido(s) {purged_count} backup(s) originais corrompidos", 10000)
        config.set("backups_verified", "1")

    def _auto_snapshot_first_run(self) -> None:
        reply = _pergunta_br(
            self, "Primeira Execução — Criar Registro",
            "Nenhum registro original existe ainda. Um registro é necessário antes que você possa importar mods.\n\n"
            "Isto vai escanear todos os arquivos do jogo e pode demorar alguns minutos.\n\n"
            "Criar registro agora?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._on_refresh_snapshot()

    def _build_ui(self) -> None:
        from PySide6.QtWidgets import QFrame, QStackedWidget, QHeaderView
        from PySide6.QtCore import QSortFilterProxyModel, QPointF, QRectF
        from PySide6.QtGui import (
            QColor, QLinearGradient, QPainter, QPainterPath,
            QBrush, QPen, QRadialGradient,
        )
        from cdumm.gui.mod_list_model import (
            COL_ENABLED, COL_ORDER, COL_NAME, COL_AUTHOR, COL_VERSION,
            COL_STATUS, COL_FILES, COL_DATE,
        )
        from cdumm.gui.logo_widget import GemLogo

        # ── ContentBackdrop cobre TODA a janela (sidebar + conteúdo) ──
        from cdumm.gui.dashboard_panel import ContentBackdrop
        from cdumm.gui.premium_buttons import PremiumNeonButton
        
        central = ContentBackdrop()
        self.setCentralWidget(central)
        main_h = QHBoxLayout(central)
        main_h.setContentsMargins(0, 0, 0, 0)
        main_h.setSpacing(0)

        # ── Sidebar Premium v3 ─────────────────────────────────────────────────
        # Classes de suporte para o novo sidebar
        class _GradSep(QWidget):
            def __init__(self, par=None):
                super().__init__(par)
                self.setFixedHeight(1)
                self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            def paintEvent(self, _):
                p = QPainter(self)
                g = QLinearGradient(0, 0, self.width(), 0)
                g.setColorAt(0.00, QColor(0, 0, 0, 0))
                g.setColorAt(0.12, QColor(0x7A, 0x2A, 0x22, 200))
                g.setColorAt(0.88, QColor(0x7A, 0x2A, 0x22, 200))
                g.setColorAt(1.00, QColor(0, 0, 0, 0))
                p.fillRect(self.rect(), QBrush(g))
                p.end()

        class _NavItem(QWidget):
            """Item de navegação premium desenhado via QPainter vetorial."""
            from PySide6.QtCore import Signal as _Signal
            clicked_label = _Signal(str)

            def __init__(self, label: str, disp: str, active: bool = False, par=None):
                super().__init__(par)
                self._label  = label
                self._disp   = disp
                self._active = active
                self._hovered = False
                self.setFixedHeight(50)
                self.setCursor(Qt.CursorShape.PointingHandCursor)
                self.setAttribute(Qt.WidgetAttribute.WA_Hover)

            def set_active(self, v: bool):
                if self._active != v:
                    self._active = v
                    self.update()

            def enterEvent(self, e):
                self._hovered = True
                self.update()
                super().enterEvent(e)

            def leaveEvent(self, e):
                self._hovered = False
                self.update()
                super().leaveEvent(e)

            def mousePressEvent(self, e):
                if e.button() == Qt.MouseButton.LeftButton:
                    self.clicked_label.emit(self._label)
                super().mousePressEvent(e)

            def paintEvent(self, _):
                from PySide6.QtGui import QPainter, QColor, QFont, QPen, QPainterPath, QLinearGradient, QPolygonF
                from PySide6.QtCore import Qt, QRectF, QPointF
                p = QPainter(self)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                w, h = self.width(), self.height()
                
                # Barra Escudo (Glass Hover) FACA QUENTE
                if self._active:
                    bg = QLinearGradient(0, 0, w, 0)
                    bg.setColorAt(0.0, QColor(229, 20, 20, 45))
                    bg.setColorAt(0.8, QColor(229, 20, 20, 0))
                    slash = QPolygonF([
                        QPointF(0, 0),
                        QPointF(w - 20, 0),
                        QPointF(w, h),
                        QPointF(0, h)
                    ])
                    path = QPainterPath()
                    path.addPolygon(slash)
                    p.fillPath(path, QBrush(bg))
                elif self._hovered:
                    p.fillRect(0, 0, w, h, QColor(255, 255, 255, 6))

                # Placa Indicadora Ativa Neon
                if self._active:
                    glow = QLinearGradient(0, 0, 0, h)
                    glow.setColorAt(0.0, QColor("#FF6E1A"))
                    glow.setColorAt(1.0, QColor("#E51414"))
                    p.fillRect(0, 8, 4, h - 16, glow)
                    
                # Cyber-Glyphs
                p.save()
                p.translate(28, h / 2)
                p_c = QColor("#FF6E1A") if self._active else QColor(255, 255, 255, 80)
                p_c_hover = QColor("#E51414")
                
                if self._label == "Painel":
                    p.setPen(QPen(p_c, 1.5))
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    h_poly = QPolygonF([QPointF(0,-5), QPointF(4,-2), QPointF(4,2), QPointF(0,5), QPointF(-4,2), QPointF(-4,-2)])
                    p.drawPolygon(h_poly)
                    if self._active: p.fillRect(-1,-1, 2, 2, QColor("#FF6E1A"))
                    elif self._hovered: p.fillRect(-1,-1, 2, 2, p_c_hover)
                elif self._label in ["PAZ Mods", "ASI Mods"]:
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(p_c if not self._hovered else QColor("#FFFFFF"))
                    if self._active: p.setBrush(QColor("#FF6E1A"))
                    p.drawRect(-4, -4, 2, 8)
                    p.drawRect(-1, -2, 2, 6)
                    p.drawRect(2, 0, 2, 4)
                elif self._label == "Tools":
                    p.setPen(QPen(p_c if not self._hovered else QColor("#FFFFFF"), 1.2))
                    if self._active: p.setPen(QPen(QColor("#FF6E1A"), 1.2))
                    p.drawEllipse(QPointF(0,0), 3.5, 3.5)
                    p.drawLine(-6, 0, -2, 0)
                    p.drawLine(2, 0, 6, 0)
                    p.drawLine(0, -6, 0, -2)
                    p.drawLine(0, 2, 0, 6)
                else:
                    p.rotate(45)
                    p.setPen(QPen(p_c, 1.5))
                    p.drawRect(-3, -3, 6, 6)
                    if self._hovered and not self._active:
                        p.setBrush(p_c_hover)
                        p.setPen(Qt.PenStyle.NoPen)
                        p.drawRect(-1, -1, 2, 2)
                p.restore()

                font_weight = QFont.Weight.Bold if self._active else QFont.Weight.Bold
                p.setFont(QFont("Consolas" if self._active else "Segoe UI", 9 if self._active else 9, font_weight))
                txt_x = 52
                
                # Texto
                if self._active:
                    p.setPen(QColor("#FFFFFF"))
                    p.drawText(txt_x, 0, w - txt_x, h, Qt.AlignmentFlag.AlignVCenter, self._disp.upper())
                elif self._hovered:
                    p.setPen(QColor("#DDD6E8"))
                    p.drawText(txt_x, 0, w - txt_x, h, Qt.AlignmentFlag.AlignVCenter, self._disp)
                else:
                    p.setPen(QColor("#8A8298")) 
                    p.drawText(txt_x, 0, w - txt_x, h, Qt.AlignmentFlag.AlignVCenter, self._disp)
                    
                p.end()

        class _PremiumSidebar(QWidget):
            """Sidebar semi-transparente HUD Operator — flutuante."""
            def __init__(self, par=None):
                super().__init__(par)
                self.setFixedWidth(236)
                self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

            def paintEvent(self, _):
                from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient, QRadialGradient, QPainterPath
                from PySide6.QtCore import Qt, QRectF
                p = QPainter(self)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                w, h = self.width(), self.height()
                
                rect = QRectF(16, 16, w - 16, h - 32)
                
                # Overlay escuro principal (permite a imagem vazar) com border-radius
                bg = QLinearGradient(0, 16, 0, h - 16)
                bg.setColorAt(0.00, QColor(9,  5, 11, 230))
                bg.setColorAt(0.38, QColor(6,  3,  8, 210))
                bg.setColorAt(1.00, QColor(4,  2,  6, 240))
                
                path = QPainterPath()
                path.addRoundedRect(rect, 10, 10)
                p.fillPath(path, QBrush(bg))
                
                # Borda neon fina 
                p.setPen(QPen(QColor(229, 20, 20, 60), 1.0))
                p.drawPath(path)

                # Bloom vermelho no topo (aura do logo superior)
                bloom = QRadialGradient(w * 0.50, 16, w * 1.15)
                bloom.setColorAt(0.00, QColor(195, 48, 24, 72))
                bloom.setColorAt(0.35, QColor(145, 28, 14, 28))
                bloom.setColorAt(1.00, QColor(0, 0, 0, 0))
                p.fillPath(path, QBrush(bloom))
                
                # Pulso Central do Logo ("Engine Core")
                reactor = QRadialGradient((w/2) + 8, 125, 120)
                reactor.setColorAt(0.0, QColor(229, 20, 20, 35))
                reactor.setColorAt(1.0, QColor(0, 0, 0, 0))
                
                glass = QPainterPath()
                glass.addRoundedRect(QRectF(26, 26, w - 36, 190), 10, 10)
                p.fillPath(glass, QBrush(reactor))
                p.fillPath(glass, QBrush(QColor(255, 255, 255, 5)))
                p.setPen(QPen(QColor(200, 60, 30, 20), 0.9))
                p.drawPath(glass)
                
                p.end()

        sidebar = _PremiumSidebar()
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(16, 16, 0, 16)
        sb_layout.setSpacing(0)

        # --- Logo panel (mantém o GemLogo/ícone original) ---
        logo_w = QWidget()
        logo_w.setFixedHeight(235)
        logo_w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        logo_lv = QVBoxLayout(logo_w)
        # Bate nela pela direita com 38px para empurrar quase 2 centímetros pra esquerda
        logo_lv.setContentsMargins(0, 0, 0, 25)
        logo_lv.setSpacing(0)
        logo_lv.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Reduzido de 235 pra 205 (se ela ficar em 235 ela ignora a margem pq já ocupou todo e espaço máximo)
        gem = GemLogo(size=215)
        gem.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        logo_lv.addWidget(gem, 0, Qt.AlignmentFlag.AlignCenter)
        
        sb_layout.addWidget(logo_w)

        # Separador premium
        sb_layout.addWidget(_GradSep())
        sb_layout.addSpacing(2)
        sb_layout.addWidget(_GradSep())
        sb_layout.addSpacing(16)

        # --- Nav items premium HUD Operator ---
        self._nav_buttons = []
        self._nav_items: dict[str, _NavItem] = {}
        
        _NAV_UI = {
            "Painel":   ("Painel", "Status Central e Telemetria da Engine"),
            "PAZ Mods": ("Gerenciar Mods", "Repositório Mestre de Assinaturas PAZ"),
            "ASI Mods": ("Plugins ASI", "Injeção Dinâmica de bibliotecas ASI"),
            "Log":      ("Log de Sistema", "Terminal de Histórico"),
            "Tools":    ("Configurações", "Ferramentas de Diagnóstico"),
            "About":    ("Sobre", "Database de Copyright e Engine"),
        }

        nav_wrap = QWidget()
        nav_wrap.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        nv = QVBoxLayout(nav_wrap)
        nv.setContentsMargins(6, 0, 6, 0)
        nv.setSpacing(4)

        for label in ["Painel", "PAZ Mods", "ASI Mods", "Log", "Tools", "About"]:
            disp, tooltip = _NAV_UI[label]
            item = _NavItem(label, disp, active=(label == "Painel"))
            item.setToolTip(tooltip)
            item.clicked_label.connect(lambda lbl: self._on_nav(lbl))
            nv.addWidget(item)
            self._nav_items[label] = item
            # Mantém _nav_buttons como lista de tuplas (label, item) para
            # compatibilidade com código legado que itera sobre ela
            self._nav_buttons.append((label, item))

        nv.addStretch()
        sb_layout.addWidget(nav_wrap, 1)

        from cdumm import __version__
        ver_lbl = QLabel(f"[ v{__version__} ]")
        ver_lbl.setObjectName("sidebarVersion")
        ver_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver_lbl.setStyleSheet(
            "color: #FF6E1A; font-family:'Consolas','Bahnschrift'; font-size:10px;"
            "font-weight:700; letter-spacing:2px; background:transparent;"
            "border-top: 1px solid rgba(255, 110, 26, 0.2); padding-top: 5px;"
        )
        sb_layout.addWidget(ver_lbl)
        sb_layout.addSpacing(22)

        main_h.addWidget(sidebar)

        # ── Área de conteúdo é agora um QWidget transparente ──
        # (o fundo já vem do ContentBackdrop que é o central widget)
        content_widget = QWidget()
        content_widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        content_widget.setAutoFillBackground(False)
        content_v = QVBoxLayout(content_widget)
        content_v.setContentsMargins(0, 0, 0, 0)
        content_v.setSpacing(0)

        # ── Section Header (Etapa 2) ── Premium Glass
        class _PremiumHeader(QWidget):
            def __init__(self, par=None):
                super().__init__(par)
                self.setFixedHeight(82)
                self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
                
            def paintEvent(self, _):
                p = QPainter(self)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                w, h = self.width(), self.height()
                
                # Fundo escuro do cabeçalho (Você pode editar as cores e a opacidade aqui)
                bg = QLinearGradient(0, 0, 0, h)
                bg.setColorAt(0.00, QColor(9,  5, 11, 100)) # 215 é o nível de escuro (0 a 255)
                bg.setColorAt(0.40, QColor(6,  3,  8, 200))
                bg.setColorAt(1.00, QColor(4,  2,  6, 150))
                p.fillRect(self.rect(), QBrush(bg))
                
                # Fio vermelho separador inferior (igual à borda direita do sidebar)
                edge = QLinearGradient(0, 0, w, 0)
                edge.setColorAt(0.00, QColor(75, 16, 10,  48))
                edge.setColorAt(0.20, QColor(155, 38, 24, 152))
                edge.setColorAt(0.80, QColor(155, 38, 24, 152))
                edge.setColorAt(1.00, QColor(75, 16, 10,  48))
                p.fillRect(0, h - 1, w, 1, QBrush(edge))
                
                # Painel glass ao redor de todo o cabeçalho
                glass = QPainterPath()
                # 8px de margem, raio=10
                glass.addRoundedRect(QRectF(8, 8, w - 16, h - 16), 10, 10)
                p.fillPath(glass, QBrush(QColor(255, 255, 255, 5)))
                p.setPen(QPen(QColor(200, 60, 30, 20), 0.9))
                p.drawPath(glass)
                
                p.end()

        _header = _PremiumHeader()
        _hh = QHBoxLayout(_header)
        _hh.setContentsMargins(28, 12, 22, 12)
        _hh.setSpacing(0)

        _tv = QVBoxLayout()
        _tv.setSpacing(4)

        _title_lbl = QLabel("GERENCIADOR DE MODS")
        _title_lbl.setObjectName("headerTitle")
        _tv.addWidget(_title_lbl)

        self._header_stats = QLabel("Crimson Desert  ·  Carregando...")
        self._header_stats.setObjectName("headerStats")
        _tv.addWidget(self._header_stats)

        _hh.addLayout(_tv)
        _hh.addStretch()
        _hh.addSpacing(16)
        for _obj, _lbl, _slot in [
            ("btnImportar",    "📑  Importar Pasta de Mod",  self._on_import_clicked),
            ("btnSincronizar", "⚡  Aplicar",               self._on_apply),
            ("btnJogar",       "▶  INICIAR JOGO",           self._on_launch_game),
        ]:
            _b = PremiumNeonButton(_lbl)
            _b.setObjectName(_obj)
            _b.clicked.connect(_slot)   # ── A1: fix — was missing
            if _obj == "btnSincronizar":
                self.apply_btn = _b
            _hh.addWidget(_b)
            _hh.addSpacing(8)

        content_v.addWidget(_header)

        # Drop zone (compact)
        self._import_widget = ImportWidget()
        self._import_widget.file_dropped.connect(self._on_import_dropped)
        content_v.addWidget(self._import_widget)

        # Stacked pages — o Painel (0) é transparente, as outras ganham shade
        class _OverlayStackedWidget(QStackedWidget):
            def paintEvent(self, e):
                if self.currentIndex() != 0:
                    p = QPainter(self)
                    p.fillRect(self.rect(), QColor(6, 4, 11, 185))
                    p.end()
                super().paintEvent(e)

        self._pages = _OverlayStackedWidget()
        self._pages.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # ── Page 0: Painel (Dashboard) ──
        from cdumm.gui.dashboard_panel import DashboardPanel
        self._dashboard_panel = DashboardPanel(self)
        self._dashboard_panel.launch_requested.connect(self._on_launch_game)
        # Passo 2: card clicks navigate to their target page
        self._dashboard_panel.navigate_requested.connect(self._on_nav)
        self._dashboard_panel.revert_requested.connect(self._on_refresh_snapshot)
        self._pages.addWidget(self._dashboard_panel)

        # ── Page 1: Mods ──
        mods_page = QWidget()
        mods_page.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        mods_page.setAutoFillBackground(False)
        mods_v = QVBoxLayout(mods_page)
        mods_v.setContentsMargins(0, 0, 0, 0)
        mods_v.setSpacing(0)

        # ── COMANDO CENTRAL (Top Bar) ──
        mods_top_w = QWidget()
        mods_top_w.setStyleSheet("""
            QWidget {
                background: rgba(12, 8, 14, 0.4);
                border-bottom: 1px solid rgba(255, 110, 26, 0.2);
            }
        """)
        mods_top_h = QHBoxLayout(mods_top_w)
        mods_top_h.setContentsMargins(20, 12, 20, 12)
        mods_top_h.setSpacing(12)
        
        lbl_mod_title = QLabel("GERENCIADOR DE MODS")
        lbl_mod_title.setStyleSheet("""
            color: #E0D4D8; font-family: 'Bahnschrift'; font-size: 15px; 
            font-weight: 800; letter-spacing: 1.5px; background: transparent; border: none;
        """)
        mods_top_h.addWidget(lbl_mod_title)
        
        mods_top_h.addStretch()
        
        from PySide6.QtWidgets import QLineEdit
        self.mod_search_input = QLineEdit()
        self.mod_search_input.setPlaceholderText("PESQUISAR MOD...")
        self.mod_search_input.setFixedWidth(240)
        self.mod_search_input.setFixedHeight(34)
        self.mod_search_input.setStyleSheet("""
            QLineEdit {
                background: rgba(0, 0, 0, 0.5);
                border: 1px solid rgba(229, 20, 20, 0.3);
                border-radius: 4px;
                color: #FFFFFF; font-family: 'Segoe UI'; font-size: 12px;
                font-weight: 600; padding: 0 12px; letter-spacing: 0.5px;
            }
            QLineEdit:focus {
                border: 1px solid rgba(255, 110, 26, 0.8);
                background: rgba(26, 8, 8, 0.6);
            }
        """)
        mods_top_h.addWidget(self.mod_search_input)

        self.btn_toggle_all = PremiumNeonButton("✓  LIGAR / DESLIGAR TUDO")
        self.btn_toggle_all.setFixedHeight(34)
        self.btn_toggle_all.clicked.connect(self._toggle_all_mods)
        mods_top_h.addWidget(self.btn_toggle_all)
        mods_v.addWidget(mods_top_w)

        splitter = QSplitter(Qt.Orientation.Vertical)

        if self._mod_manager and self._conflict_detector:
            self._mod_list_model = ModListModel(
                self._mod_manager, self._conflict_detector,
                game_dir=self._game_dir, db_path=self._db.db_path,
                deltas_dir=self._deltas_dir)
            self._mod_list_model.mod_toggled.connect(self._on_mod_toggled_via_checkbox)
            self._mod_list_model.mod_toggled.connect(lambda *_: self._set_pending_changes(True))
            # ── Update header stats once model is loaded ──
            self._update_dashboard_stats()

            class _CheckHeader(QHeaderView):
                toggle_requested = Signal()
                _label = "☐"

                def __init__(self, orientation, parent=None):
                    super().__init__(orientation, parent)
                    self.setSectionsClickable(True)

                def mousePressEvent(self, event):
                    if self.logicalIndexAt(event.pos()) == 0:
                        self.toggle_requested.emit()
                        event.accept()
                        return
                    super().mousePressEvent(event)

                def set_label(self, label: str):
                    self._label = label
                    if self.model():
                        self.model().setHeaderData(
                            0, Qt.Orientation.Horizontal, label)
                    self.viewport().update()

            from PySide6.QtCore import QSortFilterProxyModel
            class _NumericSortProxy(QSortFilterProxyModel):
                def lessThan(self, left, right):
                    from cdumm.gui.mod_list_model import COL_ORDER, COL_FILES
                    col = left.column()
                    if col in (COL_ORDER, COL_FILES):
                        try:
                            return int(left.data() or 0) < int(right.data() or 0)
                        except (ValueError, TypeError):
                            pass
                    return super().lessThan(left, right)

            self._sort_proxy = _NumericSortProxy()
            self._sort_proxy.setSourceModel(self._mod_list_model)
            
            # --- Configuração da Barra de Pesquisa ---
            self._sort_proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self._sort_proxy.setFilterRole(Qt.ItemDataRole.DisplayRole)
            self._sort_proxy.setFilterKeyColumn(2) # Coluna 2 é COL_NAME no ModListModel
            self.mod_search_input.textChanged.connect(self._sort_proxy.setFilterFixedString)
            # -----------------------------------------
            
            self._mod_list = QListView()
            self._mod_list.setModel(self._sort_proxy)
            
            from cdumm.gui.fast_mod_card_delegate import FastModCardDelegate
            self._mod_list.setItemDelegate(FastModCardDelegate(self._mod_list))
            
            self._mod_list.setSelectionMode(QListView.SelectionMode.ExtendedSelection)
            self._mod_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self._mod_list.customContextMenuRequested.connect(self._show_mod_context_menu)
            self._mod_list.setDragEnabled(True)
            self._mod_list.setAcceptDrops(True)
            self._mod_list.setDropIndicatorShown(True)
            self._mod_list.setDragDropMode(QListView.DragDropMode.InternalMove)
            self._mod_list.setDefaultDropAction(Qt.DropAction.MoveAction)
            
            self._mod_list.setSpacing(2)
            self._mod_list.setMouseTracking(True)  # necessário para hover neon
            self._mod_list.setStyleSheet("""
                QListView {
                    background-color: transparent;
                    border: none;
                    outline: none;
                }
                QScrollBar:vertical {
                    background: transparent;
                    width: 6px;
                    border-radius: 3px;
                }
                QScrollBar::handle:vertical {
                    background: rgba(192,57,43,0.30);
                    border-radius: 3px;
                    min-height: 24px;
                }
                QScrollBar::handle:vertical:hover {
                    background: rgba(192,57,43,0.65);
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
            """)
            self._mod_list.doubleClicked.connect(self._on_mod_double_clicked)
            splitter.addWidget(self._mod_list)
        else:
            splitter.addWidget(QLabel("Nenhum banco de dados conectado"))

        self._conflict_view = ConflictView()
        self._conflict_view.winner_changed.connect(self._on_set_winner)
        # ConflictView mantida como objeto oculto (não no splitter) para
        # preservar backend de detecção e badges. Painel visual removido da UI.
        self._conflict_view.hide()
        # splitter: apenas a lista de mods, ocupa 100% da área
        self._conflict_splitter = splitter  # mantido para hasattr guards
        mods_v.addWidget(splitter)

        # Item 2: Empty state — shown when mod list is empty
        self._empty_state = QLabel(
            "📂   Nenhum mod instalado ainda\n"
            "Arraste uma pasta de mod aqui ou use o botão  📑 Importar Pasta de Mod"
        )
        self._empty_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_state.setStyleSheet(
            "color: #303240; font-size: 14px; line-height: 1.8; "
            "padding: 40px; background: transparent;"
        )
        self._empty_state.setWordWrap(True)
        self._empty_state.setVisible(False)
        mods_v.addWidget(self._empty_state)

        hint = QLabel("Botão-direito no mod · Arrastar para reordenar · Ctrl+clique para múltipla seleção")
        hint.setObjectName("modHint")
        mods_v.addWidget(hint)

        self._pages.addWidget(mods_page)

        # ── Page 1: ASI ──
        if self._game_dir:
            self._asi_panel = AsiPanel(self._game_dir / "bin64")
            self._pages.addWidget(self._asi_panel)
        else:
            self._pages.addWidget(QLabel("Nenhum diretório do jogo configurado"))

        # ── Page 2: Activity Log ──
        from cdumm.engine.activity_log import ActivityLog
        from cdumm.gui.activity_panel import ActivityPanel
        if self._db:
            self._activity_log = ActivityLog(self._db)
            self._activity_panel = ActivityPanel(self._activity_log)
            self._pages.addWidget(self._activity_panel)
        else:
            self._activity_log = None
            self._pages.addWidget(QLabel("Nenhum banco de dados"))

        # ── Page 3: Tools & Settings ──
        tools_page = QWidget()
        tools_page.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        tools_page.setAutoFillBackground(False)
        tools_v = QVBoxLayout(tools_page)
        tools_v.setContentsMargins(32, 24, 32, 24)
        tools_v.setSpacing(12)

        tools_header = QLabel("FERRAMENTAS DE SISTEMA E CONFIGURAÇÃO")
        tools_header.setStyleSheet("font-family: 'Bahnschrift'; font-size: 16px; font-weight: bold; color: #FF6E1A; padding-left: 4px; letter-spacing: 1px;")
        tools_v.addWidget(tools_header)
        tools_v.addSpacing(16)

        def _add_section(title: str, actions: list) -> None:
            """Render a settings section with chevron per row."""
            sec_lbl = QLabel(title)
            sec_lbl.setStyleSheet(
                "color: #D6D6E0; font-family: 'Segoe UI'; font-size: 11px; font-weight: 800; "
                "letter-spacing: 1.5px; text-transform: uppercase; "
                "padding: 6px 0px 4px 4px; border-bottom: 2px solid #E51414; margin-bottom: 4px;"
            )
            tools_v.addWidget(sec_lbl)
            tools_v.addSpacing(6)
            for label_text, slot_func in actions:
                # Passo 1 fix: button text is EMPTY, all text rendered via child labels
                btn = PremiumNeonButton("")
                btn.setFixedHeight(36)
                inner = QHBoxLayout(btn)
                inner.setContentsMargins(14, 0, 12, 0)
                inner.setSpacing(0)
                text_lbl = QLabel(label_text)
                text_lbl.setStyleSheet(
                    "color: #F4F4FC; background: transparent; "
                    "border: none; font-size: 12px; font-family: 'Segoe UI'; letter-spacing: 0.5px;"
                )
                inner.addWidget(text_lbl)
                inner.addStretch()
                chevron = QLabel("›")
                chevron.setStyleSheet(
                    "color: #FF6E1A; background: transparent; "
                    "border: none; font-size: 18px; font-weight: 800; font-family: 'Bahnschrift';"
                )
                inner.addWidget(chevron)
                btn.clicked.connect(slot_func)
                tools_v.addWidget(btn)
            tools_v.addSpacing(14)

        _add_section("DIAGNÓSTICOS E INTEGRIDADE", [
            ("Verificar Estado do Jogo",               self._on_verify_game_state),
            ("Verificar Mods com Problemas",           self._on_check_mods),
            ("Encontrar Mod Problemático",             self._on_find_problem_mod),
            ("Re-escanear Após Verificação da Steam",  self._on_refresh_snapshot),
            ("Testar Compatibilidade do Mod",          self._on_test_mod),
        ])

        _add_section("GERENCIAMENTO E ARQUIVOS", [
            ("Mudar Diretório do Jogo",         self._on_change_game_dir),
            ("Exportar Lista de Mods Mestra",   self._on_export_list),
            ("Importar Lista de Mods",          self._on_import_list),
        ])

        tools_v.addStretch()
        self._pages.addWidget(tools_page)

        # ── Page 4: About (BR Edition) ──
        about_page = QWidget()
        about_page.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        about_page.setAutoFillBackground(False)
        about_v = QVBoxLayout(about_page)
        about_v.setContentsMargins(32, 32, 32, 24)
        about_v.setSpacing(0)

        from cdumm import __version__ as _about_ver

        # Title block
        about_title = QLabel("Crimson Desert")
        about_title.setStyleSheet(
            "font-size: 20px; font-weight: 800; color: #F4F4FC; letter-spacing: 1px;"
        )
        about_v.addWidget(about_title)

        about_subtitle = QLabel("BR Elite")
        about_subtitle.setStyleSheet(
            "font-size: 11px; font-weight: 700; color: #C0392B;"
            " letter-spacing: 3px; margin-bottom: 4px;"
        )
        about_v.addWidget(about_subtitle)

        about_v.addSpacing(6)

        from cdumm import __version__
        about_ver = QLabel(f"v{__version__}")
        about_ver.setStyleSheet("font-size: 11px; color: #505062; letter-spacing: 0.5px;")
        about_v.addWidget(about_ver)

        about_v.addSpacing(20)

        desc = QLabel(
            "<p style='margin-bottom: 8px;'>O <b>Crimson Desert Elite BR</b> (CDUMM) é o principal gerenciador tático "
            "otimizado para a comunidade brasileira. Focado em alta performance "
            "e injeção estruturada de arquivos ASI e arquétipos PAZ, garantimos um ambiente blindado contra quebras (crashes).</p>"
            "<p style='margin-bottom: 12px;'>O desenvolvimento profundo dessa ferramenta exige dedicação diária de engenharia reversa frente aos updates do jogo.</p>"
            "<p style='margin-bottom: 16px; color:#D6D6E0;'><b>APOIE O PROJETO:</b><br/>"
            "Se este motor ajudou nas suas campanhas de Crimson Desert, por favor, considere fazer uma "
            "<b>doação</b>. O suporte da comunidade é a única via que nos permite continuar o desenvolvimento livre e manter os updates vindo.</p>"
            "<p>🔗 <a href='https://www.nexusmods.com/crimsondesert/mods/700' style='color:#FF6E1A; text-decoration:none;'><b>Acessar a Página Oficial no Nexus Mods</b></a></p>"
            "<p style='font-size:10px; color:#505062;'>Você pode realizar apoios e acessar os links de doação pelo nosso perfil oficial no Nexus.</p>"
        )
        desc.setStyleSheet("font-size: 12px; color: #9898B0; line-height: 1.6; font-family: 'Segoe UI';")
        desc.setWordWrap(True)
        desc.setOpenExternalLinks(True)
        about_v.addWidget(desc)

        about_v.addStretch()

        # Divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background: #261820; margin: 0;")
        about_v.addWidget(div)

        about_v.addSpacing(12)

        credits_lbl = QLabel("by CrashByte")
        credits_lbl.setStyleSheet("font-size: 11px; color: #686878; letter-spacing: 0.3px;")
        about_v.addWidget(credits_lbl)

        about_v.addSpacing(8)

        # Hidden dummy attrs for hasattr guards in update handlers
        self._about_update_label = QLabel("", self)
        self._about_update_label.setVisible(False)

        self._pages.addWidget(about_page)

        # Fake tabs reference for tab switching on import
        self._tabs = self._pages

        content_v.addWidget(self._pages)

        # Update banner removed from UI layout — kept as attr for hasattr guards
        self._update_banner = QLabel("", self)  # parented but not in layout
        self._update_banner.setVisible(False)

        # ── Action Bar ──
        # ── Revert zone — secondary / danger action only ──
        action_bar = QFrame()
        action_bar.setObjectName("actionBar")
        action_bar.setFixedHeight(50)
        ab_layout = QHBoxLayout(action_bar)
        ab_layout.setContentsMargins(16, 5, 16, 5)

        ab_layout.addStretch()

        # Passo 3: Contextual hint with updated text (no more 'vanilla')
        _revert_hint = QLabel("Restaura os arquivos do jogo para o estado Original.")
        _revert_hint.setObjectName("actionBarHint")
        _revert_hint.setStyleSheet("color:#A5A5C5; font-size:13px; font-weight:600; letter-spacing:0.3px;")
        ab_layout.addWidget(_revert_hint)
        ab_layout.addSpacing(12)

        revert_btn = PremiumNeonButton("↩  Reverter para Original")
        revert_btn.setMinimumWidth(200)
        # revert_btn.setObjectName("revertBtn")
        revert_btn.setToolTip("Remove todos os mods aplicados e restaura os arquivos originais do jogo")
        revert_btn.clicked.connect(self._on_revert)
        ab_layout.addWidget(revert_btn)

        # Separador gradiente acima do actionBar (item 9)
        _action_sep = QFrame()
        _action_sep.setObjectName("actionBarSep")
        _action_sep.setFixedHeight(1)
        content_v.addWidget(_action_sep)
        content_v.addWidget(action_bar)
        main_h.addWidget(content_widget, 1)

        # Set initial nav
        self._on_nav("Painel")

    def _on_nav(self, label: str) -> None:
        """Switch pages via sidebar navigation."""
        page_map = {"Painel": 0, "PAZ Mods": 1, "ASI Mods": 2, "Log": 3, "Tools": 4, "About": 5}
        idx = page_map.get(label, 0)
        self._pages.setCurrentIndex(idx)

        # Item 1: Show drop zone only on the Mods page
        if hasattr(self, '_import_widget'):
            self._import_widget.setVisible(label == "PAZ Mods")

        # Item 8: Atualiza o item ativo no sidebar premium
        if hasattr(self, '_nav_items'):
            for nav_label, item in self._nav_items.items():
                item.set_active(nav_label == label)
        else:
            # Fallback para estado legado (não deve ocorrer)
            for nav_label, btn in self._nav_buttons:
                is_active = nav_label == label
                if hasattr(btn, 'set_active'):
                    btn.set_active(is_active)
                else:
                    btn.setChecked(is_active)
                    btn.setProperty("navActive", is_active)
                    btn.style().unpolish(btn)
                    btn.style().polish(btn)

    def _set_pending_changes(self, state: bool) -> None:
        self._has_pending_changes = state
        if not hasattr(self, 'apply_btn'):
            return
        if state:
            self.apply_btn.setText("⚠️ APLICAR ALTERAÇÕES")
            self.apply_btn.setStyleSheet(
                "background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                "stop:0 #E53935, stop:1 #BF616A); color: white;")
            # Micro-pulse: QPropertyAnimation on maximumWidth creates a subtle grow effect
            try:
                from PySide6.QtCore import QPropertyAnimation, QEasingCurve
                if not getattr(self, '_pulse_anim', None):
                    self._pulse_anim = QPropertyAnimation(self.apply_btn, b"minimumWidth")
                    self._pulse_anim.setDuration(700)
                    self._pulse_anim.setStartValue(90)
                    self._pulse_anim.setKeyValueAt(0.5, 108)
                    self._pulse_anim.setEndValue(90)
                    self._pulse_anim.setEasingCurve(QEasingCurve.Type.SineCurve)
                    self._pulse_anim.setLoopCount(-1)  # infinite
                self._pulse_anim.start()
            except Exception:
                pass
        else:
            self.apply_btn.setText("⚡  Aplicar")
            self.apply_btn.setStyleSheet("")
            if getattr(self, '_pulse_anim', None):
                self._pulse_anim.stop()

    def _on_conflict_collapse_toggled(self, is_collapsed: bool):
        if not hasattr(self, '_conflict_splitter'):
            return
        sizes = self._conflict_splitter.sizes()
        total = max(sum(sizes), 300)
        
        if is_collapsed:
            self._conflict_splitter.setSizes([total - 30, 30])
        else:
            target = min(int(total * 0.35), 250)
            target = max(target, 120)
            self._conflict_splitter.setSizes([total - target, target])

    def _on_launch_game(self) -> None:
        """Launch the game executable."""
        if getattr(self, "_has_pending_changes", False):
            msg = QMessageBox(self)
            msg.setWindowTitle("⚠️ Alterações de Motor Pendentes")
            msg.setText("Você configurou alterações na lista tática de Mods, mas esqueceu de aplica-lás à Engine do Crimson Desert.\nDeseja compilar os mods antes de lançar o jogo?")
            msg.setStyleSheet("""
                QMessageBox { background-color: #0E080C; border: 1px solid #E51414; }
                QLabel { color: #D6D6E0; font-family: 'Segoe UI'; font-size: 13px; font-weight: 500; }
                QPushButton { background-color: rgba(14, 8, 12, 0.8); border: 1px solid #FF6E1A; border-radius: 4px; color: #F4F4FC; padding: 6px 20px; font-family: 'Bahnschrift'; font-weight: bold; }
                QPushButton:hover { background-color: rgba(229, 20, 20, 0.6); color: white; }
            """)
            btn_apply = msg.addButton("Aplicar os Mods e Jogar", QMessageBox.ButtonRole.AcceptRole)
            btn_play = msg.addButton("Lançar Jogo Cru (Sem Aplicar)", QMessageBox.ButtonRole.RejectRole)
            btn_cancel = msg.addButton("Abortar", QMessageBox.ButtonRole.RejectRole)
            msg.exec()
            choice = msg.clickedButton()
            if choice == btn_apply:
                self._launch_after_apply = True
                self._on_apply()
                return
            elif choice == btn_cancel:
                return

        import subprocess
        if not self._game_dir:
            return
        exe = self._game_dir / "bin64" / "CrimsonDesert.exe"
        if not exe.exists():
            # Try finding the exe
            for candidate in ["CrimsonDesert.exe", "crimsondesert.exe"]:
                test = self._game_dir / "bin64" / candidate
                if test.exists():
                    exe = test
                    break
            else:
                self.statusBar().showMessage("Executável do jogo não encontrado em bin64/", 10000)
                return
        try:
            subprocess.Popen([str(exe)], cwd=str(self._game_dir / "bin64"))
            self.statusBar().showMessage("Jogo iniciado!", 5000)
        except Exception as e:
            self.statusBar().showMessage(f"Falha ao iniciar: {e}", 10000)

    def _build_toolbar(self) -> None:
        # Toolbar replaced by sidebar — this is kept as a no-op for compatibility
        pass

    def _build_status_bar(self) -> None:
        from cdumm import __version__
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        
        self._snapshot_label = QLabel()
        self._snapshot_label.setVisible(False)
        status_bar.addPermanentWidget(self._snapshot_label)
        
        version_label = QLabel("")
        version_label.setVisible(False)
        status_bar.addPermanentWidget(version_label)
        self._update_snapshot_status()

    def _update_snapshot_status(self) -> None:
        if not self._snapshot:
            self._snapshot_label.setText("Snapshot: Sem banco de dados")
            self._snapshot_label.setStyleSheet("color: gray;")
        elif self._snapshot.has_snapshot():
            count = self._snapshot.get_snapshot_count()
            self._snapshot_label.setText(f"Snapshot: {count} arquivos")
            self._snapshot_label.setStyleSheet("color: green;")
        else:
            self._snapshot_label.setText("Snapshot: Ainda não escaneado")
            self._snapshot_label.setStyleSheet("color: #FF9800;")

    def _log_activity(self, category: str, message: str, detail: str = None) -> None:
        """Log an activity to the persistent activity log."""
        if hasattr(self, '_activity_log') and self._activity_log:
            try:
                self._activity_log.log(category, message, detail)
                if hasattr(self, '_activity_panel'):
                    self._activity_panel.refresh()
            except Exception:
                pass

    def _sync_db(self) -> None:
        """Sync main DB after a worker writes via WAL checkpoint."""
        if not self._db:
            return
        try:
            self._db.connection.execute("PRAGMA wal_checkpoint(PASSIVE)")
        except Exception as e:
            logger.error("WAL checkpoint failed: %s", e)

    def _refresh_all(self, update_statuses: bool = True, skip_conflicts: bool = True) -> None:
        """Refresh UI model and table. Conflicts are NEVER run here — only on Apply."""
        import time
        t0 = time.monotonic()
        logger.debug("_refresh_all: start")
        if hasattr(self, "_mod_list_model"):
            logger.debug("_refresh_all: refreshing mod list model")
            self._mod_list_model.refresh()
            logger.debug("_refresh_all: model.refresh done (%.3fs)", time.monotonic() - t0)
            if update_statuses:
                self._mod_list_model.refresh_statuses()
                logger.debug("_refresh_all: refresh_statuses done (%.3fs)", time.monotonic() - t0)
        logger.debug("_refresh_all: updating snapshot status")
        self._update_snapshot_status()
        logger.debug("_refresh_all: snapshot status done (%.3fs)", time.monotonic() - t0)
        self._update_header_checkbox()
        logger.debug("_refresh_all: header checkbox done (%.3fs)", time.monotonic() - t0)
        
        # Sincroniza estatísticas com debounce (evita recalcular durante sequencias rápidas)
        self._schedule_dashboard_update()
        
        logger.debug("_refresh_all: done total=%.3fs", time.monotonic() - t0)

    def _schedule_dashboard_update(self) -> None:
        """Agenda atualização com debounce de 150ms — evita repintura multipla durante Toggle All."""
        from PySide6.QtCore import QTimer
        if not hasattr(self, "_dashboard_timer"):
            self._dashboard_timer = QTimer(self)
            self._dashboard_timer.setSingleShot(True)
            self._dashboard_timer.timeout.connect(self._update_dashboard_stats)
        self._dashboard_timer.start(150)

    def _update_dashboard_stats(self) -> None:
        """Atualiza a contagem visual de mods totais/ativos na barra superior e no Dashboard.
        Usa apenas dados já carregados no modelo — sem queries SQL ou disk I/O.
        """
        if hasattr(self, "_mod_list_model"):
            _total = len(self._mod_list_model._mods)
            _enabled = sum(1 for m in self._mod_list_model._mods if m.get("enabled"))
            if hasattr(self, "_header_stats"):
                self._header_stats.setText(f"Crimson Desert  ·  {_enabled} Ativos  ·  {_total} Total")

        if hasattr(self, "_dashboard_panel"):
            try:
                self._dashboard_panel.update_stats()
            except Exception:
                pass


    def _schedule_conflict_check(self) -> None:
        """Start or restart the 300ms debounce timer for conflict detection."""
        from PySide6.QtCore import QTimer
        if not hasattr(self, "_conflict_timer"):
            self._conflict_timer = QTimer(self)
            self._conflict_timer.setSingleShot(True)
            self._conflict_timer.timeout.connect(self._run_conflict_check)
        self._conflict_timer.start(300)

    def _run_conflict_check(self) -> None:
        """Run conflict detection in a background thread — never blocks the UI."""
        if not self._conflict_detector:
            return

        # Get the db_path so the worker can open its own connection
        try:
            db_path = self._conflict_detector._db.db_path
        except AttributeError:
            return

        # Cancel any previously running conflict thread
        if hasattr(self, "_conflict_thread") and self._conflict_thread is not None:
            try:
                if self._conflict_thread.isRunning():
                    self._conflict_thread.quit()
                    self._conflict_thread.wait(500)
            except RuntimeError:
                pass
            self._conflict_thread = None

        from PySide6.QtCore import QObject, QThread, Signal as _Signal

        class _ConflictWorker(QObject):
            finished = _Signal(object)

            def __init__(self, path):
                super().__init__()
                self._db_path = path

            def run(self):
                conflicts = []
                try:
                    import sqlite3
                    from cdumm.engine.conflict_detector import ConflictDetector

                    # check_same_thread=False prevents Python's sqlite3 module
                    # from raising if the connection object is GC'd from another thread.
                    conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.execute("PRAGMA foreign_keys=ON")

                    # Minimal stub so ConflictDetector can use this connection
                    _path = self._db_path

                    class _LightDB:
                        db_path = _path
                        connection = conn

                        def close(self_):
                            conn.close()

                    detector = ConflictDetector(_LightDB())
                    conflicts = detector.detect_all()
                    conn.close()
                except Exception as _e:
                    logger.warning("Conflict detection worker failed: %s", _e)
                self.finished.emit(conflicts)

        class _Relay(QObject):
            """Relay QObject that lives on the main thread.
            Worker's finished signal → relay.fire (main thread, queued) → callback."""
            fire = _Signal(object)

        worker = _ConflictWorker(db_path)
        # _Relay is NOT moved to any thread, so it stays on the main thread.
        # When AutoConnection detects that sender (worker thd) ≠ receiver (main thd),
        # it automatically uses QueuedConnection — delivering fire on the main thread.
        relay = _Relay()
        thread = QThread()
        worker.moveToThread(thread)

        # Standard thread lifecycle
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        # Cross-thread: worker.finished → relay.fire runs on MAIN thread (queued)
        worker.finished.connect(relay.fire)

        def _on_conflicts_ready(conflicts):
            try:
                logger.debug("_run_conflict_check: %d conflicts found", len(conflicts))
                self._conflict_view.update_conflicts(conflicts)
                # Conflict panel removido do splitter — só atualiza badges nos cards.
                if hasattr(self, "_mod_list_model"):
                    self._mod_list_model.refresh_conflict_cache()
                    # Notifica a tabela nativa para repintar os badges vermelhos de conflito
                    self._mod_list_model.layoutChanged.emit()
                if hasattr(self, "_mod_list"):
                    self._mod_list.viewport().update()
            except Exception as _e:
                logger.warning("Conflict UI update failed: %s", _e)
            finally:
                self._conflict_thread = None
                relay.deleteLater()

        # Same thread (main): direct connection — _on_conflicts_ready runs on main thread
        relay.fire.connect(lambda c: _on_conflicts_ready(c))

        self._conflict_thread = thread
        self._conflict_worker = worker
        self._conflict_relay = relay  # keep ref alive until relay fires
        logger.debug("_run_conflict_check: detecting conflicts (background thread)")
        thread.start()


    def _on_mod_double_clicked(self, index) -> None:
        """Double-click on a configurable mod opens the configure dialog."""
        mod = self._get_mod_at_proxy_row(index.row())
        if mod and mod.get("configurable"):
            self._on_configure_mod(mod)

    # ── Etapa 3: card list helpers ───────────────────────────────────────────────────

    def _populate_mod_cards(self) -> None:
        """Rebuild or update card QListWidget from current ModListModel data."""
        if not hasattr(self, "_mod_card_list") or not hasattr(self, "_mod_list_model"):
            return
        from PySide6.QtCore import QSize
        from PySide6.QtWidgets import QListWidgetItem
        from cdumm.gui.mod_card_delegate import ModCardDelegate as _MCD2
        
        current_count = self._mod_card_list.count()
        new_count = len(self._mod_list_model._mods)
        
        self._mod_card_list.blockSignals(True)
        if current_count != new_count:
            self._mod_card_list.clear()
            for row in range(new_count):
                card_data = self._mod_list_model.data(
                    self._mod_list_model.index(row, 0),
                    Qt.ItemDataRole.UserRole,
                )
                if card_data is None:
                    continue
                item = QListWidgetItem()
                item.setSizeHint(QSize(0, _MCD2.CARD_H + 14))
                item.setData(Qt.ItemDataRole.UserRole, card_data)
                self._mod_card_list.addItem(item)
        else:
            for row in range(new_count):
                card_data = self._mod_list_model.data(
                    self._mod_list_model.index(row, 0),
                    Qt.ItemDataRole.UserRole,
                )
                item = self._mod_card_list.item(row)
                if item and card_data is not None:
                    item.setData(Qt.ItemDataRole.UserRole, card_data)
        self._mod_card_list.blockSignals(False)
        # Refresh header stats
        _mods   = self._mod_list_model._mods
        _total  = len(_mods)
        _active = sum(1 for m in _mods if m.get("enabled"))
        if hasattr(self, "_header_stats"):
            self._header_stats.setText(
                f"Crimson Desert  ·  {_active} Ativos  ·  {_total} Total"
            )
            if hasattr(self, "_dashboard_panel"):
                self._dashboard_panel.update_stats()
        # Item 2: Toggle empty state placeholder
        if hasattr(self, '_empty_state'):
            self._empty_state.setVisible(_total == 0)

    def _repaint_cards(self) -> None:
        """Lightweight repaint: update model data in-place and ask Qt to repaint.
        
        Does NOT rebuild QListWidgetItems — only updates their UserRole data
        and triggers a viewport repaint. Use this for toggle/state changes.
        Takes ~0ms vs ~3.6s for the full _populate_mod_cards rebuild.
        """
        if not hasattr(self, "_mod_card_list") or not hasattr(self, "_mod_list_model"):
            return
        # Refresh model from DB (fast — just a SQL query)
        self._mod_list_model.refresh()
        # Update UserRole data in-place (no clear/rebuild)
        for row in range(self._mod_card_list.count()):
            if row >= len(self._mod_list_model._mods):
                break
            card_data = self._mod_list_model.data(
                self._mod_list_model.index(row, 0),
                Qt.ItemDataRole.UserRole,
            )
            item = self._mod_card_list.item(row)
            if item and card_data is not None:
                item.setData(Qt.ItemDataRole.UserRole, card_data)
        # Ask Qt to repaint only the visible area — no layout recalculation
        self._mod_card_list.viewport().update()
        # Update header stats
        _mods = self._mod_list_model._mods
        _active = sum(1 for m in _mods if m.get("enabled"))
        if hasattr(self, "_header_stats"):
            self._header_stats.setText(
                f"Crimson Desert  ·  {_active} Ativos  ·  {len(_mods)} Total"
            )

    def _on_card_toggle_requested(self, mod_id: int) -> None:
        """Legado — card list removida. Delega para _on_toggle_mod via modelo."""
        if not self._mod_manager:
            return
        mod = next(
            (m for m in self._mod_manager.list_mods() if m["id"] == mod_id), None)
        if not mod:
            return
        self._on_toggle_mod(mod)

    def _toggle_all_mods(self) -> None:
        """Ativa todos se houver algum desativado; caso contrário, desativa todos."""
        if not hasattr(self, "_mod_list_model") or not self._mod_manager:
            return
            
        mods = self._mod_list_model._mods
        if not mods:
            return
            
        any_disabled = any(not mod.get("enabled", False) for mod in mods)
        new_state = any_disabled
        
        toggled_any = False
        for mod in mods:
            mod_id = mod.get("id")
            if mod.get("enabled", False) != new_state:
                self._mod_manager.set_enabled(mod_id, new_state)
                # Atualização cirúrgica — sem beginResetModel em cascata
                self._mod_list_model.update_mod_state(mod_id, new_state)
                toggled_any = True
                
        if toggled_any:
            state_str = "Habilitados" if new_state else "Desabilitados"
            self._log_activity("bulk_action", f"Todos os Mods {state_str}", f"Ação global aplicada a {len(mods)} mods")
            self._set_pending_changes(True)
            # Dispara só o update leve do dashboard (debounced), sem resetar a lista inteira
            self._schedule_dashboard_update()



    def _on_mod_card_double_clicked(self, item) -> None:
        """Double-click on card — opens configure dialog if mod is configurable."""
        if not self._db:
            return
        card = item.data(Qt.ItemDataRole.UserRole)
        if not card:
            return
        row_result = self._db.connection.execute(
            "SELECT configurable FROM mods WHERE id = ?", (card["id"],)
        ).fetchone()
        if row_result and row_result[0]:
            full_mod = next(
                (m for m in self._mod_manager.list_mods() if m["id"] == card["id"]),
                card,
            )
            self._on_configure_mod(full_mod)

    def _on_mod_card_order_changed(self, src_parent, src_start, src_end,
                                    dst_parent, dst_row) -> None:
        """Persist drag-drop reorder — mirrors ModListModel.dropMimeData logic."""
        if not hasattr(self, "_mod_card_list") or not self._mod_manager:
            return
        try:
            new_order = []
            for i in range(self._mod_card_list.count()):
                card = self._mod_card_list.item(i).data(Qt.ItemDataRole.UserRole)
                if card:
                    new_order.append(card["id"])
            if new_order:
                self._mod_manager.reorder_mods(new_order)
                self._mod_list_model.refresh()
                self._set_pending_changes(True)
        except Exception as exc:
            logger.warning("Card order persistence failed: %s", exc)

    # --- Helper to run a worker with ProgressDialog ---
    def _run_worker(self, worker, thread: QThread, progress: ProgressDialog,
                    on_finished, on_error=None) -> None:
        """Wire a worker + thread + progress dialog with proper signal connections."""
        # CRITICAL: Keep references alive — without this, Python GC destroys the
        # worker and thread before they finish, causing silent failures.
        self._active_worker = worker
        self._worker_thread = thread
        self._active_progress = progress

        worker.moveToThread(thread)
        thread.started.connect(worker.run)

        # Use proper Slot methods on ProgressDialog — no lambdas for progress
        worker.progress_updated.connect(progress.update_progress)

        # CRITICAL: Use MainThreadDispatcher to route callbacks to the main thread.
        # PySide6 lambdas connected to signals ALWAYS execute on the emitter's
        # thread (ignoring QueuedConnection). The dispatcher is a QObject on the
        # main thread with @Slot methods, so Qt correctly queues the call.
        worker.finished.connect(
            lambda *args: self._dispatcher.call(
                self._worker_done, thread, progress, on_finished, *args)
        )
        worker.error_occurred.connect(
            lambda err: self._dispatcher.call(
                self._worker_error, thread, progress, err, on_error)
        )

        logger.info("Starting worker: %s", type(worker).__name__)
        progress.show()
        thread.start()

    def _worker_done(self, thread: QThread, progress: ProgressDialog, callback, *args) -> None:
        # This method is guaranteed to run on the main thread via MainThreadDispatcher
        logger.info("Worker finished (main thread): %s", type(self._active_worker).__name__)

        progress.hide()

        # CRITICAL Qt threading rule: the worker was moved to 'thread' via
        # moveToThread(). The worker MUST be scheduled for deletion BEFORE the
        # thread is stopped — otherwise Qt destroys the thread object while the
        # worker still holds a pointer to it, causing an access violation
        # (0xc0000005) inside Qt6Core.dll.
        worker_ref = self._active_worker
        self._active_progress = None
        self._active_worker = None
        self._worker_thread = None

        def _cleanup_thread():
            thread.quit()
            # worker lives on thread — delete it while thread is still valid
            if worker_ref is not None:
                try:
                    worker_ref.deleteLater()
                except RuntimeError:
                    pass  # already deleted
            progress.deleteLater()
            thread.deleteLater()
            logger.info("Thread and worker scheduled for deletion")

        # Defer thread cleanup to the next event loop tick so any
        # pending queued signals from the worker are processed first.
        # This also avoids blocking the main event loop with thread.wait().
        QTimer.singleShot(0, _cleanup_thread)

        logger.info("Calling completion callback")
        try:
            callback(*args)
        except Exception:
            logger.error("Completion callback crashed", exc_info=True)
        logger.info("Completion callback done")

    def _worker_error(self, thread: QThread, progress: ProgressDialog,
                      error: str, callback=None) -> None:
        # This method is guaranteed to run on the main thread via MainThreadDispatcher
        logger.error("Worker error (main thread): %s", error)
        progress.close()

        # Same deletion order as _worker_done: worker first, then thread.
        worker_ref = self._active_worker
        self._active_progress = None
        self._active_worker = None
        self._worker_thread = None

        def _cleanup_thread_err():
            thread.quit()
            if worker_ref is not None:
                try:
                    worker_ref.deleteLater()
                except RuntimeError:
                    pass
            progress.deleteLater()
            thread.deleteLater()

        QTimer.singleShot(0, _cleanup_thread_err)

        # If imports are queued, collect error and continue instead of blocking
        if hasattr(self, '_import_queue') and self._import_queue:
            if not hasattr(self, '_import_errors'):
                self._import_errors = []
            self._import_errors.append(error)
            self.statusBar().showMessage(f"Erro: {error} — continuando com o próximo mod...", 5000)
            QTimer.singleShot(300, self._process_next_import)
            return

        _critical_br(self, "Erro", error)
        if callback:
            callback(error)

    # --- Import ---
    def _on_import_clicked(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Importar Pasta de Mod",
            "", QFileDialog.Option.ShowDirsOnly,
        )
        if path:
            self._queue_import(Path(path))

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        urls = event.mimeData().urls()
        for url in urls:
            path = Path(url.toLocalFile())
            logger.info("File dropped on main window: %s", path)
            self._queue_import(path)

    def _on_import_dropped(self, path: Path) -> None:
        self._queue_import(path)

    def _queue_import(self, path: Path) -> None:
        """Add a path to the import queue. Processes sequentially."""
        # --- Hard Block: ZIP > 900 MB ---
        # ZIPs gigantes são extraídos em memória/disco de forma síncrona e
        # travam a UI por minutos. Bloqueamos antes de enfileirar.
        _900MB = 900 * 1024 * 1024
        if path.is_file() and path.suffix.lower() == ".zip":
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            if size > _900MB:
                size_mb = size / (1024 * 1024)
                _warning_br(
                    self,
                    "Arquivo ZIP Muito Grande 🛑",
                    f"Este arquivo ZIP excede o limite de 900 MB ({size_mb:.0f} MB).\n\n"
                    "Arquivos acima desse tamanho precisam ser extraídos antes de importar.\n\n"
                    "Como fazer:\n"
                    "  1. Clique com o botão direito no ZIP\n"
                    "  2. Selecione 'Extrair Aqui' ou 'Extrair para...'\n"
                    "  3. Arraste a pasta extraída para cá, ou use 📑 Importar Pasta de Mod.",
                )
                logger.warning(
                    "Hard block: ZIP too large (%.0f MB): %s", size_mb, path
                )
                return  # descarta sem enfileirar — app volta ao estado normal

        if not hasattr(self, '_import_queue'):
            self._import_queue = []
        self._import_queue.append(path)
        # If no import is running, start the first one
        if not (hasattr(self, '_active_worker') and self._active_worker):
            self._process_next_import()

    def _process_next_import(self) -> None:
        """Process the next item in the import queue."""
        if not hasattr(self, '_import_queue') or not self._import_queue:
            # Queue empty — show summary if there were errors
            if hasattr(self, '_import_errors') and self._import_errors:
                errors = self._import_errors
                self._import_errors = []
                error_list = "\n".join(f"  - {e}" for e in errors)
                _warning_br(
                    self, "Some Imports Failed",
                    f"{len(errors)} mod(s) had issues:\n\n{error_list}",
                )
            # Process deferred script mods
            if hasattr(self, '_script_queue') and self._script_queue:
                script_path = self._script_queue.pop(0)
                self._run_script_mod(script_path)
            return

        path = self._import_queue.pop(0)
        remaining = len(self._import_queue)

        # Defer script mods — they open a cmd window and block the queue.
        # Process them after all non-script mods are done.
        suffix = path.suffix.lower() if path.is_file() else ""
        if suffix in (".bat", ".py"):
            if not hasattr(self, '_script_queue'):
                self._script_queue = []
            self._script_queue.append(path)
            logger.info("Deferred script mod: %s (processing after other imports)", path.name)
            self._process_next_import()  # skip to next
            return

        if remaining:
            self.statusBar().showMessage(
                f"Importing {path.name}... ({remaining} more queued)", 0)
        self._run_import(path)

    def _run_import(self, path: Path) -> None:
        if not self._db or not self._game_dir:
            self.statusBar().showMessage("Erro: Banco de dados ou diretório do jogo não configurado.", 5000)
            return

        self.statusBar().showMessage(f"Importando {path.name}...")
        logger.info("Starting import: %s", path)

        # Check if this is an ASI mod first (fast, no thread needed)
        from cdumm.asi.asi_manager import AsiManager
        if AsiManager.contains_asi(path):
            self._install_asi_mod(path)
            return

        # Standalone PAZ mods (modinfo.json + 0.paz + 0.pamt) don't need a snapshot
        # since they add new directories rather than modifying existing files.
        # All other PAZ mods require a snapshot for delta generation.
        if not _is_standalone_paz_mod(path) and (not self._snapshot or not self._snapshot.has_snapshot()):
            self.statusBar().showMessage(
                "Arquivos do jogo não escaneados ainda. Vá para Ferramentas → Verificação da Steam primeiro.", 10000)
            return

        # Check if this is an update to an existing mod (before routing to script/PAZ)
        # Skipped for batch-queued presets — presets from the same ZIP are always
        # separate mods, never updates of each other.
        existing_mod_id = None
        _skip_dup = hasattr(self, '_no_update_check') and str(path) in self._no_update_check
        if _skip_dup:
            self._no_update_check.discard(str(path))
            logger.info("Batch preset import — skipping duplicate check for: %s", path.name)
        if self._mod_manager and not _skip_dup:
            match = self._find_existing_mod(path)
            if match:
                mid, mname = match
                reply = _pergunta_br(
                    self, "Mod Já Instalado",
                    f"'{mname}' já está instalado.\n\n"
                    "Deseja atualizá-lo para a nova versão?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    | QMessageBox.StandardButton.Cancel,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    # Save old mod's state, delete it, import fresh
                    old_details = self._mod_manager.get_mod_details(mid)
                    self._update_priority = old_details.get("priority", 0) if old_details else 0
                    self._update_enabled = old_details.get("enabled", True) if old_details else True
                    self._mod_manager.remove_mod(mid)
                    logger.info("Removed old mod %d (%s) for update", mid, mname)
                else:
                    # No or Cancel — don't install
                    self.statusBar().showMessage("Importação cancelada.", 5000)
                    return

        # Check if this is a script-based mod — needs to run on main thread
        # so the user can interact with the cmd window
        from cdumm.engine.import_handler import detect_format, import_script_live
        import zipfile as _zf
        import tempfile

        is_script_mod = False
        if path.suffix.lower() in (".bat", ".py"):
            is_script_mod = True
        elif path.suffix.lower() in (".zip", ".7z"):
            try:
                if path.suffix.lower() == ".zip":
                    with _zf.ZipFile(path) as zf:
                        names = zf.namelist()
                else:
                    import py7zr
                    with py7zr.SevenZipFile(path, 'r') as zf:
                        names = zf.getnames()
                has_scripts = any(n.endswith((".bat", ".py")) for n in names)
                has_game_files = any(
                    any(n.startswith(f"{i:04d}/") for i in range(33)) or n.startswith("meta/")
                    for n in names
                )
                if has_scripts and not has_game_files:
                    is_script_mod = True
            except Exception:
                pass
        elif path.is_dir():
            scripts = list(path.glob("*.bat")) + list(path.glob("*.py"))
            game_files = any(
                (path / f"{i:04d}").exists() for i in range(33)
            ) or (path / "meta").exists()
            if scripts and not game_files:
                is_script_mod = True

        if is_script_mod:
            # Extract 7z script mods before running
            if path.suffix.lower() == ".7z":
                import py7zr
                tmp = tempfile.mkdtemp(prefix="cdumm_7z_script_")
                with py7zr.SevenZipFile(path, 'r') as zf:
                    zf.extractall(tmp)
                scripts = list(Path(tmp).rglob("*.bat")) + list(Path(tmp).rglob("*.py"))
                if scripts:
                    path = scripts[0]
            self._run_script_mod(path, existing_mod_id=existing_mod_id)
            return

        # Check for variant folders (e.g. Fat Stacks with 2x, 5x, 10x subfolders).
        # Each subfolder contains the same game files — let user pick which one.
        if path.is_dir():
            variants = []
            for sub in sorted(path.iterdir()):
                if sub.is_dir() and not sub.name.startswith((".", "_")):
                    has_game = any(
                        (sub / f"{i:04d}").is_dir() for i in range(100)
                    ) or (sub / "meta").is_dir()
                    if has_game:
                        variants.append(sub)
            if len(variants) > 1:
                from cdumm.gui.msg_box_br import _input_item_br
                names = [v.name for v in variants]
                chosen, ok = _input_item_br(
                    self, "Escolher Variante",
                    f"Este mod tem {len(variants)} variantes.\n"
                    "Escolha qual delas instalar:",
                    names, 0)
                if ok and chosen:
                    path = variants[names.index(chosen)]
                    logger.info("User selected variant: %s", path.name)
                else:
                    self.statusBar().showMessage("Importação cancelada.", 5000)
                    return

        # Check for multiple JSON presets — let user pick one
        # For zips, extract to temp first to scan for presets
        from cdumm.gui.preset_picker import find_json_presets, PresetPickerDialog
        presets = []
        _preset_tmp = None
        if path.suffix.lower() == ".zip":
            try:
                import zipfile as _zf2
                _preset_tmp = tempfile.mkdtemp(prefix="cdumm_preset_")
                with _zf2.ZipFile(path) as zf:
                    zf.extractall(_preset_tmp)
                presets = find_json_presets(Path(_preset_tmp))
            except Exception:
                presets = []
        else:
            presets = find_json_presets(path)

        if len(presets) > 1:
            dialog = PresetPickerDialog(presets, self)
            if dialog.exec() and dialog.selected_presets:
                selected = dialog.selected_presets
                logger.info("User selected %d preset(s): %s",
                            len(selected), [p.name for p, _ in selected])

                if len(selected) > 1:
                    # Comportamento Faisal: 1 mod configurável com TODOS os presets
                    # armazenados como variantes — idêntico ao fluent_window do faisalkind.
                    from cdumm.engine.variant_handler import import_multi_variant
                    ticked_paths = {p for p, _d in selected}
                    mods_dir = self._cdmods_dir / "mods"
                    try:
                        result = import_multi_variant(
                            presets, path, self._game_dir, mods_dir, self._db,
                            initial_selection=ticked_paths,
                        )
                        if result:
                            n_en = sum(1 for v in result["variants"] if v["enabled"])
                            self.statusBar().showMessage(
                                f"Importado: {result['mod_name']} "
                                f"({n_en} de {len(result['variants'])} variantes ativas). "
                                "Clique em Aplicar.", 10000
                            )
                            self._log_activity(
                                "import", f"Importado: {result['mod_name']}",
                                f"{len(result['variants'])} variantes "
                                f"({n_en} ativas)",
                            )
                            self._refresh_all()
                            self._on_nav("PAZ Mods")
                            self._update_apply_reminder()
                        else:
                            self.statusBar().showMessage(
                                "Nenhum preset selecionado — importação ignorada.", 5000)
                    except Exception as e:
                        logger.error("import_multi_variant falhou: %s", e, exc_info=True)
                        self.statusBar().showMessage(
                            f"Erro ao importar variante: {e}", 8000)
                    finally:
                        if _preset_tmp:
                            import shutil
                            shutil.rmtree(_preset_tmp, ignore_errors=True)
                    return  # multi-variant cuida de tudo — não passa pelo ImportWorker

                # Seleção única: fluxo normal de import
                path = selected[0][0]
                logger.info("User selected preset: %s", path.name)
                # Guarda para limpar APÓS o import terminar
                self._pending_preset_tmp = _preset_tmp
                _preset_tmp = None
            else:
                if _preset_tmp:
                    import shutil
                    shutil.rmtree(_preset_tmp, ignore_errors=True)
                self.statusBar().showMessage("Importação cancelada.", 5000)
                return
        if _preset_tmp and len(presets) <= 1:
            import shutil
            shutil.rmtree(_preset_tmp, ignore_errors=True)
            _preset_tmp = None

        # Check for labeled changes (toggles/presets inside a single JSON)
        from cdumm.gui.preset_picker import has_labeled_changes, TogglePickerDialog
        from cdumm.engine.json_patch_handler import detect_json_patch

        # For zips/7z, extract to temp to check JSON content
        json_check_path = path
        _label_tmp = None
        if path.suffix.lower() in (".zip", ".7z"):
            try:
                _label_tmp = tempfile.mkdtemp(prefix="cdumm_label_")
                if path.suffix.lower() == ".zip":
                    import zipfile as _zf3
                    with _zf3.ZipFile(path) as zf:
                        zf.extractall(_label_tmp)
                else:
                    import py7zr
                    with py7zr.SevenZipFile(path, 'r') as zf:
                        zf.extractall(_label_tmp)
                json_check_path = Path(_label_tmp)
            except Exception:
                pass

        json_data = detect_json_patch(json_check_path)

        # Mark for configurable flag even if we don't show picker
        if json_data:
            any_labels = any(
                "label" in c
                for p in json_data.get("patches", [])
                for c in p.get("changes", [])
                if isinstance(c, dict)
            )
            if any_labels:
                self._configurable_source = str(path)
                self._configurable_labels = []  # populated if picker shown

        if json_data and has_labeled_changes(json_data):
            logger.info("JSON has labeled changes — showing picker dialog")
            dialog = TogglePickerDialog(json_data, self)
            if dialog.exec() and dialog.selected_data:
                # Write filtered JSON to temp file and import that
                import json as _json
                tmp_json = Path(tempfile.mktemp(suffix=".json", prefix="cdumm_filtered_"))
                # Remove non-serializable Path objects before writing
                write_data = dialog.selected_data.copy()
                write_data.pop("_json_path", None)
                tmp_json.write_text(_json.dumps(write_data, indent=2, default=str), encoding="utf-8")
                # Remember original source and selected labels for reconfiguration
                self._configurable_source = str(path)
                # Store which labels/presets were selected
                selected_labels = []
                for patch in dialog.selected_data.get("patches", []):
                    for c in patch.get("changes", []):
                        if "label" in c:
                            selected_labels.append(c["label"])
                self._configurable_labels = selected_labels
                path = tmp_json
                logger.info("User selected %d changes from labeled JSON",
                            sum(len(p.get("changes", [])) for p in dialog.selected_data.get("patches", [])))
            else:
                if _label_tmp:
                    import shutil
                    shutil.rmtree(_label_tmp, ignore_errors=True)
                self.statusBar().showMessage("Importação cancelada.", 5000)
                return

        if _label_tmp:
            import shutil
            shutil.rmtree(_label_tmp, ignore_errors=True)

        # Regular PAZ mod — run on background thread
        logger.info("Starting import worker for: %s", path)
        progress = ProgressDialog("Importando Mod", self)
        worker = ImportWorker(path, self._game_dir, self._db.db_path, self._deltas_dir,
                              existing_mod_id=existing_mod_id)
        thread = QThread()

        self._run_worker(worker, thread, progress,
                         on_finished=self._on_import_finished)

    def _run_script_mod(self, path: Path, existing_mod_id: int | None = None) -> None:
        """Handle script-based mods — launch script, poll for completion, capture changes."""
        # If updating, remove the old mod entry first so the new one replaces it
        if existing_mod_id is not None and self._mod_manager:
            self._mod_manager.set_enabled(existing_mod_id, False)
            # Apply to revert old mod's files before re-importing
            # (handled by the script prep phase which restores vanilla)
            self._mod_manager.remove_mod(existing_mod_id)
            logger.info("Removed old mod %d for update", existing_mod_id)

        import tempfile
        import zipfile as _zf
        from cdumm.engine.import_handler import (
            _detect_script_targets, _ensure_vanilla_backup, import_from_game_scan,
        )
        from cdumm.engine.snapshot_manager import hash_file as _hash_file

        logger.info("Script mod detected: %s", path)

        # Extract if zip
        script_path = path
        self._script_tmp_dir = None
        if path.suffix.lower() == ".zip":
            self._script_tmp_dir = tempfile.mkdtemp()
            with _zf.ZipFile(path) as zf:
                zf.extractall(self._script_tmp_dir)
            # Search recursively — scripts may be in subdirectories
            # Prefer .bat (install scripts) over .py (could be library files)
            bat_scripts = list(Path(self._script_tmp_dir).rglob("*.bat"))
            py_scripts = [p for p in Path(self._script_tmp_dir).rglob("*.py")
                          if "lib" not in p.parent.name.lower()
                          and "__pycache__" not in str(p)]
            scripts = bat_scripts + py_scripts
            if not scripts:
                self.statusBar().showMessage("Nenhum script encontrado no zip.", 5000)
                return
            script_path = scripts[0]
        elif path.is_dir():
            bat_scripts = list(path.rglob("*.bat"))
            py_scripts = [p for p in path.rglob("*.py")
                          if "lib" not in p.parent.name.lower()
                          and "__pycache__" not in str(p)]
            scripts = bat_scripts + py_scripts
            if not scripts:
                self.statusBar().showMessage("Nenhum script encontrado na pasta.", 5000)
                return
            script_path = scripts[0]

        # Ask the user to name the mod
        from cdumm.gui.msg_box_br import _input_text_br
        # Use parent folder name for generic script names like install.bat
        default_name = script_path.stem
        if default_name.lower() in ("install", "setup", "patch", "run", "apply", "mod"):
            default_name = script_path.parent.name
        name, ok = _input_text_br(
            self, "Designação do Mod",
            "Insira um nome para este mod de script:",
            default=default_name,
        )
        if not ok or not name.strip():
            return
        self._script_mod_name = name.strip()

        # Phase 1: Restore game files to vanilla so the .bat runs against
        # clean files. This ensures captured deltas are always relative to
        # vanilla, regardless of what mods were previously applied.
        vanilla_dir = self._deltas_dir.parent / "vanilla"
        vanilla_dir.mkdir(parents=True, exist_ok=True)

        # Detect targets from the main script AND any sibling .py files
        targeted = _detect_script_targets(script_path, self._game_dir)
        if not targeted:
            for sibling in script_path.parent.rglob("*.py"):
                if "__pycache__" not in str(sibling):
                    targeted.extend(_detect_script_targets(sibling, self._game_dir))
            targeted = list(dict.fromkeys(targeted))  # dedupe preserving order

        logger.info("Script targets: %s", targeted)

        # Phase 1: Backup, restore, and pre-hash on a background thread
        # to avoid freezing the UI for large directories
        self._pending_script_path = script_path
        self._pending_targeted = targeted

        from cdumm.gui.workers import ScriptPrepWorker
        progress = ProgressDialog("Preparando mod de script...", self)
        worker = ScriptPrepWorker(
            targeted, self._game_dir, vanilla_dir)
        thread = QThread()
        self._run_worker(worker, thread, progress,
                         on_finished=self._on_script_prep_finished)

    def _on_script_prep_finished(self, pre_hashes) -> None:
        """Backup/restore/pre-hash complete — now launch the script."""
        if pre_hashes is None:
            self._script_pre_hashes = None
            self._script_pre_stats = {}
            logger.info("No targets, launching script directly")
        else:
            self._script_pre_hashes = pre_hashes
            self._script_pre_stats = self._capture_file_stats(pre_hashes)
            logger.info("Prep done: %d files hashed", len(pre_hashes))
        self._launch_script(self._pending_script_path)

    def _on_prehash_finished(self, pre_hashes) -> None:
        """Pre-hash complete — now launch the script."""
        self._sync_db()
        self._script_pre_hashes = pre_hashes
        self._script_pre_stats = self._capture_file_stats(pre_hashes)
        logger.info("Pre-hash done: %d files", len(pre_hashes))
        self._launch_script(self._pending_script_path)

    def _capture_file_stats(self, pre_hashes: dict) -> dict[str, tuple[int, float]]:
        """Capture size+mtime for all game files — used for fast change detection."""
        stats = {}
        for rel_path in pre_hashes:
            game_file = self._game_dir / rel_path.replace("/", "\\")
            try:
                st = game_file.stat()
                stats[rel_path] = (st.st_size, st.st_mtime)
            except OSError:
                pass
        return stats

    def _launch_script(self, script_path: Path) -> None:
        """Phase 2: Launch the script in a visible cmd window (non-blocking)."""
        import subprocess
        suffix = script_path.suffix.lower()
        if suffix == ".bat":
            cmd = ["cmd", "/c", str(script_path)]
        elif suffix == ".py":
            cmd = ["py", "-3", str(script_path)]
        else:
            self.statusBar().showMessage(f"Script não suportado: {suffix}", 5000)
            return

        import os as _os
        env = _os.environ.copy()
        env["CDUMM_GAME_DIR"] = str(self._game_dir)

        logger.info("Launching script: %s", script_path)
        self._script_proc = subprocess.Popen(
            cmd,
            cwd=str(script_path.parent),
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            env=env,
        )

        self.statusBar().showMessage(
            f"Running {script_path.name} — complete the script in its window. "
            "The mod manager will capture changes when it finishes.", 60000
        )

        # Phase 3: Poll for completion with QTimer (non-blocking)
        self._script_poll_timer = QTimer(self)
        self._script_poll_timer.timeout.connect(self._poll_script_done)
        self._script_poll_timer.start(500)  # Check every 500ms

    def _poll_script_done(self) -> None:
        """Check if the script process has finished."""
        if self._script_proc.poll() is None:
            return  # Still running

        # Script finished
        self._script_poll_timer.stop()
        logger.info("Script finished with exit code: %d", self._script_proc.returncode)

        # Script finished — now capture changes on a background thread
        self.statusBar().showMessage("Script concluído. Capturando alterações...", 30000)
        self._cleanup_script()

        progress = ProgressDialog("Capturando Alterações do Script", self)
        if self._script_pre_hashes is not None:
            # Use pre-hashes for targeted capture (fast)
            from cdumm.gui.workers import ScriptCaptureWorker
            worker = ScriptCaptureWorker(
                self._script_mod_name, self._script_pre_hashes,
                self._game_dir, self._db.db_path, self._deltas_dir,
                pre_stats=getattr(self, '_script_pre_stats', None),
            )
        else:
            # No pre-hashes — use scan-based capture
            from cdumm.gui.workers import ScanChangesWorker
            worker = ScanChangesWorker(
                self._script_mod_name,
                self._game_dir, self._db.db_path, self._deltas_dir,
            )
        thread = QThread()
        self._run_worker(worker, thread, progress,
                         on_finished=self._on_script_capture_finished)

    def _on_script_capture_finished(self, result) -> None:
        logger.info("Script capture callback received")
        self._sync_db()

        error = getattr(result, 'error', None) if result else "No result returned"
        if error:
            logger.info("Script capture result: %s", error)
            self.statusBar().showMessage("Mod de script não capturado", 10000)
            _warning_br(self, "Script Mod", error)
        else:
            name = getattr(result, 'name', 'Script mod')
            files = getattr(result, 'changed_files', [])
            logger.info("Script mod captured: %s (%d files)", name, len(files))
            self._log_activity("import", f"Importado mod de script: {name}",
                               f"{len(files)} arquivos alterados")

            # Restore vanilla — the bat modified game files directly but we've
            # captured the delta. Game files should stay clean until Apply.
            self.statusBar().showMessage(
                f"Importado: {name}. Restaurando originais...", 10000)
            vanilla_dir = self._deltas_dir.parent / "vanilla"
            targeted = getattr(self, '_pending_targeted', [])
            self._restore_vanilla_for_import(targeted, vanilla_dir)
            self._log_activity("revert", "Arquivos originais restaurados após captura",
                               "Arquivos limpos — mod guardado apenas como delta")

            self.statusBar().showMessage(
                f"Importado: {name} ({len(files)} arq.). Ative e clique em Aplicar.", 15000)
            self._refresh_all()
            self._on_nav("PAZ Mods")

    def _restore_vanilla_for_import(self, targeted: list[str], vanilla_dir: Path) -> None:
        """Restore game files to vanilla before a script import.

        If targeted files are known, only restore those. Otherwise restore
        all files that have vanilla backups (full coverage).
        """
        import os
        import shutil

        if targeted:
            files_to_restore = targeted
        else:
            # Restore all files with full vanilla backups
            files_to_restore = []
            for dirpath, _dirnames, filenames in os.walk(vanilla_dir):
                for fname in filenames:
                    if fname.endswith(".vranges"):
                        continue  # skip range backups
                    full = Path(dirpath) / fname
                    rel = full.relative_to(vanilla_dir)
                    files_to_restore.append(str(rel).replace("\\", "/"))

        restored = 0
        for rel_path in files_to_restore:
            vanilla_file = vanilla_dir / rel_path.replace("/", "\\")
            game_file = self._game_dir / rel_path.replace("/", "\\")
            if vanilla_file.exists() and game_file.exists():
                shutil.copy2(vanilla_file, game_file)
                restored += 1
                logger.info("Restored vanilla: %s", rel_path)

        if restored:
            logger.info("Restored %d files to vanilla for clean import", restored)

    def _cleanup_script(self) -> None:
        """Clean up script temp files."""
        if hasattr(self, "_script_tmp_dir") and self._script_tmp_dir:
            import shutil
            shutil.rmtree(self._script_tmp_dir, ignore_errors=True)
            self._script_tmp_dir = None

    def _on_import_finished(self, result) -> None:
        logger.info("Import callback received, syncing DB...")
        self._sync_db()

        # Limpa a pasta temp de preset selecionado (ex: cdumm_preset_*)
        # agora que o worker terminou de ler o arquivo.
        if hasattr(self, '_pending_preset_tmp') and self._pending_preset_tmp:
            import shutil
            shutil.rmtree(self._pending_preset_tmp, ignore_errors=True)
            logger.info("Preset temp dir cleaned: %s", self._pending_preset_tmp)
            self._pending_preset_tmp = None

        if hasattr(result, 'error') and result.error:
            # Collect error — don't block if more imports are queued
            if not hasattr(self, '_import_errors'):
                self._import_errors = []
            name = getattr(result, 'name', 'Unknown')
            self._import_errors.append(f"{name}: {result.error}")
            self.statusBar().showMessage(f"Erro de importação para {name}", 5000)
            logger.error("Import error for %s: %s", name, result.error)
            self._log_activity("error", f"Falha ao importar: {name}", result.error)
        else:
            # Show health check dialog if critical issues were found
            health_issues = getattr(result, 'health_issues', [])
            critical = [i for i in health_issues if i.severity == "critical"]
            if critical:
                from cdumm.gui.health_check_dialog import HealthCheckDialog
                name = getattr(result, 'name', 'Unknown')
                mod_files = {}
                dialog = HealthCheckDialog(health_issues, name, mod_files, self)
                if dialog.exec() == 0:  # rejected / cancelled
                    # Remove the just-imported mod since user cancelled
                    row = self._db.connection.execute("SELECT MAX(id) FROM mods").fetchone()
                    if row and row[0]:
                        self._mod_manager.remove_mod(row[0])
                        logger.info("Removed mod after health check cancel")
                    self._refresh_all()
                    self.statusBar().showMessage("Importação cancelada devido a problemas na saúde do mod.", 10000)
                    return

            name = getattr(result, 'name', 'Unknown')
            files = getattr(result, 'changed_files', [])
            self.statusBar().showMessage(
                f"Importado: {name} ({len(files)} arq.). Clique em Aplicar.", 10000
            )
            logger.info("Import success: %s (%d files)", name, len(files))
            self._log_activity("import", f"Importado: {name}",
                               f"{len(files)} arquivos alterados")

            # Stamp mod with current game version
            mod_id = None
            try:
                from cdumm.engine.version_detector import detect_game_version
                ver = detect_game_version(self._game_dir)
                row = self._db.connection.execute("SELECT MAX(id) FROM mods").fetchone()
                if row and row[0]:
                    mod_id = row[0]
                    if ver:
                        self._db.connection.execute(
                            "UPDATE mods SET game_version_hash = ? WHERE id = ?",
                            (ver, mod_id))
                        self._db.connection.commit()
            except Exception as e:
                logger.debug("Game version stamp failed: %s", e)

            # Mark as configurable if it came from a labeled JSON
            if mod_id and hasattr(self, '_configurable_source'):
                try:
                    logger.info("Marking mod %d as configurable, source=%s",
                                mod_id, self._configurable_source)
                    self._db.connection.execute(
                        "UPDATE mods SET configurable = 1, source_path = ? WHERE id = ?",
                        (self._configurable_source, mod_id))
                    self._db.connection.commit()
                except Exception as e:
                    logger.error("Failed to set configurable flag: %s", e)
                del self._configurable_source

                if hasattr(self, '_configurable_labels'):
                    try:
                        import json as _json2
                        self._db.connection.execute(
                            "INSERT OR REPLACE INTO mod_config (mod_id, selected_labels) "
                            "VALUES (?, ?)",
                            (mod_id, _json2.dumps(self._configurable_labels)))
                        self._db.connection.commit()
                    except Exception as e:
                        logger.error("Failed to store config labels: %s", e)
                    del self._configurable_labels

            # Restore priority and enabled state if this was an update
            if hasattr(self, '_update_priority'):
                try:
                    row = self._db.connection.execute("SELECT MAX(id) FROM mods").fetchone()
                    if row and row[0]:
                        new_id = row[0]
                        self._db.connection.execute(
                            "UPDATE mods SET priority = ?, enabled = ? WHERE id = ?",
                            (self._update_priority, self._update_enabled, new_id))
                        self._db.connection.commit()
                        logger.info("Restored update state: priority=%d, enabled=%s",
                                    self._update_priority, self._update_enabled)
                except Exception as e:
                    logger.debug("Restore update state failed: %s", e)
                del self._update_priority
                del self._update_enabled

            self._refresh_all()
            self._on_nav("PAZ Mods")
            self._update_apply_reminder()

        # Process next queued import if any
        if hasattr(self, '_import_queue') and self._import_queue:
            QTimer.singleShot(500, self._process_next_import)
        else:
            # All imports done — show error summary if any failed
            if hasattr(self, '_import_errors') and self._import_errors:
                errors = self._import_errors
                self._import_errors = []
                error_list = "\n".join(f"  - {e}" for e in errors)
                _warning_br(
                    self, "Some Imports Failed",
                    f"{len(errors)} mod(s) failed to import:\n\n{error_list}\n\n"
                    "The other mods were imported successfully.",
                )
            self._update_apply_reminder()

    def _install_asi_mod(self, path: Path) -> None:
        """Install an ASI mod by copying .asi/.ini files to bin64/."""
        import tempfile
        import zipfile
        from cdumm.asi.asi_manager import AsiManager
        asi_mgr = AsiManager(self._game_dir / "bin64")

        if not asi_mgr.has_loader():
            self.statusBar().showMessage(
                "Warning: ASI Loader (winmm.dll) not found in bin64/. ASI mods won't load without it.", 10000
            )
            logger.warning("ASI Loader not found, installing ASI mod anyway")

        # Extract zip first if needed
        if path.is_file() and path.suffix.lower() == ".zip":
            tmp = tempfile.mkdtemp(prefix="cdumm_asi_")
            try:
                with zipfile.ZipFile(path) as zf:
                    zf.extractall(tmp)
                path = Path(tmp)
            except Exception as e:
                logger.error("Failed to extract ASI zip: %s", e)

        installed = asi_mgr.install(path)
        if installed:
            self.statusBar().showMessage(
                f"Installed ASI mod: {', '.join(installed)} → bin64/", 10000
            )
            logger.info("ASI install success: %s", installed)
            # Refresh ASI panel and switch to ASI tab
            if hasattr(self, "_asi_panel"):
                self._asi_panel.refresh()
                self._on_nav("ASI Mods")
        else:
            self.statusBar().showMessage("Nenhum arquivo ASI encontrado para instalar.", 5000)
            logger.warning("No ASI files found in %s", path)

    # --- Apply ---

    def _check_group_conflicts(self) -> bool:
        """Detect enabled mods that share the same PAZ group directory.

        Popup suprimido — conflitos são apenas logados.
        O Apply sempre prossegue; a prioridade (ordem na lista) resolve automaticamente.
        Badges de conflito continuam ativos via ConflictDetector em background.

        Returns True always (Apply is never blocked by conflicts).
        """
        if not self._db:
            return True

        # Query: for each game directory (0006, 0008, ...), find all enabled
        # mods that have deltas there. More than one = potential conflict.
        mods_list = self._mod_manager.list_mods()
        visual_rank_by_id = {m["id"]: i for i, m in enumerate(mods_list)}

        rows = self._db.connection.execute(
            "SELECT SUBSTR(md.file_path, 1, 4) AS grp, m.name, m.id "
            "FROM mod_deltas md "
            "JOIN mods m ON md.mod_id = m.id "
            "WHERE m.enabled = 1 "
            "  AND md.file_path NOT LIKE 'meta/%' "
            "  AND SUBSTR(md.file_path, 5, 1) = '/' "
            "GROUP BY grp, m.id"
        ).fetchall()

        from collections import defaultdict
        group_mods: dict[str, list[tuple[str, int]]] = defaultdict(list)
        for grp, name, m_id in rows:
            grp = grp.rstrip("/")
            if grp and grp.isdigit():
                if m_id in visual_rank_by_id:
                    group_mods[grp].append((name, visual_rank_by_id[m_id]))

        conflicts = {g: mods for g, mods in group_mods.items() if len(mods) >= 2}
        if conflicts:
            # Log conflicts for debugging — no popup shown
            for grp, mods in sorted(conflicts.items()):
                sorted_mods = sorted(mods, key=lambda x: x[1])
                names = ", ".join(f"{name}(prio={prio})" for name, prio in sorted_mods)
                logger.info("Group conflict in %s/: %s — winner: %s",
                            grp, names, sorted_mods[0][0])

        # Always allow Apply to proceed — priority order handles conflicts
        return True

    def _check_game_running(self) -> bool:
        """Check if the game is running. Returns True if safe to proceed.

        Uses process name check via ctypes (fast, no subprocess).
        """
        try:
            import ctypes
            import ctypes.wintypes

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            kernel32 = ctypes.windll.kernel32
            psapi = ctypes.windll.psapi

            # Get list of all PIDs
            arr = (ctypes.wintypes.DWORD * 4096)()
            cb_needed = ctypes.wintypes.DWORD()
            psapi.EnumProcesses(ctypes.byref(arr), ctypes.sizeof(arr), ctypes.byref(cb_needed))
            num_pids = cb_needed.value // ctypes.sizeof(ctypes.wintypes.DWORD)

            for i in range(num_pids):
                pid = arr[i]
                if pid == 0:
                    continue
                handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
                if not handle:
                    continue
                try:
                    buf = ctypes.create_unicode_buffer(260)
                    size = ctypes.wintypes.DWORD(260)
                    if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
                        if buf.value.lower().endswith("crimsondesert.exe"):
                            kernel32.CloseHandle(handle)
                            _warning_br(
                                self, "Motor em Execução",
                                "O executável principal do Crimson Desert está aberto.\n\n"
                                "Você precisa fechar o jogo totalmente antes de compilar ou reescrever os mods.",
                                QMessageBox.StandardButton.Ok)
                            return False
                finally:
                    kernel32.CloseHandle(handle)
        except Exception:
            pass  # If check fails, let the user proceed
        return True

    def _on_apply(self) -> None:
        if not self._db or not self._game_dir:
            return

        if not self._check_game_running():
            return

        if not self._check_group_conflicts():
            return  # user chose to cancel and adjust priority

        progress = ProgressDialog("Aplicando Mods", self)
        worker = ApplyWorker(self._game_dir, self._vanilla_dir, self._db.db_path)
        thread = QThread()

        self._run_worker(worker, thread, progress,
                         on_finished=self._on_apply_finished)


    def _build_apply_preview(self) -> str:
        """Build a human-readable preview of what Apply will do."""
        if not self._db:
            return ""
        lines = []

        # Files that will be modified by enabled mods
        enabled_files = self._db.connection.execute(
            "SELECT DISTINCT md.file_path, m.name "
            "FROM mod_deltas md JOIN mods m ON md.mod_id = m.id "
            "WHERE m.enabled = 1 AND md.file_path != 'meta/0.papgt' "
            "ORDER BY md.file_path"
        ).fetchall()

        if enabled_files:
            # Group by file
            by_file: dict[str, list[str]] = {}
            for fp, name in enabled_files:
                by_file.setdefault(fp, []).append(name)
            modify_count = len(by_file)
            lines.append(f"Modify {modify_count} file(s):")
            for fp, mods in sorted(by_file.items())[:8]:
                lines.append(f"  {fp} ({', '.join(set(mods))})")
            if len(by_file) > 8:
                lines.append(f"  ... and {len(by_file) - 8} more")

        # Files that will be reverted (disabled mods)
        disabled_files = self._db.connection.execute(
            "SELECT DISTINCT md.file_path "
            "FROM mod_deltas md JOIN mods m ON md.mod_id = m.id "
            "WHERE m.enabled = 0"
        ).fetchall()
        revert_set = {r[0] for r in disabled_files} - {fp for fp, _ in enabled_files}
        if revert_set:
            lines.append(f"\nRestore {len(revert_set)} file(s) to vanilla:")
            for fp in sorted(revert_set)[:5]:
                lines.append(f"  {fp}")
            if len(revert_set) > 5:
                lines.append(f"  ... and {len(revert_set) - 5} more")

        lines.append("\nPAPGT will be rebuilt from scratch.")

        return "\n".join(lines) if lines else ""

    def _on_apply_finished(self) -> None:
        self._needs_apply = False
        self._set_pending_changes(False)
        # Remove mods that were pending uninstall (disabled before apply)
        if hasattr(self, '_pending_removals') and self._pending_removals:
            for mid in self._pending_removals:
                self._mod_manager.remove_mod(mid)
            count = len(self._pending_removals)
            self._pending_removals = []
            self._refresh_all()
            self.statusBar().showMessage(f"{count} mod(s) desinstalado(s) com sucesso!", 10000)
        else:
            self._refresh_all()
            self.statusBar().showMessage("Aplicando mods...", 3000)
        self._snapshot_applied_state()
        self.statusBar().showMessage("Mods aplicados.", 4000)
        self._log_activity("apply", "Mods aplicados com sucesso")
        self._schedule_conflict_check()

        if getattr(self, "_launch_after_apply", False):
            self._launch_after_apply = False
            self._on_launch_game()

    def _post_apply_verify(self) -> None:
        """Deep verification after Apply.

        Checks:
        1. PAPGT hash valid
        2. Every PAPGT entry matches its PAMT hash
        3. Every PAMT entry for modded files is within PAZ bounds
        4. Every modded file can be extracted (decrypt + decompress)
        5. No duplicate paths across PAMTs
        """
        if not self._game_dir or not self._db:
            return
        import struct, os
        from cdumm.archive.hashlittle import compute_pamt_hash, compute_papgt_hash
        from cdumm.archive.paz_parse import parse_pamt
        from cdumm.archive.paz_crypto import decrypt
        import lz4.block

        issues = []

        # 1. Check PAPGT
        papgt_path = self._game_dir / "meta" / "0.papgt"
        if papgt_path.exists():
            data = papgt_path.read_bytes()
            if len(data) >= 12:
                stored = struct.unpack_from('<I', data, 4)[0]
                computed = compute_papgt_hash(data)
                if stored != computed:
                    issues.append(("PAPGT", "PAPGT hash is invalid"))

                entry_count = data[8]
                entry_start = 12
                str_table_off = entry_start + entry_count * 12 + 4
                for i in range(entry_count):
                    pos = entry_start + i * 12
                    name_off = struct.unpack_from('<I', data, pos + 4)[0]
                    papgt_hash = struct.unpack_from('<I', data, pos + 8)[0]
                    abs_off = str_table_off + name_off
                    if abs_off < len(data):
                        end = data.index(0, abs_off) if 0 in data[abs_off:] else len(data)
                        dir_name = data[abs_off:end].decode('ascii', errors='replace')
                        pamt_path = self._game_dir / dir_name / "0.pamt"
                        if pamt_path.exists():
                            actual = compute_pamt_hash(pamt_path.read_bytes())
                            if actual != papgt_hash:
                                issues.append(("PAPGT", f"{dir_name} PAMT hash mismatch"))
                        elif not (self._game_dir / dir_name).exists():
                            issues.append(("PAPGT", f"Missing directory {dir_name}"))

        # 2. Get all files modified by enabled mods
        modded_files = self._db.connection.execute(
            "SELECT DISTINCT md.file_path, m.name "
            "FROM mod_deltas md JOIN mods m ON md.mod_id = m.id "
            "WHERE m.enabled = 1 AND md.file_path NOT LIKE 'meta/%'"
        ).fetchall()

        # Group by directory
        modded_dirs = set()
        mod_by_file = {}
        for fp, mod_name in modded_files:
            parts = fp.split("/")
            if len(parts) >= 2 and parts[0].isdigit():
                modded_dirs.add(parts[0])
            mod_by_file.setdefault(fp, []).append(mod_name)

        # 3. For each modded directory, parse PAMT and verify entries
        all_paths = {}  # path -> list of (dir_name, entry) for duplicate detection
        for dir_name in modded_dirs:
            pamt_path = self._game_dir / dir_name / "0.pamt"
            if not pamt_path.exists():
                continue

            try:
                entries = parse_pamt(str(pamt_path), paz_dir=str(self._game_dir / dir_name))
            except Exception as e:
                issues.append((dir_name, f"Failed to parse PAMT: {e}"))
                continue

            for e in entries:
                # Bounds check
                paz_path = self._game_dir / dir_name / f"{e.paz_index}.paz"
                if paz_path.exists():
                    paz_size = paz_path.stat().st_size
                    if e.offset + e.comp_size > paz_size:
                        mods = ", ".join(set(mod_by_file.get(f"{dir_name}/{e.paz_index}.paz", ["?"])))
                        issues.append((mods, f"{e.path}: out of bounds "
                                       f"(offset={e.offset} + comp={e.comp_size} > paz={paz_size})"))

            # 4. Extract test: try decrypt+decompress for a sample of modded entries
            modded_paz_files = set()
            for fp, _ in modded_files:
                if fp.startswith(dir_name + "/") and fp.endswith(".paz"):
                    modded_paz_files.add(fp)

            if modded_paz_files:
                # Test up to 20 entries from this directory
                tested = 0
                for e in entries:
                    if tested >= 20:
                        break
                    paz_fp = f"{dir_name}/{e.paz_index}.paz"
                    if paz_fp not in modded_paz_files:
                        continue

                    try:
                        paz_path = self._game_dir / dir_name / f"{e.paz_index}.paz"
                        with open(paz_path, 'rb') as f:
                            f.seek(e.offset)
                            raw = f.read(e.comp_size)

                        is_lz4 = e.compressed and e.compression_type == 2
                        if is_lz4:
                            # Try decompress, then decrypt+decompress
                            try:
                                lz4.block.decompress(raw, uncompressed_size=e.orig_size)
                            except Exception:
                                dec = decrypt(raw, os.path.basename(e.path))
                                lz4.block.decompress(dec, uncompressed_size=e.orig_size)

                        tested += 1
                    except Exception as ex:
                        mods = ", ".join(set(mod_by_file.get(paz_fp, ["?"])))
                        issues.append((mods, f"{e.path}: extract failed — {ex}"))
                        tested += 1

        # 5. Check for mods imported on a different game version
        try:
            from cdumm.engine.version_detector import detect_game_version
            current_ver = detect_game_version(self._game_dir)
            if current_ver:
                cursor = self._db.connection.execute(
                    "SELECT name, game_version_hash FROM mods "
                    "WHERE enabled = 1 AND game_version_hash IS NOT NULL")
                for name, ver in cursor.fetchall():
                    if ver and ver != current_ver:
                        issues.append((name, "Imported on a different game version — may be outdated"))
        except Exception:
            pass

        if issues:
            # Group by mod/source
            issue_lines = []
            for source, detail in issues[:15]:
                issue_lines.append(f"[{source}] {detail}")
            if len(issues) > 15:
                issue_lines.append(f"... and {len(issues) - 15} more")

            issue_text = "\n".join(issue_lines)
            _warning_br(
                self, "Verificação Pós-Aplicação",
                f"Encontrados {len(issues)} problema(s) que podem fechar o jogo:\n\n"
                f"{issue_text}\n\n"
                "O nome do mod entre colchetes indica a provável causa.",
            )
            logger.warning("Post-apply issues: %s", issues)
            self._log_activity("warning",
                               f"Verificação Pós-Aplicação: {len(issues)} problema(s)",
                               "; ".join(f"[{s}] {d}" for s, d in issues[:5]))
        else:
            self.statusBar().showMessage("Mods aplicados e verificados com sucesso!", 10000)
            logger.info("Post-apply verification passed")
            self._log_activity("apply", "Mods aplicados e verificados com sucesso")

    # --- Revert ---
    def _on_revert(self) -> None:
        if not self._db or not self._game_dir:
            return

        if not self._check_game_running():
            return

        reply = _pergunta_br(
            self, "Reverter para Original",
            "Isso irá restaurar todos os arquivos do jogo para o seu estado original.\n"
            "Todas as alterações dos mods aplicados serão removidas.\n\nContinuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        progress = ProgressDialog("Revertendo para Vanilla", self)
        worker = RevertWorker(self._game_dir, self._vanilla_dir, self._db.db_path)
        thread = QThread()

        worker.warning.connect(
            lambda msg: self._dispatcher.call(self._show_revert_warning, msg))
        self._run_worker(worker, thread, progress,
                         on_finished=self._on_revert_finished)

    def _show_revert_warning(self, msg: str) -> None:
        _warning_br(self, "Reversão Incompleta", msg)

    def _on_revert_finished(self) -> None:
        # Untick all mods so the UI matches the vanilla state
        if self._mod_manager:
            for mod in self._mod_manager.list_mods():
                if mod["enabled"]:
                    self._mod_manager.set_enabled(mod["id"], False)
        self._refresh_all()
        self._snapshot_applied_state()
        self._log_activity("revert", "Todos os arquivos do jogo foram revertidos para original (vanilla)")
        self.statusBar().showMessage("Revertido para vanilla com sucesso.", 10000)
        # Check for leftover .bak files from mod scripts
        self._check_leftover_backups()

    def _check_leftover_backups(self) -> None:
        """Warn about .bak files left behind by mod scripts in game directories."""
        if not self._game_dir:
            return
        bak_files = []
        for d in self._game_dir.iterdir():
            if not d.is_dir() or not d.name.isdigit() or len(d.name) != 4:
                continue
            for f in d.iterdir():
                if f.is_file() and f.suffix.lower() == ".bak":
                    bak_files.append(f)
        if not bak_files:
            return

        total_mb = sum(f.stat().st_size for f in bak_files) / (1024 * 1024)
        names = "\n".join(f"  {f.parent.name}/{f.name}" for f in bak_files[:10])
        if len(bak_files) > 10:
            names += f"\n  ... and {len(bak_files) - 10} more"

        reply = _pergunta_br(
            self, "Arquivos de Backup Antigos Encontrados",
            f"Foram encontrados {len(bak_files)} arquivo(s) de backup ({total_mb:.0f} MB) na sua\n"
            f"pasta do jogo:\n\n{names}\n\n"
            "Esses arquivos foram criados por scripts de mods individuais (não pelo Elite BR).\n"
            "O Elite BR possui seu próprio sistema de backup e não utiliza esses arquivos.\n"
            "Eles estão apenas ocupando espaço em disco.\n\n"
            "Deseja excluí-los?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            deleted = 0
            for f in bak_files:
                try:
                    f.unlink()
                    deleted += 1
                except Exception:
                    pass
            self.statusBar().showMessage(
                f"Deleted {deleted} leftover backup file(s).", 5000)

    # --- Remove mod ---
    def _on_remove_mod(self, mod_id: int | None = None, mod_ids: list[int] | None = None) -> None:
        """Remove one or more mods.

        Priority:
          1. mod_ids (explicit list) — used by card context menu for correct multi-select
          2. mod_id  (single explicit id) — used by table context menu single-click
          3. None    — reads selectedRows() from self._mod_list (table widget)
        """
        if not hasattr(self, "_mod_list") or not self._mod_manager:
            return

        # Build list of mods to remove
        mods_to_remove: list[tuple[int, str]] = []

        if mod_ids is not None:
            # Explicit list passed by caller (card context menu batch remove)
            for mid in mod_ids:
                cursor = self._db.connection.execute("SELECT name FROM mods WHERE id = ?", (mid,))
                row = cursor.fetchone()
                mods_to_remove.append((mid, row[0] if row else f"Mod {mid}"))
        elif mod_id is not None:
            # Single explicit mod_id (table context menu)
            cursor = self._db.connection.execute("SELECT name FROM mods WHERE id = ?", (mod_id,))
            row = cursor.fetchone()
            mods_to_remove.append((mod_id, row[0] if row else f"Mod {mod_id}"))
        else:
            # Fall back to table widget selection
            indexes = self._mod_list.selectionModel().selectedRows()
            if not indexes:
                return
            for idx in indexes:
                mod = self._get_mod_at_proxy_row(idx.row())
                if mod:
                    mods_to_remove.append((mod["id"], mod["name"]))

        if not mods_to_remove:
            return

        if len(mods_to_remove) == 1:
            msg = f"Desinstalar o mod '{mods_to_remove[0][1]}'?"
        else:
            names = "\n".join(f"  • {name}" for _, name in mods_to_remove)
            msg = f"Deseja desinstalar {len(mods_to_remove)} mods?\n\n{names}"

        reply = _pergunta_br(
            self, "Desinstalar Mods", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            # Check if any mod was actually applied (enabled AND has delta data).
            # If the mod has no deltas (e.g. after a version migration that
            # wiped delta data), just delete it — no Apply needed.
            needs_apply = False
            for mid, name in mods_to_remove:
                mod_row = self._db.connection.execute(
                    "SELECT enabled FROM mods WHERE id = ?", (mid,)).fetchone()
                delta_count = self._db.connection.execute(
                    "SELECT COUNT(*) FROM mod_deltas WHERE mod_id = ?", (mid,)).fetchone()[0]
                if mod_row and mod_row[0] and delta_count > 0:
                    needs_apply = True
                    break

            if needs_apply:
                for mid, name in mods_to_remove:
                    self._mod_manager.set_enabled(mid, False)
                    logger.info("Disabled for uninstall: %s", name)
                self._pending_removals = [mid for mid, _ in mods_to_remove]
                self._refresh_all()
                self.statusBar().showMessage(
                    f"Desinstalando {len(mods_to_remove)} mod(s) — Clicar Aplicar necessário para reverter arquivos...", 10000)
                self._on_apply()
            else:
                for mid, name in mods_to_remove:
                    self._mod_manager.remove_mod(mid)
                    self._log_activity("remove", f"Removido: {name}",
                                       "Este mod nunca foi ativamente aplicado ao jogo, então nada a reverter")
                    logger.info("Removed unapplied mod: %s", name)
                self._refresh_all()
                self.statusBar().showMessage(
                    f"Removido(s) {len(mods_to_remove)} mod(s).", 10000)


    def _update_header_checkbox(self) -> None:
        """Sync the header checkbox label with current mod states."""
        if not hasattr(self, '_check_header') or not hasattr(self, "_mod_list_model") or not self._mod_list_model:
            return
        mods = self._mod_list_model._mods
        if not mods or not any(m.get("enabled") for m in mods):
            label = "☐"
        elif all(m.get("enabled") for m in mods):
            label = "☑"
        else:
            label = "◧"
        self._check_header.set_label(label)

    def _find_existing_mod(self, path: Path) -> tuple[int, str] | None:
        """Check if a dropped mod matches an already-installed mod by name.

        Returns (mod_id, mod_name) or None.
        """
        from cdumm.engine.import_handler import _read_modinfo
        from cdumm.engine.json_patch_handler import detect_json_patch
        from cdumm.engine.crimson_browser_handler import detect_crimson_browser

        def _normalize(s: str) -> str:
            return s.lower().strip().replace("-", " ").replace("_", " ")

        def _compact(s: str) -> str:
            """Remove all spaces for matching concatenated names like CDLootMultiplier."""
            return _normalize(s).replace(" ", "")

        # Get the mod name from the drop
        drop_name = path.stem.lower()
        modinfo = _read_modinfo(path) if path.is_dir() else None
        if modinfo and modinfo.get("name"):
            drop_name = modinfo["name"].lower()
        elif path.suffix.lower() == ".json":
            jp = detect_json_patch(path)
            if jp and jp.get("name"):
                drop_name = jp["name"].lower()
        elif path.is_dir():
            cb = detect_crimson_browser(path)
            if cb and cb.get("id"):
                drop_name = cb["id"].lower()

        drop_norm = _normalize(drop_name)
        drop_compact = _compact(drop_name)
        for m in self._mod_manager.list_mods():
            mod_norm = _normalize(m["name"])
            mod_compact = _compact(m["name"])
            # Check with spaces (loot multiplier in cdlootmultiplier)
            if len(mod_norm) >= 4 and mod_norm in drop_norm:
                return (m["id"], m["name"])
            if len(drop_norm) >= 4 and drop_norm in mod_norm:
                return (m["id"], m["name"])
            # Check without spaces (lootmultiplier in cdlootmultiplier)
            if len(mod_compact) >= 4 and mod_compact in drop_compact:
                return (m["id"], m["name"])
            if len(drop_compact) >= 4 and drop_compact in mod_compact:
                return (m["id"], m["name"])

        return None

    def _on_toggle_all(self) -> None:
        """Toggle all mods on/off."""
        if not self._mod_manager:
            return
        mods = self._mod_manager.list_mods()
        if not mods:
            return
        any_enabled = any(m["enabled"] for m in mods)
        for m in mods:
            self._mod_manager.set_enabled(m["id"], not any_enabled)
        self._refresh_all()
        self._update_apply_reminder()

    # --- View details ---
    def _get_mod_at_proxy_row(self, proxy_row: int) -> dict | None:
        """Map a proxy model row to the source model and get the mod."""
        if hasattr(self, "_sort_proxy"):
            source_index = self._sort_proxy.mapToSource(self._sort_proxy.index(proxy_row, 0))
            return self._mod_list_model.get_mod_at_row(source_index.row())
        return self._mod_list_model.get_mod_at_row(proxy_row)

    def _on_view_details(self) -> None:
        if not hasattr(self, "_mod_list") or not self._mod_manager:
            return
        indexes = self._mod_list.selectionModel().selectedRows()
        if not indexes:
            return
        mod = self._get_mod_at_proxy_row(indexes[0].row())
        if not mod:
            return
        self._show_mod_contents(mod["id"])

    # --- Mod context menu ---
    def _show_mod_context_menu(self, pos) -> None:
        if not hasattr(self, "_mod_list") or not self._mod_manager:
            return
        index = self._mod_list.indexAt(pos)
        if not index.isValid():
            return
        mod = self._get_mod_at_proxy_row(index.row())
        if not mod:
            return

        # Capture full selection NOW — before any other operation can change it.
        # QListView.selectedIndexes() returns all selected items correctly,
        # unlike selectedRows() which can miss items in a list-only model.
        _all_selected_ids: list[int] = []
        for sel_idx in self._mod_list.selectedIndexes():
            sel_mod = self._get_mod_at_proxy_row(sel_idx.row())
            if sel_mod and sel_mod["id"] not in _all_selected_ids:
                _all_selected_ids.append(sel_mod["id"])
        # Always include the right-clicked mod (may not be in selection if user
        # right-clicked without Ctrl/Shift — treat as single-mod action in that case)
        if not _all_selected_ids:
            _all_selected_ids = [mod["id"]]

        from PySide6.QtGui import QAction
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(14, 8, 12, 0.96);
                border: 1px solid rgba(229, 20, 20, 0.6);
                border-radius: 6px;
                padding: 6px;
                margin: 0px;
            }
            QMenu::item {
                color: #E0E0E0;
                font-family: 'Segoe UI';
                font-size: 12px;
                font-weight: 500;
                padding: 8px 32px 8px 16px;
                border-radius: 4px;
                margin: 2px 4px;
            }
            QMenu::item:selected {
                background-color: rgba(229, 20, 20, 0.35);
                color: #FFFFFF;
                border-left: 2px solid #FF6E1A;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 110, 26, 0.25);
                margin: 6px 12px;
            }
        """)


        # Enable/Disable
        if mod["enabled"]:
            toggle_action = QAction("Desativar", self)
        else:
            toggle_action = QAction("Ativar", self)
        toggle_action.triggered.connect(lambda: self._on_toggle_mod(mod))
        menu.addAction(toggle_action)

        menu.addSeparator()

        # Configure (only for mods with labeled changes)
        is_configurable = self._db.connection.execute(
            "SELECT configurable FROM mods WHERE id = ?", (mod["id"],)
        ).fetchone()
        if is_configurable and is_configurable[0]:
            configure_action = QAction("Configurar...", self)
            configure_action.triggered.connect(lambda: self._on_configure_mod(mod))
            menu.addAction(configure_action)

        # Patch toggle (only for JSON mods with individual byte patches)
        json_src_row = self._db.connection.execute(
            "SELECT json_source FROM mods WHERE id = ?", (mod["id"],)
        ).fetchone()
        if json_src_row and json_src_row[0]:
            patch_action = QAction("⚡ Alternar Patches...", self)
            patch_action.triggered.connect(lambda: self._on_patch_toggle_mod(mod))
            menu.addAction(patch_action)

        rename_action = QAction("Renomear", self)
        rename_action.triggered.connect(lambda: self._on_rename_mod(mod))
        menu.addAction(rename_action)

        update_action = QAction("Atualizar (substituir por nova versão)", self)
        update_action.triggered.connect(lambda: self._on_update_mod(mod))
        menu.addAction(update_action)

        # Reimport from source (v2.3.2)
        source_dir = self._cdmods_dir / "sources" / str(mod["id"])
        if source_dir.exists() and any(source_dir.iterdir()):
            reimport_action = QAction("Reimportar da origem", self)
            reimport_action.triggered.connect(lambda: self._on_reimport_from_source(mod))
            menu.addAction(reimport_action)

        menu.addSeparator()

        # Uninstall — use pre-captured selection to avoid QListView selectedRows() bug
        if len(_all_selected_ids) > 1:
            remove_action = QAction(f"Desinstalar {len(_all_selected_ids)} mods selecionados", self)
            remove_action.triggered.connect(
                lambda checked=False, ids=_all_selected_ids: self._on_remove_mod(mod_ids=ids))
        else:
            remove_action = QAction("Desinstalar", self)
            remove_action.triggered.connect(lambda checked=False: self._on_remove_mod(mod_id=mod["id"]))
        menu.addAction(remove_action)

        menu.exec(self._mod_list.viewport().mapToGlobal(pos))

    def _show_mod_card_context_menu(self, pos) -> None:
        """Context menu for the card list — same actions as _show_mod_context_menu."""
        if not hasattr(self, "_mod_card_list") or not self._mod_manager:
            return
        item = self._mod_card_list.itemAt(pos)
        if not item:
            return
        card = item.data(Qt.ItemDataRole.UserRole)
        if not card:
            return
        mod = next(
            (m for m in self._mod_manager.list_mods() if m["id"] == card["id"]),
            None,
        )
        if not mod:
            return

        from PySide6.QtGui import QAction
        menu = QMenu(self)

        toggle_action = QAction("Desativar" if mod["enabled"] else "Ativar", self)
        toggle_action.triggered.connect(lambda: self._on_toggle_mod(mod))
        menu.addAction(toggle_action)

        menu.addSeparator()

        is_configurable = self._db.connection.execute(
            "SELECT configurable FROM mods WHERE id = ?", (mod["id"],)
        ).fetchone()
        if is_configurable and is_configurable[0]:
            configure_action = QAction("Configurar...", self)
            configure_action.triggered.connect(lambda: self._on_configure_mod(mod))
            menu.addAction(configure_action)

        rename_action = QAction("Renomear", self)
        rename_action.triggered.connect(lambda: self._on_rename_mod(mod))
        menu.addAction(rename_action)

        update_action = QAction("Atualizar (substituir por nova versão)", self)
        update_action.triggered.connect(lambda: self._on_update_mod(mod))
        menu.addAction(update_action)

        # Reimport from source (v2.3.2)
        source_dir = self._cdmods_dir / "sources" / str(mod["id"])
        if source_dir.exists() and any(source_dir.iterdir()):
            reimport_action = QAction("Reimportar da origem", self)
            reimport_action.triggered.connect(lambda: self._on_reimport_from_source(mod))
            menu.addAction(reimport_action)

        menu.addSeparator()

        # Uninstall — card menu passes explicit IDs to avoid cross-widget selection confusion
        selected_card_items = self._mod_card_list.selectedItems()
        if len(selected_card_items) > 1:
            # Collect mod IDs from all selected cards
            selected_ids = []
            for item in selected_card_items:
                card_data = item.data(Qt.ItemDataRole.UserRole)
                if card_data and "id" in card_data:
                    selected_ids.append(card_data["id"])
            remove_action = QAction(f"Desinstalar {len(selected_ids)} mods selecionados", self)
            remove_action.triggered.connect(lambda checked=False, ids=selected_ids: self._on_remove_mod(mod_ids=ids))
        else:
            remove_action = QAction("Desinstalar", self)
            remove_action.triggered.connect(
                lambda: self._on_remove_mod(mod_id=mod["id"]))
        menu.addAction(remove_action)

        menu.exec(self._mod_card_list.viewport().mapToGlobal(pos))

    def _on_configure_mod(self, mod: dict) -> None:
        """Reabrir o seletor de variantes/patches para um mod configurável.

        Dois caminhos:
        1. Mod multi-variante (import_multi_variant) → lê coluna `variants`
           → mostra PresetPickerDialog pré-selecionado → update_variant_selection
        2. Mod configurável legado (source_path + labeled changes)
           → TogglePickerDialog (fluxo original)
        """
        import json as _json_cfg

        # ── Caminho 1: mod multi-variante ────────────────────────────────
        variants_row = self._db.connection.execute(
            "SELECT variants FROM mods WHERE id = ?", (mod["id"],)
        ).fetchone()

        if variants_row and variants_row[0]:
            try:
                variants_list = _json_cfg.loads(variants_row[0])
            except Exception as e:
                logger.error("Falha ao ler variantes do mod %d: %s", mod["id"], e)
                _warning_br(self, "Erro", "Não foi possível ler as variantes deste mod.")
                return

            mods_dir = self._cdmods_dir / "mods"
            variants_dir = mods_dir / str(mod["id"]) / "variants"

            # Reconstruir (path, data) do disco, preservando a ordem de variants_list
            presets: list[tuple] = []
            enabled_flags: list[bool] = []
            for v in variants_list:
                vpath = variants_dir / v["filename"]
                if not vpath.exists():
                    logger.warning("Arquivo de variante ausente: %s", vpath)
                    continue
                try:
                    data = _json_cfg.loads(vpath.read_text(encoding="utf-8"))
                except Exception as e:
                    logger.warning("Falha ao ler variante (%s): %s", vpath, e)
                    data = {}
                presets.append((vpath, data))
                enabled_flags.append(bool(v.get("enabled", False)))

            if not presets:
                _warning_br(self, "Impossível Configurar",
                            "Nenhum arquivo de variante encontrado em:\n"
                            f"{variants_dir}\n\n"
                            "Reimporte o mod para restaurar as variantes.")
                return

            from cdumm.gui.preset_picker import PresetPickerDialog
            dialog = PresetPickerDialog(presets, self)
            dialog.setWindowTitle("Configurar Variantes")
            # Pré-selecionar quais variantes estão ativas
            for i, cb in enumerate(dialog._checkboxes):
                cb.setChecked(enabled_flags[i] if i < len(enabled_flags) else False)

            if dialog.exec() and dialog.selected_presets is not None:
                selected_names = {p.name for p, _ in dialog.selected_presets}
                # Montar lista de seleção na ordem original de variants_list
                new_selection = [
                    {"enabled": v["filename"] in selected_names}
                    for v in variants_list
                ]
                from cdumm.engine.variant_handler import update_variant_selection
                update_variant_selection(
                    mod["id"], new_selection, mods_dir, self._db)
                self.statusBar().showMessage(
                    "Configuração de variantes salva. Clique em Aplicar para efetivar.",
                    8000)
            return  # multi-variante tratado — não cai no fluxo legado

        # ── Caminho 2: mod configurável legado (source_path) ─────────────
        source = self._db.connection.execute(
            "SELECT source_path FROM mods WHERE id = ?", (mod["id"],)
        ).fetchone()
        if not source or not source[0]:
            _warning_br(self, "Impossível Configurar",
                                "A origem original do mod não foi encontrada.")
            return

        source_path = Path(source[0])
        if not source_path.exists():
            _warning_br(self, "Impossível Configurar",
                                f"Arquivo original não encontrado:\n{source_path}\n\n"
                                "Solte o arquivo do mod novamente para reimportar com novas configurações.")
            return

        from cdumm.gui.preset_picker import has_labeled_changes, TogglePickerDialog
        from cdumm.engine.json_patch_handler import detect_json_patch
        import tempfile

        # Extract if archive
        check_path = source_path
        tmp_dir = None
        if source_path.suffix.lower() in (".zip", ".7z"):
            try:
                tmp_dir = tempfile.mkdtemp(prefix="cdumm_reconfig_")
                if source_path.suffix.lower() == ".zip":
                    import zipfile
                    with zipfile.ZipFile(source_path) as zf:
                        zf.extractall(tmp_dir)
                else:
                    import py7zr
                    with py7zr.SevenZipFile(source_path, 'r') as zf:
                        zf.extractall(tmp_dir)
                check_path = Path(tmp_dir)
            except Exception:
                pass

        json_data = detect_json_patch(check_path)
        if not json_data or not has_labeled_changes(json_data):
            if tmp_dir:
                import shutil
                shutil.rmtree(tmp_dir, ignore_errors=True)
            _warning_br(self, "Impossível Configurar",
                                "Nenhuma opção configurável interna encontrada neste mod.")
            return

        # Load previous selection
        previous_labels = None
        try:
            import json as _json3
            row = self._db.connection.execute(
                "SELECT selected_labels FROM mod_config WHERE mod_id = ?",
                (mod["id"],)).fetchone()
            if row and row[0]:
                previous_labels = _json3.loads(row[0])
        except Exception:
            pass

        dialog = TogglePickerDialog(json_data, self, previous_labels=previous_labels)
        if dialog.exec() and dialog.selected_data:
            import json as _json
            # Save old state
            old_priority = mod.get("priority", 0)
            old_enabled = mod.get("enabled", False)

            # Remove old mod and re-import with new selection
            self._mod_manager.remove_mod(mod["id"])

            tmp_json = Path(tempfile.mktemp(suffix=".json", prefix="cdumm_reconfig_"))
            write_data = dialog.selected_data.copy()
            write_data.pop("_json_path", None)
            tmp_json.write_text(_json.dumps(write_data, indent=2, default=str), encoding="utf-8")
            self._configurable_source = str(source_path)
            # Store new selection for future reconfigure
            new_labels = []
            for patch in dialog.selected_data.get("patches", []):
                for c in patch.get("changes", []):
                    if "label" in c:
                        new_labels.append(c["label"])
            self._configurable_labels = new_labels

            # Import the filtered JSON
            progress = ProgressDialog("Reimportando com nova configuração...", self)
            worker = ImportWorker(tmp_json, self._game_dir, self._db.db_path, self._deltas_dir)
            thread = QThread()

            def on_done(result):
                self._on_import_finished(result)
                # Restore priority and name
                try:
                    row = self._db.connection.execute("SELECT MAX(id) FROM mods").fetchone()
                    if row and row[0]:
                        self._db.connection.execute(
                            "UPDATE mods SET priority = ?, enabled = ?, name = ? WHERE id = ?",
                            (old_priority, old_enabled, mod["name"], row[0]))
                        self._db.connection.commit()
                    self._refresh_all()
                except Exception:
                    pass
                self._log_activity("import", f"Reconfigurado: {mod['name']}")

            self._run_worker(worker, thread, progress, on_finished=on_done)

        if tmp_dir:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def _on_toggle_mod(self, mod: dict) -> None:
        """Toggle via menu de contexto — instantâneo: só atualiza DB e modelo."""
        if not self._mod_manager:
            return
        new_state = not mod["enabled"]
        self._mod_manager.set_enabled(mod["id"], new_state)
        # Atualiza a linha via update_mod_state em vez de full refresh
        if hasattr(self, "_mod_list_model"):
            self._mod_list_model.update_mod_state(mod["id"], new_state)
        self._update_apply_reminder()
        self._update_header_checkbox()
        self._schedule_dashboard_update()

    def _on_patch_toggle_mod(self, mod: dict) -> None:
        """Abre o dialog de alternâncias de patches individuais para um mod JSON."""
        from cdumm.gui.patch_toggle_dialog import PatchToggleDialog
        dialog = PatchToggleDialog(mod, self._mod_manager, self)
        dialog.exec()
        # Patches afetam apenas o Apply — não precisamos de full refresh da lista
        self.statusBar().showMessage(
            "Configuração de patches atualizada. Clique em Aplicar para efetivar.", 5000
        )

    def _on_mod_toggled_via_checkbox(self) -> None:
        self._update_apply_reminder()
        # Atualiza contador do header sem resetar o modelo
        self._schedule_dashboard_update()

    def _snapshot_applied_state(self) -> None:
        """Save current mod enabled states as the 'applied' baseline."""
        if self._mod_manager:
            self._applied_state = {m["id"]: m["enabled"] for m in self._mod_manager.list_mods()}

    def _update_apply_reminder(self) -> None:
        """Show or clear the apply reminder based on whether state differs from last apply."""
        if not hasattr(self, "_mod_list_model") or not self._mod_list_model:
            return
        current = {m.get("id"): m.get("enabled") for m in self._mod_list_model._mods}
        if current != self._applied_state:
            self._needs_apply = True
            self.statusBar().showMessage(
                "Lista de mods alterada — clique em Aplicar para atualizar os arquivos do jogo.", 0)
        else:
            self._needs_apply = False
            self.statusBar().clearMessage()

    def _on_rename_mod(self, mod: dict) -> None:
        from cdumm.gui.msg_box_br import _input_text_br
        name, ok = _input_text_br(
            self, "Renomear Mod", "Novo nome:", default=mod["name"])
        if ok and name.strip():
            self._mod_manager.rename_mod(mod["id"], name.strip())
            self._refresh_all()
            self.statusBar().showMessage(f"Renomeado para: {name.strip()}", 5000)

    # --- Update mod ---
    def _on_update_mod(self, mod: dict) -> None:
        """Show overlay for drag-drop mod update."""
        if not self._db or not self._game_dir or not self._mod_manager:
            return
        from cdumm.gui.update_overlay import UpdateOverlay
        self._update_overlay = UpdateOverlay(mod["name"], parent=self.centralWidget())
        self._update_mod_target = mod
        self._update_overlay.folder_dropped.connect(self._on_update_drop)
        self._update_overlay.cancelled.connect(lambda: self._update_overlay.deleteLater())
        self._update_overlay.show_overlay()

    def _on_update_drop(self, path: Path) -> None:
        """Handle the dropped folder/zip for mod update."""
        mod = self._update_mod_target
        self._update_overlay.deleteLater()

        # Validate: check the dropped content looks like the same mod
        from cdumm.engine.import_handler import _read_modinfo
        modinfo = _read_modinfo(path) if path.is_dir() else None

        # Check by modinfo name match if available
        if modinfo and modinfo.get("name"):
            dropped_name = modinfo["name"].lower().strip()
            existing_name = mod["name"].lower().strip()
            # Allow partial matches (mod names often have version suffixes)
            if dropped_name not in existing_name and existing_name not in dropped_name:
                # Names don't match — warn the user
                reply = _pergunta_br(
                    self, "Mod Name Mismatch",
                    f"The dropped mod is \"{modinfo['name']}\" but you're updating "
                    f"\"{mod['name']}\".\n\nAre you sure this is the right mod?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return

        mod_id = mod["id"]
        logger.info("Updating mod %d (%s) from %s", mod_id, mod["name"], path)

        # Clear old deltas but keep the mod entry
        self._mod_manager.clear_deltas(mod_id)

        # Check for script mods — same flow as import but with existing mod_id
        from cdumm.engine.import_handler import detect_format
        import zipfile as _zf

        is_script_mod = False
        if path.suffix.lower() in (".bat", ".py"):
            is_script_mod = True
        elif path.suffix.lower() == ".zip":
            try:
                with _zf.ZipFile(path) as zf:
                    names = zf.namelist()
                    has_scripts = any(n.endswith((".bat", ".py")) for n in names)
                    has_game_files = any(
                        any(n.startswith(f"{i:04d}/") for i in range(33)) or n.startswith("meta/")
                        for n in names
                    )
                    if has_scripts and not has_game_files:
                        is_script_mod = True
            except _zf.BadZipFile:
                pass
        elif path.is_dir():
            scripts = list(path.glob("*.bat")) + list(path.glob("*.py"))
            game_files = any(
                (path / f"{i:04d}").exists() for i in range(33)
            ) or (path / "meta").exists()
            if scripts and not game_files:
                is_script_mod = True

        if is_script_mod:
            # Script update — use the existing script flow, mod_id will be handled
            # by ScriptCaptureWorker writing to a new mod entry.
            # For simplicity, re-import as new and delete the old one, preserving priority.
            self.statusBar().showMessage(
                "Script mods must be re-imported. Remove the old version and import the new one.", 10000)
            return

        # Regular PAZ mod update — run on background thread with existing_mod_id
        progress = ProgressDialog(f"Atualizando: {mod['name']}", self)
        worker = ImportWorker(path, self._game_dir, self._db.db_path,
                              self._deltas_dir, existing_mod_id=mod_id)
        thread = QThread()

        self._run_worker(worker, thread, progress,
                         on_finished=self._on_update_finished)

    def _on_update_finished(self, result) -> None:
        self._sync_db()

        error = getattr(result, 'error', None) if result else "No result"
        if error:
            self.statusBar().showMessage(f"Erro na atualização: {error}", 10000)
        else:
            name = getattr(result, 'name', 'Mod')
            files = getattr(result, 'changed_files', [])
            self.statusBar().showMessage(
                f"Atualizado: {name} ({len(files)} arquivos alterados)", 10000)
            self._refresh_all()

    # --- Reimport from source (v2.3.2) ---
    def _on_reimport_from_source(self, mod: dict) -> None:
        """Reimporta um mod a partir dos arquivos de origem armazenados."""
        if not self._db or not self._game_dir or not self._mod_manager:
            return
        source_dir = self._cdmods_dir / "sources" / str(mod["id"])
        if not source_dir.exists():
            _warning_br(self, "Sem Origem",
                        "Nenhum arquivo de origem armazenado encontrado para este mod.")
            return

        reply = _pergunta_br(
            self, "Reimportar da Origem",
            f"Reimportar \"{mod['name']}\" a partir dos arquivos de origem armazenados?\n\n"
            f"Isso limpará os deltas antigos e reimportará contra a versão atual do jogo.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            from cdumm.engine.import_handler import import_from_folder
            # Limpa deltas antigos
            self._mod_manager.clear_deltas(mod["id"])
            # Reimporta
            result = import_from_folder(
                source_dir, self._game_dir, self._db, self._snapshot,
                self._deltas_dir, existing_mod_id=mod["id"])
            if result.error:
                _warning_br(self, "Reimportação Falhou", result.error)
            else:
                count = len(result.changed_files)
                from cdumm.gui.msg_box_br import _info_br
                _info_br(
                    self, "Reimportado",
                    f"Reimportado \"{mod['name']}\" com {count} arquivo(s).")
            self._refresh_all()
        except Exception as e:
            from cdumm.gui.msg_box_br import _critical_br
            _critical_br(self, "Erro de Reimportação", str(e))

    # --- Load order ---
    def _on_move_up(self) -> None:
        if not hasattr(self, "_mod_list") or not self._mod_manager:
            return
        indexes = self._mod_list.selectionModel().selectedRows()
        if not indexes:
            return
        mod = self._get_mod_at_proxy_row(indexes[0].row())
        if not mod:
            return
        self._mod_manager.move_up(mod["id"])
        self._refresh_all()
        # Re-select the moved mod
        new_row = max(0, indexes[0].row() - 1)
        self._mod_list.selectRow(new_row)
        self.statusBar().showMessage(f"Moveu '{mod['name']}' para cima na ordem de carregamento", 3000)

    def _on_move_down(self) -> None:
        if not hasattr(self, "_mod_list") or not self._mod_manager:
            return
        indexes = self._mod_list.selectionModel().selectedRows()
        if not indexes:
            return
        mod = self._get_mod_at_proxy_row(indexes[0].row())
        if not mod:
            return
        self._mod_manager.move_down(mod["id"])
        self._refresh_all()
        # Re-select the moved mod
        new_row = min(self._mod_list_model.rowCount() - 1, indexes[0].row() + 1)
        self._mod_list.selectRow(new_row)
        self.statusBar().showMessage(f"Moveu '{mod['name']}' para baixo na ordem de carregamento", 3000)

    def _on_set_winner(self, mod_id: int) -> None:
        """Set a mod as the winner (highest priority) from conflict view context menu."""
        if not self._mod_manager:
            return
        self._mod_manager.set_winner(mod_id)
        self._refresh_all()
        self.statusBar().showMessage("Ordem de carga atualizada — conflito resolvido", 5000)

    # --- Test Mod ---
    def _on_test_mod(self) -> None:
        if not self._db or not self._snapshot or not self._game_dir:
            _warning_br(self, "Erro", "Banco de dados ou diretório do jogo não configurados.")
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Mod to Test",
            "", "Mod Files (*.zip);;All Files (*)",
        )
        if not path:
            return
        self.statusBar().showMessage(f"Testando mod: {Path(path).name}...")
        from cdumm.engine.test_mod_checker import test_mod
        from cdumm.gui.test_mod_dialog import TestModDialog
        result = test_mod(Path(path), self._game_dir, self._db, self._snapshot)
        dialog = TestModDialog(result, self)
        dialog.exec()
        self.statusBar().showMessage("Teste concluído", 5000)

    # --- Snapshot ---
    def _on_refresh_snapshot(self, skip_verify_prompt: bool = False) -> None:
        if not self._db or not self._game_dir:
            return
        if self._snapshot_in_progress:
            return

        if not skip_verify_prompt:
            reply = _pergunta_br(
                self, "Re-escanear Arquivos do Jogo",
                "Isso criará um novo backup original a partir dos arquivos atuais do jogo.\n\n"
                "Você já verificou a integridade dos arquivos pela Steam?\n\n"
                "  Steam → Clique-direito em Crimson Desert → Propriedades\n"
                "  → Arquivos Instalados → Verificar integridade dos arquivos\n\n"
                "Só re-escaneie DEPOIS de verificar pela Steam — senão o backup\n"
                "pode capturar arquivos de mods como sendo originais.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self._snapshot_in_progress = True

        progress = ProgressDialog("Criando Backup Original", self)
        worker = SnapshotWorker(
            self._game_dir,
            self._db.db_path,
            # Passa vanilla_dir para limpar na thread de background (evita freeze na GUI)
            vanilla_dir=self._vanilla_dir if self._vanilla_dir and self._vanilla_dir.exists() else None,
        )
        worker.activity.connect(self._log_activity)
        thread = QThread()

        self._run_worker(worker, thread, progress,
                         on_finished=self._on_snapshot_finished)

    def _on_snapshot_finished(self, count: int) -> None:
        self._snapshot_in_progress = False
        logger.info("Snapshot callback: %d files", count)
        self._sync_db()

        # Save game version fingerprint with the snapshot
        try:
            from cdumm.engine.version_detector import detect_game_version
            from cdumm.storage.config import Config
            fp = detect_game_version(self._game_dir)
            if fp:
                Config(self._db).set("game_version_fingerprint", fp)
                logger.info("Saved game version fingerprint: %s", fp)
        except Exception:
            pass

        # Refresh stale vanilla backups de forma lazy (evita freeze no thread principal).
        # Adia 500 ms para o dialog de progresso fechar e a UI ficar responsiva primeiro.
        QTimer.singleShot(500, self._refresh_vanilla_backups)

        self._update_snapshot_status()
        self.statusBar().showMessage(f"Backup original concluído: {count} arquivos indexados. Pode importar mods.", 10000)
        logger.info("Snapshot finished and UI updated")
        self._log_activity("snapshot", f"Verificação de arquivos: {count} arquivos indexados")

        # Atualiza o card "Proteção de Arquivos" no dashboard imediatamente,
        # sem precisar trocar de aba.
        self._schedule_dashboard_update()

        # Auto-reimport mods from stored sources after game update
        if getattr(self, '_pending_auto_reimport', False):
            self._pending_auto_reimport = False
            QTimer.singleShot(1000, self._auto_reimport_mods)

    def _auto_migrate_after_update(self) -> None:
        """Reverte e reimporta todos os mods após uma atualização do CDUMM.

        Deltas de versões anteriores podem usar formatos incompatíveis
        (FULL_COPY em vez de ENTR, criptografia errada, hashes PAPGT obsoletos).
        Garante que os mods sejam armazenados no formato da versão atual.
        Executado em background com barra de progresso.
        """
        if not self._mod_manager or not self._game_dir:
            return

        # Verificar se algum mod tem fontes armazenadas para reimportar
        sources_dir = self._cdmods_dir / "sources"
        mods = self._db.connection.execute(
            "SELECT id, name, source_path FROM mods").fetchall()
        has_sources = any(
            (sources_dir / str(mid)).exists() or (sp and Path(sp).exists())
            for mid, _, sp in mods
        )
        if not has_sources:
            return

        reply = _pergunta_br(
            self, "Crimson Desert Atualizado",
            f"O Crimson Desert foi atualizado e o formato interno dos mods mudou.\n\n"
            f"Seus {len(mods)} mod(s) precisam ser reimportados para funcionar corretamente\n"
            f"com a nova versão. Isso reverterá para o jogo original e reimportará\n"
            f"todos os mods automaticamente. Suas definições são preservadas.\n\n"
            f"Reimportar agora? (Recomendado)"
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Salvar estado dos mods antes da migração
        mod_states = []
        for mod in self._mod_manager.list_mods():
            mod_states.append({
                "name": mod["name"],
                "enabled": mod["enabled"],
                "priority": mod["priority"],
            })
        self._migrate_mod_states = mod_states

        # Executar em thread background com barra de progresso
        from cdumm.gui.workers import MigrateWorker
        progress = ProgressDialog("Migrando Mods", self)
        worker = MigrateWorker(
            self._game_dir, self._vanilla_dir, self._cdmods_dir,
            self._db.db_path, self._deltas_dir)
        thread = QThread()
        self._run_worker(worker, thread, progress,
                         on_finished=self._on_migrate_finished)

    def _auto_reimport_mods(self) -> None:
        """Re-import all mods from stored sources after a game update."""
        from cdumm.engine.import_handler import (
            _process_extracted_files, detect_format, import_from_json_patch,
        )
        from cdumm.engine.json_patch_handler import detect_json_patch

        sources_dir = self._cdmods_dir / "sources"
        if not sources_dir.exists():
            return

        # Get all mods with their source paths
        mods = self._db.connection.execute(
            "SELECT id, name, source_path, priority FROM mods "
            "ORDER BY priority").fetchall()

        reimported = 0
        failed = 0
        for mod_id, mod_name, source_path, priority in mods:
            # Check if source exists in CDModsElite/sources/<mod_id>/
            src = sources_dir / str(mod_id)
            if not src.exists() or not any(src.iterdir()):
                # Try the stored source_path as fallback
                if source_path and Path(source_path).exists():
                    src = Path(source_path)
                else:
                    logger.warning("No source for %s (id=%d), skipping", mod_name, mod_id)
                    failed += 1
                    continue

            try:
                self.statusBar().showMessage(
                    f"Reimportando {mod_name}...", 0)
                logger.info("Auto-reimporting: %s from %s", mod_name, src)

                # Detect if it's a JSON patch
                json_data = detect_json_patch(src)
                if json_data:
                    result = import_from_json_patch(
                        src, self._game_dir, self._db,
                        self._snapshot, self._deltas_dir,
                        existing_mod_id=mod_id)
                else:
                    result = _process_extracted_files(
                        src, self._game_dir, self._db,
                        self._snapshot, self._deltas_dir,
                        mod_name, existing_mod_id=mod_id)

                if result.error:
                    logger.warning("Auto-reimport failed for %s: %s",
                                   mod_name, result.error)
                    failed += 1
                else:
                    reimported += 1
                    logger.info("Auto-reimported: %s (%d files)",
                                mod_name, len(result.changed_files))
            except Exception as e:
                logger.warning("Auto-reimport error for %s: %s", mod_name, e)
                failed += 1

        self._refresh_all()
        msg = f"{reimported} mod(s) auto-reimportados após atualização do jogo."
        if failed:
            msg += f" {failed} mod(s) exigem reimportação manual."
        self.statusBar().showMessage(msg, 15000)
        self._log_activity("import", msg)
        logger.info(msg)

    def _refresh_vanilla_backups(self) -> None:
        """Validate and refresh vanilla backups against the snapshot.

        Only runs when no mods are enabled (game files are clean).
        Three operations:
        1. Remove orphan backups not in snapshot (from mod-created directories)
        2. Replace backups whose size doesn't match the game file
        3. Purge stale range backups
        """
        if not self._game_dir or not self._vanilla_dir or not self._vanilla_dir.exists():
            return
        if not self._db:
            return

        # Safety: only refresh when no mods are enabled — game files must be clean
        enabled_count = self._db.connection.execute(
            "SELECT COUNT(*) FROM mods WHERE enabled = 1"
        ).fetchone()[0]
        if enabled_count > 0:
            logger.debug("Skipping vanilla backup refresh — %d mods enabled", enabled_count)
            return

        # Load snapshot file paths for orphan detection
        snap_files = set()
        try:
            cursor = self._db.connection.execute("SELECT file_path FROM snapshots")
            snap_files = {row[0] for row in cursor.fetchall()}
        except Exception:
            return

        import shutil
        refreshed = 0
        orphans_removed = 0

        for backup in list(self._vanilla_dir.rglob("*")):
            if not backup.is_file():
                continue
            if backup.name.endswith(".vranges"):
                continue

            rel = str(backup.relative_to(self._vanilla_dir)).replace("\\", "/")

            # Remove orphan backups not in snapshot (mod-created directories)
            if rel not in snap_files:
                backup.unlink()
                orphans_removed += 1
                logger.info("Removed orphan vanilla backup: %s (not in snapshot)", rel)
                continue

            game_file = self._game_dir / rel.replace("/", "\\")
            if not game_file.exists():
                continue

            # Size difference = stale backup, replace with clean game file
            if backup.stat().st_size != game_file.stat().st_size:
                shutil.copy2(game_file, backup)
                refreshed += 1
                logger.info("Refreshed stale vanilla backup: %s", rel)

        if orphans_removed:
            logger.info("Removed %d orphan vanilla backup(s)", orphans_removed)
            # Clean empty directories left behind
            for d in sorted(self._vanilla_dir.rglob("*"), reverse=True):
                if d.is_dir() and not any(d.iterdir()):
                    d.rmdir()

        if refreshed:
            logger.info("Refreshed %d stale vanilla backup(s)", refreshed)

        if orphans_removed or refreshed:
            # Purge range backups — they reference old byte positions
            for vr in self._vanilla_dir.rglob("*.vranges"):
                vr.unlink()
                logger.info("Purged stale range backup: %s", vr.name)

    # --- Change Game Directory ---
    def _on_change_game_dir(self) -> None:
        current = str(self._game_dir) if self._game_dir else ""
        new_dir = QFileDialog.getExistingDirectory(
            self, "Select Crimson Desert Game Directory", current)
        if not new_dir:
            return
        new_path = Path(new_dir)
        # Basic validation — check for expected game files
        if not (new_path / "meta" / "0.papgt").exists():
            _warning_br(
                self, "Diretório Inválido",
                "Isso não parece ser uma instalação do Crimson Desert.\n"
                "Esperava encontrar meta/0.papgt na pasta selecionada.")
            return
        from cdumm.storage.config import Config
        config = Config(self._db)
        config.set("game_directory", str(new_path))
        self._game_dir = new_path
        self._cdmods_dir = new_path / "CDModsElite"
        self._cdmods_dir.mkdir(parents=True, exist_ok=True)
        self._deltas_dir = self._cdmods_dir / "deltas"
        self._vanilla_dir = self._cdmods_dir / "vanilla"
        self.statusBar().showMessage(f"Diretório alterado para: {new_path}", 10000)
        _info_br(
            self, "Diretório do Jogo Alterado",
            f"Diretório do jogo definido para:\n{new_path}\n\n"
            "Você deve reescanear (Refresh Snapshot) para indexar a nova instalação.")

    # --- Find Problem Mod ---
    def _on_find_problem_mod(self) -> None:
        if not self._db or not self._game_dir or not self._mod_manager:
            return
        enabled = [m for m in self._mod_manager.list_mods() if m["enabled"]]
        if len(enabled) < 2:
            _info_br(self, "Encontrar Mod Problemático",
                                   "Você precisa de pelo menos 2 mods ativos para rodar esta ferramenta.")
            return

        from cdumm.gui.binary_search_dialog import BinarySearchDialog
        dialog = BinarySearchDialog(
            self._mod_manager, self._game_dir, self._vanilla_dir, self._db, self)
        dialog.finished.connect(lambda: self._on_binary_search_done())
        dialog.exec()

    def _on_binary_search_done(self) -> None:
        self._refresh_all()
        self._snapshot_applied_state()

    # --- Check Mods For Issues ---
    def _on_check_mods(self) -> None:
        """Run deep verification on enabled mods in background."""
        if not self._db or not self._game_dir:
            return

        from cdumm.gui.workers import ModCheckWorker
        progress = ProgressDialog("Verificando Problemas em Mods", self)
        worker = ModCheckWorker(self._game_dir, self._db.db_path, vanilla_dir=self._vanilla_dir)
        thread = QThread()
        self._run_worker(worker, thread, progress,
                         on_finished=self._on_check_mods_finished)

    def _on_check_mods_finished(self, issues: list) -> None:
        if not issues:
            _info_br(self, "Checagem de Mods", "Nenhum problema encontrado. O estado dos mods está perfeito.")
            self._log_activity("verify", "Verificação de mods aprovada — nenhum problema encontrado")
        else:
            # Collect unique mod names that have issues
            broken_mods = set()
            issue_lines = []
            for source, detail in issues[:15]:
                issue_lines.append(f"[{source}] {detail}")
                if source not in ("PAPGT", "Conflict", "?"):
                    broken_mods.add(source)
            if len(issues) > 15:
                issue_lines.append(f"... and {len(issues) - 15} more")
            issue_text = "\n".join(issue_lines)

            if broken_mods:
                reply = _warning_br(
                    self, "Checagem de Mods",
                    f"Encontrados {len(issues)} problema(s):\n\n{issue_text}\n\n"
                    f"Desativar {len(broken_mods)} mod(s) problemático(s)?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    disabled = 0
                    for mod in self._mod_manager.list_mods():
                        if mod["name"] in broken_mods and mod["enabled"]:
                            self._mod_manager.set_enabled(mod["id"], False)
                            disabled += 1
                            self._log_activity("warning",
                                               f"Auto-desativado: {mod['name']}",
                                               "Falhou na checagem de compatibilidade de mod")
                    self._refresh_all()
                    self.statusBar().showMessage(
                        f"{disabled} mod(s) problemático(s) desativado(s). Clique em Aplicar para reverter.", 10000)
            else:
                _warning_br(
                    self, "Checagem de Mods",
                    f"Encontrados {len(issues)} problema(s):\n\n{issue_text}",
                )

            self._log_activity("warning",
                               f"Verificação de mods: {len(issues)} problema(s)",
                               "; ".join(f"[{s}] {d}" for s, d in issues[:5]))

    # --- Verify Game State ---
    def _on_verify_game_state(self) -> None:
        if not self._db or not self._game_dir:
            return
        if not self._snapshot or not self._snapshot.has_snapshot():
            _info_br(self, "Nenhum Snapshot",
                                   "Snapshot não rastreado. Verifique os arquivos primários do jogo primeiro.")
            return

        from cdumm.gui.verify_dialog import VerifyWorker, VerifyDialog
        progress = ProgressDialog("Verificando Estado do Jogo", self)
        worker = VerifyWorker(self._game_dir, self._db.db_path)
        thread = QThread()
        self._run_worker(worker, thread, progress,
                         on_finished=self._on_verify_finished)

    def _on_verify_finished(self, results: dict) -> None:
        from cdumm.gui.verify_dialog import VerifyDialog
        modded = len(results.get("modded", []))
        vanilla = len(results.get("vanilla", []))
        extra = len(results.get("extra_dirs", []))
        if modded == 0 and extra == 0:
            self._log_activity("verify", f"Estado do jogo verificado: TOTALMENTE LIMPO ({vanilla} arquivos originais)")
        else:
            self._log_activity("verify",
                               f"Estado do jogo verificado: {modded} com mod, {extra} pastas extras, {vanilla} originais")
        dialog = VerifyDialog(results, self)
        dialog.exec()

    # --- Patch Notes ---
    def _on_show_patch_notes(self) -> None:
        dialog = PatchNotesDialog(self, latest_only=False)
        dialog.exec()

    def _check_show_update_notes(self) -> None:
        """Show patch notes if the app was just updated.
        Also triggers auto-reimport of mods so they use the new format.
        """
        if not self._db:
            return
        config = Config(self._db)
        last_seen = config.get("last_seen_version") or ""
        from cdumm import __version__
        if last_seen != __version__ and CHANGELOG:
            config.set("last_seen_version", __version__)
            # Patch notes popup suppressed from auto-startup
            # (method _show_update_notes is intact; re-enable by uncommenting)
            # QTimer.singleShot(500, self._show_update_notes)

            # Migração automática APENAS quando o formato de delta muda de versão.
            # Este número só é incrementado em mudanças de formato incompatíveis,
            # não a cada atualização de código. Evita reimportações desnecessárias.
            CURRENT_FORMAT_VERSION = "2"  # incrementar apenas ao mudar o formato de delta
            stored_format = config.get("migration_format_version") or "0"
            if (stored_format != CURRENT_FORMAT_VERSION
                    and self._mod_manager and self._mod_manager.get_mod_count() > 0):
                config.set("migration_format_version", CURRENT_FORMAT_VERSION)
                QTimer.singleShot(1500, self._auto_migrate_after_update)

    def _show_update_notes(self) -> None:
        dialog = PatchNotesDialog(self, latest_only=True)
        dialog.exec()

    # --- Bug Report ---
    def _on_report_bug(self) -> None:
        from cdumm.gui.bug_report import generate_bug_report, BugReportDialog
        report = generate_bug_report(self._db, self._game_dir, self._app_data_dir)
        dialog = BugReportDialog(report, self)
        dialog.exec()

    def _offer_crash_report(self) -> None:
        reply = _pergunta_br(
            self, "A Sessão Anterior Travou",
            "Parece que o aplicativo não foi fechado corretamente na última vez.\n"
            "Isso pode indicar um bug.\n\n"
            "Você gostaria de gerar um relatório de bug?\n"
            "(Você pode anexá-lo à sua denúncia no Nexus Mods)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            from cdumm.gui.bug_report import generate_bug_report, BugReportDialog
            report = generate_bug_report(self._db, self._game_dir, self._app_data_dir)
            dialog = BugReportDialog(report, self, is_crash=True)
            dialog.exec()

    # --- Profiles ---
    def _on_profiles(self) -> None:
        from cdumm.gui.profile_dialog import ProfileDialog
        dialog = ProfileDialog(self._db, self)
        dialog.exec()
        if dialog.was_profile_loaded:
            self._refresh_all()
            self._on_apply()

    # --- Export/Import Mod List ---
    def _on_export_list(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Mod List", "cdumm_modlist.json", "JSON Files (*.json)")
        if not path:
            return
        from cdumm.engine.mod_list_io import export_mod_list
        count = export_mod_list(self._db, Path(path))
        self.statusBar().showMessage(f"Exportados {count} mods para {Path(path).name}", 10000)

    def _on_import_list(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Mod List", "", "JSON Files (*.json)")
        if not path:
            return
        from cdumm.engine.mod_list_io import import_mod_list
        mods = import_mod_list(Path(path))
        if not mods:
            _info_br(self, "Importar Lista", "Nenhum mod foi encontrado neste arquivo de importação.")
            return
        # Show what mods the list contains vs what we have installed
        installed = {m["name"].lower() for m in (self._mod_manager.list_mods() if self._mod_manager else [])}
        lines = []
        missing = 0
        for m in mods:
            status = "installed" if m["name"].lower() in installed else "MISSING"
            if status == "MISSING":
                missing += 1
            lines.append(f"[{status}] {m['name']}" + (f" by {m['author']}" if m.get('author') else ""))
        _info_br(
            self, "Lista de Mods",
            f"{len(mods)} mods na lista, {missing} não instalados:\n\n" + "\n".join(lines))

    # --- Update Check ---
    # Versions at or below this have known game-breaking bugs and must update.
    _MINIMUM_SAFE_VERSION = "1.7.0"

    def _check_for_updates(self) -> None:
        from cdumm import __version__
        from cdumm.engine.update_checker import UpdateCheckWorker
        logger.info("Checking for updates (current: v%s)", __version__)
        worker = UpdateCheckWorker(__version__)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        self._update_found = False
        worker.update_available.connect(self._on_update_available)
        worker.finished.connect(self._on_update_check_done)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(lambda: setattr(self, '_update_thread', None))
        self._update_thread = thread
        self._update_worker = worker
        thread.start()

    def _on_update_check_done(self) -> None:
        if not self._update_found:
            if hasattr(self, '_about_update_label'):
                self._about_update_label.setText("\u2714  Elite BR está atualizado")
                self._about_update_label.setStyleSheet(
                    "font-size: 15px; font-weight: bold; color: #4CAF50; "
                    "padding: 12px; border: 1px solid #4CAF50; border-radius: 8px; "
                    "background: #1A2E1A;")
            self._set_about_nav_indicator("green")
            if hasattr(self, '_update_banner'):
                self._update_banner.setVisible(False)

    def _on_update_available(self, info: dict) -> None:
        self._update_found = True
        self._pending_update_info = info
        tag = info.get("tag", "new version")

        # Update About tab
        if hasattr(self, '_about_update_label'):
            self._about_update_label.setText(
                f"\u26A0  Update available: {tag}\n"
                "Click the red banner at the bottom to update.")
            self._about_update_label.setStyleSheet(
                "font-size: 15px; font-weight: bold; color: #F44336; "
                "padding: 12px; border: 1px solid #F44336; border-radius: 8px; "
                "background: #2E1A1A;")
        self._set_about_nav_indicator("red")

        # Show persistent banner — always visible until they update
        if hasattr(self, '_update_banner'):
            self._update_banner.setText(
                f"\u26A0  Update available: {tag} — click here to update now")
            self._update_banner.setVisible(True)

        # Check if this version is critically outdated
        from cdumm import __version__
        from cdumm.engine.update_checker import _version_newer
        is_critical = _version_newer(self._MINIMUM_SAFE_VERSION, __version__)

        if is_critical:
            # Force update — this version has known game-breaking bugs
            download_url = info.get("download_url", "")
            if download_url:
                _critical_br(
                    self, "Atualização Crítica Necessária",
                    f"Você está executando a v{__version__} que possui problemas conhecidos "
                    f"que podem quebrar seu jogo.\n\n"
                    f"A versão {tag} corrige esses problemas.\n\n"
                    "A atualização será baixada e instalada agora.")
                self._download_and_apply_update(download_url)
            else:
                import webbrowser
                _critical_br(
                    self, "Atualização Crítica Necessária",
                    f"Você está executando a v{__version__} que possui problemas conhecidos "
                    f"que podem quebrar seu jogo.\n\n"
                    f"Por favor baixe a versão {tag} do GitHub.")
                if info.get("url"):
                    webbrowser.open(info["url"])
        else:
            # Normal update — ask once, then rely on banner for reminders
            if getattr(self, '_update_dialog_shown', False):
                return  # already asked this session, don't nag
            self._update_dialog_shown = True
            download_url = info.get("download_url", "")
            if download_url:
                reply = _pergunta_br(
                    self, "Atualização Disponível",
                    f"Uma nova versão está disponível: {tag}\n\n"
                    f"{info.get('body', '')[:300]}\n\n"
                    "Baixar e instalar agora?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self._download_and_apply_update(download_url)

    def _on_banner_clicked(self) -> None:
        """User clicked the persistent update banner."""
        info = getattr(self, '_pending_update_info', None)
        if not info:
            return
        download_url = info.get("download_url", "")
        if download_url:
            self._download_and_apply_update(download_url)
        elif info.get("url"):
            import webbrowser
            webbrowser.open(info["url"])

    def _set_about_nav_indicator(self, color: str) -> None:
        """Update check disabled — About nav indicator suppressed."""
        return  # update UI removed

    def _download_and_apply_update(self, download_url: str) -> None:
        from cdumm.engine.update_checker import UpdateDownloadWorker
        progress = ProgressDialog("Baixando Atualização", self)
        worker = UpdateDownloadWorker(download_url)
        thread = QThread()
        self._run_worker(worker, thread, progress,
                         on_finished=self._on_update_downloaded)

    def _on_update_downloaded(self, new_exe_path) -> None:
        if not new_exe_path:
            # Download failed — fall back to opening browser
            import webbrowser
            _warning_br(
                self, "Falha no Download",
                "Automatic download failed. Opening the download page instead.")
            info = getattr(self, '_pending_update_info', {})
            if info.get("url"):
                webbrowser.open(info["url"])
            return
        from pathlib import Path
        from cdumm.engine.update_checker import apply_update
        # Apply immediately — no second confirmation needed
        apply_update(Path(str(new_exe_path)))

    # --- View Mod Contents ---
    def _show_mod_contents(self, mod_id: int) -> None:
        mod = None
        for m in self._mod_list_model._mods:
            if m["id"] == mod_id:
                mod = m
                break
        if mod:
            from cdumm.gui.mod_contents_dialog import ModContentsDialog
            dialog = ModContentsDialog(mod, self._mod_manager, self)
            dialog.exec()

    def closeEvent(self, event) -> None:
        """Encerramento limpo, remove lock e mata o processo."""
        # Remover lock file
        if hasattr(self, "_lock_file") and self._lock_file.exists():
            try:
                self._lock_file.unlink()
            except Exception:
                pass

        event.accept()
        import os
        os._exit(0)

