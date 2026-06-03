import os
import json
import re
import shutil
import threading
import time
from utils.altermatic_helper import sync_sidecar_metadata, get_available_materials_for_context

class AltermaticController:
    def __init__(self, master_controller):
        self.mc = master_controller
        self.settings = master_controller.settings
        self.view = master_controller.view
        self.original_editing_label = ""

    def toggle_altermatic(self, mod_data: dict, is_active: bool):
        current_char_id = mod_data["name"]
        fmodel_altermatic_dir = mod_data.get("fmodel_altermatic_path")
        if not fmodel_altermatic_dir:
            fmodel_root = self.settings.get("fmodel_output", "")
            fmodel_altermatic_dir = os.path.join(fmodel_root, "Exports", "Pal", "Content", "Palbaker", "Model", "Character", "Monster", current_char_id)

        os.makedirs(fmodel_altermatic_dir, exist_ok=True)
        manifest_name = f"{mod_data['name']}_altermatic.json"
        manifest_path = os.path.join(fmodel_altermatic_dir, manifest_name)

        manifest_data = {"is_altermatic_active": is_active, "variants": {}}
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f_man:
                    manifest_data = json.load(f_man)
                if isinstance(manifest_data.get("variants"), list):
                    old_list = manifest_data["variants"]
                    manifest_data["variants"] = {}
                    for item in old_list:
                        lbl_key = item.get("label", "base")
                        manifest_data["variants"][lbl_key] = item
            except Exception:
                pass

        manifest_data["is_altermatic_active"] = is_active
        if is_active:
            has_base = any(k == "base" for k in manifest_data["variants"].keys())
            if not has_base:
                default_skeleton_source = "base"
                base_blend_name = f"{mod_data['name']}.blend"
                if mod_data.get("fmodel_path") and os.path.exists(os.path.join(mod_data["fmodel_path"], base_blend_name)):
                    default_skeleton_source = base_blend_name
                manifest_data["variants"]["base"] = {
                    "SkeletonSource": default_skeleton_source, "Gender": "None",
                    "IsRarePal": False, "SkinName": "", "ReqTrait": [],
                    "PrefTrait": [], "MatReplace": [], "MorphTarget": [],
                    "is_base": True, "base_type": "vanilla"
                }

        try:
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=4)
            if is_active:
                self.view.write_log(f"Altermatic Mod Mode enabled for {current_char_id}.", "success")
            else:
                self.view.write_log(f"Altermatic Mod Mode disabled for {current_char_id}. Staged models remain untouched on disk.", "warning")
        except Exception as e:
            self.view.write_log(f"ERROR: Failed to save Altermatic state: {e}", "error")
        self.mc.refresh_mods(scan_disk=True)

    def add_altermatic_variant(self, mod_data: dict):
        self.view.show_add_variant_dialog(mod_data)

    def execute_add_variant(self, mod_data: dict, label_name: str, custom_mesh: bool, clone_source: str):
        current_char_id = mod_data["name"]
        fmodel_altermatic_dir = mod_data.get("fmodel_altermatic_path")
        if not fmodel_altermatic_dir:
            fmodel_root = self.settings.get("fmodel_output", "")
            fmodel_altermatic_dir = os.path.join(fmodel_root, "Exports", "Pal", "Content", "Palbaker", "Model", "Character", "Monster", current_char_id)

        clean_label = re.sub(r'[^a-zA-Z0-9_]', '_', label_name)
        new_label = f"{current_char_id}_{clean_label}"

        manifest_path = os.path.join(fmodel_altermatic_dir, f"{current_char_id}_altermatic.json")
        manifest_data = {"is_altermatic_active": True, "variants": {}}
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f_man:
                    manifest_data = json.load(f_man)
                if isinstance(manifest_data.get("variants"), list):
                    old_list = manifest_data["variants"]
                    manifest_data["variants"] = {item.get("label", "base"): item for item in old_list}
                if new_label in manifest_data["variants"]:
                    self.view.show_snackbar(f"Error: A variant named '{clean_label}' already exists!", "red")
                    return
            except Exception:
                pass

        self.view.write_log(f"Staging Altermatic variant '{clean_label}'...", "standard")

        def background_clone_worker():
            try:
                target_blend_name = f"{current_char_id}_{clean_label}.blend"
                os.makedirs(fmodel_altermatic_dir, exist_ok=True)
                target_blend_path = os.path.join(fmodel_altermatic_dir, target_blend_name)

                base_blend = os.path.join(mod_data["fmodel_path"], f"{current_char_id}.blend")
                if os.path.exists(base_blend):
                    self.view.write_log(f"Refreshing base model layout...", "standard")
                    sync_sidecar_metadata(self.settings.get("blender"), base_blend)

                if custom_mesh:
                    src_blend_path = ""
                    if clone_source == "base":
                        src_blend_path = base_blend
                    else:
                        src_blend_path = os.path.join(fmodel_altermatic_dir, clone_source)

                    if os.path.exists(src_blend_path):
                        shutil.copy2(src_blend_path, target_blend_path)
                        self.view.write_log(f"Cloned skeleton: {os.path.basename(src_blend_path)} -> {target_blend_name}", "standard")
                        src_sidecar_path = os.path.join(os.path.dirname(src_blend_path), f"{os.path.splitext(os.path.basename(src_blend_path))[0]}_blend.json")
                        dest_sidecar_path = os.path.join(os.path.dirname(target_blend_path), f"{os.path.splitext(os.path.basename(target_blend_path))[0]}_blend.json")
                        if os.path.exists(src_sidecar_path):
                            shutil.copy2(src_sidecar_path, dest_sidecar_path)
                            self.view.write_log(f"Inherited material mappings: {os.path.basename(src_sidecar_path)} -> {os.path.basename(dest_sidecar_path)}", "standard")
                    else:
                        with open(target_blend_path, "w") as f: f.write("")

                    self.view.write_log(f"Extracting layout and metadata for {target_blend_name}...", "standard")
                    sync_sidecar_metadata(self.settings.get("blender"), target_blend_path)

                manifest_data_to_write = {"is_altermatic_active": True, "variants": {}}
                if os.path.exists(manifest_path):
                    try:
                        with open(manifest_path, "r", encoding="utf-8") as f_man:
                            manifest_data_to_write = json.load(f_man)
                        if isinstance(manifest_data_to_write.get("variants"), list):
                            old_list = manifest_data_to_write["variants"]
                            manifest_data_to_write["variants"] = {item.get("label", "base"): item for item in old_list}
                    except Exception:
                        pass

                new_variant = {
                    "SkeletonSource": target_blend_name if custom_mesh else "base",
                    "Gender": "None", "IsRarePal": False, "SkinName": "",
                    "ReqTrait": [], "PrefTrait": [], "MaterialOverrides": {},
                    "MorphTarget": [], "is_base": False
                }
                manifest_data_to_write["variants"][new_label] = new_variant
                with open(manifest_path, "w", encoding="utf-8") as f_man:
                    json.dump(manifest_data_to_write, f_man, indent=4)

                self.view.write_log(f"Successfully generated variant: {clean_label}", "success")
                self.mc.refresh_mods(scan_disk=True)

                def open_editor_delay():
                    time.sleep(0.5)
                    refreshed_mod = next((m for m in self.mc.raw_mods if m["name"] == current_char_id), None)
                    if refreshed_mod:
                        variants_list = refreshed_mod.get("altermatic_variants", [])
                        new_index = next((idx for idx, v in enumerate(variants_list) if v["label"] == new_label), -1)
                        if new_index != -1:
                            self.edit_altermatic_variant(refreshed_mod, new_index)
                threading.Thread(target=open_editor_delay, daemon=True).start()
            except Exception as err:
                self.view.write_log(f"FAILED to stage variant: {err}", "error")

        threading.Thread(target=background_clone_worker, daemon=True).start()

    def edit_altermatic_variant(self, mod_data: dict, index: int):
        variants = mod_data.get("altermatic_variants", [])
        if index < 0 or index >= len(variants): return
        v = variants[index]
        current_char_id = mod_data["name"]
        self.original_editing_label = v["label"]

        fmodel_altermatic_dir = mod_data.get("fmodel_altermatic_path")
        fmodel_dir = mod_data.get("fmodel_path")
        blend_files = get_blend_files_for_context(fmodel_altermatic_dir, fmodel_dir)
        fmodel_root = self.settings.get("fmodel_output", "")
        available_mats = get_available_materials_for_context(fmodel_root, fmodel_altermatic_dir, current_char_id)

        self.view.show_edit_variant_dialog(current_char_id, index, v, blend_files, available_mats)

    def delete_altermatic_variant(self, mod_data: dict, index: int):
        variants = mod_data.get("altermatic_variants", [])
        if index < 0 or index >= len(variants): return
        v = variants[index]
        current_char_id = mod_data["name"]
        fmodel_altermatic_dir = mod_data.get("fmodel_altermatic_path")
        if not fmodel_altermatic_dir: return

        is_material_only_reskin = (v.get("SkeletonSource", "base") == "base")
        self.view.show_delete_variant_confirm(current_char_id, index, v, is_material_only_reskin)

    def execute_delete_variant(self, current_char_id: str, index: int):
        fmodel_root = self.settings.get("fmodel_output", "")
        fmodel_altermatic_dir = os.path.join(fmodel_root, "Exports", "Pal", "Content", "Palbaker", "Model", "Character", "Monster", current_char_id)

        mod_data = next((m for m in self.mc.raw_mods if m["name"] == current_char_id), None)
        if not mod_data: return
        variants = mod_data.get("altermatic_variants", [])
        if index < 0 or index >= len(variants): return
        v = variants[index]
        is_material_only_reskin = (v.get("SkeletonSource", "base") == "base")

        manifest_path = os.path.join(fmodel_altermatic_dir, f"{current_char_id}_altermatic.json")
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f_man:
                    manifest_data = json.load(f_man)
                if isinstance(manifest_data.get("variants"), list):
                    old_list = manifest_data["variants"]
                    manifest_data["variants"] = {item.get("label", "base"): item for item in old_list}
                manifest_data["variants"].pop(v["label"], None)
                with open(manifest_path, "w", encoding="utf-8") as f_man:
                    json.dump(manifest_data, f_man, indent=4)
            except Exception:
                pass

        if not is_material_only_reskin:
            blend_file = os.path.join(fmodel_altermatic_dir, v["SkeletonSource"])
            if os.path.exists(blend_file):
                try: os.remove(blend_file)
                except OSError: pass

        self.view.write_log(f"Deleted variant: {v['label']}", "warning")
        self.mc.refresh_mods(scan_disk=True)

    def delete_altermatic_variant_by_index(self, monster_name: str, index: int):
        mod_data = next((m for m in self.mc.raw_mods if m["name"] == monster_name), None)
        if mod_data:
            self.delete_altermatic_variant(mod_data, index)

    def save_altermatic_variant_callback(self, index: int, variant_data: dict):
        is_base = variant_data.get("is_base", False)
        current_char_id = variant_data["CharacterID"]
        fmodel_target_dir = os.path.join(
            self.settings.get("fmodel_output", ""),
            "Exports", "Pal", "Content", "Palbaker", "Model", "Character", "Monster", current_char_id
        )
        os.makedirs(fmodel_target_dir, exist_ok=True)
        manifest_name = f"{current_char_id}_altermatic.json"
        manifest_path = os.path.join(fmodel_target_dir, manifest_name)

        manifest_data = {"is_altermatic_active": True, "variants": {}}
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f_man:
                    manifest_data = json.load(f_man)
                if isinstance(manifest_data.get("variants"), list):
                    old_list = manifest_data["variants"]
                    manifest_data["variants"] = {item.get("label", "base"): item for item in old_list}
            except Exception:
                pass

        new_label = f"{current_char_id}_{variant_data['label']}" if not is_base else "base"

        for label_key, other_var in manifest_data["variants"].items():
            if label_key != self.original_editing_label and label_key == new_label:
                self.mc.view.show_snackbar(f"Error: A variant named '{variant_data['label']}' already exists!", "red")
                self.mc.refresh_mods(scan_disk=True)
                return

        old_label = self.original_editing_label if (index != -1 and hasattr(self, "original_editing_label")) else ""
        if index >= 0 and index < len(manifest_data["variants"]):
            if old_label and old_label != new_label and not is_base:
                old_sidecar = os.path.join(fmodel_target_dir, f"{old_label}_blend.json")
                new_sidecar = os.path.join(fmodel_target_dir, f"{new_label}_blend.json")
                if os.path.exists(old_sidecar):
                    try:
                        os.rename(old_sidecar, new_sidecar)
                        self.view.write_log(f"Renamed sidecar file: {os.path.basename(old_sidecar)} -> {os.path.basename(new_sidecar)}", "standard")
                    except OSError: pass

                if old_label in manifest_data["variants"] and manifest_data["variants"][old_label].get("SkeletonSource") != "base":
                    old_blend_file = os.path.join(fmodel_target_dir, manifest_data["variants"][old_label]["SkeletonSource"])
                    new_blend_name = f"{new_label}.blend"
                    new_blend_file = os.path.join(fmodel_target_dir, new_blend_name)
                    if os.path.exists(old_blend_file):
                        try:
                            os.rename(old_blend_file, new_blend_file)
                            self.view.write_log(f"Renamed .blend model: {manifest_data['variants'][old_label]['SkeletonSource']} -> {new_blend_name}", "standard")
                        except OSError: pass
                    variant_data["SkeletonSource"] = new_blend_name

            manifest_data["variants"].pop(old_label, None)

        mat_replace_map = {}
        for item in variant_data.get("MatReplace", []):
            if "SlotName" in item:
                mat_replace_map[item["SlotName"]] = item["MatPath"].split("/")[-1]

        sidecar_structure = {
            "Gender": variant_data["Gender"], "IsRarePal": variant_data["IsRarePal"],
            "SkinName": variant_data["SkinName"], "ReqTrait": variant_data["ReqTrait"],
            "PrefTrait": variant_data["PrefTrait"], "MaterialOverrides": mat_replace_map, "MorphTarget": []
        }
        for m in variant_data.get("MorphTarget", []):
            if "Set" in m:
                sidecar_structure["MorphTarget"].append({"Target": m["Target"], "Type": "Static", "Set": m["Set"]})
            else:
                sidecar_structure["MorphTarget"].append({"Target": m["Target"], "Type": "Random", "Min": m.get("Min", 0.0), "Max": m.get("Max", 1.0), "Type": m.get("Type", "Free")})

        if is_base:
            base_type = "custom" if variant_data["SkeletonSource"] != "base" else "vanilla"
        else:
            base_skel = manifest_data["variants"].get("base", {}).get("SkeletonSource", "base")
            base_type = "custom" if base_skel != "base" else "vanilla"

        save_block = {"SkeletonSource": variant_data["SkeletonSource"]}
        if sidecar_structure["Gender"] != "None":
            save_block["Gender"] = sidecar_structure["Gender"]
        if sidecar_structure["IsRarePal"]:
            save_block["IsRarePal"] = sidecar_structure["IsRarePal"]
        if sidecar_structure["SkinName"]:
            save_block["SkinName"] = sidecar_structure["SkinName"]
        if sidecar_structure["ReqTrait"]:
            save_block["ReqTrait"] = sidecar_structure["ReqTrait"]
        if sidecar_structure["PrefTrait"]:
            save_block["PrefTrait"] = sidecar_structure["PrefTrait"]
        if sidecar_structure["MaterialOverrides"]:
            save_block["MaterialOverrides"] = sidecar_structure["MaterialOverrides"]
        if sidecar_structure["MorphTarget"]:
            save_block["MorphTarget"] = sidecar_structure["MorphTarget"]
        save_block["is_base"] = is_base
        save_block["base_type"] = base_type

        manifest_data["variants"][new_label] = save_block
        try:
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=4)
            self.view.write_log(f"Successfully saved Altermatic variant manifest: {manifest_name}", "success")

            palworld_exe = self.settings.get("palworld_exe", "")
            if palworld_exe and os.path.exists(palworld_exe):
                swap_json_dir = os.path.join(os.path.dirname(palworld_exe), "Pal", "Content", "Paks", "~Mods", "SwapJSON")
                from utils.altermatic_helper import compile_unified_altermatic_json
                success, msg = compile_unified_altermatic_json(current_char_id, fmodel_target_dir, swap_json_dir)
                if success:
                    self.view.write_log(f"Auto-deployed updated Altermatic JSON config: {msg}", "success")
                else:
                    self.view.write_log(f"Auto-deployment failed: {msg}", "error")
        except Exception as e:
            self.view.write_log(f"ERROR: Failed to save Altermatic manifest: {e}", "error")
        self.mc.refresh_mods(scan_disk=True)

def get_blend_files_for_context(fmodel_altermatic_dir: str, fmodel_dir: str = "") -> list[str]:
    blend_files = []
    if fmodel_dir and os.path.exists(fmodel_dir):
        for f in os.listdir(fmodel_dir):
            if f.endswith(".blend"):
                blend_files.append(f)
    if fmodel_altermatic_dir and os.path.exists(fmodel_altermatic_dir):
        for f in os.listdir(fmodel_altermatic_dir):
            if f.endswith(".blend") and f not in blend_files:
                blend_files.append(f)
    return blend_files
