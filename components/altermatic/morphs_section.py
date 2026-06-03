import os
import json
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSlider, QScrollArea, QFrame
from PyQt6.QtCore import Qt

class MorphsSection(QWidget):
    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.active_morph_states = {}

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel("Dynamic Morph Target Parameters")
        title.setStyleSheet("font-weight: bold; color: white;")
        layout.addWidget(title)

        self.morphs_scroll = QScrollArea()
        self.morphs_scroll.setWidgetResizable(True)
        self.morphs_widget = QWidget()
        self.morphs_layout = QVBoxLayout(self.morphs_widget)
        self.morphs_scroll.setWidget(self.morphs_widget)
        layout.addWidget(self.morphs_scroll)

    def get_morph_targets_for_skeleton(self, u_project_dir: str, character_id: str, source: str) -> list[str]:
        if source == "base":
            sidecar_path = os.path.join(u_project_dir, "Content", "Pal", "Model", "Character", "Monster", character_id, f"{character_id}_blend.json")
        else:
            sidecar_name = f"{os.path.splitext(source)[0]}_blend.json"
            sidecar_path = os.path.join(
                os.path.dirname(u_project_dir), "Palbaker", "Model", "Character", "Monster", character_id, sidecar_name
            ) if "Palbaker" not in source else os.path.join(u_project_dir, "Palbaker", "Model", "Character", "Monster", character_id, sidecar_name)

        if os.path.exists(sidecar_path):
            try:
                with open(sidecar_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    morphs = [m["Target"] for m in data.get("MorphTarget", []) if "Target" in m]
                    if morphs:
                        return morphs
            except Exception:
                pass
        return ["breast_size", "belly_fat", "waist_width", "height_scale"]

    def populate(self, character_id: str, selected_source: str, preloaded_morphs: list, is_base: bool):
        self.setVisible(not is_base)
        if is_base:
            return

        while self.morphs_layout.count():
            w = self.morphs_layout.takeAt(0).widget()
            if w: w.deleteLater()
        self.active_morph_states.clear()

        u_project_dir = os.path.dirname(self.settings.get("uproject", ""))
        morph_names = self.get_morph_targets_for_skeleton(u_project_dir, character_id, selected_source)

        preload_map = {}
        if preloaded_morphs:
            for item in preloaded_morphs:
                preload_map[item["Target"]] = item

        for name in morph_names:
            card = QFrame()
            card.setStyleSheet("background-color: #1a1a2e; border: 1px solid #333; border-radius: 6px; padding: 8px;")
            card_layout = QVBoxLayout(card)

            header = QHBoxLayout()
            header.addWidget(QLabel(name))
            mode_combo = QComboBox()
            mode_combo.addItems(["Ignore", "Static (Set)", "Random (Range)"])
            preload_data = preload_map.get(name)
            initial_mode = 0
            if preload_data:
                if "Set" in preload_data:
                    initial_mode = 1
                elif "Min" in preload_data or "Max" in preload_data:
                    initial_mode = 2
            mode_combo.setCurrentIndex(initial_mode)
            header.addWidget(mode_combo)
            card_layout.addLayout(header)

            options_widget = QWidget()
            options_layout = QVBoxLayout(options_widget)
            card_layout.addWidget(options_widget)

            state_key = name
            if state_key not in self.active_morph_states:
                self.active_morph_states[state_key] = {
                    "mode": ["None", "Static", "Random"][initial_mode],
                    "set_val": 0.5, "min_val": 0.0, "max_val": 1.0, "type_val": "Free"
                }

            if preload_data:
                if "Set" in preload_data:
                    self.active_morph_states[state_key]["set_val"] = float(preload_data["Set"])
                elif "Min" in preload_data or "Max" in preload_data:
                    self.active_morph_states[state_key]["min_val"] = float(preload_data.get("Min", 0.0))
                    self.active_morph_states[state_key]["max_val"] = float(preload_data.get("Max", 1.0))
                    self.active_morph_states[state_key]["type_val"] = preload_data.get("Type", "Free")

            def update_mode(combo, sname=state_key, ow=options_widget):
                idx = combo.currentIndex()
                mode = ["None", "Static", "Random"][idx]
                self.active_morph_states[sname]["mode"] = mode
                self.update_options_widget(ow, sname)

            mode_combo.currentIndexChanged.connect(lambda idx, c=mode_combo, s=state_key, ow=options_widget: update_mode(c, s, ow))
            self.update_options_widget(options_widget, state_key)
            self.morphs_layout.addWidget(card)

    def update_options_widget(self, widget, state_key):
        while widget.layout().count():
            w = widget.layout().takeAt(0).widget()
            if w: w.deleteLater()
        state = self.active_morph_states.get(state_key, {})
        mode = state.get("mode", "None")

        if mode == "Static":
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(int(state.get("set_val", 0.5) * 100))
            slider.valueChanged.connect(lambda v: self.active_morph_states[state_key].__setitem__("set_val", v / 100.0))
            lbl = QLabel(f"Set: {state.get('set_val', 0.5):.2f}")
            slider.valueChanged.connect(lambda v: lbl.setText(f"Set: {v / 100:.2f}"))
            widget.layout().addWidget(lbl)
            widget.layout().addWidget(slider)
        elif mode == "Random":
            min_slider = QSlider(Qt.Orientation.Horizontal)
            min_slider.setRange(0, 100)
            min_slider.setValue(int(state.get("min_val", 0.0) * 100))
            min_slider.valueChanged.connect(lambda v: self.active_morph_states[state_key].__setitem__("min_val", v / 100.0))
            max_slider = QSlider(Qt.Orientation.Horizontal)
            max_slider.setRange(0, 100)
            max_slider.setValue(int(state.get("max_val", 1.0) * 100))
            max_slider.valueChanged.connect(lambda v: self.active_morph_states[state_key].__setitem__("max_val", v / 100.0))
            widget.layout().addWidget(QLabel(f"Min: {state.get('min_val', 0.0):.2f}"))
            widget.layout().addWidget(min_slider)
            widget.layout().addWidget(QLabel(f"Max: {state.get('max_val', 1.0):.2f}"))
            widget.layout().addWidget(max_slider)

    def get_values(self) -> list[dict]:
        morphs = []
        for name, state in self.active_morph_states.items():
            if state["mode"] == "Static":
                morphs.append({"Target": name, "Set": state["set_val"]})
            elif state["mode"] == "Random":
                morphs.append({"Target": name, "Min": state["min_val"], "Max": state["max_val"], "Type": state["type_val"]})
        return morphs
