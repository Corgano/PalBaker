from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFrame, QScrollArea
from PyQt6.QtCore import Qt
from utils.theme import Theme

class TraitsSection(QWidget):
    def __init__(self, traits_db: dict, parent=None):
        super().__init__(parent)
        self.traits_db = traits_db
        self.temp_req_traits = []
        self.temp_pref_traits = []

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel("Required & Preferred Passive Traits")
        title.setStyleSheet(f"font-weight: bold; color: white;")
        layout.addWidget(title)

        self.selected_tags_layout = QHBoxLayout()
        self.selected_tags_layout.setSpacing(5)
        self.selected_tags_widget = QWidget()
        self.selected_tags_widget.setLayout(self.selected_tags_layout)
        layout.addWidget(self.selected_tags_widget)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Fuzzy Search Passive Traits...")
        self.search_input.textChanged.connect(self.on_search_changed)
        layout.addWidget(self.search_input)

        self.results_area = QScrollArea()
        self.results_area.setWidgetResizable(True)
        self.results_area.setMaximumHeight(150)
        self.results_widget = QWidget()
        self.results_layout = QVBoxLayout(self.results_widget)
        self.results_area.setWidget(self.results_widget)
        self.results_area.setVisible(False)
        layout.addWidget(self.results_area)

    def populate(self, variant_data: dict, is_base: bool):
        self.setVisible(not is_base)
        if is_base:
            return
        self.temp_req_traits = list(variant_data.get("ReqTrait", []))
        self.temp_pref_traits = list(variant_data.get("PrefTrait", []))
        self.search_input.clear()
        self.results_area.setVisible(False)
        self.refresh_selected_tags()
        self.refresh_search_results("")

    def refresh_selected_tags(self):
        while self.selected_tags_layout.count():
            w = self.selected_tags_layout.takeAt(0).widget()
            if w: w.deleteLater()

        for trait_id in self.temp_req_traits:
            game_name = next((g for g, i in self.traits_db.items() if i == trait_id), trait_id)
            tag = QPushButton(f"Req: {game_name}  ✕")
            tag.setStyleSheet(f"background-color: #1b5e20; color: white; border-radius: 4px; padding: 2px 6px; font-size: 10px;")
            tag.clicked.connect(lambda checked, tid=trait_id: self.remove_trait(tid, "req"))
            self.selected_tags_layout.addWidget(tag)

        for trait_id in self.temp_pref_traits:
            game_name = next((g for g, i in self.traits_db.items() if i == trait_id), trait_id)
            tag = QPushButton(f"Pref: {game_name}  ✕")
            tag.setStyleSheet(f"background-color: #4a148c; color: white; border-radius: 4px; padding: 2px 6px; font-size: 10px;")
            tag.clicked.connect(lambda checked, tid=trait_id: self.remove_trait(tid, "pref"))
            self.selected_tags_layout.addWidget(tag)

    def remove_trait(self, trait_id: str, list_type: str):
        if list_type == "req":
            if trait_id in self.temp_req_traits:
                self.temp_req_traits.remove(trait_id)
        else:
            if trait_id in self.temp_pref_traits:
                self.temp_pref_traits.remove(trait_id)
        self.refresh_selected_tags()
        self.refresh_search_results(self.search_input.text())

    def on_search_changed(self, text: str):
        self.results_area.setVisible(bool(text.strip()) or True)
        self.refresh_search_results(text)

    def refresh_search_results(self, query: str):
        while self.results_layout.count():
            w = self.results_layout.takeAt(0).widget()
            if w: w.deleteLater()

        query = query.strip().lower()
        matches = 0
        for game_name, internal_id in self.traits_db.items():
            if not query or (query in game_name.lower() or query in internal_id.lower()):
                if internal_id in self.temp_req_traits or internal_id in self.temp_pref_traits:
                    continue
                row = QHBoxLayout()
                row.addWidget(QLabel(f"{game_name} ({internal_id})"))
                req_btn = QPushButton("Add Req")
                req_btn.setStyleSheet(f"color: #81c784;")
                req_btn.clicked.connect(lambda checked, tid=internal_id: self.add_trait(tid, "req"))
                pref_btn = QPushButton("Add Pref")
                pref_btn.setStyleSheet(f"color: #ce93d8;")
                pref_btn.clicked.connect(lambda checked, tid=internal_id: self.add_trait(tid, "pref"))
                row.addWidget(req_btn)
                row.addWidget(pref_btn)
                container = QWidget()
                container.setLayout(row)
                self.results_layout.addWidget(container)
                matches += 1

        if matches == 0:
            self.results_layout.addWidget(QLabel("No matching traits found."))

    def add_trait(self, trait_id: str, list_type: str):
        if list_type == "req":
            self.temp_req_traits.append(trait_id)
        else:
            self.temp_pref_traits.append(trait_id)
        self.search_input.clear()
        self.refresh_search_results("")
        self.refresh_selected_tags()

    def get_values(self) -> tuple[list[str], list[str]]:
        return list(self.temp_req_traits), list(self.temp_pref_traits)
