import sys; sys.path.insert(0,'sp_dashboard')
import database as db

print('=== Indicadores ===')
inds = db.get_all_indicadores()
for i in inds:
    print(f"  {i['codigo_indicador']} | {i['nome_indicador'][:40]}")

print()
print('=== Subindicadores ===')
subs = db.get_all_subindicadores()
for s in subs:
    print(f"  id={s['id']} | {s['codigo_indicador']} | {s['nome_subindicador'][:40]} | ativo={s['ativo']}")

print()
print('=== Historico SP.IND.006 via subindicador ===')
sub6 = db.get_subindicadores('SP.IND.006')
if sub6:
    hist = db.get_historico_subindicador(sub6[0]['id'], [2025, 2026])
    print(f"  Sub id={sub6[0]['id']}: 2026={hist.get(2026,{})} | 2025 keys={list(hist.get(2025,{}).keys())[:3]}")

print()
print('=== Historico agregado SP.IND.006 ===')
hist_ind = db.get_historico_indicador('SP.IND.006', [2026])
print(f"  {hist_ind}")

print()
print('=== Stats ===')
print(db.get_stats_indicadores())
