# views/mods_view.py
import os
import asyncio
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QScrollArea, QTextEdit, QSplitter, QFrame, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
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

class ModsView(QWidget):
    render_mods_signal = pyqtSignal(object, bool, str)
    write_log_signal = pyqtSignal(str, str, bool)
    set_refresh_state_signal = pyqtSignal(bool)
    update_card_progress_signal = pyqtSignal(str, str, bool)
    reset_card_state_signal = pyqtSignal(str, bool)
    render_empty_signal = pyqtSignal()
    render_error_signal = pyqtSignal(str)
    prompt_overwrite_warning_signal = pyqtSignal(object, object)
    prompt_decompile_options_signal = pyqtSignal(object)
    prompt_troubleshooting_advisor_signal = pyqtSignal(object)

    def __init__(self, parent_window, settings: dict):
        super().__init__()
        self.main_page = parent_window
        self.settings = settings
        
        # Link the Controller
        from controllers.mods_controller import ModsController
        self.controller = ModsController(self, settings)
        
        self.cached_components = {}
        
        # Connect thread-safe signals to internal slots
        self.render_mods_signal.connect(self._render_mods_slot)
        self.write_log_signal.connect(self._write_log_slot)
        self.set_refresh_state_signal.connect(self._set_refresh_state_slot)
        self.update_card_progress_signal.connect(self._update_card_progress_slot)
        self.reset_card_state_signal.connect(self._reset_card_state_slot)
        self.render_empty_signal.connect(self._render_empty_slot)
        self.render_error_signal.connect(self._render_error_slot)
        self.prompt_overwrite_warning_signal.connect(self._prompt_overwrite_warning_slot)
        self.prompt_decompile_options_signal.connect(self._prompt_decompile_options_slot)
        self.prompt_troubleshooting_advisor_signal.connect(self._prompt_troubleshooting_advisor_slot)
        
        # Layout definition
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # --- TOP PANEL ---
        self.top_panel = QWidget()
        top_layout = QVBoxLayout(self.top_panel)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        search_layout = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search by internal or actual name...")
        self.search_bar.textChanged.connect(lambda text: self.controller.update_search(text))
        
        self.refresh_spinner = QLabel("Loading...")
        self.refresh_spinner.setStyleSheet(f"color: {Theme.PRIMARY}; font-weight: bold;")  # <--- UPDATED
        self.refresh_spinner.setVisible(False)
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(lambda: self.controller.refresh_mods(scan_disk=True))
        
        search_layout.addWidget(self.search_bar, 1)
        search_layout.addWidget(self.refresh_spinner, 0)
        search_layout.addWidget(self.refresh_button, 0)
        top_layout.addLayout(search_layout)
        
        # Tag Filter Chips
        self.badge_chips = QHBoxLayout()
        badge_label = QLabel("Tags:")
        badge_label.setStyleSheet("font-weight: bold; color: white;")
        self.badge_chips.addWidget(badge_label)
        tags = ["RAW", "SOURCE", "UE ASSETS", "MODIFIED"]
        self.tag_buttons = {}
        for tag in tags:
            btn = QPushButton(tag)
            btn.setCheckable(True)
            btn.setStyleSheet(Theme.get_chip_style())  # <--- UPDATED
            btn.toggled.connect(lambda checked, t=tag: self.controller.update_badge_filter(t, checked))
            self.badge_chips.addWidget(btn)
            self.tag_buttons[tag] = btn
        self.badge_chips.addStretch()
        top_layout.addLayout(self.badge_chips)
        
        # Status Filter Chips
        self.status_chips = QHBoxLayout()
        status_label = QLabel("Status:")
        status_label.setStyleSheet("font-weight: bold; color: white;")
        self.status_chips.addWidget(status_label)
        statuses = ["Packed", "Packed with Errors", "Unpacked", "Outdated"]
        self.status_buttons = {}
        for status in statuses:
            btn = QPushButton(status)
            btn.setCheckable(True)
            btn.setStyleSheet(Theme.get_chip_style())  # <--- UPDATED
            btn.toggled.connect(lambda checked, s=status: self.controller.update_status_filter(s, checked))
            self.status_chips.addWidget(btn)
            self.status_buttons[status] = btn
        self.status_chips.addStretch()
        top_layout.addLayout(self.status_chips)
        
        # Scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.mods_list_widget = QWidget()
        self.mods_list_layout = QVBoxLayout(self.mods_list_widget)
        self.mods_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_area.setWidget(self.mods_list_widget)
        top_layout.addWidget(self.scroll_area)
        
        # --- BOTTOM PANEL ---
        self.bottom_panel = QWidget()
        bottom_layout = QVBoxLayout(self.bottom_panel)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        header_layout = QHBoxLayout()
        console_title = QLabel("Build Console")
        console_title.setStyleSheet(f"font-size: {Theme.FONT_SIZE_TITLE}; font-weight: bold; color: white;")  # <--- UPDATED
        
        copy_btn = QPushButton("Copy Console")
        copy_btn.clicked.connect(self.copy_console_to_clipboard)
        
        header_layout.addWidget(console_title)
        header_layout.addStretch()
        header_layout.addWidget(copy_btn)
        bottom_layout.addLayout(header_layout)
        
        self.log_view_widget = QTextEdit()
        self.log_view_widget.setReadOnly(True)
        self.log_view_widget.setStyleSheet(Theme.get_console_style())  # <--- UPDATED
        self.log_view_widget.textChanged.connect(lambda: self.log_view_widget.ensureCursorVisible())
        bottom_layout.addWidget(self.log_view_widget)
        
        # --- SPLITTER ---
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.addWidget(self.top_panel)
        self.splitter.addWidget(self.bottom_panel)
        
        self.console_height = int(settings.get("console_height", 200))
        initial_height = self.main_page.height() if hasattr(self.main_page, 'height') else 800
        self.splitter.setSizes([initial_height - self.console_height, self.console_height])
        self.splitter.splitterMoved.connect(self.on_splitter_resized)
        
        main_layout.addWidget(self.splitter)

    def on_splitter_resized(self, pos, index):
        sizes = self.splitter.sizes()
        if len(sizes) > 1:
            self.console_height = sizes[1]
            self.settings["console_height"] = self.console_height
            from utils.config import save_settings
            save_settings(self.settings)

    def run_in_thread(self, func):
        import threading
        t = threading.Thread(target=func, daemon=True)
        t.start()

    def run_async_task(self, func, *args):
        func(*args)

    def clear_ui_cache(self):
        for item in self.cached_components.values():
            try:
                item.deleteLater()
            except Exception:
                pass
        self.cached_components.clear()

    # --- THREAD-SAFE PUBLIC SIGNAL WRAPPERS ---
    def render_mods(self, mods_data: list[dict], global_building: bool, active_mod_name: str):
        self.render_mods_signal.emit(mods_data, global_building, active_mod_name)

    def write_log(self, text: str, category: str = "standard", flush: bool = True):
        self.write_log_signal.emit(text, category, flush)

    def set_refresh_state(self, loading: bool):
        self.set_refresh_state_signal.emit(loading)

    def update_card_progress(self, mod_name: str, line: str, flush: bool):
        self.update_card_progress_signal.emit(mod_name, line, flush)

    def reset_card_state(self, mod_name: str, success: bool):
        self.reset_card_state_signal.emit(mod_name, success)

    def render_empty(self):
        self.render_empty_signal.emit()

    def render_error(self, message: str):
        self.render_error_signal.emit(message)

    def prompt_overwrite_warning(self, mod_data, confirm_callback):
        self.prompt_overwrite_warning_signal.emit(mod_data, confirm_callback)

    def prompt_decompile_options(self, mod_data):
        self.prompt_decompile_options_signal.emit(mod_data)

    def prompt_troubleshooting_advisor(self, summary):
        self.prompt_troubleshooting_advisor_signal.emit(summary)

    # --- SLOTS ---
    def _render_mods_slot(self, mods_data: list[dict], global_building: bool, active_mod_name: str):
        while self.mods_list_layout.count():
            child = self.mods_list_layout.takeAt(0)
            widget = child.widget()
            if widget:
                widget.hide()
                widget.setParent(None)
        
        for mod_data in mods_data:
            name = mod_data["name"]
            
            from components.mods.mod_card import ModItem
            
            if name in self.cached_components:
                item = self.cached_components[name]
                item.mod_data = mod_data
                item.set_show_mapped(self.controller.show_mapped)
                item.set_state(global_building, is_active_target=(name == active_mod_name))
            else:
                item = ModItem(
                    mod_data=mod_data,
                    on_action_click=self.controller.handle_action,
                    on_cancel_click=self.controller.handle_cancel,
                    on_pick_icon=self.trigger_icon_picker,
                    on_pick_audio=self.trigger_audio_picker,
                    on_play_audio=self.controller.play_audio,
                    on_clear_audio=self.controller.clear_audio,
                    is_building=global_building,
                    show_mapped=self.controller.show_mapped
                )
                item.set_state(global_building, is_active_target=(name == active_mod_name))
                self.cached_components[name] = item
                
            self.mods_list_layout.addWidget(item)
            item.show()
            
        self.force_update()

    def _write_log_slot(self, text: str, category: str, flush: bool):
        color_map = {
            "error": Theme.ERROR, "warning": Theme.WARNING, 
            "success": Theme.SUCCESS, "stage": Theme.CYAN_ACCENT, "standard": Theme.TEXT_MUTED
        }  # <--- UPDATED
        color = color_map.get(category, Theme.TEXT_MUTED)
        html_line = f"<font color='{color}'>{text}</font><br>"
        self.log_view_widget.insertHtml(html_line)
        
        doc = self.log_view_widget.document()
        if doc.blockCount() > 250:
            cursor = self.log_view_widget.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.KeepAnchor, 50)
            cursor.removeSelectedText()

    def _set_refresh_state_slot(self, loading: bool):
        self.refresh_button.setEnabled(not loading)
        self.refresh_spinner.setVisible(loading)
        self.force_update()

    def _update_card_progress_slot(self, mod_name: str, line: str, flush: bool):
        if mod_name in self.cached_components:
            self.cached_components[mod_name].update_progress(line, flush)

    def _reset_card_state_slot(self, mod_name: str, success: bool):
        if mod_name in self.cached_components:
            self.cached_components[mod_name].set_state(global_building=False, is_active_target=False, success=success)

    def _render_empty_slot(self):
        while self.mods_list_layout.count():
            child = self.mods_list_layout.takeAt(0)
            widget = child.widget()
            if widget:
                widget.hide()
                widget.setParent(None)
        lbl = QLabel("No mods match active filters.")
        lbl.setStyleSheet(f"color: {Theme.WARNING}; padding: 15px;")  # <--- UPDATED
        self.mods_list_layout.addWidget(lbl)
        self.force_update()

    def _render_error_slot(self, message: str):
        while self.mods_list_layout.count():
            child = self.mods_list_layout.takeAt(0)
            widget = child.widget()
            if widget:
                widget.hide()
                widget.setParent(None)
        lbl = QLabel(message)
        lbl.setStyleSheet(f"color: {Theme.ERROR}; padding: 15px;")  # <--- UPDATED
        self.mods_list_layout.addWidget(lbl)
        self.force_update()

    def _prompt_overwrite_warning_slot(self, mod_data, confirm_callback):
        from components.mods.dialogs import create_overwrite_warning_dialog
        dlg = create_overwrite_warning_dialog(
            self.main_page,
            mod_data.get("ue_modified_files", []), 
            confirm_callback,
            lambda: None
        )
        self.show_dialog(dlg)

    def _prompt_decompile_options_slot(self, mod_data):
        from components.mods.dialogs import create_decompile_options_dialog
        dlg = create_decompile_options_dialog(
            self.main_page,
            lambda: self.controller.execute_decompile_pipeline(mod_data, False),
            lambda: self.controller.execute_decompile_pipeline(mod_data, True),
            lambda: None
        )
        self.show_dialog(dlg)

    def _prompt_troubleshooting_advisor_slot(self, summary):
        from components.mods.dialogs import create_troubleshooting_advisor_dialog
        dlg = create_troubleshooting_advisor_dialog(
            self.main_page,
            summary, 
            lambda: None
        )
        self.show_dialog(dlg)

    # --- SYNCHRONOUS PICKER TRIGGERS ---
    def trigger_icon_picker(self, mod_data):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Icon File", "", "Images (*.png *.jpg *.jpeg)"
        )
        if path:
            if asyncio.iscoroutinefunction(self.controller.apply_custom_icon):
                run_async(self.controller.apply_custom_icon(mod_data, path))
            else:
                self.controller.apply_custom_icon(mod_data, path)

    def trigger_audio_picker(self, mod_data, cry_name):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Audio File", "", "Audio (*.wav *.mp3 *.ogg)"
        )
        if path:
            if asyncio.iscoroutinefunction(self.controller.apply_custom_audio):
                run_async(self.controller.apply_custom_audio(mod_data, cry_name, path))
            else:
                self.controller.apply_custom_audio(mod_data, cry_name, path)

    def show_dialog(self, dlg):
        if hasattr(dlg, 'exec'):
            dlg.exec()

    def pop_dialog(self):
        pass

    def force_update(self):
        self.update()

    def copy_console_to_clipboard(self):
        plain_text = self.log_view_widget.toPlainText()
        if plain_text.strip():
            clipboard = QApplication.clipboard()
            clipboard.setText(plain_text)
            self.main_page.statusBar().showMessage("Console content copied!", 3000)

    def refresh_mods(self, scan_disk: bool = True):
        self.controller.refresh_mods(scan_disk)