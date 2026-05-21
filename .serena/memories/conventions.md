# Conventions

- UI modules are imperative PySide6 widget builders; keep changes localized to the owning panel module.
- Database access is centralized in `database.py`; add CRUD helpers there instead of issuing SQL from panels.
- Monthly history uses Portuguese month names from each module's `MESES` constant and persists to `dados_historicos` keyed by `(subindicador_id, ano, mes)`.
- Dashboard/reporting paths must use `database.is_valid_year`/`parse_valid_year` semantics; maintenance UI may still surface invalid legacy years so users can delete them.
- Hourly launches persist to `lancamentos_horario`; consolidated monthly results are written back to `dados_historicos` only when explicitly consolidated.
- Existing style uses Portuguese user-facing messages, Segoe UI, and color constants from `styles.py`.
- Avoid broad formatting churn: several modules have historical semicolon/unused-import style debt.