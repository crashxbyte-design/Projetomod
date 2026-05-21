import sys; sys.path.insert(0,'sp_dashboard')
from data_loader import get_all_data
d = get_all_data()
print('=== STATS ===')
print(d['stats'])
print()
print('=== INDICADORES ===')
for i in d['indicadores']:
    titulo = i['titulo'][:40]
    print(f"{i['codigo']} | {titulo} | Jan={i['resultado_jan']} | Fev={i['resultado_fev']} | Status={i['status']} | Meta={i['meta']}")
print()
sub26 = [s for s in d['sub_raw'] if s['ano'] == 2026]
print(f"Sub_raw 2026: {len(sub26)} | Total: {len(d['sub_raw'])}")
for s in sub26[:6]:
    print(s)
