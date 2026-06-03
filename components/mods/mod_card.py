# components/mods/mod_card.py
import os
import sys
import subprocess
import glob
import re
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QProgressBar, QMenu
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction

from components.mods.mod_details import ModDetails
from utils.theme import Theme  # <--- UPDATED

def open_folder(path: str):
    if path and os.path.exists(path):
        if os.name == 'nt':
            os.startfile(path)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', path])
        else:
            subprocess.Popen(['xdg-open', path])

def open_file_in_explorer(file_path: str):
    if not file_path:
        return
    if os.path.exists(file_path):
        if os.name == 'nt':
            subprocess.run(['explorer.exe', f'/select,{os.path.normpath(file_path)}'])
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', '-R', file_path])
        else:
            parent_dir = os.path.dirname(file_path)
            if os.path.exists(parent_dir):
                subprocess.Popen(['xdg-open', parent_dir])

class ModItem(QFrame):
    def __init__(self, mod_data: dict, on_action_click, on_cancel_click, on_pick_icon, on_pick_audio, on_play_audio, on_clear_audio, is_building: bool, show_mapped: bool):
        super().__init__()
        self.mod_data = mod_data
        self.on_action_click = on_action_click
        self.on_cancel_click = on_cancel_click
        self.on_pick_icon = on_pick_icon
        self.on_pick_audio = on_pick_audio
        self.on_play_audio = on_play_audio
        self.on_clear_audio = on_clear_audio
        self.is_building = is_building
        self.show_mapped = show_mapped

        self.import_total_steps = 1
        self.import_current_step = 0

        self.setObjectName("ModItemCard")
        self.update_card_styles(Theme.BORDER_COLOR)  # <--- UPDATED

        card_layout = QVBoxLayout(self)
        card_layout.setContentsMargins(10, 10, 10, 10)
        card_layout.setSpacing(5)

        # --- MAIN ROW ---
        self.main_row_layout = QHBoxLayout()
        self.main_row_layout.setSpacing(10)

        # Chevron toggle
        self.details_visible = False
        self.chevron = QPushButton("▼")
        self.chevron.setFixedSize(24, 24)
        self.chevron.setStyleSheet("border: none; color: #b3b3b3; font-weight: bold; background: transparent;")
        self.chevron.clicked.connect(self.toggle_details)
        self.main_row_layout.addWidget(self.chevron)

        folder_icon = QLabel("📁")
        folder_icon.setStyleSheet("color: #90caf9; font-size: 16px;")
        self.main_row_layout.addWidget(folder_icon)

        # Mod Display Name
        self.name_text = QLabel(self.get_display_name())
        self.name_text.setStyleSheet(f"font-weight: bold; font-size: {Theme.FONT_SIZE_TITLE}; color: white;")  # <--- UPDATED
        self.main_row_layout.addWidget(self.name_text)

        badge_layout = QHBoxLayout()
        badge_layout.setSpacing(5)
        for text, color_hex in mod_data["badges"]:
            tooltip_msg = ""
            if text == "RAW":
                tooltip_msg = "FModel files extracted, but no Blender (.blend) file has been created yet."
            elif text == "SOURCE":
                tooltip_msg = "Blender (.blend) source file detected. Mod is actively being worked on."
            elif text == "UE ASSETS":
                tooltip_msg = "Unreal Engine binaries (.uasset) found in the ModKit project."
            elif text == "MODIFIED":
                tooltip_msg = "Warning: Files have been manually modified inside Unreal Engine since your last Push!"
            elif text == "SRC CHANGED":
                tooltip_msg = "Source files (Blender/textures) have been edited since your last Push! It is recommended to run 'Push & Cook & Pack'."

            badge_lbl = QLabel(text)
            badge_lbl.setToolTip(tooltip_msg)
            badge_lbl.setStyleSheet(f"""
                QLabel {{
                    background-color: {color_hex};
                    color: white;
                    font-size: {Theme.FONT_SIZE_TINY};
                    font-weight: bold;
                    border-radius: {Theme.RADIUS_NORMAL};
                    padding: 2px 6px;
                }}
            """)  # <--- UPDATED
            badge_layout.addWidget(badge_lbl)
        self.main_row_layout.addLayout(badge_layout)

        self.main_row_layout.addStretch(1)

        # Status text label
        status_colors = {
            "Packed": Theme.SUCCESS,
            "Packed with Errors": Theme.WARNING,
            "Outdated": Theme.WARNING,
            "Unpacked": Theme.ERROR
        }  # <--- UPDATED
        color = status_colors.get(mod_data["pak_status"], Theme.ERROR)
        
        status_lbl = QLabel(mod_data["pak_status"])
        status_lbl.setFixedWidth(120)
        status_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        status_lbl.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")
        self.main_row_layout.addWidget(status_lbl)

        # Main Action Button
        self.update_primary_button_config()
        self.primary_button = QPushButton(self.primary_text)
        self.primary_button.setEnabled(not self.is_building and self.primary_action != "none")
        self.primary_button.clicked.connect(self.handle_button_click)
        self.main_row_layout.addWidget(self.primary_button)

        self.overflow_btn = QPushButton("⋮")
        self.overflow_btn.setFixedSize(24, 24)
        self.overflow_btn.setStyleSheet("border: none; color: white; font-size: 16px; background: transparent;")
        self.overflow_btn.clicked.connect(self.show_overflow_menu)
        self.main_row_layout.addWidget(self.overflow_btn)

        card_layout.addLayout(self.main_row_layout)

        # --- PROGRESS CONTAINER ---
        self.progress_container = QFrame()
        self.progress_container.setVisible(False)
        self.progress_container.setStyleSheet("background: transparent; border: none;")
        progress_layout = QVBoxLayout(self.progress_container)
        progress_layout.setContentsMargins(0, 5, 0, 0)
        progress_layout.setSpacing(4)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(f"background-color: {Theme.BORDER_COLOR}; max-height: 1px;")  # <--- UPDATED
        progress_layout.addWidget(div)

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {Theme.BORDER_COLOR};
                border-radius: {Theme.RADIUS_NORMAL};
                text-align: center;
                background-color: {Theme.BG_MAIN};
            }}
            QProgressBar::chunk {{
                background-color: {Theme.CYAN_ACCENT};
            }}
        """)  # <--- UPDATED
        progress_layout.addWidget(self.progress_bar)

        self.status_text = QLabel("Waiting...")
        self.status_text.setStyleSheet(f"font-size: {Theme.FONT_SIZE_SMALL}; color: {Theme.TEXT_MUTED}; font-style: italic;")  # <--- UPDATED
        progress_layout.addWidget(self.status_text)

        card_layout.addWidget(self.progress_container)

        # --- DETAILS CONTAINER ---
        self.details = ModDetails(
            mod_data=mod_data,
            on_pick_icon=on_pick_icon,
            on_pick_audio=on_pick_audio,
            on_play_audio=on_play_audio,
            on_clear_audio=on_clear_audio
        )
        self.details_container = QFrame()
        self.details_container.setVisible(False)
        self.details_container.setStyleSheet("background: transparent; border: none;")
        details_layout = QVBoxLayout(self.details_container)
        details_layout.setContentsMargins(0, 5, 0, 0)
        details_layout.addWidget(self.details)
        
        card_layout.addWidget(self.details_container)
        
        self.view = self

    def update_card_styles(self, border_color):
        self.setStyleSheet(Theme.get_card_style(border_color))  # <--- UPDATED

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet(Theme.get_menu_style())  # <--- UPDATED
        
        open_fmodel = menu.addAction("Open source in file explorer")
        open_fmodel.setEnabled(self.mod_data["has_fmodel"])
        open_fmodel.triggered.connect(lambda: open_folder(self.mod_data["fmodel_path"]))

        open_ue = menu.addAction("Open unreal assets in file explorer")
        open_ue.setEnabled(self.mod_data["has_ue"])
        open_ue.triggered.connect(lambda: open_folder(self.mod_data["ue_path"]))

        open_pak = menu.addAction("Open PAK in file explorer")
        open_pak.setEnabled(self.mod_data.get("pak_status") == "Packed")
        open_pak.triggered.connect(lambda: open_file_in_explorer(self.mod_data.get("pak_path", "")))

        show_unreal = menu.addAction("Show in Unreal Content Browser")
        show_unreal.setEnabled(self.mod_data["has_ue"])
        show_unreal.triggered.connect(lambda: self.on_action_click(self.mod_data, "browse_unreal"))

        menu.exec(event.globalPos())

    def show_overflow_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(Theme.get_menu_style())  # <--- UPDATED

        push = menu.addAction("Push to Unreal")
        push.setEnabled(self.mod_data["has_fmodel"] and self.mod_data.get("has_blend", False))
        push.triggered.connect(lambda: self.on_action_click(self.mod_data, "push"))

        cook = menu.addAction("Cook & Pack (Skip Import)")
        cook.setEnabled(self.mod_data["has_ue"])
        cook.triggered.connect(lambda: self.on_action_click(self.mod_data, "cook"))

        full = menu.addAction("Push & Cook & Pack")
        full.setEnabled(self.mod_data["has_fmodel"] and self.mod_data.get("has_blend", False))
        full.triggered.connect(lambda: self.on_action_click(self.mod_data, "full"))

        decompile = menu.addAction("Generate Sources")
        decompile.setEnabled(self.mod_data["has_ue"])
        decompile.triggered.connect(lambda: self.on_action_click(self.mod_data, "decompile"))

        menu.exec(self.overflow_btn.mapToGlobal(self.overflow_btn.rect().bottomLeft()))

    def toggle_details(self):
        self.details_visible = not self.details_visible
        self.details_container.setVisible(self.details_visible)
        self.chevron.setText("▲" if self.details_visible else "▼")

    def handle_button_click(self):
        if self.is_building:
            if self.on_cancel_click:
                self.on_cancel_click()
        elif self.primary_action == "create_blend":
            self.on_action_click(self.mod_data, "create_blend")
        elif self.primary_action == "open_folder":
            open_folder(self.mod_data["fmodel_path"])
        else:
            self.on_action_click(self.mod_data, self.primary_action)

    def update_primary_button_config(self):
        if self.mod_data["has_ue"]:
            if self.mod_data.get("source_modified", False):
                self.primary_text = "Push & Cook & Pack"
                self.primary_action = "full"
            else:
                self.primary_text = "Cook & Pack"
                self.primary_action = "cook"
        elif self.mod_data["has_fmodel"]:
            if not self.mod_data.get("has_blend", False):
                self.primary_text = "Create .blend file"
                self.primary_action = "create_blend"
            else:
                self.primary_text = "Push to Unreal"
                self.primary_action = "push"
        else:
            self.primary_text = "Unavailable"
            self.primary_action = "none"

    def get_display_name(self) -> str:
        return str(self.mod_data["localized_name"]) if self.show_mapped else str(self.mod_data["name"])

    def set_show_mapped(self, show_mapped: bool):
        self.show_mapped = show_mapped
        self.name_text.setText(self.get_display_name())

    def set_state(self, global_building: bool, is_active_target: bool = False, success: bool | None = None):
        self.is_building = global_building
        self.update_primary_button_config()

        if is_active_target:
            fmodel_path = self.mod_data["fmodel_path"]
            if os.path.exists(fmodel_path):
                pngs = len(glob.glob(os.path.join(fmodel_path, "*.png")))
                jsons = len(glob.glob(os.path.join(fmodel_path, "MI_*.json")))
                fbx = 1 if glob.glob(os.path.join(fmodel_path, "*.fbx")) else 0
                self.import_total_steps = pngs + jsons + fbx + 1
            else:
                self.import_total_steps = 1
            
            self.import_current_step = 0
            self.progress_container.setVisible(True)
            self.progress_bar.setValue(0)
            self.status_text.setText("Starting pipeline...")
            self.update_card_styles("#00c853")

            self.primary_button.setText("Cancel")
            self.primary_button.setEnabled(True)
            self.primary_button.setStyleSheet(f"background-color: {Theme.ERROR}; font-weight: bold; color: white;")  # <--- UPDATED
        else:
            self.progress_container.setVisible(False)
            self.primary_button.setText(self.primary_text)
            self.primary_button.setEnabled(not global_building and self.primary_action != "none")
            self.primary_button.setStyleSheet("")
            
            if success is True:
                self.update_card_styles(Theme.SUCCESS)  # <--- UPDATED
                QTimer.singleShot(2500, lambda: self.update_card_styles(Theme.BORDER_COLOR))
            elif success is False:
                self.update_card_styles(Theme.ERROR)  # <--- UPDATED
                QTimer.singleShot(2500, lambda: self.update_card_styles(Theme.BORDER_COLOR))

    def update_progress(self, line: str, flush: bool = True):
        line = line.strip()
        if not line: return
        
        if "Running headless Blender" in line:
            self.progress_bar.setValue(5)
            self.status_text.setText("[1/4] Running Blender (Exporting FBX)...")
            
        elif "Connecting to Open Unreal Engine" in line:
            self.progress_bar.setValue(15)
            self.status_text.setText("[2/4] Connecting to Unreal Engine...")
            
        elif "Importing texture:" in line or "Importing skeletal mesh:" in line or "Creating material instance:" in line or "Linking Materials" in line:
            self.import_current_step += 1
            progress = 0.15 + (0.30 * (self.import_current_step / max(1, self.import_total_steps)))
            self.progress_bar.setValue(int(min(0.45, progress) * 100))
            self.status_text.setText(f"[2/4] Importing Assets into Unreal ({self.import_current_step}/{self.import_total_steps})...")
            
        elif "Cooking Target Folders" in line:
            self.progress_bar.setValue(45)
            self.status_text.setText("[3/4] Preparing to Cook Assets...")
            
        elif "LogCook: Display: Cooked packages" in line:
            match = re.search(r"Cooked packages (\d+) Packages Remain (\d+)", line)
            if match:
                cooked = int(match.group(1))
                remain = int(match.group(2))
                total = cooked + remain
                if total > 0:
                    sub_progress = cooked / total
                    progress_value = 0.45 + (0.45 * sub_progress)
                    self.progress_bar.setValue(int(progress_value * 100))
                    self.status_text.setText(f"[3/4] Cooking Assets ({cooked}/{total} packages)...")
                    
        elif "Preparing Pak" in line:
            self.progress_bar.setValue(90)
            self.status_text.setText("[4/4] Packing Cooked Assets...")
            
        elif "Building final PAK" in line:
            self.progress_bar.setValue(95)
            self.status_text.setText("[4/4] Generating .pak file...")