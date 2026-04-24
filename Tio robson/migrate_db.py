"""
migrate_db.py - Migração cirúrgica do banco de dados para o novo schema.
Execute UMA vez: python migrate_db.py
"""
import sys, sqlite3, os
sys.path.insert(0, 'sp_dashboard')

DB = 'sp_indicadores.db'
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys=OFF")

from datetime import datetime
now = datetime.now().isoformat(sep=" ", timespec="seconds")

print("=== Migração do banco sp_indicadores.db ===\n")

# 1. Backup da tabela dados_historicos antiga
print("1. Backup de dados_historicos → dados_historicos_legacy...")
conn.execute("""
    CREATE TABLE IF NOT EXISTS dados_historicos_legacy AS
    SELECT * FROM dados_historicos
""")
conn.commit()
n_legacy = conn.execute("SELECT COUNT(*) FROM dados_historicos_legacy").fetchone()[0]
print(f"   {n_legacy} registros preservados em dados_historicos_legacy.")

# 2. Drop e recria dados_historicos com novo schema
print("\n2. Recriando dados_historicos com novo schema (subindicador_id)...")
conn.execute("DROP TABLE dados_historicos")
conn.execute("""
    CREATE TABLE dados_historicos (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        subindicador_id  INTEGER NOT NULL,
        ano              INTEGER NOT NULL,
        mes              TEXT NOT NULL,
        valor            REAL,
        observacoes      TEXT,
        UNIQUE(subindicador_id, ano, mes)
    )
""")
conn.commit()
print("   Tabela recriada.")

# 3. Garante que subindicadores já foram criados (via database.py init)
import database as db
print("\n3. Verificando subindicadores...")
subs = db.get_all_subindicadores()
print(f"   {len(subs)} subindicadores encontrados.")

# 4. Migra histórico legado para o subindicador-padrão de cada indicador
print("\n4. Migrando histórico legado → dados_historicos (por subindicador_id)...")
legacy = conn.execute("SELECT * FROM dados_historicos_legacy").fetchall()
migrated = 0; skipped = 0
for row in legacy:
    cod = row["codigo_indicador"]
    sub = conn.execute(
        "SELECT id FROM subindicadores WHERE codigo_indicador=? ORDER BY id LIMIT 1", (cod,)
    ).fetchone()
    if not sub:
        print(f"   AVISO: sem subindicador para {cod}, criando...")
        ind = conn.execute("SELECT * FROM indicadores WHERE codigo_indicador=?", (cod,)).fetchone()
        nome = dict(ind)["nome_indicador"] if ind else cod
        cur = conn.execute("""
            INSERT INTO subindicadores (codigo_indicador, nome_subindicador, ordem, ativo, observacoes, atualizado_em)
            VALUES (?,?,0,1,'Subindicador padrão (migrado automaticamente)',?)
        """, (cod, nome, now))
        conn.commit()
        sub_id = cur.lastrowid
    else:
        sub_id = sub["id"]
    try:
        conn.execute("""
            INSERT OR IGNORE INTO dados_historicos (subindicador_id, ano, mes, valor)
            VALUES (?,?,?,?)
        """, (sub_id, row["ano"], row["mes"], row["valor"]))
        migrated += 1
    except Exception as e:
        print(f"   Erro: {e}")
        skipped += 1

conn.commit()
print(f"   {migrated} registros migrados | {skipped} ignorados.")

# 5. Cria subindicadores-padrão para indicadores sem subindicador
print("\n5. Garantindo subindicador-padrão para todos os indicadores...")
inds = conn.execute("SELECT codigo_indicador, nome_indicador FROM indicadores").fetchall()
criados = 0
for ind in inds:
    cod = ind["codigo_indicador"]
    existing = conn.execute("SELECT id FROM subindicadores WHERE codigo_indicador=?", (cod,)).fetchone()
    if not existing:
        conn.execute("""
            INSERT INTO subindicadores (codigo_indicador, nome_subindicador, ordem, ativo, observacoes, atualizado_em)
            VALUES (?,?,0,1,'Subindicador padrão',?)
        """, (cod, ind["nome_indicador"], now))
        criados += 1
conn.commit()
print(f"   {criados} subindicadores-padrão criados.")

conn.close()

# 6. Validação final
print("\n6. Validação final...")
import database as db_final
stats = db_final.get_stats_indicadores()
print(f"   Indicadores: {stats['total']} | Subindicadores: {stats['n_subindicadores']} | Histórico: {stats['n_historico']}")
hist = db_final.get_historico_indicador('SP.IND.006', [2026])
print(f"   SP.IND.006 / 2026: {hist.get(2026, {})}")
hist2 = db_final.get_historico_indicador('SP.IND.001', [2026])
print(f"   SP.IND.001 / 2026: {hist2.get(2026, {})}")

print("\n=== Migração concluída com sucesso! ===")
