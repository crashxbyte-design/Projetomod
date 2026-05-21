import sys
sys.path.insert(0, 'sp_dashboard')
try:
    import database
    print("database OK")
    import data_loader
    print("data_loader OK")
    import panel_base_dados
    print("panel_base_dados OK")
    import panel_historico
    print("panel_historico OK")
    print("TUDO OK - pode tentar abrir o app")
except Exception as e:
    import traceback
    traceback.print_exc()
