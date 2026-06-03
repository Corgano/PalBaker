from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QCheckBox, QPushButton
from PyQt6.QtCore import Qt
from utils.theme import Theme

class GeneralSection(QWidget):
    def __init__(self, on_open_blend=None, on_refresh_layout=None):
        super().__init__()
        self.on_open_blend = on_open_blend
        self.on_refresh_layout = on_refresh_layout

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        self.label_input = QLineEdit()
        self.label_input.setPlaceholderText("e.g., SFW_Bikini_T-Shirt")
        layout.addWidget(QLabel("Variant Label/Name:"))
        layout.addWidget(self.label_input)

        self.char_id_input = QLineEdit()
        self.char_id_input.setEnabled(False)
        layout.addWidget(QLabel("Character ID (Locked):"))
        layout.addWidget(self.char_id_input)

        skel_row = QHBoxLayout()
        self.skeleton_combo = QComboBox()
        self.skeleton_combo.currentIndexChanged.connect(self.on_skeleton_changed)
        skel_row.addWidget(QLabel("Skeleton / Mesh Source:"), 0)
        skel_row.addWidget(self.skeleton_combo, 1)

        if self.on_open_blend:
            open_btn = QPushButton("Open in Blender")
            open_btn.clicked.connect(self.on_open_blend)
            skel_row.addWidget(open_btn, 0)

        if self.on_refresh_layout:
            refresh_btn = QPushButton("Sync Layout")
            refresh_btn.clicked.connect(self.on_refresh_layout)
            skel_row.addWidget(refresh_btn, 0)

        layout.addLayout(skel_row)

        gender_row = QHBoxLayout()
        gender_row.addWidget(QLabel("Gender:"))
        self.gender_combo = QComboBox()
        for g in ["None", "Male", "Female", "Futa", "FullFuta", "Andro", "Neutered"]:
            self.gender_combo.addItem(g)
        gender_row.addWidget(self.gender_combo)
        self.is_rare_check = QCheckBox("Is Rare/Lucky Pal")
        gender_row.addWidget(self.is_rare_check)
        gender_row.addStretch()
        layout.addLayout(gender_row)

        self.skin_name_input = QLineEdit()
        self.skin_name_input.setPlaceholderText("e.g., WeaselDragon_Skin001")
        layout.addWidget(QLabel("Target Skin Override Name (Optional):"))
        layout.addWidget(self.skin_name_input)

    def on_skeleton_changed(self, index):
        pass

    def populate(self, character_id: str, blend_files: list[str], variant_data: dict, is_base: bool):
        self.char_id_input.setText(character_id)
        self.label_input.setEnabled(not is_base)

        self.skeleton_combo.clear()
        self.skeleton_combo.addItem("base (Vanilla Canonical Mesh)", "base")
        for f in blend_files:
            clean_lbl = f
            prefix = f"{character_id}_"
            if clean_lbl.startswith(prefix):
                clean_lbl = clean_lbl[len(prefix):]
            self.skeleton_combo.addItem(f"Blender: {clean_lbl}", f)

        gender_widget = self.gender_combo.parent() if self.gender_combo.parent() else None
        if gender_widget:
            gender_widget.setVisible(not is_base)
        self.is_rare_check.setVisible(not is_base)
        self.skin_name_input.setVisible(not is_base)

        if is_base:
            self.label_input.setText("base")
            idx = self.skeleton_combo.findData(variant_data.get("SkeletonSource", "base"))
            if idx >= 0: self.skeleton_combo.setCurrentIndex(idx)
        else:
            raw_label = variant_data.get("label", "")
            prefix = f"{character_id}_"
            if raw_label.startswith(prefix):
                raw_label = raw_label[len(prefix):]
            self.label_input.setText(raw_label)
            idx = self.skeleton_combo.findData(variant_data.get("SkeletonSource", "base"))
            if idx >= 0: self.skeleton_combo.setCurrentIndex(idx)
            gender_idx = self.gender_combo.findText(variant_data.get("Gender", "None"))
            if gender_idx >= 0: self.gender_combo.setCurrentIndex(gender_idx)
            self.is_rare_check.setChecked(bool(variant_data.get("IsRarePal", False)))
            self.skin_name_input.setText(variant_data.get("SkinName", ""))

    def get_values(self) -> dict:
        return {
            "label": self.label_input.text().strip(),
            "SkeletonSource": self.skeleton_combo.currentData(),
            "Gender": self.gender_combo.currentText(),
            "IsRarePal": self.is_rare_check.isChecked(),
            "SkinName": self.skin_name_input.text().strip()
        }
