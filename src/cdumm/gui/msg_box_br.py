from PySide6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton
from PySide6.QtCore import Qt

def _pergunta_br(parent, title, text, buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, defaultButton=QMessageBox.StandardButton.NoButton, icon=QMessageBox.Icon.Question):
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setIcon(icon)
    msg.setStyleSheet("""
        QMessageBox { background-color: #0E080C; border: 1px solid #FF6E1A; }
        QLabel { color: #D6D6E0; font-family: 'Segoe UI'; font-size: 13px; font-weight: 500; }
        QPushButton { background-color: rgba(14, 8, 12, 0.8); border: 1px solid #FF6E1A; border-radius: 4px; color: #F4F4FC; padding: 6px 20px; font-family: 'Bahnschrift'; font-weight: bold; }
        QPushButton:hover { background-color: rgba(229, 20, 20, 0.6); color: white; }
    """)
    
    # Adicionando botões forçados em PT-BR
    btn_sim = msg.addButton("Sim", QMessageBox.ButtonRole.YesRole)
    btn_nao = msg.addButton("Não", QMessageBox.ButtonRole.NoRole)
    
    btn_cancel = None
    if buttons & QMessageBox.StandardButton.Cancel:
        btn_cancel = msg.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        
    msg.exec()
    clicked = msg.clickedButton()
    
    # Convertendo de volta para StandardButton para manter a compatibilidade
    if clicked == btn_sim:
        return QMessageBox.StandardButton.Yes
    elif clicked == btn_nao:
        return QMessageBox.StandardButton.No
    elif clicked == btn_cancel:
        return QMessageBox.StandardButton.Cancel
    return QMessageBox.StandardButton.NoButton

def _info_br(parent, title, text):
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setIcon(QMessageBox.Icon.Information)
    msg.setStyleSheet("""
        QMessageBox { background-color: #0E080C; border: 1px solid #FF6E1A; }
        QLabel { color: #D6D6E0; font-family: 'Segoe UI'; font-size: 13px; font-weight: 500; }
        QPushButton { background-color: rgba(14, 8, 12, 0.8); border: 1px solid #FF6E1A; border-radius: 4px; color: #F4F4FC; padding: 6px 20px; font-family: 'Bahnschrift'; font-weight: bold; }
        QPushButton:hover { background-color: rgba(229, 20, 20, 0.6); color: white; }
    """)
    msg.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
    msg.exec()
    return QMessageBox.StandardButton.Ok

def _warning_br(parent, title, text):
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setIcon(QMessageBox.Icon.Warning)
    msg.setStyleSheet("""
        QMessageBox { background-color: #0E080C; border: 1px solid #E51414; }
        QLabel { color: #D6D6E0; font-family: 'Segoe UI'; font-size: 13px; font-weight: 500; }
        QPushButton { background-color: rgba(14, 8, 12, 0.8); border: 1px solid #E51414; border-radius: 4px; color: #F4F4FC; padding: 6px 20px; font-family: 'Bahnschrift'; font-weight: bold; }
        QPushButton:hover { background-color: rgba(229, 20, 20, 0.6); color: white; }
    """)
    msg.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
    msg.exec()
    return QMessageBox.StandardButton.Ok

def _critical_br(parent, title, text):
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setIcon(QMessageBox.Icon.Critical)
    msg.setStyleSheet("""
        QMessageBox { background-color: #0E080C; border: 1px solid #E51414; }
        QLabel { color: #D6D6E0; font-family: 'Segoe UI'; font-size: 13px; font-weight: 500; }
        QPushButton { background-color: rgba(14, 8, 12, 0.8); border: 1px solid #E51414; border-radius: 4px; color: #F4F4FC; padding: 6px 20px; font-family: 'Bahnschrift'; font-weight: bold; }
        QPushButton:hover { background-color: rgba(229, 20, 20, 0.6); color: white; }
    """)
    msg.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
    msg.exec()
    return QMessageBox.StandardButton.Ok

def _input_text_br(parent, title, label, default=""):
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setMinimumWidth(350)
    dialog.setStyleSheet("""
        QDialog { background-color: #0E080C; border: 1px solid #FF6E1A; }
        QLabel { color: #D6D6E0; font-family: 'Segoe UI'; font-size: 13px; font-weight: 500; }
        QLineEdit { background: rgba(14, 8, 12, 0.8); border: 1px solid #26181A; border-radius: 4px; color: #F4F4FC; padding: 6px; font-size: 13px; }
        QLineEdit:focus { border: 1px solid #FF6E1A; }
        QPushButton { background-color: rgba(14, 8, 12, 0.8); border: 1px solid #FF6E1A; border-radius: 4px; color: #F4F4FC; padding: 6px 20px; font-family: 'Bahnschrift'; font-weight: bold; }
        QPushButton:hover { background-color: rgba(229, 20, 20, 0.6); color: white; }
    """)
    vbox = QVBoxLayout(dialog)
    vbox.addWidget(QLabel(label))
    line = QLineEdit(default)
    vbox.addWidget(line)
    hbox = QHBoxLayout()
    hbox.addStretch()
    
    btn_cancelar = QPushButton("Cancelar")
    btn_cancelar.clicked.connect(dialog.reject)
    hbox.addWidget(btn_cancelar)
    
    btn_ok = QPushButton("Confirmar")
    btn_ok.setDefault(True)
    btn_ok.clicked.connect(dialog.accept)
    hbox.addWidget(btn_ok)
    
    vbox.addLayout(hbox)
    
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return line.text(), True
    return "", False

def _input_item_br(parent, title, label, items, default_idx=0):
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setMinimumWidth(380)
    dialog.setStyleSheet("""
        QDialog { background-color: #0E080C; border: 1px solid #FF6E1A; }
        QLabel { color: #D6D6E0; font-family: 'Segoe UI'; font-size: 13px; font-weight: 500; }
        QComboBox { background: rgba(14, 8, 12, 0.8); border: 1px solid #26181A; border-radius: 4px; color: #F4F4FC; padding: 6px; font-size: 13px; }
        QComboBox:focus { border: 1px solid #FF6E1A; }
        QComboBox::drop-down { border: none; }
        QComboBox QAbstractItemView { background: #0E080C; border: 1px solid #FF6E1A; selection-background-color: rgba(229, 20, 20, 0.4); color: white; }
        QPushButton { background-color: rgba(14, 8, 12, 0.8); border: 1px solid #FF6E1A; border-radius: 4px; color: #F4F4FC; padding: 6px 20px; font-family: 'Bahnschrift'; font-weight: bold; }
        QPushButton:hover { background-color: rgba(229, 20, 20, 0.6); color: white; }
    """)
    vbox = QVBoxLayout(dialog)
    lbl = QLabel(label)
    lbl.setWordWrap(True)
    vbox.addWidget(lbl)
    
    combo = QComboBox()
    combo.addItems(items)
    if 0 <= default_idx < len(items):
        combo.setCurrentIndex(default_idx)
    vbox.addWidget(combo)
    
    hbox = QHBoxLayout()
    hbox.addStretch()
    
    btn_cancelar = QPushButton("Cancelar")
    btn_cancelar.clicked.connect(dialog.reject)
    hbox.addWidget(btn_cancelar)
    
    btn_ok = QPushButton("Confirmar")
    btn_ok.setDefault(True)
    btn_ok.clicked.connect(dialog.accept)
    hbox.addWidget(btn_ok)
    
    vbox.addLayout(hbox)
    
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return combo.currentText(), True
    return "", False
