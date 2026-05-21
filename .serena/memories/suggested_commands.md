# Suggested Commands

- Run app: `python sp_dashboard/app.py` or `iniciar_dashboard.bat` from project root.
- Install runtime dependencies: `python -m pip install -r requirements.txt`.
- Import smoke test: `python test_import.py`.
- Data validation snapshot: `python validate_data.py`.
- Migration/data inspection snapshot: `python validate_migration.py`.
- Compile touched Python files: `python -m compileall sp_dashboard\\database.py sp_dashboard\\panel_historico.py`.
- Focused lint for touched history/db files: `python -m ruff check sp_dashboard\\database.py sp_dashboard\\panel_historico.py`.
- Windows search preference: `rg <pattern> sp_dashboard --glob '!build/**' --glob '!__pycache__/**'`.