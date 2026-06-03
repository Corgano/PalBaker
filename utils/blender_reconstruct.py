# utils/blender_reconstruct.py
import bpy
import sys
import os
import json
from mathutils import Matrix

# Inject paths into Blender context to allow importing from utils package
current_dir = os.path.dirname(__file__)
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Ensure the parent directory is in path so we can import 'fmodel_helper' and 'node_builder'
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

import node_builder
from fmodel_helper import resolve_and_copy_material_json

def parse_args():
    args = []
    if "--" in sys.argv:
        args = sys.argv[sys.argv.index("--") + 1:]
    
    fbx_path = None
    blend_path = None
    for i, arg in enumerate(args):
        if arg == "--fbx" and i + 1 < len(args):
            fbx_path = args[i + 1]
        elif arg == "--output" and i + 1 < len(args):
            blend_path = args[i + 1]
    return fbx_path, blend_path

def fix_hierarchy():
    print("Cleaning up bone hierarchy (removing dummy Empties)...")
    empties = [obj for obj in bpy.data.objects if obj.type == 'EMPTY']
    
    for empty in empties:
        children = list(empty.children)
        for child in children:
            world_mat = child.matrix_world.copy()
            child.parent = None
            child.matrix_world = world_mat
        bpy.data.objects.remove(empty, do_unlink=True)
        
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            obj.name = "Armature"
            obj.data.name = "Armature"# type: ignore

def reconstruct_materials(working_dir):
    """
    Constructs materials loaded into Blender. If materials are missing configurations 
    locally, it performs a search across FModel folders to resolve dependencies dynamically.
    """
    # FModel base root directory is 7 layers up from the CHARACTER directory
    # Exports/Pal/Content/Pal/Model/Character/Category/Monster -> Exports is level 7
    # Let's derive fmodel_root safely:
    fmodel_root = working_dir
    parts = os.path.normpath(working_dir).replace("\\", "/").split("/")
    
    # Find index of "Exports"
    if "Exports" in parts:
        exp_idx = parts.index("Exports")
        fmodel_root = "/".join(parts[:exp_idx])
    
    meta_path = os.path.join(working_dir, "materials_metadata.json")
    
    metadata = {}
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load local materials_metadata: {e}")

    # Inspect materials active inside Blender after mesh import
    active_materials = [mat.name for mat in bpy.data.materials if mat]
    print(f"Discovered active mesh materials in Blender: {active_materials}")

    updated_meta = False

    for mat_name in active_materials:
        # Ignore dummy Blender default material
        if mat_name.lower() == "material":
            continue
            
        # Clean naming variant formatting (e.g. MI_Body.001 -> MI_Body)
        clean_name = mat_name.split(".")[0]
        
        # If this material doesn't have local metadata, perform dynamic parent-wide pull
        if clean_name not in metadata:
            print(f"Missing local configuration for '{clean_name}'. Executing dynamic search...", flush=True)
            resolved = resolve_and_copy_material_json(clean_name, working_dir, fmodel_root)
            if resolved:
                metadata[clean_name] = resolved
                updated_meta = True

    # Save resolved metadata locally to optimize subsequent pipeline runs
    if updated_meta:
        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=4)
        except Exception as e:
            print(f"Warning: Failed to write updated materials_metadata: {e}")

    print(f"Resolved Metadata Keys: {list(metadata.keys()) if metadata else 'None'}")

    if metadata:
        for mat_name in active_materials:
            if mat_name.lower() == "material":
                continue
                
            clean_name = mat_name.split(".")[0]
            mat = bpy.data.materials.get(mat_name)
            if not mat:
                continue
                
            data = metadata.get(clean_name)
            if data:
                parent_class = data.get("parent_class", "")
                params = data.get("parameters", {})
                node_builder.build_material(mat, parent_class, params, working_dir)
            else:
                print(f"Warning: No mapping resolved for '{mat_name}', running suffix fallback...")
                # Run dynamic suffix matching on this single slot
                textures = [os.path.join(working_dir, f).replace("\\", "/") for f in os.listdir(working_dir) if f.endswith(".png")]
                tex_base = node_builder.find_best_texture_match(mat_name, textures, "B")
                tex_norm = node_builder.find_best_texture_match(mat_name, textures, "N")
                tex_mrao = node_builder.find_best_texture_match(mat_name, textures, "M")
                tex_em = node_builder.find_best_texture_match(mat_name, textures, "EM")
                
                params = {}
                if tex_base: params["Base Texture"] = tex_base
                if tex_norm: params["Normal Map"] = tex_norm
                if tex_mrao: params["MetallicRoughnessOcclusionSpecularTexture"] = tex_mrao
                if tex_em: params["Emissive Texture"] = tex_em
                
                node_builder.build_material(mat, mat_name, params, working_dir)
    else:
        node_builder.build_materials_heuristically(working_dir)

def reconstruct_blend(input_path, blend_path):
    if not input_path or not os.path.exists(input_path):
        print(f"ERROR: Input mesh file not found at {input_path}")
        sys.exit(1)

    input_path = os.path.abspath(input_path).replace("\\", "/")
    blend_path = os.path.abspath(blend_path).replace("\\", "/")

    print("Beginning path injection to locate Blender addons/extensions...", flush=True)

    # 1. Inject script paths / legacy addons discovered through Blender's API
    try:
        for script_path in bpy.utils.script_paths():
            addons_path = os.path.join(script_path, "addons")
            if os.path.exists(addons_path) and addons_path not in sys.path:
                sys.path.append(addons_path)
                print(f"Injected scripts addons path from bpy: {addons_path}", flush=True)
    except Exception as e:
        print(f"Note: Could not query script_paths: {e}", flush=True)

    # 2. Inject modern extension repositories registered in preferences (Blender 4.2+)
    try:
        if hasattr(bpy.context.preferences, "extensions"):
            for repo in bpy.context.preferences.extensions.repositories:
                repo_path = os.path.abspath(repo.directory).replace("\\", "/")
                if os.path.exists(repo_path) and repo_path not in sys.path:
                    sys.path.append(repo_path)
                    print(f"Injected extension repository path from preferences: {repo_path}", flush=True)
    except Exception as e:
        print(f"Note: Could not query extension repositories from preferences: {e}", flush=True)

    # 3. Fallback standard local scanning for Windows AppData
    if os.name == 'nt':
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            version_str = f"{bpy.app.version[0]}.{bpy.app.version[1]}"
            ext_dir = os.path.join(appdata, "Blender Foundation", "Blender", version_str, "extensions")
            
            if os.path.exists(ext_dir):
                if ext_dir not in sys.path:
                    sys.path.append(ext_dir)
                    print(f"Injected fallback extensions root: {ext_dir}", flush=True)
                
                for entry in os.listdir(ext_dir):
                    entry_path = os.path.join(ext_dir, entry)
                    if os.path.isdir(entry_path):
                        if entry_path not in sys.path:
                            sys.path.append(entry_path)
                            print(f"Injected fallback repository subdirectory: {entry_path}", flush=True)

    print("Clearing default scene objects...")
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

    if input_path.lower().endswith(".psk"):
        print(f"Importing PSK: {input_path}", flush=True)
        
        import addon_utils
        try:
            # Force refresh to make our injected sys.path directories discoverable by Blender
            addon_utils.modules_refresh()
        except Exception:
            pass

        # Build a set of physically present addon module names in this Blender environment
        available_modules = set()
        try:
            for mod in addon_utils.modules():
                available_modules.add(mod.__name__)
        except Exception as e:
            print(f"Note: Dynamic module scan failed: {e}", flush=True)

        potential_addons = []
        
        # Discover modules matching "psk_psa" or "psa_psk"
        for name in available_modules:
            if "psk_psa" in name or "psa_psk" in name:
                potential_addons.append(name)

        # Fallback list of traditional and extension names
        static_fallbacks = [
            "bl_ext.blender_org.io_scene_psk_psa",
            "bl_ext.user_default.io_scene_psk_psa",
            "bl_ext.user.io_scene_psk_psa",
            "io_scene_psk_psa",
            "io_import_scene_unreal_psa_psk"
        ]
        for f in static_fallbacks:
            if f not in potential_addons:
                potential_addons.append(f)

        # CRITICAL FILTER: Only attempt to enable addons that are physically present in the system.
        # This completely prevents Blender's internal C-engine from printing "Add-on not loaded" warnings
        # to the terminal output stream.
        addons_to_try = [addon for addon in potential_addons if addon in available_modules]

        print(f"Discovered potential PSK importers to try: {addons_to_try}", flush=True)
        
        enabled_addon = None
        
        # Check if any matches are already enabled first
        for addon in addons_to_try:
            try:
                _, already_enabled = addon_utils.check(addon)
                if already_enabled:
                    enabled_addon = addon
                    print(f"PSK addon '{addon}' is already enabled.", flush=True)
                    break
            except Exception:
                pass
                
        # If none were already enabled, attempt to enable the first available candidate
        if not enabled_addon:
            for addon in addons_to_try:
                try:
                    addon_utils.enable(addon, default_set=True)
                    _, now_enabled = addon_utils.check(addon)
                    if now_enabled:
                        enabled_addon = addon
                        print(f"Successfully registered and enabled addon: {addon}", flush=True)
                        break
                except Exception as e:
                    print(f"Failed to enable addon '{addon}': {e}", flush=True)
            
        # Determine raw operator registry presence
        has_darklight = "psk" in dir(bpy.ops) and "import_file" in dir(bpy.ops.psk) # type: ignore
        has_legacy = "import_scene" in dir(bpy.ops) and "psk" in dir(bpy.ops.import_scene) # type: ignore
        
        imported = False
        
        # Try modern Darklight/Befzz operator first
        if has_darklight:
            try:
                print("Executing modern 'bpy.ops.psk.import_file' operator...", flush=True)
                bpy.ops.psk.import_file(filepath=input_path)# type: ignore
                imported = True
            except (AttributeError, Exception) as e:
                print(f"Modern importer executed with an error (possible dummy registry): {e}. Falling back...", flush=True)
                
        # Try legacy addon operator as an automatic fallback
        if not imported and has_legacy:
            try:
                print("Executing legacy 'bpy.ops.import_scene.psk' operator...", flush=True)
                bpy.ops.import_scene.psk(filepath=input_path)# type: ignore
                imported = True
            except Exception as e:
                print(f"Legacy importer failed: {e}", flush=True)
                
        if not imported:
            print("CRITICAL ERROR: No working PSK importer operator could be successfully executed in this environment.", flush=True)
            sys.exit(1)
            
    else:
        print(f"Importing FBX: {input_path}")
        bpy.ops.import_scene.fbx(
            filepath=input_path,
            ignore_leaf_bones=True,
            global_scale=100.0
        )
    
    fix_hierarchy()
    
    working_dir = os.path.dirname(blend_path).replace("\\", "/")
    reconstruct_materials(working_dir)

    print(f"Saving .blend file to: {blend_path}")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print("BLEND Reconstruction Complete.")

if __name__ == "__main__":
    fbx, blend = parse_args()
    reconstruct_blend(fbx, blend)