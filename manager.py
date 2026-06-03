# manager.py
import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget, QMessageBox
)
from PyQt6.QtCore import QTimer, QSize
from PyQt6.QtGui import QIcon

from utils.config import load_settings, save_settings
from utils.autofill_helper import detect_unreal_engine, detect_palworld_exe, find_blender_versions
from views.settings_view import SettingsView
from views.mods_view import ModsView
from utils.builder.config_helper import restore_palbaker_backup
from utils.theme import Theme  # <--- UPDATED

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Palworld Baker Mod Manager")
        
        # Load state
        self.settings = load_settings()
        
        # Set window size
        width = int(self.settings.get("window_width", 900))
        height = int(self.settings.get("window_height", 800))
        self.resize(width, height)
        
        # Restore backup immediately on startup
        uproject_path = self.settings.get("uproject")
        if isinstance(uproject_path, str):
            restore_palbaker_backup(uproject_path)

        # Tabs container (Mimics TabBar + TabBarView in Flet)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # Mount views
        self.mods_view = ModsView(self, self.settings)
        self.settings_view = SettingsView(self, self.settings, on_save_callback=self.mods_view.refresh_mods)
        
        self.tabs.addTab(self.mods_view, "Manager")
        self.tabs.addTab(self.settings_view, "Settings")
        
        # Initialize native status bar for SnackBar fallback messages
        self.statusBar().setStyleSheet(f"color: {Theme.TEXT_MUTED}; background-color: {Theme.BG_MAIN};")
        
        # Apply complete application-wide dark stylesheet
        self.setStyleSheet(Theme.get_global_stylesheet())  # <--- UPDATED
        
        # Autofill settings if empty
        self.run_autofills()
        
        # Automatically detect and fix Unreal Project requirements (Remote Execution & Cooking configs)
        self.auto_configure_project()
        
        # Periodic save timer (30 seconds) on Qt's main event loop (safer than raw background threads)
        self.last_saved_settings = self.settings.copy()
        self.save_timer = QTimer(self)
        self.save_timer.timeout.connect(self.periodic_save)
        self.save_timer.start(30000)
        
        # Check and handle multiple Blender paths
        self.check_multiple_blenders()
        
        # Initial scan
        self.mods_view.refresh_mods()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.settings["window_width"] = int(self.width())
        self.settings["window_height"] = int(self.height())
        save_settings(self.settings)

    def periodic_save(self):
        if self.settings != self.last_saved_settings:
            save_settings(self.settings)
            self.last_saved_settings = self.settings.copy()
            print("Periodic settings save triggered.")

    def run_autofills(self):
        changed = False
        # Unreal Engine
        if not self.settings.get("ue_root"):
            detected_ue = detect_unreal_engine()
            if detected_ue:
                print(f"Auto-detected Unreal Engine location as: '{detected_ue}'")
                self.settings["ue_root"] = detected_ue
                changed = True
        
        # Palworld
        if not self.settings.get("palworld_exe"):
            detected_pal = detect_palworld_exe()
            if detected_pal:
                print(f"Auto-detected Palworld.exe location as: '{detected_pal}'")
                self.settings["palworld_exe"] = detected_pal
                changed = True
                    
        # Blender
        self.blender_versions = find_blender_versions()
        blender_path = self.settings.get("blender")
        if not blender_path or blender_path == "blender":
            if len(self.blender_versions) == 1:
                print(f"Auto-detected single Blender installation: '{self.blender_versions[0]}'")
                self.settings["blender"] = self.blender_versions[0]
                changed = True
        
        if changed:
            save_settings(self.settings)
            self.settings_view.update_settings(self.settings)

    def auto_configure_project(self):
        """Automatically checks the open project's config and enables remote python execution if disabled."""
        uproject_path = self.settings.get("uproject")
        ue_root = self.settings.get("ue_root")
        
        if uproject_path and os.path.exists(uproject_path) and ue_root and os.path.exists(ue_root):
            from utils.plugin_manager import check_project_requirements
            try:
                reqs = check_project_requirements(ue_root, uproject_path)
                
                # Auto-heal remote execution python settings (DefaultEngine.ini)
                if reqs.get("needs_remote_exec_enable"):
                    from utils.plugins.installer import enable_remote_execution_settings
                    success, msg = enable_remote_execution_settings(uproject_path)
                    if success:
                        print("Auto-enabled Python Remote Execution settings in DefaultEngine.ini.")
                        self.mods_view.write_log("Project auto-configured: Enabled Python Remote Execution.", "success")
                        
                # Auto-heal project packaging settings (DefaultGame.ini)
                if reqs.get("needs_cooking_setup"):
                    from utils.plugins.installer import enable_cooking_settings
                    success, msg = enable_cooking_settings(uproject_path)
                    if success:
                        print("Auto-configured project cooking packaging settings in DefaultGame.ini.")
                        self.mods_view.write_log("Project auto-configured: Updated Packaging Settings.", "success")
            except Exception as e:
                print(f"Warning during project auto-configuration: {e}")

    def check_multiple_blenders(self):
        blender_path = self.settings.get("blender")
        if hasattr(self, "blender_versions") and len(self.blender_versions) > 1 and (not blender_path or blender_path == "blender"):
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Multiple Blender Versions Detected")
            msg_box.setText("Please select the Blender version to use:")
            msg_box.setStyleSheet(f"QLabel {{ color : {Theme.TEXT_MAIN}; }}")  # <--- UPDATED
            
            buttons = {}
            for v in self.blender_versions:
                btn = msg_box.addButton(v, QMessageBox.ButtonRole.ActionRole)
                buttons[btn] = v
            
            msg_box.exec()
            clicked_button = msg_box.clickedButton()
            if clicked_button in buttons:
                selected = buttons[clicked_button]
                self.settings["blender"] = selected
                save_settings(self.settings)
                self.settings_view.update_settings(self.settings)

    def closeEvent(self, event):
        save_settings(self.settings)
        super().closeEvent(event)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()