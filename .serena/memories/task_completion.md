# Task Completion

- For dashboard/history/database edits, run at least: `python test_import.py`, `python -m compileall <touched files>`, and a focused functional script when behavior touches SQLite.
- For chart changes, verify `panel_subindicadores.HAS_MPL` and `panel_executivo.HAS_MPL/HAS_QTA` are true in the active Python environment.
- Run focused Ruff on touched files when available. Full-project Ruff currently reports historical issues across unrelated modules, so do not treat a full-project failure as proof of regressions in a narrow patch.
- If dependencies change, update root `requirements.txt` and validate imports with the same `python` used by `iniciar_dashboard.bat`.