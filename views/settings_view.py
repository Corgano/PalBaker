# views/settings_view.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QCheckBox, QFileDialog, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt
from utils.theme import Theme  # <--- UPDATED

class PathPicker(QWidget):
    def __init__(self, label: str, value: str, on_browse_click):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.label_widget = QLabel(label)
        self.label_widget.setMinimumWidth(220)
        self.label_widget.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-weight: bold;")  # <--- UPDATED
        
        self.input_widget = QLineEdit(value)
        
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.clicked.connect(on_browse_click)
        
        layout.addWidget(self.label_widget, 0)
        layout.addWidget(self.input_widget, 1)
        layout.addWidget(self.browse_btn, 0)
        self.setLayout(layout)
        
    def get_value(self) -> str:
        return self.input_widget.text()
        
    def set_value(self, text: str):
        self.input_widget.setText(text)

class SettingsView(QWidget):
    def __init__(self, parent_window, settings: dict, on_save_callback):
        super().__init__()
        self.main_page = parent_window
        self.settings = settings
        self.on_save_callback = on_save_callback
        
        # Link the Controller
        from controllers.settings_controller import SettingsController
        self.controller = SettingsController(self, settings, on_save_callback)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(15)
        
        title = QLabel("Application Paths")
        title.setStyleSheet(f"font-size: {Theme.FONT_SIZE_HEADER}; font-weight: bold; color: white;")  # <--- UPDATED
        scroll_layout.addWidget(title)
        
        self.fmodel_picker = PathPicker(
            "FModel Output Folder", 
            str(settings.get("fmodel_output", "")),
            lambda: self.pick_directory(self.fmodel_picker)
        )
        self.ue_root_picker = PathPicker(
            "Unreal Engine Root (e.g. UE_5.1)", 
            str(settings.get("ue_root", "")),
            lambda: self.pick_directory(self.ue_root_picker)
        )
        self.uproject_picker = PathPicker(
            "Palworld ModKit .uproject Path", 
            str(settings.get("uproject", "")),
            lambda: self.pick_file(self.uproject_picker, "Unreal Project (*.uproject)")
        )
        self.blender_picker = PathPicker(
            "Blender Executable Path", 
            str(settings.get("blender", "")),
            lambda: self.pick_file(self.blender_picker, "Executable (*.exe)")
        )
        self.palworld_exe_picker = PathPicker(
            "Palworld.exe Path", 
            str(settings.get("palworld_exe", "")),
            lambda: self.pick_file(self.palworld_exe_picker, "Executable (*.exe)")
        )
        
        scroll_layout.addWidget(self.fmodel_picker)
        scroll_layout.addWidget(self.ue_root_picker)
        scroll_layout.addWidget(self.uproject_picker)
        scroll_layout.addWidget(self.blender_picker)
        scroll_layout.addWidget(self.palworld_exe_picker)
        
        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setStyleSheet(f"background-color: {Theme.BORDER_COLOR};")  # <--- UPDATED
        scroll_layout.addWidget(line1)
        
        pref_title = QLabel("Preferences")
        pref_title.setStyleSheet(f"font-size: {Theme.FONT_SIZE_HEADER}; font-weight: bold; color: white;")  # <--- UPDATED
        scroll_layout.addWidget(pref_title)
        
        self.show_mapped_switch = QCheckBox("Show Mapped Names (e.g. Chillet instead of WeaselDragon)")
        self.show_mapped_switch.setChecked(bool(settings.get("show_mapped", False)))
        scroll_layout.addWidget(self.show_mapped_switch)
        
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setStyleSheet(f"background-color: {Theme.BORDER_COLOR};")  # <--- UPDATED
        scroll_layout.addWidget(line2)
        
        self.save_btn = QPushButton("Save and Reload Mod List")
        self.save_btn.setFixedHeight(50)
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.PRIMARY};
                font-weight: bold;
                font-size: 14px;
                border-radius: {Theme.RADIUS_MEDIUM};
            }}
            QPushButton:hover {{
                background-color: {Theme.PRIMARY_HOVER};
            }}
        """)  # <--- UPDATED
        self.save_btn.clicked.connect(self._on_save)
        scroll_layout.addWidget(self.save_btn)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

    def pick_directory(self, picker):
        path = QFileDialog.getExistingDirectory(self, "Select Directory", picker.get_value())
        if path:
            picker.set_value(path)

    def pick_file(self, picker, file_filter="All Files (*)"):
        path, _ = QFileDialog.getOpenFileName(self, "Select File", picker.get_value(), file_filter)
        if path:
            picker.set_value(path)

    def update_settings(self, new_settings: dict):
        self.settings = new_settings
        self.fmodel_picker.set_value(str(new_settings.get("fmodel_output", "")))
        self.ue_root_picker.set_value(str(new_settings.get("ue_root", "")))
        self.uproject_picker.set_value(str(new_settings.get("uproject", "")))
        self.blender_picker.set_value(str(new_settings.get("blender", "")))
        self.palworld_exe_picker.set_value(str(new_settings.get("palworld_exe", "")))
        self.show_mapped_switch.setChecked(bool(new_settings.get("show_mapped", False)))

    def _on_save(self):
        current_paths = {
            "fmodel_output": self.fmodel_picker.get_value(),
            "ue_root": self.ue_root_picker.get_value(),
            "uproject": self.uproject_picker.get_value(),
            "blender": self.blender_picker.get_value(),
            "palworld_exe": self.palworld_exe_picker.get_value(),
        }
        self.controller.save_clicked(current_paths, bool(self.show_mapped_switch.isChecked()))

    def show_dialog(self, dlg):
        if hasattr(dlg, 'exec'):
            dlg.exec()

    def pop_dialog(self):
        pass

    def show_snackbar(self, message: str, color: str):
        self.main_page.statusBar().showMessage(message, 3000)