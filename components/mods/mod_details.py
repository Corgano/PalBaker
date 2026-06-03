# components/mods/mod_details.py
import asyncio
import os
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFrame, QGridLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from utils.theme import Theme  # <--- UPDATED

def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(coro)
        else:
            loop.run_until_complete(coro)
    except Exception:
        asyncio.run(coro)

class ModDetails(QWidget):
    def __init__(self, mod_data: dict, on_pick_icon, on_pick_audio, on_play_audio, on_clear_audio, on_toggle_altermatic=None, on_add_variant=None, on_edit_variant=None, on_delete_variant=None):
        super().__init__()
        self.mod_data = mod_data
        self.on_pick_icon = on_pick_icon
        self.on_pick_audio = on_pick_audio
        self.on_play_audio = on_play_audio
        self.on_clear_audio = on_clear_audio
        self.on_toggle_altermatic = on_toggle_altermatic
        self.on_add_variant = on_add_variant
        self.on_edit_variant = on_edit_variant
        self.on_delete_variant = on_delete_variant

        self.setStyleSheet(Theme.get_details_style())  # <--- UPDATED

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(20)

        # --- LEFT: ICON SLOT ---
        icon_section = QVBoxLayout()
        icon_section.setSpacing(5)
        
        icon_title = QLabel("Pal Icon")
        icon_title.setStyleSheet(f"font-size: {Theme.FONT_SIZE_SMALL}; font-weight: bold; color: white;")  # <--- UPDATED
        icon_section.addWidget(icon_title)

        has_icon = mod_data.get("has_icon", False)
        icon_path = mod_data.get("icon_path", "")

        self.icon_btn = QPushButton()
        self.icon_btn.setFixedSize(64, 64)
        self.icon_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.BG_MAIN};
                border: 1px solid {Theme.BORDER_COLOR};
                border-radius: {Theme.RADIUS_LARGE};
            }}
            QPushButton:hover {{
                border: 1px solid {Theme.PRIMARY};
            }}
        """)  # <--- UPDATED
        self.icon_btn.clicked.connect(self.handle_icon_click)
        
        if has_icon and icon_path and os.path.exists(icon_path):
            pixmap = QPixmap(icon_path).scaled(56, 56, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            from PyQt6.QtGui import QIcon
            self.icon_btn.setIcon(QIcon(pixmap))
            self.icon_btn.setIconSize(pixmap.size())
        else:
            self.icon_btn.setText("+")
            self.icon_btn.setStyleSheet(self.icon_btn.styleSheet() + f" color: {Theme.TEXT_MUTED}; font-size: 20px; font-weight: bold;")  # <--- UPDATED
            
        icon_section.addWidget(self.icon_btn)
        icon_section.addStretch()
        layout.addLayout(icon_section, 0)

        # Vertical Divider Separator
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.VLine)
        divider.setStyleSheet(f"background-color: {Theme.BORDER_COLOR}; max-width: 1px;")  # <--- UPDATED
        layout.addWidget(divider, 0)

        # --- RIGHT: AUDIO CUSTOMIZATION ---
        audio_section_layout = QVBoxLayout()
        audio_section_layout.setSpacing(5)
        
        has_fmodel = mod_data.get("has_fmodel", False)
        sound_meta = mod_data.get("sound_metadata", {})

        if not has_fmodel:
            lbl = QLabel(
                "Audio replacement requires raw FModel files.\n"
                "Please click 'Create .blend file' or 'Generate Sources' first."
            )
            lbl.setStyleSheet(f"color: #666666; font-style: italic; font-size: {Theme.FONT_SIZE_SMALL};")  # <--- UPDATED
            audio_section_layout.addWidget(lbl)
        elif not sound_meta:
            lbl = QLabel("No mapped database found for this Pal.")
            lbl.setStyleSheet(f"color: #666666; font-style: italic; font-size: {Theme.FONT_SIZE_SMALL};")  # <--- UPDATED
            audio_section_layout.addWidget(lbl)
        else:
            audio_title = QLabel("Custom Pal Cries (.wav, .mp3, .ogg)")
            audio_title.setStyleSheet(f"font-size: {Theme.FONT_SIZE_SMALL}; font-weight: bold; color: white;")  # <--- UPDATED
            audio_section_layout.addWidget(audio_title)

            grid = QGridLayout()
            grid.setSpacing(8)
            
            audio_overrides = mod_data.get("audio_overrides", {})
            available_cries = [c for c in ["Normal", "Joy", "Anger", "Sorrow", "Pain", "Death"] if c in sound_meta]

            for i, cry_name in enumerate(available_cries):
                is_set = audio_overrides.get(cry_name) is not None
                color_css = f"color: {Theme.SUCCESS};" if is_set else "color: #555555;"  # <--- UPDATED
                status_text = "Custom Override" if is_set else "Original Game Sound"

                row_frame = QFrame()
                row_frame.setStyleSheet(f"""
                    QFrame {{
                        background-color: {"#161616" if is_set else "transparent"};
                        border: 1px solid {Theme.BORDER_COLOR};
                        border-radius: {Theme.RADIUS_MEDIUM};
                    }}
                """)  # <--- UPDATED
                row_layout = QHBoxLayout(row_frame)
                row_layout.setContentsMargins(5, 5, 5, 5)
                row_layout.setSpacing(5)

                play_btn = QPushButton("▶")
                play_btn.setFixedSize(24, 24)
                play_btn.setStyleSheet(f"color: {Theme.CYAN_ACCENT}; font-weight: bold; border: none; background: transparent;")  # <--- UPDATED
                play_btn.clicked.connect(lambda _, c=cry_name: self.handle_play_click(c))
                
                txt_layout = QVBoxLayout()
                txt_layout.setSpacing(1)
                txt_layout.setContentsMargins(0, 0, 0, 0)
                
                cry_lbl = QLabel(cry_name)
                cry_lbl.setStyleSheet(f"font-size: {Theme.FONT_SIZE_SMALL}; font-weight: bold; color: white;")  # <--- UPDATED
                
                status_lbl = QLabel(status_text)
                status_lbl.setStyleSheet(f"font-size: {Theme.FONT_SIZE_TINY}; {color_css}")  # <--- UPDATED
                
                txt_layout.addWidget(cry_lbl)
                txt_layout.addWidget(status_lbl)

                upload_btn = QPushButton("⇡")
                upload_btn.setFixedSize(24, 24)
                upload_btn.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-weight: bold; border: none; background: transparent;")  # <--- UPDATED
                upload_btn.clicked.connect(lambda _, c=cry_name: self.handle_upload_click(c))

                clear_btn = QPushButton("🗑")
                clear_btn.setFixedSize(24, 24)
                clear_btn.setStyleSheet(f"color: {Theme.ERROR}; font-weight: bold; border: none; background: transparent;")  # <--- UPDATED
                clear_btn.clicked.connect(lambda _, c=cry_name: self.handle_clear_click(c))
                clear_btn.setVisible(is_set)

                row_layout.addWidget(play_btn)
                row_layout.addLayout(txt_layout, 1)
                row_layout.addWidget(upload_btn)
                row_layout.addWidget(clear_btn)

                grid.addWidget(row_frame, i // 2, i % 2)

            audio_section_layout.addLayout(grid)
            
        audio_section_layout.addStretch()
        layout.addLayout(audio_section_layout, 1)

        # --- LEFT-CENTER: ALTERMATIC SECTION ---
        altermatic_section = QVBoxLayout()
        altermatic_section.setSpacing(5)

        alt_title = QLabel("Altermatic Variants")
        alt_title.setStyleSheet(f"font-size: {Theme.FONT_SIZE_SMALL}; font-weight: bold; color: white;")
        altermatic_section.addWidget(alt_title)

        is_active = mod_data.get("is_altermatic_active", False)
        self.altermatic_toggle_btn = QPushButton("Disable Altermatic" if is_active else "Enable Altermatic")
        self.altermatic_toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {"#9c27b0" if is_active else Theme.BG_SURFACE};
                color: white;
                font-weight: bold;
                border-radius: {Theme.RADIUS_NORMAL};
                padding: 4px 10px;
            }}
        """)
        if self.on_toggle_altermatic:
            self.altermatic_toggle_btn.clicked.connect(lambda: self.on_toggle_altermatic(self.mod_data, not is_active))
        altermatic_section.addWidget(self.altermatic_toggle_btn)

        if is_active:
            self.variant_list_widget = QFrame()
            variant_list_layout = QVBoxLayout(self.variant_list_widget)
            variant_list_layout.setSpacing(3)

            variants = mod_data.get("altermatic_variants", [])
            for idx, v in enumerate(variants):
                row = QHBoxLayout()
                label_short = v.get("label", f"variant_{idx}")
                if "_" in label_short:
                    label_short = label_short.split("_", 1)[-1]
                label_w = QLabel(label_short)
                label_w.setStyleSheet(f"color: white; font-size: {Theme.FONT_SIZE_SMALL};")
                row.addWidget(label_w)
                row.addStretch()

                edit_btn = QPushButton("Edit")
                edit_btn.setFixedWidth(50)
                edit_btn.clicked.connect(lambda _, m=self.mod_data, i=idx: self.on_edit_variant(m, i) if self.on_edit_variant else None)
                row.addWidget(edit_btn)

                del_btn = QPushButton("Del")
                del_btn.setFixedWidth(50)
                del_btn.setStyleSheet(f"color: {Theme.ERROR};")
                del_btn.clicked.connect(lambda _, m=self.mod_data, i=idx: self.on_delete_variant(m, i) if self.on_delete_variant else None)
                row.addWidget(del_btn)

                container = QWidget()
                container.setLayout(row)
                variant_list_layout.addWidget(container)

            if self.on_add_variant:
                add_btn = QPushButton("+ Add Variant")
                add_btn.clicked.connect(lambda: self.on_add_variant(self.mod_data))
                variant_list_layout.addWidget(add_btn)

            altermatic_section.addWidget(self.variant_list_widget)

        altermatic_section.addStretch()
        layout.addLayout(altermatic_section, 0)

        self.view = self

    def handle_icon_click(self):
        self.on_pick_icon(self.mod_data)

    def handle_play_click(self, cry_name):
        if asyncio.iscoroutinefunction(self.on_play_audio):
            run_async(self.on_play_audio(self.mod_data, cry_name))
        else:
            self.on_play_audio(self.mod_data, cry_name)

    def handle_upload_click(self, cry_name):
        self.on_pick_audio(self.mod_data, cry_name)

    def handle_clear_click(self, cry_name):
        if asyncio.iscoroutinefunction(self.on_clear_audio):
            run_async(self.on_clear_audio(self.mod_data, cry_name))
        else:
            self.on_clear_audio(self.mod_data, cry_name)