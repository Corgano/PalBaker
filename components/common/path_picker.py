# components/common/path_picker.py
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton
from utils.theme import Theme  # <--- UPDATED

class PathPicker(QWidget):
    def __init__(self, label: str, value: str, icon=None, on_browse_click=None):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        self.text_field = QLineEdit(value)
        self.text_field.setPlaceholderText(label)
        self.text_field.textChanged.connect(self._on_text_change)
        
        self.button = QPushButton("Browse")
        if on_browse_click:
            self.button.clicked.connect(on_browse_click)
            
        layout.addWidget(self.text_field, 1)
        layout.addWidget(self.button, 0)
        
        self.view = self

    def _on_text_change(self, text):
        pass

    def get_value(self) -> str:
        return self.text_field.text()

    def set_value(self, value: str):
        self.text_field.setText(value)