"""
database.py - Backend SQLite do sistema de Indicadores de Segurança Patrimonial.

Modelo de dados:
  indicadores      → indicadores principais (agrupadores)
  subindicadores   → filhos do indicador; recebem o histórico mensal
  dados_historicos → valores mensais por subindicador_id
  analise_critica  → análise por indicador (causa, ação, responsável, prazo)
  config           → pares chave/valor globais

Regras:
  - Banco inicia vazio; todo conteúdo é cadastrado manualmente no app.
  - Excel não é lido em nenhum momento pelo runtime.
  - Sem seed automático. Sem migração. Sem importação.
"""

import sqlite3
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.normpath(os.path.join(BASE_DIR, "..", "sp_indicadores.db"))

MESES = [
    "Janeiro","Fevereiro","Março","Abril","Maio","Junho",
    "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"
]

# ── Schema ─────────────────────────────────────────────────────────────────

_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS indicadores (
        codigo_indicador  TEXT PRIMARY KEY,
        nome_indicador    TEXT NOT NULL,
        tipo              TEXT DEFAULT 'Operacional',
        periodicidade     TEXT DEFAULT 'Mensal',
        unidade           TEXT,
        meta_texto        TEXT,
        meta_numero       REAL,
        menor_melhor      INTEGER DEFAULT 1,
        observacoes       TEXT,
        indicador_ativo   INTEGER DEFAULT 1,
        atualizado_em     TEXT
    )""",

    """CREATE TABLE IF NOT EXISTS subindicadores (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_indicador  TEXT NOT NULL,
        nome_subindicador TEXT NOT NULL,
        ordem             INTEGER DEFAULT 0,
        ativo             INTEGER DEFAULT 1,
        observacoes       TEXT,
        atualizado_em     TEXT,
        FOREIGN KEY (codigo_indicador) REFERENCES indicadores(codigo_indicador)
    )""",

    """CREATE TABLE IF NOT EXISTS dados_historicos (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        subindicador_id  INTEGER NOT NULL,
        ano              INTEGER NOT NULL,
        mes              TEXT NOT NULL,
        valor            REAL,
        observacoes      TEXT,
        UNIQUE(subindicador_id, ano, mes),
        FOREIGN KEY (subindicador_id) REFERENCES subindicadores(id)
    )""",

    """CREATE TABLE IF NOT EXISTS analise_critica (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_indicador TEXT NOT NULL,
        periodo          TEXT,
        analise          TEXT,
        causa            TEXT,
        acao             TEXT,
        responsavel      TEXT,
        prazo            TEXT,
        nivel            TEXT DEFAULT 'ATENÇÃO',
        atualizado_em    TEXT
    )""",

    """CREATE TABLE IF NOT EXISTS config (
        chave TEXT PRIMARY KEY,
        valor TEXT
    )""",
]

# ── Conexão ────────────────────────────────────────────────────────────────

def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = _connect()
    try:
        for stmt in _SCHEMA:
            conn.execute(stmt)
        conn.commit()
        _seed_config_defaults(conn)
    finally:
        conn.close()


def _seed_config_defaults(conn: sqlite3.Connection):
    defaults = [
        ("nome_book",        "Indicadores de Segurança Patrimonial"),
        ("nome_instituicao", ""),
        ("responsavel",      ""),
        ("periodo_atual",    ""),
        ("data_atualizacao", ""),
    ]
    for chave, valor in defaults:
        conn.execute(
            "INSERT OR IGNORE INTO config (chave, valor) VALUES (?,?)",
            (chave, valor)
        )
    conn.commit()


# ── CRUD: indicadores ──────────────────────────────────────────────────────

def get_all_indicadores() -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM indicadores ORDER BY codigo_indicador"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_indicadores_ativos() -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM indicadores WHERE indicador_ativo=1 ORDER BY codigo_indicador"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_indicador(codigo: str) -> dict | None:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM indicadores WHERE codigo_indicador=?", (codigo,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def upsert_indicador(rec: dict) -> bool:
    conn = _connect()
    try:
        rec = dict(rec)
        rec["atualizado_em"] = datetime.now().isoformat(sep=" ", timespec="seconds")
        conn.execute("""
            INSERT INTO indicadores
                (codigo_indicador, nome_indicador, tipo, periodicidade, unidade,
                 meta_texto, meta_numero, menor_melhor, observacoes, indicador_ativo, atualizado_em)
            VALUES
                (:codigo_indicador,:nome_indicador,:tipo,:periodicidade,:unidade,
                 :meta_texto,:meta_numero,:menor_melhor,:observacoes,:indicador_ativo,:atualizado_em)
            ON CONFLICT(codigo_indicador) DO UPDATE SET
                nome_indicador  = excluded.nome_indicador,
                tipo            = excluded.tipo,
                periodicidade   = excluded.periodicidade,
                unidade         = excluded.unidade,
                meta_texto      = excluded.meta_texto,
                meta_numero     = excluded.meta_numero,
                menor_melhor    = excluded.menor_melhor,
                observacoes     = excluded.observacoes,
                indicador_ativo = excluded.indicador_ativo,
                atualizado_em   = excluded.atualizado_em
        """, rec)
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] upsert_indicador: {e}")
        return False
    finally:
        conn.close()


def delete_indicador(codigo: str) -> bool:
    conn = _connect()
    try:
        sub_ids = [r[0] for r in conn.execute(
            "SELECT id FROM subindicadores WHERE codigo_indicador=?", (codigo,)
        ).fetchall()]
        if sub_ids:
            ph = ",".join("?" * len(sub_ids))
            conn.execute(f"DELETE FROM dados_historicos WHERE subindicador_id IN ({ph})", sub_ids)
        conn.execute("DELETE FROM subindicadores WHERE codigo_indicador=?", (codigo,))
        conn.execute("DELETE FROM analise_critica WHERE codigo_indicador=?", (codigo,))
        conn.execute("DELETE FROM indicadores WHERE codigo_indicador=?", (codigo,))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] delete_indicador: {e}")
        return False
    finally:
        conn.close()


def get_stats_indicadores() -> dict:
    inds  = get_all_indicadores()
    total = len(inds)
    conn  = _connect()
    try:
        n_subs = conn.execute("SELECT COUNT(*) FROM subindicadores WHERE ativo=1").fetchone()[0]
        n_hist = conn.execute("SELECT COUNT(*) FROM dados_historicos").fetchone()[0]
    finally:
        conn.close()
    com_meta = sum(1 for i in inds if i.get("meta_numero") is not None)
    return {
        "total":            total,
        "ativos":           sum(1 for i in inds if i["indicador_ativo"]),
        "inativos":         sum(1 for i in inds if not i["indicador_ativo"]),
        "com_meta":         com_meta,
        "sem_meta":         total - com_meta,
        "n_subindicadores": n_subs,
        "n_historico":      n_hist,
    }


# ── CRUD: subindicadores ───────────────────────────────────────────────────

def get_subindicadores(codigo: str) -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM subindicadores WHERE codigo_indicador=? ORDER BY ordem, id",
            (codigo,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_subindicador(sub_id: int) -> dict | None:
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM subindicadores WHERE id=?", (sub_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_all_subindicadores() -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute("""
            SELECT s.*, i.nome_indicador
            FROM subindicadores s
            JOIN indicadores i ON i.codigo_indicador = s.codigo_indicador
            ORDER BY s.codigo_indicador, s.ordem, s.id
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def upsert_subindicador(rec: dict) -> int | None:
    conn = _connect()
    try:
        rec = dict(rec)
        rec["atualizado_em"] = datetime.now().isoformat(sep=" ", timespec="seconds")
        rec.setdefault("ordem", 0)
        rec.setdefault("ativo", 1)
        if rec.get("id"):
            conn.execute("""
                UPDATE subindicadores SET
                    nome_subindicador=:nome_subindicador, ordem=:ordem,
                    ativo=:ativo, observacoes=:observacoes, atualizado_em=:atualizado_em
                WHERE id=:id
            """, rec)
            conn.commit()
            return int(rec["id"])
        else:
            cur = conn.execute("""
                INSERT INTO subindicadores
                    (codigo_indicador, nome_subindicador, ordem, ativo, observacoes, atualizado_em)
                VALUES (:codigo_indicador,:nome_subindicador,:ordem,:ativo,:observacoes,:atualizado_em)
            """, rec)
            conn.commit()
            return cur.lastrowid
    except Exception as e:
        print(f"[DB] upsert_subindicador: {e}")
        return None
    finally:
        conn.close()


def delete_subindicador(sub_id: int) -> bool:
    conn = _connect()
    try:
        conn.execute("DELETE FROM dados_historicos WHERE subindicador_id=?", (sub_id,))
        conn.execute("DELETE FROM subindicadores WHERE id=?", (sub_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] delete_subindicador: {e}")
        return False
    finally:
        conn.close()


# ── CRUD: dados_historicos ─────────────────────────────────────────────────

def upsert_historico(subindicador_id: int, ano: int, mes: str, valor, obs: str = "") -> bool:
    conn = _connect()
    try:
        conn.execute("""
            INSERT INTO dados_historicos (subindicador_id, ano, mes, valor, observacoes)
            VALUES (?,?,?,?,?)
            ON CONFLICT(subindicador_id, ano, mes) DO UPDATE SET
                valor=excluded.valor, observacoes=excluded.observacoes
        """, (subindicador_id, ano, mes, valor, obs))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] upsert_historico: {e}")
        return False
    finally:
        conn.close()


def delete_historico_mes(subindicador_id: int, ano: int, mes: str) -> bool:
    conn = _connect()
    try:
        conn.execute(
            "DELETE FROM dados_historicos WHERE subindicador_id=? AND ano=? AND mes=?",
            (subindicador_id, ano, mes)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] delete_historico_mes: {e}")
        return False
    finally:
        conn.close()


def get_historico_subindicador(sub_id: int, anos: list[int] | None = None) -> dict:
    """Retorna {ano: {mes: valor}}."""
    conn = _connect()
    try:
        if anos:
            ph   = ",".join("?" * len(anos))
            rows = conn.execute(
                f"SELECT ano, mes, valor FROM dados_historicos WHERE subindicador_id=? AND ano IN ({ph}) ORDER BY ano",
                [sub_id] + anos
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT ano, mes, valor FROM dados_historicos WHERE subindicador_id=? ORDER BY ano",
                (sub_id,)
            ).fetchall()
        result: dict = {}
        for r in rows:
            result.setdefault(r["ano"], {})[r["mes"]] = r["valor"]
        return result
    finally:
        conn.close()


def get_historico_indicador(codigo: str, anos: list[int] | None = None) -> dict:
    """Agrega histórico de todos os subindicadores → {ano: {mes: soma}}."""
    subs   = get_subindicadores(codigo)
    totais: dict = {}
    for sub in subs:
        hist = get_historico_subindicador(sub["id"], anos)
        for ano, meses in hist.items():
            for mes, val in meses.items():
                if val is not None:
                    totais.setdefault(ano, {})
                    totais[ano][mes] = (totais[ano].get(mes) or 0) + val
    return totais


# ── CRUD: analise_critica ──────────────────────────────────────────────────

def get_analise_critica(codigo: str | None = None) -> list[dict]:
    conn = _connect()
    try:
        if codigo:
            rows = conn.execute(
                "SELECT * FROM analise_critica WHERE codigo_indicador=? ORDER BY id DESC",
                (codigo,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM analise_critica ORDER BY codigo_indicador, id DESC"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def upsert_analise_critica(rec: dict) -> bool:
    conn = _connect()
    now  = datetime.now().isoformat(sep=" ", timespec="seconds")
    try:
        rec  = dict(rec)
        cod  = rec["codigo_indicador"]
        existing = conn.execute(
            "SELECT id FROM analise_critica WHERE codigo_indicador=? ORDER BY id DESC LIMIT 1",
            (cod,)
        ).fetchone()
        if existing:
            conn.execute("""
                UPDATE analise_critica SET
                    periodo=?, analise=?, causa=?, acao=?,
                    responsavel=?, prazo=?, nivel=?, atualizado_em=?
                WHERE id=?
            """, (
                rec.get("periodo"), rec.get("analise"), rec.get("causa"),
                rec.get("acao"), rec.get("responsavel"), rec.get("prazo"),
                rec.get("nivel","ATENÇÃO"), now, existing["id"]
            ))
        else:
            conn.execute("""
                INSERT INTO analise_critica
                    (codigo_indicador, periodo, analise, causa, acao, responsavel, prazo, nivel, atualizado_em)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (
                cod, rec.get("periodo"), rec.get("analise"), rec.get("causa"),
                rec.get("acao"), rec.get("responsavel"), rec.get("prazo"),
                rec.get("nivel","ATENÇÃO"), now
            ))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] upsert_analise_critica: {e}")
        return False
    finally:
        conn.close()


def delete_analise_critica(ac_id: int) -> bool:
    conn = _connect()
    try:
        conn.execute("DELETE FROM analise_critica WHERE id=?", (ac_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] delete_analise_critica: {e}")
        return False
    finally:
        conn.close()


# ── CRUD: config ───────────────────────────────────────────────────────────

def get_config(chave: str, default: str = "") -> str:
    conn = _connect()
    try:
        row = conn.execute("SELECT valor FROM config WHERE chave=?", (chave,)).fetchone()
        return row["valor"] if row and row["valor"] is not None else default
    finally:
        conn.close()


def set_config(chave: str, valor: str):
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO config (chave, valor) VALUES (?,?) "
            "ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor",
            (chave, valor)
        )
        conn.commit()
    finally:
        conn.close()


def get_all_config() -> dict:
    conn = _connect()
    try:
        rows = conn.execute("SELECT chave, valor FROM config").fetchall()
        return {r["chave"]: r["valor"] or "" for r in rows}
    finally:
        conn.close()


# ── Inicialização ──────────────────────────────────────────────────────────
init_db()
