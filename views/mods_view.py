# views/mods_view.py
import flet as ft
from controllers.mods_controller import ModsController

class ModsView:
    def __init__(self, page: ft.Page, settings: dict):
        self.main_page = page
        self.settings = settings
        
        # Link the Controller
        self.controller = ModsController(self, settings)

        # Presentation Layout Controls
        self.mods_list = ft.ListView(expand=True, spacing=10)
        self.log_view = ft.ListView(expand=True, spacing=2, auto_scroll=True)

        self.search_bar = ft.TextField(
            label="Search by internal or actual name...",
            expand=True,
            on_change=lambda e: self.controller.update_search(self.search_bar.value),
            prefix_icon=ft.Icons.SEARCH
        )
        
        self.badge_chips = ft.Row([
            ft.Text("Tags:", weight=ft.FontWeight.BOLD),
            ft.Chip(label=ft.Text("RAW"), on_select=lambda e: self.controller.update_badge_filter("RAW", e.control.selected)),
            ft.Chip(label=ft.Text("SOURCE"), on_select=lambda e: self.controller.update_badge_filter("SOURCE", e.control.selected)),
            ft.Chip(label=ft.Text("UE ASSETS"), on_select=lambda e: self.controller.update_badge_filter("UE ASSETS", e.control.selected)),
            ft.Chip(label=ft.Text("MODIFIED"), on_select=lambda e: self.controller.update_badge_filter("MODIFIED", e.control.selected)),
        ], spacing=10)

        self.status_chips = ft.Row([
            ft.Text("Status:", weight=ft.FontWeight.BOLD),
            ft.Chip(label=ft.Text("Packed"), on_select=lambda e: self.controller.update_status_filter("Packed", e.control.selected)),
            ft.Chip(label=ft.Text("Packed with Errors"), on_select=lambda e: self.controller.update_status_filter("Packed with Errors", e.control.selected)),  # ADDED: Filter for error-paks
            ft.Chip(label=ft.Text("Unpacked"), on_select=lambda e: self.controller.update_status_filter("Unpacked", e.control.selected)),
            ft.Chip(label=ft.Text("Outdated"), on_select=lambda e: self.controller.update_status_filter("Outdated", e.control.selected)),
        ], spacing=10)


        self.refresh_button = ft.IconButton(
            icon=ft.Icons.REFRESH, 
            tooltip="Rescan disk for mods",
            on_click=lambda e: self.controller.refresh_mods(scan_disk=True)
        )
        self.refresh_spinner = ft.ProgressRing(
            width=16, 
            height=16, 
            stroke_width=2, 
            visible=False
        )

        row_controls: list[ft.Control] = [
            self.search_bar,
            self.refresh_spinner,
            self.refresh_button
        ]

        self.console_container = ft.Container(
            content=self.log_view, 
            expand=True, 
            bgcolor=ft.Colors.BLACK, 
            border_radius=10, 
            padding=15, 
            border=ft.Border.all(1, ft.Colors.WHITE10)
        )

        self.view = ft.Column(
            expand=True,
            controls=[
                ft.Row(controls=row_controls),
                self.badge_chips,
                self.status_chips,
                ft.Container(self.mods_list, height=300, border=ft.Border.all(1, ft.Colors.WHITE10), border_radius=10, padding=10),
                ft.Row([
                    ft.Text("Build Console", size=16, weight=ft.FontWeight.BOLD),
                    ft.IconButton(
                        icon=ft.Icons.COPY_ALL, 
                        tooltip="Copy console content to clipboard", 
                        on_click=self.copy_console_to_clipboard
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                self.console_container
            ]
        )

    # --- Controller Triggered Interface Methods ---

    def set_refresh_state(self, loading: bool):
        self.refresh_button.disabled = loading
        self.refresh_spinner.visible = loading
        self.force_update()

    def set_log_autoscroll(self, enabled: bool):
        self.log_view.auto_scroll = enabled
        self.force_update()

    def write_log(self, text: str, category: str = "standard", flush: bool = True):
        """The GUI Adapter: Maps string categories back to Flet UI Colors."""
        color_map = {
            "error": ft.Colors.RED_400,
            "warning": ft.Colors.ORANGE_400,
            "success": ft.Colors.GREEN_400,
            "stage": ft.Colors.CYAN_400,
            "standard": ft.Colors.WHITE70
        }
        color = color_map.get(category, ft.Colors.WHITE70)
        
        self.log_view.controls.append(ft.Text(text, color=color, size=12, font_family="Consolas"))
        
        MAX_LINES = 100
        if len(self.log_view.controls) > MAX_LINES:
            self.log_view.controls = self.log_view.controls[-MAX_LINES:]
            
        if flush:
            self.force_update()

    def render_mods(self, controls: list[ft.Control]):
        self.mods_list.controls.clear()
        self.mods_list.controls.extend(controls)
        self.force_update()

    def render_empty(self):
        self.mods_list.controls.clear()
        self.mods_list.controls.append(ft.Text("No mods match active filters.", color=ft.Colors.YELLOW_400))
        self.force_update()

    def render_error(self, message: str):
        self.mods_list.controls.clear()
        self.mods_list.controls.append(ft.Text(message, color=ft.Colors.RED_400))
        self.force_update()

    def show_dialog(self, dlg: ft.AlertDialog):
        self.main_page.show_dialog(dlg)

    def pop_dialog(self):
        self.main_page.pop_dialog()

    def refresh_mods(self, scan_disk: bool = True):
        # Point the interface boundary to the controller
        self.controller.refresh_mods(scan_disk)

    def force_update(self):
        try:
            self.view.update()
        except Exception:
            pass

    async def copy_console_to_clipboard(self, e):
        log_lines = []
        for ctrl in self.log_view.controls:
            if isinstance(ctrl, ft.Text) and ctrl.value:
                log_lines.append(ctrl.value)
        
        full_log = "\n".join(log_lines)
        if full_log.strip():
            await ft.Clipboard().set(full_log)
            self.main_page.overlay.append(ft.SnackBar(ft.Text("Console content copied to clipboard!"), open=True))
        else:
            self.main_page.overlay.append(ft.SnackBar(ft.Text("Console is currently empty."), open=True))
        self.main_page.update()