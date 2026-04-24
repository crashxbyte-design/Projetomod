"""
database.py - Backend SQLite persistente do sistema.
Arquivo: C:/Users/Admin/Documents/Robson/sp_indicadores.db

Modelo:
  indicadores       — indicadores principais (agrupadores)
  subindicadores    — filhos do indicador, recebem histórico mensal
  dados_historicos  — valores mensais por subindicador_id
  analise_critica   — análise por indicador (causa, ação, responsável, prazo)
  config            — chave/valor globais
  importacoes_log   — log de importações Excel (opcional)
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
    # Indicadores principais (agrupadores)
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

    # Subindicadores (filhos — recebem o histórico mensal)
    """CREATE TABLE IF NOT EXISTS subindicadores (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_indicador  TEXT NOT NULL,
        nome_subindicador TEXT NOT NULL,
        ordem             INTEGER DEFAULT 0,
        unidade           TEXT,
        meta_texto        TEXT,
        meta_numero       REAL,
        menor_melhor      INTEGER DEFAULT 1,
        ativo             INTEGER DEFAULT 1,
        observacoes       TEXT,
        atualizado_em     TEXT,
        FOREIGN KEY (codigo_indicador) REFERENCES indicadores(codigo_indicador)
    )""",

    # Histórico mensal por subindicador
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

    # Análise crítica por indicador
    """CREATE TABLE IF NOT EXISTS analise_critica (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_indicador  TEXT NOT NULL,
        periodo           TEXT,
        analise           TEXT,
        causa             TEXT,
        acao              TEXT,
        responsavel       TEXT,
        prazo             TEXT,
        nivel             TEXT DEFAULT 'ATENÇÃO',
        atualizado_em     TEXT
    )""",

    # Configurações globais
    """CREATE TABLE IF NOT EXISTS config (
        chave TEXT PRIMARY KEY,
        valor TEXT
    )""",

    # Log de importações (opcional)
    """CREATE TABLE IF NOT EXISTS importacoes_log (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        data_hora TEXT,
        arquivo   TEXT,
        registros INTEGER,
        status    TEXT,
        mensagem  TEXT
    )""",
]

# Migrations seguras para banco existente
_MIGRATIONS = [
    # Tabela indicadores (nova — pode não existir)
    # Subindicadores (nova)
    # analise_critica: novas colunas
    "ALTER TABLE analise_critica ADD COLUMN causa TEXT",
    "ALTER TABLE analise_critica ADD COLUMN acao TEXT",
    "ALTER TABLE analise_critica ADD COLUMN responsavel TEXT",
]


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Cria tabelas e aplica migrations seguras."""
    conn = _connect()
    try:
        for stmt in _SCHEMA:
            conn.execute(stmt)
        conn.commit()
        for mig in _MIGRATIONS:
            try:
                conn.execute(mig)
                conn.commit()
            except sqlite3.OperationalError:
                pass  # coluna já existe
    finally:
        conn.close()


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
        rec.setdefault("tipo", "Operacional")
        rec.setdefault("periodicidade", "Mensal")
        rec.setdefault("indicador_ativo", 1)
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
        print(f"[DB] Erro upsert_indicador: {e}")
        return False
    finally:
        conn.close()


def delete_indicador(codigo: str) -> bool:
    """Remove indicador e seus subindicadores + histórico em cascata."""
    conn = _connect()
    try:
        # Deleta histórico dos subindicadores
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
        print(f"[DB] Erro delete_indicador: {e}")
        return False
    finally:
        conn.close()


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
        row = conn.execute(
            "SELECT * FROM subindicadores WHERE id=?", (sub_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_all_subindicadores() -> list[dict]:
    """Retorna todos os subindicadores com nome do indicador pai."""
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
    """Insere ou atualiza subindicador. Retorna o id."""
    conn = _connect()
    try:
        rec = dict(rec)
        rec["atualizado_em"] = datetime.now().isoformat(sep=" ", timespec="seconds")
        rec.setdefault("ordem", 0)
        rec.setdefault("ativo", 1)
        if rec.get("id"):
            conn.execute("""
                UPDATE subindicadores SET
                    nome_subindicador=:nome_subindicador,
                    ordem=:ordem,
                    unidade=:unidade,
                    meta_texto=:meta_texto,
                    meta_numero=:meta_numero,
                    menor_melhor=:menor_melhor,
                    ativo=:ativo,
                    observacoes=:observacoes,
                    atualizado_em=:atualizado_em
                WHERE id=:id
            """, rec)
            conn.commit()
            return rec["id"]
        else:
            cur = conn.execute("""
                INSERT INTO subindicadores
                    (codigo_indicador, nome_subindicador, ordem, unidade,
                     meta_texto, meta_numero, menor_melhor, ativo, observacoes, atualizado_em)
                VALUES
                    (:codigo_indicador,:nome_subindicador,:ordem,:unidade,
                     :meta_texto,:meta_numero,:menor_melhor,:ativo,:observacoes,:atualizado_em)
            """, rec)
            conn.commit()
            return cur.lastrowid
    except Exception as e:
        print(f"[DB] Erro upsert_subindicador: {e}")
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
        print(f"[DB] Erro delete_subindicador: {e}")
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
                valor=excluded.valor,
                observacoes=excluded.observacoes
        """, (subindicador_id, ano, mes, valor, obs))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] Erro upsert_historico: {e}")
        return False
    finally:
        conn.close()


def get_historico_subindicador(sub_id: int, anos: list[int] | None = None) -> dict:
    """Retorna {ano: {mes: valor}} para um subindicador."""
    conn = _connect()
    try:
        if anos:
            ph = ",".join("?" * len(anos))
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
    """
    Agrega histórico de todos os subindicadores de um indicador principal.
    Retorna {ano: {mes: valor_total}} (soma dos subindicadores com dados).
    """
    subs = get_subindicadores(codigo)
    if not subs:
        return {}
    totais: dict = {}
    for sub in subs:
        hist = get_historico_subindicador(sub["id"], anos)
        for ano, meses in hist.items():
            for mes, val in meses.items():
                if val is not None:
                    totais.setdefault(ano, {})
                    totais[ano][mes] = (totais[ano].get(mes) or 0) + val
    return totais


def get_historico_multi_indicadores(codigos: list[str], anos: list[int]) -> dict:
    """Retorna {codigo: {ano: {mes: valor}}} — agregado por indicador."""
    return {cod: get_historico_indicador(cod, anos) for cod in codigos}


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
    """Upsert da análise crítica de um indicador (um registro por indicador)."""
    conn = _connect()
    now = datetime.now().isoformat(sep=" ", timespec="seconds")
    try:
        rec = dict(rec)
        cod = rec["codigo_indicador"]
        existing = conn.execute(
            "SELECT id FROM analise_critica WHERE codigo_indicador=? ORDER BY id DESC LIMIT 1",
            (cod,)
        ).fetchone()
        if existing:
            conn.execute("""
                UPDATE analise_critica SET
                    periodo=:periodo, analise=:analise, causa=:causa,
                    acao=:acao, responsavel=:responsavel, prazo=:prazo,
                    nivel=:nivel, atualizado_em=?
                WHERE id=?
            """, {**rec, "atualizado_em": now, "id": existing["id"]}, )
            # sqlite3 doesn't accept mixing dict and positional, fix:
        else:
            conn.execute("""
                INSERT INTO analise_critica
                    (codigo_indicador, periodo, analise, causa, acao, responsavel, prazo, nivel, atualizado_em)
                VALUES (:codigo_indicador,:periodo,:analise,:causa,:acao,:responsavel,:prazo,:nivel,:atualizado_em)
            """, {**rec, "atualizado_em": now})
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] Erro upsert_analise_critica: {e}")
        return False
    finally:
        conn.close()


# ── CRUD: config ───────────────────────────────────────────────────────────

def get_config(chave: str, default: str = "") -> str:
    conn = _connect()
    try:
        row = conn.execute("SELECT valor FROM config WHERE chave=?", (chave,)).fetchone()
        return row["valor"] if row else default
    finally:
        conn.close()


def set_config(chave: str, valor: str):
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO config (chave, valor) VALUES (?,?) ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor",
            (chave, valor)
        )
        conn.commit()
    finally:
        conn.close()


def get_all_config() -> dict:
    conn = _connect()
    try:
        rows = conn.execute("SELECT chave, valor FROM config").fetchall()
        return {r["chave"]: r["valor"] for r in rows}
    finally:
        conn.close()


# ── Stats para KPIs ────────────────────────────────────────────────────────

def get_stats_indicadores() -> dict:
    inds = get_all_indicadores()
    total    = len(inds)
    ativos   = sum(1 for i in inds if i["indicador_ativo"])
    com_meta = sum(1 for i in inds if i.get("meta_numero") is not None)
    conn = _connect()
    try:
        n_subs = conn.execute("SELECT COUNT(*) FROM subindicadores WHERE ativo=1").fetchone()[0]
        n_hist = conn.execute("SELECT COUNT(*) FROM dados_historicos").fetchone()[0]
    finally:
        conn.close()
    return {
        "total": total, "ativos": ativos, "inativos": total - ativos,
        "com_meta": com_meta, "sem_meta": total - com_meta,
        "n_subindicadores": n_subs, "n_historico": n_hist,
    }


# ── Migração: tabela antiga → nova ────────────────────────────────────────

def migrate_from_legacy():
    """
    Migra dados da tabela `indicadores_mapeamento` (legada) para `indicadores` e `subindicadores`.
    Cria 1 subindicador-padrão por indicador e migra os dados_historicos pelo codigo_indicador.
    Executado apenas uma vez — idempotente.
    """
    conn = _connect()
    now  = datetime.now().isoformat(sep=" ", timespec="seconds")
    try:
        # Verifica se tabela legada existe
        exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='indicadores_mapeamento'"
        ).fetchone()
        if not exists:
            return  # Nada a migrar

        # Verifica se indicadores já foram migrados
        count_new = conn.execute("SELECT COUNT(*) FROM indicadores").fetchone()[0]
        legacy    = conn.execute("SELECT * FROM indicadores_mapeamento ORDER BY codigo_indicador").fetchall()

        if count_new == 0 and legacy:
            print(f"[MIGRAÇÃO] Migrando {len(legacy)} indicadores para novo schema...")
            for row in legacy:
                r = dict(row)
                conn.execute("""
                    INSERT OR IGNORE INTO indicadores
                        (codigo_indicador, nome_indicador, tipo, periodicidade, unidade,
                         meta_texto, meta_numero, menor_melhor, observacoes, indicador_ativo, atualizado_em)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    r["codigo_indicador"],
                    r["nome_indicador"],
                    r.get("tipo") or "Operacional",
                    r.get("periodicidade") or "Mensal",
                    r.get("unidade"),
                    r.get("meta_texto"),
                    r.get("meta_numero"),
                    r.get("menor_melhor", 1),
                    r.get("observacoes"),
                    r.get("indicador_ativo", 1),
                    now,
                ))
            conn.commit()
            print("[MIGRAÇÃO] Indicadores migrados.")

        # Cria subindicador-padrão para indicadores sem subindicador
        indicadores = conn.execute("SELECT codigo_indicador, nome_indicador FROM indicadores").fetchall()
        for ind in indicadores:
            cod  = ind["codigo_indicador"]
            nome = ind["nome_indicador"]
            existing_sub = conn.execute(
                "SELECT id FROM subindicadores WHERE codigo_indicador=?", (cod,)
            ).fetchone()
            if not existing_sub:
                cur = conn.execute("""
                    INSERT INTO subindicadores
                        (codigo_indicador, nome_subindicador, ordem, ativo, observacoes, atualizado_em)
                    VALUES (?,?,0,1,'Subindicador padrão (migrado automaticamente)',?)
                """, (cod, nome, now))
                sub_id = cur.lastrowid
                conn.commit()

                # Migra histórico antigo (por codigo_indicador) para este subindicador
                # dados_historicos legados têm codigo_indicador (TEXT), novos têm subindicador_id (INT)
                # Detecta se há coluna codigo_indicador na tabela
                cols = [c[1] for c in conn.execute("PRAGMA table_info(dados_historicos)").fetchall()]
                if "codigo_indicador" in cols:
                    old_hist = conn.execute(
                        "SELECT ano, mes, valor FROM dados_historicos WHERE codigo_indicador=? AND (subindicador_id IS NULL OR subindicador_id=0)",
                        (cod,)
                    ).fetchall()
                    for h in old_hist:
                        conn.execute("""
                            INSERT OR IGNORE INTO dados_historicos (subindicador_id, ano, mes, valor)
                            VALUES (?,?,?,?)
                        """, (sub_id, h["ano"], h["mes"], h["valor"]))
                    if old_hist:
                        print(f"[MIGRAÇÃO] {cod}: {len(old_hist)} registros históricos migrados para subindicador {sub_id}.")
                conn.commit()

        print("[MIGRAÇÃO] Concluída.")
    except Exception as e:
        print(f"[MIGRAÇÃO] Erro: {e}")
        conn.rollback()
    finally:
        conn.close()


# ── Bootstrap ──────────────────────────────────────────────────────────────

def _seed_config_defaults():
    defaults = [
        ("nome_book",       "Indicadores de Segurança Patrimonial"),
        ("nome_instituicao","Hospital Universitário Evangélico Mackenzie"),
        ("responsavel",     "Segurança Patrimonial"),
        ("periodo_atual",   "Jan a Fev/2026"),
        ("data_atualizacao",""),
    ]
    conn = _connect()
    try:
        for chave, valor in defaults:
            conn.execute(
                "INSERT OR IGNORE INTO config (chave, valor) VALUES (?,?)",
                (chave, valor)
            )
        conn.commit()
    finally:
        conn.close()


def _seed_from_mapping_if_empty():
    """Bootstrap: usa mapping_db.py apenas se indicadores estiver vazio."""
    conn = _connect()
    try:
        count = conn.execute("SELECT COUNT(*) FROM indicadores").fetchone()[0]
    finally:
        conn.close()
    if count > 0:
        return
    try:
        from mapping_db import MAPEAMENTO_INDICADORES
        now = datetime.now().isoformat(sep=" ", timespec="seconds")
        conn = _connect()
        for m in MAPEAMENTO_INDICADORES:
            conn.execute("""
                INSERT OR IGNORE INTO indicadores
                    (codigo_indicador, nome_indicador, observacoes, atualizado_em)
                VALUES (?,?,?,?)
            """, (m["codigo_indicador"], m["nome_indicador"], m.get("observacoes"), now))
        conn.commit()
        conn.close()
    except ImportError:
        pass


init_db()
migrate_from_legacy()
_seed_config_defaults()
_seed_from_mapping_if_empty()
