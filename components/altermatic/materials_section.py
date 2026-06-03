import os
import json
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QScrollArea
from PyQt6.QtCore import Qt

DEFAULT_SLOTS_MAP = {
    "WeaselDragon": ["mi_weaseldragon_body", "mi_weaseldragon_eye", "mi_weaseldragon_mouth"],
    "Cattiva": ["mi_cattiva_body", "mi_cattiva_eye"]
}

class MaterialsSection(QWidget):
    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.active_material_dropdowns = {}

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel("Visual Material Overrides (MatReplace)")
        title.setStyleSheet("font-weight: bold; color: white;")
        layout.addWidget(title)

        self.materials_scroll = QScrollArea()
        self.materials_scroll.setWidgetResizable(True)
        self.materials_widget = QWidget()
        self.materials_layout = QVBoxLayout(self.materials_widget)
        self.materials_scroll.setWidget(self.materials_widget)
        layout.addWidget(self.materials_scroll)

    def get_slots_for_skeleton(self, u_project_dir: str, character_id: str, source: str, fmodel_altermatic_dir: str = "") -> list[str]:
        if source == "base":
            sidecar_path = os.path.join(u_project_dir, "Content", "Pal", "Model", "Character", "Monster", character_id, f"{character_id}_blend.json")
        else:
            sidecar_name = f"{os.path.splitext(source)[0]}_blend.json"
            sidecar_path = os.path.join(fmodel_altermatic_dir if fmodel_altermatic_dir else u_project_dir, sidecar_name)

        if os.path.exists(sidecar_path):
            try:
                with open(sidecar_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    mats = data.get("materials", {})
                    if mats:
                        return list(mats.keys())
            except Exception:
                pass
        return DEFAULT_SLOTS_MAP.get(character_id, ["mi_body", "mi_eye"])

    def populate(self, character_id: str, selected_source: str, variant_data: dict | None, available_mats: list[str], is_base: bool, fmodel_altermatic_dir: str = ""):
        self.setVisible(not is_base)
        if is_base:
            return

        while self.materials_layout.count():
            w = self.materials_layout.takeAt(0).widget()
            if w: w.deleteLater()

        self.active_material_dropdowns.clear()

        u_project_dir = os.path.dirname(self.settings.get("uproject", ""))
        slots = self.get_slots_for_skeleton(u_project_dir, character_id, selected_source, fmodel_altermatic_dir)

        preloaded_overrides_dict = {}
        if variant_data:
            mat_overrides = variant_data.get("MaterialOverrides", {})
            if isinstance(mat_overrides, dict):
                for k, v in mat_overrides.items():
                    preloaded_overrides_dict[k.lower()] = v
            mat_replaces = variant_data.get("MatReplace", [])
            if isinstance(mat_replaces, list):
                for item in mat_replaces:
                    idx = item.get("Index")
                    mat_path = item.get("MatPath", "")
                    if idx is not None and mat_path:
                        try:
                            idx_int = int(idx)
                            if 0 <= idx_int < len(slots):
                                slot_name = slots[idx_int]
                                mat_name = mat_path.split("/")[-1]
                                preloaded_overrides_dict[slot_name.lower()] = mat_name
                        except (ValueError, TypeError):
                            pass

        for idx, slot_name in enumerate(slots):
            row = QHBoxLayout()
            row.addWidget(QLabel(f"Slot {idx} ({slot_name}):"))

            combo = QComboBox()
            combo.addItem("Default (No Override)", "default")
            for mat in available_mats:
                combo.addItem(mat, mat)

            slot_key = slot_name.lower()
            if slot_key in preloaded_overrides_dict:
                val = preloaded_overrides_dict[slot_key]
                ci = combo.findText(val)
                if ci >= 0:
                    combo.setCurrentIndex(ci)

            self.active_material_dropdowns[idx] = combo
            row.addWidget(combo, 1)
            container = QWidget()
            container.setLayout(row)
            self.materials_layout.addWidget(container)

    def get_values(self, character_id: str, selected_source: str, fmodel_altermatic_dir: str = "") -> list[dict]:
        mat_replaces = []
        u_project_dir = os.path.dirname(self.settings.get("uproject", ""))
        slots = self.get_slots_for_skeleton(u_project_dir, character_id, selected_source, fmodel_altermatic_dir)

        for idx, combo in self.active_material_dropdowns.items():
            if combo.currentData() and combo.currentData() != "default":
                mat_path = f"/Game/Palbaker/Model/Character/Monster/{character_id}/{combo.currentData()}"
                mat_replaces.append({
                    "Index": str(idx), "MatPath": mat_path, "SlotName": slots[idx]
                })
        return mat_replaces
