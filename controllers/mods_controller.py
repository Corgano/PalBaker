# controllers/mods_controller.py
import asyncio
import os
import sys
import shutil
import subprocess
from utils import get_mod_info
from utils.builder.pipeline_runner import run_pipeline_async
from utils.builder.log_analyzer import LogAnalyzer
from utils.plugins.decompiler import run_decompile_pipeline

class ModsController:
    def __init__(self, view, settings: dict):
        self.view = view
        self.settings = settings
        
        self.is_building = False
        self.active_mod_name = ""
        self.active_token = {"process": None}
        
        self.raw_mods: list[dict] = []
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
                # Clear the cached UI elements ONLY on actual disk rescan
                self.view.clear_ui_cache()
                self.view.set_refresh_state(loading=False)
                self.apply_filters()
            self.view.run_in_thread(worker)
        else:
            self.apply_filters()

    def apply_filters(self):
        fmodel_dir = str(self.settings.get("fmodel_output", ""))
        if not fmodel_dir or not os.path.exists(fmodel_dir):
            self.view.render_error("Set a valid FModel Output Folder in Settings.")
            return

        filtered_mods = []
        for mod in self.raw_mods:
            search_lower = self.search_query.lower()
            name_match = (search_lower in mod["name"].lower()) or (search_lower in mod["localized_name"].lower())
            if not name_match: continue

            if self.selected_badges:
                mod_badges = {b[0] for b in mod["badges"]}
                if not self.selected_badges.issubset(mod_badges): continue

            if self.selected_statuses:
                if mod["pak_status"] not in self.selected_statuses: continue

            filtered_mods.append(mod)

        filtered_mods.sort(key=lambda x: str(x["localized_name"] if self.show_mapped else x["name"]).lower())

        if not filtered_mods:
            self.view.render_empty()
        else:
            self.view.render_mods(filtered_mods, self.is_building, self.active_mod_name)

    def apply_custom_icon(self, mod_data: dict, src_path: str):
        """Pure disk I/O logic for setting an icon."""
        dest_path = mod_data["icon_path"]
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        try:
            shutil.copy2(src_path, dest_path)
            self.view.write_log(f"SUCCESS: Set custom icon for {mod_data['name']}", "success")
            self.refresh_mods(scan_disk=True)
        except Exception as e:
            self.view.write_log(f"ERROR: Failed to copy icon file: {e}", "error")

    # --- AUDIO MODDING IMPLEMENTATION ---
    async def apply_custom_audio(self, mod_data: dict, cry_name: str, src_path: str):
        """Stands up an isolated thread to convert audio to .wem instantly upon file upload."""
        def conversion_worker():
            try:
                fmodel_path = mod_data.get("fmodel_path")
                if not fmodel_path: return False, "No FModel path found."
                
                audio_dir = os.path.join(fmodel_path, ".palbaker_audio")
                sources_dir = os.path.join(audio_dir, "sources")
                wem_dir = os.path.join(audio_dir, "WwiseAudio", "Media")
                
                os.makedirs(sources_dir, exist_ok=True)
                os.makedirs(wem_dir, exist_ok=True)
                
                ext = os.path.splitext(src_path)[1].lower()
                for clean_ext in [".wav", ".mp3", ".ogg"]:
                    old_file = os.path.join(sources_dir, f"{cry_name}{clean_ext}")
                    if os.path.exists(old_file):
                        try: os.remove(old_file)
                        except OSError: pass
                
                # Copy source to local FModel staging directory
                dest_path = os.path.join(sources_dir, f"{cry_name}{ext}")
                shutil.copy2(src_path, dest_path)
                
                # Discover Media ID target from internal DB
                sound_meta = mod_data.get("sound_metadata", {}).get(cry_name, {})
                media_id = sound_meta.get("media_id")
                if not media_id:
                    return False, f"No media_id found for {cry_name}"
                    
                repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                candidate_paths = [
                    os.path.join(repo_root, "deps", "wwise", "Authoring", "x64", "Release", "bin", "WwiseConsole.exe"),
                    os.path.join(repo_root, "deps", "wwise", "bin", "WwiseConsole.exe")
                ]
                wwise_console = next((p for p in candidate_paths if os.path.exists(p)), None)
                
                project_dir = os.path.join(repo_root, "deps", "wwise", "project")
                wproj_path = None
                if os.path.exists(project_dir):
                    for root, _, files in os.walk(project_dir):
                        for f in files:
                            if f.endswith(".wproj"):
                                wproj_path = os.path.join(root, f)
                                break
                        if wproj_path: break
                
                if not wwise_console or not wproj_path:
                    return False, "Wwise environment not found in deps/wwise/. Cannot compile."
                    
                
                # ====================================================================
                # WWISE BYPASS: Convert MP3/OGG to a temporary WAV before feeding Wwise
                # ====================================================================
                wwise_target_file = dest_path
                vgmstream_cli = os.path.join(repo_root, "deps", "vgmstream", "vgmstream-cli.exe")
                if not os.path.exists(vgmstream_cli):
                    vgmstream_cli = os.path.join(repo_root, "deps", "vgmstream-cli.exe")
                    
                if ext in [".mp3", ".ogg"]:
                    temp_wav_path = os.path.join(sources_dir, f"{cry_name}_temp.wav")
                    if os.path.exists(temp_wav_path):
                        try: os.remove(temp_wav_path)
                        except OSError: pass
                        
                    if os.path.exists(vgmstream_cli):
                        decode_cmd = [vgmstream_cli, "-o", temp_wav_path, dest_path]
                        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                        subprocess.run(decode_cmd, capture_output=True, creationflags=creation_flags)
                        
                        if os.path.exists(temp_wav_path):
                            wwise_target_file = temp_wav_path
                        else:
                            return False, f"Failed to decode {ext.upper()} to WAV for Wwise compilation."
                    else:
                        return False, "vgmstream-cli not found. Cannot decode MP3/OGG for Wwise."
                # ====================================================================

                wsources_path = os.path.join(audio_dir, f"{cry_name}_list.wsources")
                output_test_dir = os.path.join(audio_dir, "output_test")
                
                if os.path.exists(output_test_dir):
                    shutil.rmtree(output_test_dir, ignore_errors=True)
                os.makedirs(output_test_dir, exist_ok=True)
                
                # Write XML source mapping
                xml_content = f'<?xml version="1.0" encoding="utf-8"?>\n<ExternalSourcesList SchemaVersion="1">\n    <Source Path="{wwise_target_file.replace(os.sep, "/")}" Conversion="Default Conversion Settings" />\n</ExternalSourcesList>'
                with open(wsources_path, "w", encoding="utf-8") as f:
                    f.write(xml_content)
                    
                cmd = [
                    wwise_console,
                    "convert-external-source", wproj_path,
                    "--source-file", wsources_path,
                    "--output", output_test_dir,
                    "--platform", "Windows"
                ]
                
                # Run the command silently and capture output so it won't crash our entire pipeline
                creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                subprocess.run(cmd, capture_output=True, creationflags=creation_flags)
                
                compiled_dir = os.path.join(output_test_dir, "Windows")
                success_file = False
                
                # Safely harvest the WEM from the isolated test folder and plant it under the FModel root
                if os.path.exists(compiled_dir):
                    files = [f for f in os.listdir(compiled_dir) if f.endswith(".wem")]
                    if files:
                        source_wem = os.path.join(compiled_dir, files[0])
                        target_wem = os.path.join(wem_dir, f"{media_id}.wem")
                        shutil.copy2(source_wem, target_wem)
                        success_file = True
                        
                shutil.rmtree(output_test_dir, ignore_errors=True)
                try: os.remove(wsources_path)
                except OSError: pass
                
                # Cleanup the temp WAV if we generated one
                if wwise_target_file != dest_path and os.path.exists(wwise_target_file):
                    try: os.remove(wwise_target_file)
                    except OSError: pass
                
                if success_file:
                    return True, f"SUCCESS: Converted and staged {cry_name} -> {media_id}.wem"
                else:
                    return False, f"ERROR: Wwise failed to generate .wem for {cry_name}. The file may be corrupted."

            except Exception as e:
                return False, f"Exception during audio processing: {e}"
                
        self.view.write_log(f"Staging and compiling {cry_name}...", "standard")
        success, msg = await asyncio.to_thread(conversion_worker)
        if success:
            self.view.write_log(msg, "success")
        else:
            self.view.write_log(msg, "error")
            
        self.refresh_mods(scan_disk=True)

    async def clear_audio(self, mod_data: dict, cry_name: str):
        """Deletes both the source override and the compiled .wem cache."""
        fmodel_path = mod_data.get("fmodel_path")
        if not fmodel_path: return

        audio_dir = os.path.join(fmodel_path, ".palbaker_audio")
        sources_dir = os.path.join(audio_dir, "sources")
        wem_dir = os.path.join(audio_dir, "WwiseAudio", "Media")
        removed = False
        
        # Remove source overrides
        if os.path.exists(sources_dir):
            for ext in [".wav", ".mp3", ".ogg"]:
                path = os.path.join(sources_dir, f"{cry_name}{ext}")
                if os.path.exists(path):
                    try:
                        os.remove(path)
                        removed = True
                    except Exception as e:
                        self.view.write_log(f"ERROR: Failed to delete audio source: {e}", "error")
        
        # Remove compiled WEM packages
        media_id = mod_data.get("sound_metadata", {}).get(cry_name, {}).get("media_id")
        if media_id and os.path.exists(wem_dir):
            wem_path = os.path.join(wem_dir, f"{media_id}.wem")
            if os.path.exists(wem_path):
                try:
                    os.remove(wem_path)
                    removed = True
                except OSError: pass
                
        if removed:
            self.view.write_log(f"REVERTED: Removed custom override for {mod_data['name']} ({cry_name})", "standard")
            self.refresh_mods(scan_disk=True)

    def play_wav_file(self, wav_path: str):
        """Plays a WAV file natively via Python OS bindings. (Bypasses Flet Audio crashes)"""
        if not os.path.exists(wav_path):
            return

        if sys.platform == "win32":
            import winsound
            try:
                winsound.PlaySound(wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception as e:
                self.view.write_log(f"Windows Playback Error: {e}", "error")
        elif sys.platform == "darwin":
            subprocess.Popen(["afplay", wav_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            for player in ["paplay", "aplay", "play"]:
                if shutil.which(player):
                    subprocess.Popen([player, wav_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    break

    async def play_audio(self, mod_data: dict, cry_name: str):
        """Plays either the custom override (.wav/.mp3/.ogg) or decodes the original game audio natively."""
        fmodel_path = mod_data.get("fmodel_path")
        if not fmodel_path: return

        audio_dir = os.path.join(fmodel_path, ".palbaker_audio", "sources")
        
        custom_file = None
        for ext in [".wav", ".mp3", ".ogg"]:
            test_file = os.path.join(audio_dir, f"{cry_name}{ext}")
            if os.path.exists(test_file):
                custom_file = test_file
                break

        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        vgmstream_cli = os.path.join(repo_root, "deps", "vgmstream", "vgmstream-cli.exe")
        if not os.path.exists(vgmstream_cli):
            vgmstream_cli = os.path.join(repo_root, "deps", "vgmstream-cli.exe")

        # Scenario A: Play the custom audio override directly
        if custom_file:
            ext = os.path.splitext(custom_file)[1].lower()
            if ext == ".wav":
                self.play_wav_file(custom_file)
                self.view.write_log(f"Playing custom override for {mod_data['name']}: {cry_name}", "standard")
            else:
                # Decode to temporary WAV first for playback
                temp_custom_wav = os.path.join(audio_dir, ".temp_custom_preview.wav")
                if not os.path.exists(vgmstream_cli):
                    self.view.write_log("Could not locate 'vgmstream-cli.exe' to decode custom MP3/OGG preview.", "error")
                    return
                
                self.view.write_log(f"Decoding custom {ext[1:].upper()} override for playback...", "standard")
                
                def decode_custom():
                    try:
                        if os.path.exists(temp_custom_wav):
                            try: os.remove(temp_custom_wav)
                            except OSError: pass
                        cmd = [vgmstream_cli, "-o", temp_custom_wav, custom_file]
                        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=creation_flags)
                        if os.path.exists(temp_custom_wav):
                            self.play_wav_file(temp_custom_wav)
                    except Exception as e:
                        self.view.write_log(f"Failed to decode custom override: {e}", "error")
                
                self.view.run_in_thread(decode_custom)
            return

        # Scenario B: Play the original game sound via vgmstream
        sound_meta = mod_data.get("sound_metadata", {})
        cry_meta = sound_meta.get(cry_name)
        if not cry_meta:
            self.view.write_log(f"No sound metadata found for {cry_name}", "warning")
            return

        wem_rel = cry_meta.get("wem_relative_path")
        if not wem_rel: return

        fmodel_root = self.settings.get("fmodel_output", "")
        if not fmodel_root: return

        wem_abs_path = os.path.normpath(os.path.join(fmodel_root, "Exports", wem_rel))
        if not os.path.exists(wem_abs_path):
            self.view.write_log(f"Original game .wem asset not found inside FModel output: {os.path.basename(wem_abs_path)}", "error")
            return

        if not os.path.exists(vgmstream_cli):
            self.view.write_log("Could not locate 'vgmstream-cli.exe' inside 'deps/vgmstream/'. Preview unavailable.", "error")
            return

        os.makedirs(audio_dir, exist_ok=True)
        temp_wav = os.path.join(audio_dir, ".temp_preview.wav")

        self.view.write_log(f"Decoding original game audio for {mod_data['name']} ({cry_name})...", "standard")

        def decode_worker():
            try:
                if os.path.exists(temp_wav):
                    try: os.remove(temp_wav)
                    except OSError: pass

                cmd = [vgmstream_cli, "-o", temp_wav, wem_abs_path]
                creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                
                subprocess.run(
                    cmd, 
                    check=True, 
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.DEVNULL, 
                    creationflags=creation_flags
                )
                
                if os.path.exists(temp_wav):
                    self.play_wav_file(temp_wav)
                else:
                    self.view.write_log("vgmstream executed but failed to save temporary preview wav.", "error")
            except Exception as e:
                self.view.write_log(f"vgmstream decoding failed: {e}", "error")

        self.view.run_in_thread(decode_worker)

    # --- PIPELINE ORCHESTRATORS ---
    def handle_action(self, mod_data, action):
        if self.is_building: return

        if action in ["push", "full"] and mod_data.get("ue_modified"):
            self.view.prompt_overwrite_warning(mod_data, lambda: self.execute_pipeline(mod_data, action))
        elif action == "decompile":
            self.view.prompt_decompile_options(mod_data)
        elif action == "browse_unreal":
            self.execute_browse_unreal(mod_data)
        else:
            self.execute_pipeline(mod_data, action)

    def handle_cancel(self):
        if self.active_token and self.active_token.get("process"):
            self.view.write_log("\n[!] Force terminating the active pipeline...", "error")
            try:
                proc = self.active_token["process"]
                if os.name == 'nt':
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    proc.kill()
            except Exception as e:
                self.view.write_log(f"Error terminating process: {e}", "error")

    def execute_decompile_pipeline(self, mod_data, overwrite: bool = False):
        self.is_building = True
        self.active_mod_name = mod_data["name"]
        self.refresh_mods(scan_disk=False)
        self.view.write_log(f"\n>>> EXECUTING DECOMPILER: {mod_data['name']}", "stage")
        
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
                analyzed_text, category, is_error = analyzer.analyze_line(line)
                self.view.write_log(analyzed_text, category, flush=False)
                
            summary = analyzer.generate_summary(success)
            status = summary.get("status", "failed") if summary else "pure_success"
            
            if success and status == "pure_success":
                self.view.write_log("SUCCESS: Decompile completed cleanly.", "success")
            elif status == "success_with_warnings":
                self.view.write_log("WARNING: Decompile completed with warnings.", "warning")
            elif status == "success_with_errors":
                self.view.write_log("ERROR: Decompile completed but found compiler errors.", "error")
            else:
                self.view.write_log("FAILED: Decompile failed. Check logs.", "error")
                
            self.is_building = False
            self.active_mod_name = ""
            
            if summary:
                self.view.prompt_troubleshooting_advisor(summary)
                
            self.refresh_mods(scan_disk=True)
            
        self.view.run_async_task(decompile_task)

    def execute_pipeline(self, mod_data, action):
        self.is_building = True
        self.view.set_log_autoscroll(True)
        self.active_mod_name = mod_data["name"]
        self.refresh_mods(scan_disk=False)
        self.view.write_log(f"\n>>> EXECUTING [{action.upper()}]: {mod_data['name']}", "stage")
        
        self.active_token = {"process": None}
        
        async def run_task():
            def log_callback(text, category, flush=True):
                if text is not None:
                    self.view.write_log(text, category, flush=False)
                if flush:
                    self.view.force_update()
                    
            def progress_callback(line, flush=True):
                self.view.update_card_progress(self.active_mod_name, line, flush)
                        
            def complete_callback(success, returncode, summary):
                status = "pure_success"
                if summary:
                    status = summary.get("status", "failed")

                if status == "pure_success" and success:
                    self.view.write_log("SUCCESS: Operation completed cleanly.", "success")
                elif status == "success_with_warnings":
                    self.view.write_log(f"WARNING: Operation completed with {summary['total_warnings']} warnings.", "warning")
                elif status == "success_with_errors":
                    self.view.write_log(f"ERROR: Operation completed but found {summary['total_errors']} compilation errors.", "error")
                else:
                    self.view.write_log(f"FAILED: Process terminated with exit code {returncode}", "error")
                
                self.is_building = False
                self.view.set_log_autoscroll(False)
                self.active_token = {"process": None}
                
                # Signal view to reset the specific card
                card_success = success and (status != "success_with_errors")
                self.view.reset_card_state(self.active_mod_name, card_success)
                self.active_mod_name = ""
                
                if summary:
                    self.view.prompt_troubleshooting_advisor(summary)
                    
                self.refresh_mods(scan_disk=True)

            script_args = [mod_data["name"], mod_data["category"], action]
            await run_pipeline_async(script_args, log_callback, progress_callback, complete_callback, self.active_token)

        self.view.run_async_task(run_task)

    def execute_browse_unreal(self, mod_data):
        self.is_building = True
        self.active_mod_name = mod_data["name"]
        self.refresh_mods(scan_disk=False)
        self.view.write_log(f"\n>>> FOCUSING UNREAL CONTENT BROWSER: {mod_data['name']}", "stage")
        
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
                self.view.write_log(f"SUCCESS: Focused Content Browser to: {ue_virtual_path}", "success")
                focus_unreal_window(target_project_name)
            else:
                self.view.write_log(f"FAILED to focus Unreal: {msg}", "error")
                
            self.is_building = False
            self.active_mod_name = ""
            self.refresh_mods(scan_disk=False)
            
        self.view.run_async_task(browse_task)