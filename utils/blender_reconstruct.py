import bpy
import sys
import os
import json
from mathutils import Matrix

# Ensure utils package can be imported inside the headless Blender environment
current_dir = os.path.dirname(__file__)
if current_dir not in sys.path:
    sys.path.append(current_dir)

import node_builder

def parse_args():
    """Parses command-line arguments passed after the double dash '--' in Blender."""
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
    """Removes dummy Empties from UE imports and secures the Armature name."""
    print("Cleaning up bone hierarchy (removing dummy Empties)...")
    empties = [obj for obj in bpy.data.objects if obj.type == 'EMPTY']
    
    for empty in empties:
        children = list(empty.children)
        for child in children:
            # Preserve the exact world transform so nothing shifts when unparented
            world_mat = child.matrix_world.copy()
            child.parent = None
            child.matrix_world = world_mat
        
        bpy.data.objects.remove(empty, do_unlink=True)
        
    # Name parent Armature Object to exactly "Armature" (retains the inner bone "root")
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            obj.name = "Armature"
            obj.data.name = "Armature"

def parse_fmodel_jsons(working_dir):
    """Scans the working folder for raw FModel MI_*.json files and parses their properties directly."""
    metadata = {}
    
    for file in os.listdir(working_dir):
        if file.startswith("MI_") and file.endswith(".json"):
            json_path = os.path.join(working_dir, file)
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # FModel exports arrays with one main object containing "Properties"
                if isinstance(data, list) and len(data) > 0 and "Properties" in data[0]:
                    props = data[0]["Properties"]
                    mat_name = data[0].get("Name", os.path.splitext(file)[0])
                    
                    parent_name = "CharacterBodyBase"
                    if "Parent" in props:
                        parent_name = props["Parent"].get("ObjectName", "CharacterBodyBase")
                    
                    params = {}
                    for tex_param in props.get("TextureParameterValues", []):
                        param_name = tex_param.get("ParameterInfo", {}).get("Name", "")
                        param_val = tex_param.get("ParameterValue", {}).get("ObjectName", "")
                        if param_name and param_val:
                            # Extract raw texture name from "Texture2D'T_BlueThunderHorse_Body_B'"
                            if "'" in param_val:
                                tex_name = param_val.split("'")[1]
                            else:
                                tex_name = param_val
                            params[param_name] = tex_name
                            
                    metadata[mat_name] = {
                        "parent_class": parent_name,
                        "parameters": params
                    }
            except Exception as e:
                print(f"Warning: Failed to parse raw FModel JSON {file}: {e}")
                
    return metadata

def reconstruct_materials(working_dir):
    """Reads metadata (or parses raw FModel JSONs) and calls the node_builder to construct materials."""
    meta_path = os.path.join(working_dir, "materials_metadata.json")
    
    metadata = {}
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    else:
        print("No materials_metadata.json found. Attempting to parse raw FModel JSONs...")
        metadata = parse_fmodel_jsons(working_dir)

    # FIXED: Added diagnostic printing to see what metadata keys are being loaded
    print(f"Resolved Metadata Keys: {list(metadata.keys()) if metadata else 'None'}")

    if metadata:
        for mat_name, data in metadata.items():
            # Case-insensitive lookup to protect against naming deviations
            mat = None
            for m in bpy.data.materials:
                if m.name.lower() == mat_name.lower():
                    mat = m
                    break
            if not mat:
                mat = bpy.data.materials.new(name=mat_name)
                
            parent_class = data.get("parent_class", "")
            params = data.get("parameters", {})
            
            node_builder.build_material(mat, parent_class, params, working_dir)
    else:
        # Run the Blender-Side Suffix Heuristics Fallback if no JSONs exist
        node_builder.build_materials_heuristically(working_dir)

def reconstruct_blend(input_path, blend_path):
    if not input_path or not os.path.exists(input_path):
        print(f"ERROR: Input mesh file not found at {input_path}")
        sys.exit(1)

    # Normalize incoming paths to forward slashes to prevent string escaping crashes
    input_path = os.path.abspath(input_path).replace("\\", "/")
    blend_path = os.path.abspath(blend_path).replace("\\", "/")

    # Force-inject the Blender 4.2+ extensions directory on Windows
    if os.name == 'nt':
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            ext_path = os.path.join(appdata, "Blender Foundation", "Blender", "5.1", "extensions")
            if os.path.exists(ext_path) and ext_path not in sys.path:
                sys.path.append(ext_path)
                print(f"Injected AppData extensions path: {ext_path}")

    # Clear default scene objects manually instead of resetting factory settings.
    # This prevents the command-line loaded addons from being unregistered.
    print("Clearing default scene objects...")
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

    # Detect if we are importing a raw FModel PSK or a compiled Unreal FBX
    if input_path.lower().endswith(".psk"):
        print(f"Importing PSK: {input_path}")
        
        # Loop through both modern namespaced Extension IDs and legacy local Addon IDs
        addons_to_try = [
            "bl_ext.blender_org.io_scene_psk_psa",
            "bl_ext.user_default.io_scene_psk_psa",
            "io_scene_psk_psa",
            "io_import_scene_unreal_psa_psk"
        ]
        
        import addon_utils
        for addon in addons_to_try:
            try:
                addon_utils.enable(addon, default_check=True)
                print(f"Successfully registered and enabled addon: {addon}")
            except Exception as e:
                pass
            
        # Check which API standard is active on this machine
        has_darklight = hasattr(bpy.ops, "psk") and hasattr(bpy.ops.psk, "import_file")
        has_legacy = hasattr(bpy.ops.import_scene, "psk")
        
        if not has_darklight and not has_legacy:
            print("CRITICAL ERROR: No PSK importer addon/extension is registered in this Blender environment.")
            sys.exit(1)
            
        # Route to the correct operator standard dynamically
        if has_darklight:
            print("Executing modern 'bpy.ops.psk.import_file' operator...")
            bpy.ops.psk.import_file(filepath=input_path)
        else:
            print("Executing legacy 'bpy.ops.import_scene.psk' operator...")
            bpy.ops.import_scene.psk(filepath=input_path)
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