import os
import subprocess
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QWidget, QMessageBox
from PyQt6.QtCore import Qt
from utils.theme import Theme
from components.altermatic.general_section import GeneralSection
from components.altermatic.traits_section import TraitsSection
from components.altermatic.materials_section import MaterialsSection
from components.altermatic.morphs_section import MorphsSection

class AltermaticDialog(QDialog):
    def __init__(self, parent, settings: dict, traits_db: dict, on_save_callback, on_refresh_callback, on_delete_callback):
        super().__init__(parent)
        self.settings = settings
        self.traits_db = traits_db
        self.on_save_callback = on_save_callback
        self.on_refresh_callback = on_refresh_callback
        self.on_delete_callback = on_delete_callback
        self.main_page = parent

        self.current_character_id = ""
        self.editing_index = -1
        self.is_base = False
        self.available_mats = []

        self.setWindowTitle("Visual Altermatic Configurator")
        self.setModal(True)
        self.resize(600, 500)
        self.setStyleSheet(Theme.get_dialog_style())

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        self.title_label = QLabel("Configurator")
        self.title_label.setStyleSheet(f"font-size: {Theme.FONT_SIZE_TITLE}; font-weight: bold; color: white;")
        layout.addWidget(self.title_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(15)

        self.general_section = GeneralSection(
            on_open_blend=self.handle_open_blend_click,
            on_refresh_layout=self.handle_refresh_layout_click
        )
        scroll_layout.addWidget(self.general_section)

        self.traits_section = TraitsSection(traits_db=traits_db)
        scroll_layout.addWidget(self.traits_section)

        self.materials_section = MaterialsSection(settings=settings)
        scroll_layout.addWidget(self.materials_section)

        self.morphs_section = MorphsSection(settings=settings)
        scroll_layout.addWidget(self.morphs_section)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        btn_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setStyleSheet(f"background-color: {Theme.ERROR}; color: white; font-weight: bold;")
        self.delete_btn.clicked.connect(self.handle_delete_click)
        btn_layout.addWidget(self.delete_btn)

        btn_layout.addStretch()

        self.apply_btn = QPushButton("Apply Changes")
        self.apply_btn.setStyleSheet(f"background-color: {Theme.PRIMARY}; color: white; font-weight: bold;")
        self.apply_btn.clicked.connect(self.save_variant)
        btn_layout.addWidget(self.apply_btn)

        layout.addLayout(btn_layout)

    def show(self, character_id: str, index: int, variant_data: dict, blend_files: list[str], available_mats: list[str]):
        self.editing_index = index
        self.current_character_id = character_id
        self.available_mats = available_mats
        self.is_base = variant_data.get("is_base", False)

        self.general_section.populate(character_id, blend_files, variant_data, self.is_base)
        self.traits_section.populate(variant_data, self.is_base)

        selected_source = self.general_section.skeleton_combo.currentData()
        fmodel_root = self.settings.get("fmodel_output", "")
        fmodel_altermatic_dir = os.path.join(fmodel_root, "Exports", "Pal", "Content", "Palbaker", "Model", "Character", "Monster", character_id) if fmodel_root else ""

        self.materials_section.populate(character_id, selected_source, variant_data, available_mats, self.is_base, fmodel_altermatic_dir)
        self.morphs_section.populate(character_id, selected_source, variant_data.get("MorphTarget", []), self.is_base)

        self.delete_btn.setVisible(not self.is_base)

        clean_title = variant_data["label"]
        prefix = f"{character_id}_"
        if clean_title.startswith(prefix):
            clean_title = clean_title[len(prefix):]
        self.title_label.setText(f"Configurator: {clean_title}")

        self.exec()

    def handle_open_blend_click(self):
        source = self.general_section.skeleton_combo.currentData()
        if not source:
            return

        fmodel_root = self.settings.get("fmodel_output", "")
        if not fmodel_root:
            return

        if source == "base":
            blend_path = os.path.normpath(os.path.join(fmodel_root, "Exports", "Pal", "Content", "Pal", "Model", "Character", "Monster", self.current_character_id, f"{self.current_character_id}.blend"))
        else:
            blend_path = os.path.normpath(os.path.join(fmodel_root, "Exports", "Pal", "Content", "Palbaker", "Model", "Character", "Monster", self.current_character_id, source))

        blender_exe = self.settings.get("blender")
        if os.path.exists(blend_path) and blender_exe and os.path.exists(blender_exe):
            try:
                subprocess.Popen([blender_exe, blend_path])
            except Exception as err:
                print(f"Failed to launch Blender: {err}", flush=True)

    def handle_refresh_layout_click(self):
        self.accept()
        self.on_refresh_callback(self.current_character_id)

    def handle_delete_click(self):
        result = QMessageBox.question(self, "Confirm Deletion",
            f"Are you sure you want to delete this variant?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if result == QMessageBox.StandardButton.Yes:
            self.accept()
            self.on_delete_callback(self.current_character_id, self.editing_index)

    def save_variant(self):
        general_values = self.general_section.get_values()
        if not general_values["label"] or not general_values["SkeletonSource"]:
            return

        req_traits, pref_traits = self.traits_section.get_values()

        fmodel_root = self.settings.get("fmodel_output", "")
        fmodel_altermatic_dir = os.path.join(fmodel_root, "Exports", "Pal", "Content", "Palbaker", "Model", "Character", "Monster", self.current_character_id) if fmodel_root else ""
        selected_source = self.general_section.skeleton_combo.currentData()

        mat_replaces = self.materials_section.get_values(self.current_character_id, selected_source, fmodel_altermatic_dir)
        morphs = self.morphs_section.get_values()

        variant_data = {
            "label": "base" if self.is_base else general_values["label"],
            "CharacterID": self.current_character_id,
            "SkeletonSource": general_values["SkeletonSource"],
            "Gender": general_values["Gender"],
            "IsRarePal": general_values["IsRarePal"],
            "SkinName": general_values["SkinName"],
            "ReqTrait": req_traits,
            "PrefTrait": pref_traits,
            "MatReplace": mat_replaces,
            "MorphTarget": morphs,
            "is_base": self.is_base
        }

        self.accept()
        self.on_save_callback(self.editing_index, variant_data)
