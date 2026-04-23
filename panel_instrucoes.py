"""
panel_instrucoes.py - Tela de Instruções.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from styles import (
    BRANCO, CINZA_BG, CINZA_BORDA, CINZA_SUAVE, PRETO_TITULO, VERMELHO
)
from widgets import SectionTitle

class InstrucoesPanel(QWidget):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root.addWidget(scroll)

        container = QWidget()
        container.setStyleSheet(f"background: {CINZA_BG};")
        scroll.setWidget(container)

        main = QVBoxLayout(container)
        main.setContentsMargins(28, 24, 28, 32)
        main.setSpacing(24)

        title = SectionTitle("MANUAL DE USO DO DASHBOARD")
        main.addWidget(title)

        content_frame = QFrame()
        content_frame.setStyleSheet(f"""
            QFrame {{
                background: {BRANCO};
                border: 1px solid {CINZA_BORDA};
                border-radius: 8px;
            }}
        """)
        c_ly = QVBoxLayout(content_frame)
        c_ly.setContentsMargins(32, 32, 32, 32)
        c_ly.setSpacing(20)

        instrucoes = [
            ("COMO ATUALIZAR OS DADOS",
             "Este Dashboard funciona em conjunto com o arquivo Excel BD_Dashboard_Seguranca.xlsx. "
             "Para atualizar os dados apresentados nas telas, siga os passos:\n"
             "1. Abra o arquivo Excel BD_Dashboard_Seguranca.xlsx.\n"
             "2. Atualize os dados nas abas correspondentes.\n"
             "3. Salve e feche o arquivo Excel.\n"
             "4. Clique no botão '🔄 Recarregar Dados' no menu lateral deste Dashboard."),
            
            ("SIGNIFICADO DAS ABAS NO EXCEL",
             "• Base_Indicadores: Dados cadastrais de cada indicador (nome, meta, responsável).\n"
             "• Base_Subindicadores: Lançamento mensal dos valores reais dos subindicadores.\n"
             "• Base_Analise_Critica: Registro de planos de ação, prazos e justificativas para indicadores pendentes.\n"
             "• Config: Ajustes de textos do sistema (período atual, datas, títulos)."),
            
            ("LEGENDA DE STATUS",
             "🟢 DENTRO DA META: O resultado atual atingiu ou superou a meta estabelecida.\n"
             "🟠 EM ATENÇÃO: O resultado está fora da meta, requerendo acompanhamento.\n"
             "🔴 PENDENTE: Faltam processos, aprovações ou checklists para viabilizar a mensuração.\n"
             "⚪ A PREENCHER: Dados não consolidados para o período selecionado.")
        ]

        for titulo, texto in instrucoes:
            t = QLabel(titulo)
            t.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            t.setStyleSheet(f"color: {VERMELHO}; border: none;")
            c_ly.addWidget(t)

            lbl = QLabel(texto)
            lbl.setFont(QFont("Segoe UI", 10))
            lbl.setStyleSheet(f"color: {PRETO_TITULO}; border: none; line-height: 1.6;")
            lbl.setWordWrap(True)
            c_ly.addWidget(lbl)

            div = QFrame()
            div.setFrameShape(QFrame.Shape.HLine)
            div.setStyleSheet(f"color: {CINZA_BORDA};")
            c_ly.addWidget(div)

        # Remove o último separador
        c_ly.itemAt(c_ly.count() - 1).widget().deleteLater()
        
        main.addWidget(content_frame)
        main.addStretch()
