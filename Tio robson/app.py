"""
app.py - Ponto de entrada do dashboard Segurança Patrimonial.
Execute: python sp_dashboard/app.py
"""

import sys
import os

# Garante que o módulo encontra os arquivos relativos ao projeto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon

from styles import GLOBAL_STYLE, CINZA_BG, BRANCO, CINZA_BORDA
from data_loader import get_all_data
from main_window import Sidebar, TopHeader
from panel_executivo import PainelExecutivoPanel
from panel_indicadores import IndicadoresPanel
from panel_subindicadores import SubindicadoresPanel
from panel_pendencias import PendenciasPanel
from panel_instrucoes import InstrucoesPanel
from panel_base_dados import BaseDadosPanel
from panel_historico import HistoricoPanel
from panel_analise_critica import AnaliseCriticaPanel
from panel_config import ConfigPanel


PAGE_TITLES = {
    "painel":         ("BOOK DE INDICADORES",  "PAINEL EXECUTIVO"),
    "indicadores":    ("BOOK DE INDICADORES",  "INDICADORES"),
    "subindicadores": ("SEGURANÇA PATRIMONIAL", "GRÁFICOS E SUBINDICADORES"),
    "pendencias":     ("SEGURANÇA PATRIMONIAL", "PENDÊNCIAS E OBSERVAÇÕES"),
    "historico":      ("SEGURANÇA PATRIMONIAL", "HISTÓRICO MENSAL"),
    "analise":        ("SEGURANÇA PATRIMONIAL", "ANÁLISE CRÍTICA"),
    "base_dados":     ("SEGURANÇA PATRIMONIAL", "BASE DE DADOS"),
    "config":         ("SEGURANÇA PATRIMONIAL", "CONFIGURAÇÕES"),
    "instrucoes":     ("SEGURANÇA PATRIMONIAL", "INSTRUÇÕES"),
}


class MainApp(QMainWindow):
    def __init__(self, data):
        super().__init__()
        self.data = data
        self.setWindowTitle("Book de Indicadores – Segurança Patrimonial | Mackenzie")
        self.setMinimumSize(1280, 780)
        self.resize(1440, 900)
        self.setStyleSheet(GLOBAL_STYLE)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top Header ─────────────────────────────────────────────────────
        self.header = TopHeader()
        root.addWidget(self.header)

        # ── Layout Horizontal (Sidebar + Conteúdo) ─────────────────────────
        body_ly = QHBoxLayout()
        body_ly.setContentsMargins(0, 0, 0, 0)
        body_ly.setSpacing(0)

        # Sidebar
        self.sidebar = Sidebar()
        self.sidebar.on_navigate(self._navigate)
        body_ly.addWidget(self.sidebar)

        # Área de conteúdo
        content_area = QWidget()
        content_area.setStyleSheet(f"background: {CINZA_BG};")
        content_ly = QVBoxLayout(content_area)
        content_ly.setContentsMargins(0, 0, 0, 0)
        content_ly.setSpacing(0)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background: {CINZA_BG};")
        content_ly.addWidget(self.stack, 1)

        body_ly.addWidget(content_area, 1)
        root.addLayout(body_ly, 1)

        self.sidebar.btn_reload.clicked.connect(self.reload_data)

        # ── Páginas ────────────────────────────────────────────────────────
        self._pages = {}
        self.build_pages()

        # Inicia na tela Painel Executivo
        self._navigate("painel")

    def build_pages(self):
        # Remove widgets antigos se existirem
        while self.stack.count() > 0:
            widget = self.stack.widget(0)
            self.stack.removeWidget(widget)
            widget.deleteLater()
            
        self._pages.clear()
        self._add_page("painel",         PainelExecutivoPanel(self.data))
        self._add_page("indicadores",    IndicadoresPanel(self.data))
        self._add_page("subindicadores", SubindicadoresPanel(self.data))
        self._add_page("pendencias",     PendenciasPanel(self.data))
        self._add_page("historico",      HistoricoPanel(self.data))
        self._add_page("analise",        AnaliseCriticaPanel(self.data))
        self._add_page("base_dados",     BaseDadosPanel(self.data))
        self._add_page("config",         ConfigPanel(self.data))
        self._add_page("instrucoes",     InstrucoesPanel(self.data))
        
        # Restaurar página atual se houver
        current_key = "painel"
        for btn in self.sidebar._buttons:
            if btn._active: current_key = btn.key
        self._navigate(current_key)

    def reload_data(self):
        try:
            from data_loader import get_all_data
            self.data = get_all_data()
            self.build_pages()
            print("[INFO] Dados recarregados com sucesso do banco SQLite.")
        except Exception as e:
            print(f"[ERRO] Falha ao recarregar dados: {e}")

    def _add_page(self, key, widget):
        self._pages[key] = widget
        self.stack.addWidget(widget)

    def _navigate(self, key):
        if key in self._pages:
            self.stack.setCurrentWidget(self._pages[key])
            self.sidebar.set_active(key)
            title, subtitle = PAGE_TITLES.get(key, ("BOOK DE INDICADORES", ""))
            self.header.set_page(title, subtitle)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("SP Dashboard")
    app.setOrganizationName("Mackenzie")
    app.setFont(QFont("Segoe UI", 10))

    # Carrega dados — fonte única: SQLite via data_loader
    try:
        data = get_all_data()
    except Exception as e:
        print(f"[AVISO] Erro ao carregar dados do banco: {e}")
        # Fallback seguro com estrutura mínima vazia
        data = {
            "config":       {},
            "indicadores":  [],
            "pendencias":   [],
            "stats":        {"total":0,"com_meta":0,"sem_meta":0,"em_atencao":0,
                             "pendentes_processo":0,"a_preencher":0,
                             "periodo":"—","responsavel":"—","atualizacao":"—"},
            "comparativos": {},
            "sub_raw":      [],
            "ac_raw":       [],
        }

    window = MainApp(data)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
