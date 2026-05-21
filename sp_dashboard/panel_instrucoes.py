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
             "Este Dashboard funciona com um banco de dados local seguro. "
             "Para atualizar os dados apresentados nas telas, siga os passos:\n"
             "1. Acesse a aba 'Base de Dados' no menu lateral.\n"
             "2. Utilize os formulários integrados para lançar novos Subindicadores, registrar Análises Críticas ou configurar o painel.\n"
             "3. As alterações são salvas automaticamente. Para forçar a atualização nas outras telas, clique no botão '🔄 Recarregar Dados' no menu lateral inferior."),
            
            ("ORGANIZAÇÃO DO SISTEMA",
             "• Painel Executivo: Visão consolidada para a alta gestão (KPIs gerais).\n"
             "• Indicadores: Resumo de status, metas e resultados macro de cada indicador.\n"
             "• Gráficos e Subindicadores: Ambiente de análise evolutiva mensal (visões linha, barra e grade).\n"
             "• Base de Dados: Módulo principal de preenchimento e gerenciamento das tabelas do sistema."),
            
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
