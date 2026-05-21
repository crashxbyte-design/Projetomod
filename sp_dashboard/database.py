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

import sys

def get_db_path():
    if getattr(sys, 'frozen', False):
        # Se rodando via EXE gerado pelo PyInstaller, o DB fica na mesma pasta do executável
        base_path = os.path.dirname(sys.executable)
        return os.path.join(base_path, "sp_indicadores.db")
    else:
        # Se rodando como script normal, o DB está um nível acima (ou onde você definiu)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.normpath(os.path.join(base_dir, "..", "sp_indicadores.db"))

DB_PATH = get_db_path()

MESES = [
    "Janeiro","Fevereiro","Março","Abril","Maio","Junho",
    "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"
]

DEFAULT_YEAR = 2026
YEAR_MIN = 2000
YEAR_MAX = 2100


def parse_valid_year(value) -> int | None:
    text = str(value).strip()
    if len(text) != 4 or not text.isdecimal():
        return None

    year = int(text)
    if YEAR_MIN <= year <= YEAR_MAX:
        return year
    return None


def is_valid_year(value) -> bool:
    return parse_valid_year(value) is not None

# ── Schema ─────────────────────────────────────────────────────────────────

_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS indicadores (
        codigo_indicador  TEXT PRIMARY KEY,
        nome_indicador    TEXT NOT NULL,
        tipo              TEXT DEFAULT 'Operacional',
        periodicidade     TEXT DEFAULT 'Mensal',
        unidade           TEXT,
        meta_operador     TEXT,
        meta_numero       REAL,
        meta_texto        TEXT,
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
        modo_lancamento   TEXT    DEFAULT 'mensal',
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

    # ── Tabela de lançamentos por faixa horária ───────────────────────────────
    # Vinculada por subindicador_id (FK). Constraint única garante que não há
    # duplicidade de (subindicador, ano, mês, dia, faixa_horaria).
    # Separada de dados_historicos para não contaminar o fluxo mensal.
    """CREATE TABLE IF NOT EXISTS lancamentos_horario (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        subindicador_id INTEGER NOT NULL,
        ano             INTEGER NOT NULL,
        mes             TEXT    NOT NULL,
        dia             INTEGER NOT NULL,
        faixa_horaria   TEXT    NOT NULL,
        valor           REAL,
        observacoes     TEXT,
        criado_em       TEXT,
        UNIQUE(subindicador_id, ano, mes, dia, faixa_horaria),
        FOREIGN KEY (subindicador_id) REFERENCES subindicadores(id)
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
        # Migração segura: adiciona meta_operador se não existir (banco já criado)
        try:
            conn.execute("ALTER TABLE indicadores ADD COLUMN meta_operador TEXT")
            conn.commit()
            # Converte menor_melhor legado para meta_operador onde meta_numero existe
            conn.execute("""
                UPDATE indicadores
                SET meta_operador = CASE
                    WHEN menor_melhor = 1 AND meta_numero IS NOT NULL THEN '<='
                    WHEN menor_melhor = 0 AND meta_numero IS NOT NULL THEN '>='
                    ELSE NULL
                END
                WHERE meta_operador IS NULL
            """)
            conn.commit()
        except Exception:
            pass  # coluna já existe
        _seed_config_defaults(conn)

        # ── Migrações idempotentes (ALTER TABLE só se a coluna não existir) ───
        # Adiciona modo_lancamento caso o banco já existia antes dessa versão.
        # Retrocompatibilidade: registros antigos herdam DEFAULT 'mensal' e
        # continuam funcionando sem nenhuma alteração nos fluxos existentes.
        try:
            conn.execute(
                "ALTER TABLE subindicadores ADD COLUMN modo_lancamento TEXT DEFAULT 'mensal'"
            )
            conn.commit()
        except Exception:
            pass  # coluna já existe — sem erro, sem perda de dados

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
        # Garante legado: se meta_texto não vier, gera a partir de operador+numero
        if not rec.get("meta_texto") and rec.get("meta_operador") and rec.get("meta_numero") is not None:
            rec["meta_texto"] = f"{rec['meta_operador']} {rec['meta_numero']}"
        # Garante legado: menor_melhor derivado de meta_operador
        op = rec.get("meta_operador", "")
        if op in ("<", "<="):
            rec.setdefault("menor_melhor", 1)
        elif op in (">", ">="):
            rec.setdefault("menor_melhor", 0)
        else:
            rec.setdefault("menor_melhor", 1)

        conn.execute("""
            INSERT INTO indicadores
                (codigo_indicador, nome_indicador, tipo, periodicidade, unidade,
                 meta_operador, meta_numero, meta_texto, menor_melhor,
                 observacoes, indicador_ativo, atualizado_em)
            VALUES
                (:codigo_indicador,:nome_indicador,:tipo,:periodicidade,:unidade,
                 :meta_operador,:meta_numero,:meta_texto,:menor_melhor,
                 :observacoes,:indicador_ativo,:atualizado_em)
            ON CONFLICT(codigo_indicador) DO UPDATE SET
                nome_indicador  = excluded.nome_indicador,
                tipo            = excluded.tipo,
                periodicidade   = excluded.periodicidade,
                unidade         = excluded.unidade,
                meta_operador   = excluded.meta_operador,
                meta_numero     = excluded.meta_numero,
                meta_texto      = excluded.meta_texto,
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


def get_anos_disponiveis() -> list[int]:
    """Retorna lista de anos com dados no banco (ex: [2024, 2025, 2026])."""
    conn = _connect()
    try:
        rows = conn.execute("SELECT DISTINCT ano FROM dados_historicos ORDER BY ano").fetchall()
        return [r["ano"] for r in rows if is_valid_year(r["ano"])]
    except Exception as e:
        print(f"[DB] get_anos_disponiveis erro: {e}")
        return []
    finally:
        conn.close()


def get_anos_historico_subindicador(subindicador_id: int) -> list[int]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT DISTINCT ano FROM dados_historicos WHERE subindicador_id=? ORDER BY ano",
            (subindicador_id,)
        ).fetchall()
        return [r["ano"] for r in rows if r["ano"]]
    except Exception as e:
        print(f"[DB] get_anos_historico_subindicador erro: {e}")
        return []
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
        rec.setdefault("modo_lancamento", "mensal")  # retrocompatibilidade
        if rec.get("id"):
            conn.execute("""
                UPDATE subindicadores SET
                    nome_subindicador=:nome_subindicador, ordem=:ordem,
                    ativo=:ativo, modo_lancamento=:modo_lancamento,
                    observacoes=:observacoes, atualizado_em=:atualizado_em
                WHERE id=:id
            """, rec)
            conn.commit()
            return int(rec["id"])
        else:
            cur = conn.execute("""
                INSERT INTO subindicadores
                    (codigo_indicador, nome_subindicador, ordem, ativo,
                     modo_lancamento, observacoes, atualizado_em)
                VALUES (:codigo_indicador,:nome_subindicador,:ordem,:ativo,
                        :modo_lancamento,:observacoes,:atualizado_em)
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


def delete_historico_ano(subindicador_id: int, ano: int) -> int:
    conn = _connect()
    try:
        cur_hist = conn.execute(
            "DELETE FROM dados_historicos WHERE subindicador_id=? AND ano=?",
            (subindicador_id, ano)
        )
        cur_hora = conn.execute(
            "DELETE FROM lancamentos_horario WHERE subindicador_id=? AND ano=?",
            (subindicador_id, ano)
        )
        conn.commit()
        return max(cur_hist.rowcount, 0) + max(cur_hora.rowcount, 0)
    except Exception as e:
        print(f"[DB] delete_historico_ano: {e}")
        return 0
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


# ── CRUD: lancamentos_horario ──────────────────────────────────────────────
# Sugestões de rótulos para autocomplete — não são obrigatórias.
# O sistema aceita qualquer texto que o usuário definir.
FAIXAS_HORARIAS = ["00h–06h", "06h–12h", "12h–18h", "18h–24h"]


def upsert_lancamento_horario(
    subindicador_id: int, ano: int, mes: str,
    dia: int, faixa: str, valor, obs: str = ""
) -> bool:
    """
    Grava ou atualiza um lançamento por faixa horária.
    A UNIQUE constraint (subindicador_id, ano, mes, dia, faixa_horaria)
    garante idempotência: relançar o mesmo registro atualiza o valor
    sem criar duplicidade.
    """
    conn = _connect()
    try:
        conn.execute("""
            INSERT INTO lancamentos_horario
                (subindicador_id, ano, mes, dia, faixa_horaria, valor, observacoes, criado_em)
            VALUES (?,?,?,?,?,?,?,?)
            ON CONFLICT(subindicador_id, ano, mes, dia, faixa_horaria) DO UPDATE SET
                valor=excluded.valor,
                observacoes=excluded.observacoes,
                criado_em=excluded.criado_em
        """, (
            subindicador_id, ano, mes, dia, faixa, valor, obs,
            datetime.now().isoformat(sep=" ", timespec="seconds")
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] upsert_lancamento_horario: {e}")
        return False
    finally:
        conn.close()


def get_lancamentos_horario(subindicador_id: int, ano: int, mes: str) -> dict:
    """
    Retorna {dia: {faixa_horaria: {"valor": v, "obs": o}}} para o grid.
    """
    conn = _connect()
    try:
        rows = conn.execute("""
            SELECT dia, faixa_horaria, valor, observacoes
            FROM lancamentos_horario
            WHERE subindicador_id=? AND ano=? AND mes=?
            ORDER BY dia, faixa_horaria
        """, (subindicador_id, ano, mes)).fetchall()
        result: dict = {}
        for r in rows:
            result.setdefault(r["dia"], {})[r["faixa_horaria"]] = {
                "valor": r["valor"],
                "obs":   r["observacoes"] or "",
            }
        return result
    except Exception as e:
        print(f"[DB] get_lancamentos_horario: {e}")
        return {}
    finally:
        conn.close()


def delete_lancamento_horario(
    subindicador_id: int, ano: int, mes: str, dia: int, faixa: str
) -> bool:
    """Remove um lançamento horário específico."""
    conn = _connect()
    try:
        conn.execute("""
            DELETE FROM lancamentos_horario
            WHERE subindicador_id=? AND ano=? AND mes=? AND dia=? AND faixa_horaria=?
        """, (subindicador_id, ano, mes, dia, faixa))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] delete_lancamento_horario: {e}")
        return False
    finally:
        conn.close()


def get_faixas_usadas(subindicador_id: int) -> list[str]:
    """
    Retorna a lista de rótulos de horário/período já usados para
    um subindicador (distinct, ordenados alfabéticamente).
    Usado pelo QCompleter para sugerir rótulos anteriores ao digitar.
    O usuário pode ignorar as sugestões e escrever qualquer rótulo novo.
    """
    conn = _connect()
    try:
        rows = conn.execute("""
            SELECT DISTINCT faixa_horaria
            FROM lancamentos_horario
            WHERE subindicador_id=? AND faixa_horaria IS NOT NULL
            ORDER BY faixa_horaria
        """, (subindicador_id,)).fetchall()
        return [r["faixa_horaria"] for r in rows]
    finally:
        conn.close()


def consolidar_mensal_horario(subindicador_id: int, ano: int, mes: str) -> float | None:
    """
    Soma todos os valores de faixas horárias do mês e retorna o total.
    Usado pela camada de leitura (data_loader) para alimentar gráficos
    existentes de forma transparente — os gráficos sempre recebem um
    número mensal sem saber a origem.
    Retorna None se não houver nenhum lançamento para o período.
    """
    conn = _connect()
    try:
        row = conn.execute("""
            SELECT SUM(valor) as total
            FROM lancamentos_horario
            WHERE subindicador_id=? AND ano=? AND mes=? AND valor IS NOT NULL
        """, (subindicador_id, ano, mes)).fetchone()
        return row["total"] if row and row["total"] is not None else None
    finally:
        conn.close()


def get_anos_horario(subindicador_id: int) -> list[int]:
    """Anos distintos que possuem ao menos um lançamento em lancamentos_horario."""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT DISTINCT ano FROM lancamentos_horario WHERE subindicador_id=? ORDER BY ano",
            (subindicador_id,)
        ).fetchall()
        return [r["ano"] for r in rows]
    except Exception:
        return []
    finally:
        conn.close()


def get_meses_horario(subindicador_id: int, ano: int) -> list[str]:
    """Meses em ordem calendário com ao menos um lançamento para o ano."""
    _M = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
          "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT DISTINCT mes FROM lancamentos_horario WHERE subindicador_id=? AND ano=?",
            (subindicador_id, ano)
        ).fetchall()
        have = {r["mes"] for r in rows}
        return [m for m in _M if m in have]
    except Exception:
        return []
    finally:
        conn.close()

def get_modo_lancamento_sub(subindicador_id: int) -> str:
    """Retorna o modo_lancamento do subindicador ('mensal' ou 'por_horario')."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT modo_lancamento FROM subindicadores WHERE id=?",
            (subindicador_id,)
        ).fetchone()
        return (row["modo_lancamento"] or "mensal") if row else "mensal"
    except Exception:
        return "mensal"
    finally:
        conn.close()


# ── CRUD: analise_critica ─────────────────────────────────────────────────────────────

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
