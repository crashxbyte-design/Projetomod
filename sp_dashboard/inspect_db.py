import sqlite3
conn = sqlite3.connect("sp_indicadores.db")
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print("TABELAS:", tables)

for t in tables:
    cur.execute(f"PRAGMA table_info({t})")
    cols = cur.fetchall()
    print(f"\n=== {t} ===")
    for c in cols:
        print(f"  {c[1]:30s}  {c[2]}")
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    print(f"  ROWS: {cur.fetchone()[0]}")

# Mostrar 2 linhas de indicadores
cur.execute("SELECT * FROM indicadores LIMIT 2")
rows = cur.fetchall()
for r in rows:
    print("\nINDICADOR:", r)

conn.close()
