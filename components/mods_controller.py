# components/mods_controller.py
import asyncio
import os
import sys
import flet as ft
from utils import get_mod_info
from components.mod_item import ModItem
from utils.builder.pipeline_runner import run_pipeline_async
from utils.builder.log_analyzer import LogAnalyzer
from utils.plugins.decompiler import run_decompile_pipeline
from components.mods_dialogs import (
    create_overwrite_warning_dialog,
    create_decompile_options_dialog,
    create_troubleshooting_advisor_dialog
)

class ModsController:
    def __init__(self, view, settings: dict):
        self.view = view
        self.settings = settings
        
        self.is_building = False
        self.active_mod_name = ""
        self.active_token = {"process": None}
        
        self.raw_mods: list[dict] = []
        self.cached_items: list[ModItem] = [] 
        self.search_query = ""
        self.show_mapped = False
        self.selected_badges: set[str] = set()
        self.selected_statuses: set[str] = set()

    def update_search(self, query: str):
        self.search_query = query
        self.apply_filters()

    def update_badge_filter(self, badge: str, selected: bool):
        if selected:
            self.selected_badges.add(badge)
        else:
            self.selected_badges.discard(badge)
        self.apply_filters()

    def update_status_filter(self, status: str, selected: bool):
        if selected:
            self.selected_statuses.add(status)
        else:
            self.selected_statuses.discard(status)
        self.apply_filters()

    def refresh_mods(self, scan_disk: bool = True):
        self.show_mapped = bool(self.settings.get("show_mapped", False))

        if scan_disk:
            self.view.set_refresh_state(loading=True)
            
            def worker():
                self.raw_mods = get_mod_info(self.settings)
                self.cached_items.clear()
                for mod_data in self.raw_mods:
                    self.cached_items.append(
                        ModItem(
                            mod_data, 
                            on_action_click=self.handle_action, 
                            on_cancel_click=self.handle_cancel,
                            is_building=self.is_building,
                            show_mapped=self.show_mapped
                        )
                    )
                self.view.set_refresh_state(loading=False)
                self.apply_filters()

            self.view.main_page.run_thread(worker)
        else:
            for item in self.cached_items:
                item.set_show_mapped(self.show_mapped)
                is_active = (getattr(item, "mod_data")["name"] == self.active_mod_name)
                item.set_state(global_building=self.is_building, is_active_target=is_active)
            self.apply_filters()

    def apply_filters(self):
        fmodel_dir = str(self.settings.get("fmodel_output", ""))
        if not fmodel_dir or not os.path.exists(fmodel_dir):
            self.view.render_error("Set a valid FModel Output Folder in Settings.")
            return

        filtered_items = []
        for item in self.cached_items:
            mod = getattr(item, "mod_data", None)
            if not mod: continue
            
            search_lower = self.search_query.lower()
            name_match = (search_lower in mod["name"].lower()) or (search_lower in mod["localized_name"].lower())
            if not name_match:
                continue

            if self.selected_badges:
                mod_badges = {b[0] for b in mod["badges"]}
                if not self.selected_badges.issubset(mod_badges):
                    continue

            if self.selected_statuses:
                if mod["pak_status"] not in self.selected_statuses:
                    continue

            filtered_items.append(item)

        filtered_items.sort(key=lambda x: str(getattr(x, "mod_data")["localized_name"] if self.show_mapped else getattr(x, "mod_data")["name"]).lower())

        if not filtered_items:
            self.view.render_empty()
        else:
            self.view.render_mods([item.view for item in filtered_items])

    def handle_action(self, mod_data, action):
        if self.is_building: return

        if action in ["push", "full"] and mod_data.get("ue_modified"):
            dlg = create_overwrite_warning_dialog(
                mod_data.get("ue_modified_files", []),
                on_confirm=lambda e: (self.view.pop_dialog(), self.execute_pipeline(mod_data, action)),
                on_cancel=lambda e: self.view.pop_dialog()
            )
            self.view.show_dialog(dlg)

        elif action == "decompile":
            dlg = create_decompile_options_dialog(
                on_missing_only=lambda e: (self.view.pop_dialog(), self.execute_decompile_pipeline(mod_data, overwrite=False)),
                on_overwrite_all=lambda e: (self.view.pop_dialog(), self.execute_decompile_pipeline(mod_data, overwrite=True)),
                on_cancel=lambda e: self.view.pop_dialog()
            )
            self.view.show_dialog(dlg)
            
        elif action == "browse_unreal":
            self.execute_browse_unreal(mod_data)
        else:
            self.execute_pipeline(mod_data, action)

    def handle_cancel(self):
        if self.active_token and self.active_token.get("process"):
            self.view.write_log("\n[!] Force terminating the active pipeline...", ft.Colors.RED_400)
            try:
                proc = self.active_token["process"]
                if os.name == 'nt':
                    import subprocess
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    proc.kill()
            except Exception as e:
                self.view.write_log(f"Error terminating process: {e}", ft.Colors.RED_400)

    def execute_decompile_pipeline(self, mod_data, overwrite: bool = False):
        self.is_building = True
        self.active_mod_name = mod_data["name"]
        self.refresh_mods(scan_disk=False)
        self.view.write_log(f"\n>>> EXECUTING DECOMPILER: {mod_data['name']}", ft.Colors.CYAN_400)
        
        async def decompile_task():
            fmodel_dir = mod_data["fmodel_path"]
            ue_virtual_path = f"/Game/Pal/Model/Character/{mod_data['category']}/{mod_data['name']}"
            
            success, msg = await asyncio.to_thread(
                run_decompile_pipeline,
                self.settings["ue_root"],
                self.settings["uproject"],
                mod_data["name"],
                fmodel_dir,
                ue_virtual_path,
                self.settings["blender"],
                verbose=True,
                overwrite=overwrite
            )
            
            analyzer = LogAnalyzer()
            for line in msg.splitlines():
                analyzed_text, color, is_error = analyzer.analyze_line(line)
                self.view.write_log(analyzed_text, color, flush=False)
                
            if success:
                self.view.write_log(f"SUCCESS: {msg}", ft.Colors.GREEN_400)
            else:
                self.view.write_log("FAILED: Compilation or Blender traceback detected.", ft.Colors.RED_400)
                
            self.is_building = False
            self.active_mod_name = ""
            
            summary = analyzer.generate_summary(success)
            if summary:
                dlg = create_troubleshooting_advisor_dialog(summary, on_dismiss=lambda e: self.view.pop_dialog())
                self.view.show_dialog(dlg)
                
            self.refresh_mods(scan_disk=True)
            
        self.view.main_page.run_task(decompile_task)

    def execute_pipeline(self, mod_data, action):
        self.is_building = True
        self.view.set_log_autoscroll(True)
        self.active_mod_name = mod_data["name"]
        self.refresh_mods(scan_disk=False)
        self.view.write_log(f"\n>>> EXECUTING [{action.upper()}]: {mod_data['name']}", ft.Colors.CYAN_400)
        
        self.active_token = {"process": None}
        
        async def run_task():
            def log_callback(text, color, flush=True):
                if text is not None:
                    self.view.write_log(text, color, flush=False)
                if flush:
                    self.view.force_update()
                    
            def progress_callback(line, flush=True):
                for item in self.cached_items:
                    if getattr(item, "mod_data")["name"] == self.active_mod_name:
                        item.update_progress(line, flush=flush)
                        break
                        
            def complete_callback(success, returncode, summary):
                if success:
                    self.view.write_log("SUCCESS: Operation completed.", ft.Colors.GREEN_400)
                else:
                    self.view.write_log(f"Process terminated with exit code {returncode}", ft.Colors.RED_400)
                
                self.is_building = False
                self.view.set_log_autoscroll(False)
                self.active_token = {"process": None}
                
                for item in self.cached_items:
                    if getattr(item, "mod_data")["name"] == self.active_mod_name:
                        item.set_state(global_building=False, is_active_target=False, success=success)
                        break
                        
                self.active_mod_name = ""
                
                if summary:
                    dlg = create_troubleshooting_advisor_dialog(summary, on_dismiss=lambda e: self.view.pop_dialog())
                    self.view.show_dialog(dlg)
                    
                self.refresh_mods(scan_disk=True)

            script_args = [mod_data["name"], mod_data["category"], action]
            await run_pipeline_async(script_args, log_callback, progress_callback, complete_callback, self.active_token)

        self.view.main_page.run_task(run_task)

    def execute_browse_unreal(self, mod_data):
        self.is_building = True
        self.active_mod_name = mod_data["name"]
        self.refresh_mods(scan_disk=False)
        self.view.write_log(f"\n>>> FOCUSING UNREAL CONTENT BROWSER: {mod_data['name']}", ft.Colors.CYAN_400)
        
        async def browse_task():
            ue_virtual_path = f"/Game/Pal/Model/Character/{mod_data['category']}/{mod_data['name']}"
            python_cmd = f'import unreal; unreal.EditorUtilityLibrary.sync_browser_to_folders(["{ue_virtual_path}"])'
            
            from utils.builder.unreal_helper import run_remote_command, focus_unreal_window
            target_project_name = os.path.splitext(os.path.basename(self.settings["uproject"]))[0]
            
            success, msg = await asyncio.to_thread(
                run_remote_command,
                self.settings["ue_root"],
                target_project_name,
                python_cmd
            )
            
            if success:
                self.view.write_log(f"SUCCESS: Focused Content Browser to: {ue_virtual_path}", ft.Colors.GREEN_400)
                focus_unreal_window(target_project_name)