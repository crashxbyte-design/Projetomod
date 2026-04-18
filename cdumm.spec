# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Crimson Desert Elite BR v4.0
# Shell: EliteBR (main_window.py) + Backend: Faisal

import importlib.util
import os

from PyInstaller.utils.hooks import collect_data_files

_xxhash_spec = importlib.util.find_spec('xxhash._xxhash')
_xxhash_binaries = [(_xxhash_spec.origin, 'xxhash')] if _xxhash_spec else []

# cdumm_native Rust extension (.pyd) — installed in site-packages/cdumm_native/
_native_spec = importlib.util.find_spec('cdumm_native')
_native_binaries = []
if _native_spec and _native_spec.submodule_search_locations:
    _native_dir = list(_native_spec.submodule_search_locations)[0]
    for f in os.listdir(_native_dir):
        if f.endswith('.pyd') or f.endswith('.so'):
            _native_binaries.append((os.path.join(_native_dir, f), 'cdumm_native'))
elif _native_spec and _native_spec.origin:
    _native_binaries.append((_native_spec.origin, '.'))

# NOTE: qfluentwidgets / qframelesswindow removed — EliteBR shell does not use Fluent UI


a = Analysis(
    ['src/cdumm/main.py'],
    pathex=['src'],
    binaries=_xxhash_binaries + _native_binaries,
    datas=[
           # App icon and ASI loader
           ('cdumm.ico', '.'),
           ('asi_loader/winmm.dll', 'asi_loader'),
           # Translations
           ('src/cdumm/translations', 'cdumm/translations'),
           # Schema for PAZ semantic parser
           ('schemas/pabgb_complete_schema.json', 'schemas'),
           # Fonts
           ('assets/fonts/Oxanium-VariableFont_wght.ttf', 'assets/fonts'),
           # Assets (logos, store icons)
           ('assets/cdumm-logo.png', 'assets'),
           ('assets/cdumm-logo-light.png', 'assets'),
           ('assets/cdumm-logo-dark.png', 'assets'),
           ('assets/store-steam.svg', 'assets'),
           ('assets/store-xbox.svg', 'assets'),
           ('assets/store-epic.svg', 'assets'),
           ('assets/store-steam-white.svg', 'assets'),
           ('assets/store-xbox-white.svg', 'assets'),
           ('assets/store-epic-white.svg', 'assets'),
           # GUI inline images — splash (importlib.resources) + dashboard
           ('src/cdumm/gui/logo.png', 'cdumm/gui'),
           ('src/cdumm/gui/crimson_hero_bg.png', 'cdumm/gui'),
           ],
    hiddenimports=[
        # ── Core entry points ──
        'cdumm.cli',
        'cdumm.worker_process',
        # ── GUI — EliteBR shell ──
        'cdumm.gui.main_window',
        'cdumm.gui.setup_dialog',
        'cdumm.gui.import_widget',
        'cdumm.gui.conflict_view',
        'cdumm.gui.mod_list_model',
        'cdumm.gui.asi_panel',
        'cdumm.gui.activity_panel',
        'cdumm.gui.dashboard_panel',
        'cdumm.gui.test_mod_dialog',
        'cdumm.gui.workers',
        'cdumm.gui.bug_report',
        'cdumm.gui.health_check_dialog',
        'cdumm.gui.binary_search_dialog',
        'cdumm.gui.verify_dialog',
        'cdumm.gui.progress_dialog',
        'cdumm.gui.msg_box_br',
        'cdumm.gui.premium_buttons',
        'cdumm.gui.logo_widget',
        'cdumm.gui.fast_mod_card_delegate',
        'cdumm.gui.mod_card_delegate',
        'cdumm.gui.patch_toggle_dialog',
        'cdumm.gui.splash',
        'cdumm.gui.mod_contents_dialog',
        'cdumm.gui.profile_dialog',
        'cdumm.gui.update_overlay',
        'cdumm.gui.changelog',
        'cdumm.gui.preset_picker',
        'cdumm.gui.theme',
        'cdumm.gui.i18n',
        # ── Engine & Backend (Faisal) ──
        'cdumm_native',
        'cdumm.engine.snapshot_manager',
        'cdumm.engine.delta_engine',
        'cdumm.engine.import_handler',
        'cdumm.engine.conflict_detector',
        'cdumm.engine.apply_engine',
        'cdumm.engine.mod_manager',
        'cdumm.engine.test_mod_checker',
        'cdumm.engine.offset_collision',
        'cdumm.engine.crimson_browser_handler',
        'cdumm.engine.json_patch_handler',
        'cdumm.engine.texture_mod_handler',
        'cdumm.engine.mod_health_check',
        'cdumm.engine.update_checker',
        'cdumm.engine.version_detector',
        'cdumm.engine.profile_manager',
        'cdumm.engine.mod_list_io',
        'cdumm.engine.activity_log',
        'cdumm.engine.binary_search',
        'cdumm.engine.game_monitor',
        # ── Archive ──
        'cdumm.archive.transactional_io',
        'cdumm.archive.hashlittle',
        'cdumm.archive.papgt_manager',
        'cdumm.archive.format_parsers.base',
        'cdumm.archive.format_parsers.pabgb_parser',
        'cdumm.archive.format_parsers.paac_parser',
        'cdumm.archive.format_parsers.pamt_parser',
        'cdumm.archive.paz_parse',
        'cdumm.archive.paz_crypto',
        'cdumm.archive.paz_repack',
        'cdumm.archive.pathc_handler',
        # ── Semantic ──
        'cdumm.semantic',
        'cdumm.semantic.changeset',
        'cdumm.semantic.parser',
        'cdumm.semantic.differ',
        'cdumm.semantic.merger',
        'cdumm.semantic.engine',
        # ── Storage ──
        'cdumm.storage.database',
        'cdumm.storage.config',
        'cdumm.storage.game_finder',
        # ── ASI ──
        'cdumm.asi.asi_manager',
        # ── Third-party ──
        'xxhash', 'xxhash._xxhash',
        'py7zr',
        'darkdetect',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # PySide6 modules not used by CDUMM (only QtCore/QtGui/QtWidgets/QtSvg needed)
        'PySide6.QtWebEngine', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebEngineCore',
        'PySide6.Qt3DCore', 'PySide6.Qt3DRender', 'PySide6.Qt3DInput', 'PySide6.Qt3DExtras',
        'PySide6.QtCharts', 'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets',
        'PySide6.QtQuick', 'PySide6.QtQml', 'PySide6.QtBluetooth',
        'PySide6.QtPositioning', 'PySide6.QtSensors', 'PySide6.QtSerialPort',
        'PySide6.QtRemoteObjects', 'PySide6.QtNfc',
        'PySide6.QtOpenGL', 'PySide6.QtOpenGLWidgets',
        'PySide6.QtNetwork',
        'PySide6.QtDataVisualization', 'PySide6.QtGraphs',
        'PySide6.QtAxContainer', 'PySide6.QtDesigner',
        'PySide6.QtHelp', 'PySide6.QtPdf', 'PySide6.QtPdfWidgets',
        'PySide6.QtQuick3D', 'PySide6.QtShaderTools',
        'PySide6.QtSpatialAudio', 'PySide6.QtHttpServer',
        'PySide6.QtTest', 'PySide6.QtDBus', 'PySide6.QtConcurrent',
        # scipy/numpy — only needed for acrylic blur (disabled)
        'scipy', 'numpy', 'numpy.core', 'numpy.linalg',
        # PIL/Pillow — not imported by CDUMM (colorthief dep, unused)
        'PIL', 'PIL._imaging', 'PIL._avif', 'PIL._webp', 'PIL.Image',
        'Pillow', 'colorthief',
        # brotli — not used by CDUMM (transitive dep from py7zr)
        'brotli', '_brotli', 'brotlicffi',
        # cryptography — only used as ChaCha20 fallback in paz_crypto.py.
        # cdumm_native Rust module handles all crypto at runtime.
        'cryptography', 'cryptography.hazmat', 'cryptography.hazmat.primitives',
        'cryptography.hazmat.primitives.ciphers', 'cryptography.hazmat.bindings',
        'cryptography.x509', 'cryptography.fernet',
        # setuptools/pkg_resources not needed at runtime
        'setuptools', 'pkg_resources',
    ],
    noarchive=False,
)

# Strip large unused DLLs from binaries
_dll_excludes = {
    'opengl32sw.dll',        # ~20 MB software OpenGL (not needed)
    'Qt6Network.dll',        # ~3 MB
    'Qt6Pdf.dll',            # ~4 MB
    'Qt6Designer.dll',       # ~5 MB
    'Qt6Quick.dll',          # ~6 MB
    'Qt6Qml.dll',            # ~5 MB
    'Qt6ShaderTools.dll',    # ~4 MB
    'Qt6Quick3DRuntimeRender.dll',
    'Qt6OpenGL.dll',         # ~1.9 MB (not used — no OpenGL rendering)
    'Qt6QmlModels.dll',      # ~0.95 MB
    'Qt6QmlMeta.dll',        # ~0.15 MB
    'Qt6QmlWorkerScript.dll',  # ~0.08 MB
    'Qt6VirtualKeyboard.dll',  # ~0.4 MB (desktop app, no touch keyboard)
    'qdirect2d.dll',         # ~1 MB (qwindows.dll is sufficient)
    'avcodec-61.dll',        # ~13 MB multimedia codec
    'avformat-61.dll',
    'avutil-59.dll',
    'swresample-5.dll',
    'swscale-8.dll',
    # cryptography native DLLs (cdumm_native handles ChaCha20)
    'libcrypto-3.dll',       # ~5 MB
    'libssl-3.dll',          # ~0.76 MB
    # Image format plugins CDUMM doesn't use (keep qico, qsvg, qgif)
    'qtiff.dll',             # ~0.43 MB
    'qwebp.dll',             # ~0.55 MB
    'qjpeg.dll',             # ~0.56 MB
    'qpdf.dll',              # ~0.04 MB
    'qicns.dll',             # ~0.05 MB (Apple icon format)
    'qtga.dll',              # ~0.04 MB
    'qwbmp.dll',             # ~0.04 MB
}
# Also filter out PIL/brotli/cryptography binary extensions
_binary_name_excludes = {
    '_avif', '_imaging', '_webp', '_imagingcms', '_brotli',
    '_rust',       # cryptography Rust binding (8.7 MB)
    '_ec_ws',      # Cryptodome elliptic curve (not used by CDUMM)
    '_ed448',      # Cryptodome Ed448
    '_curve448',   # Cryptodome Curve448
}

def _should_exclude_bin(name):
    basename = name.split('/')[-1].split('\\')[-1]
    if basename in _dll_excludes:
        return True
    stem = basename.rsplit('.', 1)[0]
    for excl in _binary_name_excludes:
        if stem.startswith(excl):
            return True
    return False

a.binaries = [b for b in a.binaries if not _should_exclude_bin(b[0])]

# Strip Qt translations for languages CDUMM doesn't support (save ~4.4 MB)
_keep_langs = {'en', 'de', 'es', 'fr', 'ko', 'pt', 'zh', 'ar', 'it', 'pl', 'ru', 'tr', 'ja', 'uk', 'id'}
def _should_keep_data(name):
    if name.endswith('.qm') and 'translations' in name:
        import os
        basename = os.path.basename(name).replace('.qm', '')
        parts = basename.split('_')
        lang = parts[-1] if len(parts) > 1 else ''
        return lang in _keep_langs
    return True

a.datas = [d for d in a.datas if _should_keep_data(d[0])]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CrimsonDesertEliteBR',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,   # strip=False on Windows (GNU strip not available; avoids build warnings)
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon='cdumm.ico',
    version='version_info.txt',   # Windows Details tab: FileDescription, ProductName, etc.
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
