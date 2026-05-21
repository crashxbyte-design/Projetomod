# Tech Stack

- Python desktop app using PySide6 widgets and SQLite from stdlib.
- Runtime dependencies are pinned in root `requirements.txt`: PySide6, Matplotlib, NumPy.
- Charts use Matplotlib QtAgg integration: `FigureCanvasQTAgg` in executive/subindicator panels, with `Agg` selected before pyplot imports.
- PyInstaller config lives at `sp_dashboard/SP_Dashboard.spec`; hidden imports include Matplotlib backends, NumPy, and PySide6 SVG/XML modules.
- No pyproject or formal test framework is present; validation is script-based.