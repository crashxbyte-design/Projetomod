# Core

- Desktop dashboard in `sp_dashboard/`, PySide6 UI with panel-per-tab modules.
- Runtime entrypoint: `sp_dashboard/app.py`; root launcher `iniciar_dashboard.bat` runs `python sp_dashboard/app.py` from project root.
- SQLite DB is `sp_indicadores.db` at project root in script mode; `database.get_db_path()` switches to executable directory when frozen by PyInstaller.
- Main data flow: UI panels call `database.py`; dashboard aggregate reads are assembled by `data_loader.py`.
- Base data tab (`panel_base_dados.py`) embeds `HistoricoPanel`, `AnaliseCriticaPanel`, and `ConfigPanel` as sub-tabs.
- Read `mem:tech_stack` for dependencies and packaging. Read `mem:suggested_commands` for local validation commands. Read `mem:task_completion` before handing off coding changes.