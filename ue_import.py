import unreal
import json
import os

def run_import():
    working_dir = globals().get('TARGET_FOLDER', os.getcwd())
    config_path = os.path.join(working_dir, "import_config.json")
    
    with open(config_path, "r") as f:
        config = json.load(f)

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    ue_path = config["ue_target_path"]
    folder_name = ue_path.split("/")[-1]

    # PRE-WIPE CACHE
    if config.get("fbx_file") and os.path.exists(config["fbx_file"]):
        fbx_base_name = os.path.splitext(os.path.basename(config['fbx_file']))[0]
        sk_path = f"{ue_path}/SK_{fbx_base_name}"
        if unreal.EditorAssetLibrary.does_asset_exist(sk_path):
            unreal.EditorAssetLibrary.delete_asset(sk_path)
            
        pa_path = f"{ue_path}/PA_{folder_name}_PhysicsAsset"
        if unreal.EditorAssetLibrary.does_asset_exist(pa_path):
            unreal.EditorAssetLibrary.delete_asset(pa_path)
            
        skel_path = f"/Game/Pal/Model/Character/Skeleton/{folder_name}/SK_{folder_name}_Skeleton"
        if unreal.EditorAssetLibrary.does_asset_exist(skel_path):
            unreal.EditorAssetLibrary.delete_asset(skel_path)
            
    for json_file in config["mi_jsons"]:
        mi_name = os.path.basename(json_file).replace('.json', '')
        mi_path = f"{ue_path}/{mi_name}"
        if unreal.EditorAssetLibrary.does_asset_exist(mi_path):
            unreal.EditorAssetLibrary.delete_asset(mi_path)

    # 1. IMPORT TEXTURES
    for png in config["textures"]:
        print(f"Importing texture: {os.path.basename(png)}")
        task = unreal.AssetImportTask()
        task.filename = png
        task.destination_path = ue_path
        task.automated = True
        task.save = True
        task.replace_existing = True
        asset_tools.import_asset_tasks([task])

    # 2. IMPORT FBX & GENERATE ASSETS natively at 1.0 Scale
    target_asset_path = ""
    target_phys_path = ""
    
    if config.get("fbx_file") and os.path.exists(config["fbx_file"]):
        fbx_filename = os.path.basename(config['fbx_file'])
        fbx_base_name = os.path.splitext(fbx_filename)[0]
        fbx_import_name = f"SK_{fbx_base_name}"
        target_asset_path = f"{ue_path}/{fbx_import_name}"
        
        print(f"Importing skeletal mesh: {fbx_filename} as {fbx_import_name}")
        fbx_task = unreal.AssetImportTask()
        fbx_task.filename = config["fbx_file"]
        fbx_task.destination_path = ue_path
        fbx_task.destination_name = fbx_import_name
        fbx_task.automated = True
        fbx_task.save = True
        fbx_task.replace_existing = True
        
        options = unreal.FbxImportUI()
        options.import_mesh = True
        options.import_as_skeletal = True
        options.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
        options.set_editor_property('import_materials', False)
        options.set_editor_property('import_textures', False)
        options.set_editor_property('create_physics_asset', True)
        
        skel_data = unreal.FbxSkeletalMeshImportData()
        skel_data.set_editor_property('import_content_type', unreal.FBXImportContentType.FBXICT_ALL)
        skel_data.set_editor_property('normal_import_method', unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
        skel_data.set_editor_property('update_skeleton_reference_pose', False)
        skel_data.set_editor_property('use_t0_as_ref_pose', True)
        # REMOVED import_uniform_scale. Blender passes it fully baked.
        
        options.skeletal_mesh_import_data = skel_data
        fbx_task.options = options
        
        asset_tools.import_asset_tasks([fbx_task])

        # RELOCATE SKELETON
        auto_skeleton_path = f"{ue_path}/{fbx_import_name}_Skeleton"
        target_skeleton_path = f"/Game/Pal/Model/Character/Skeleton/{folder_name}/SK_{folder_name}_Skeleton"
        
        if unreal.EditorAssetLibrary.does_asset_exist(auto_skeleton_path):
            unreal.EditorAssetLibrary.make_directory(f"/Game/Pal/Model/Character/Skeleton/{folder_name}")
            if unreal.EditorAssetLibrary.does_asset_exist(target_skeleton_path):
                unreal.EditorAssetLibrary.delete_asset(target_skeleton_path)
            unreal.EditorAssetLibrary.rename_asset(auto_skeleton_path, target_skeleton_path)

        # RENAME PHYSICS ASSET
        auto_phys_path = f"{ue_path}/{fbx_import_name}_PhysicsAsset"
        target_phys_path = f"{ue_path}/PA_{folder_name}_PhysicsAsset"
        
        if unreal.EditorAssetLibrary.does_asset_exist(auto_phys_path):
            if unreal.EditorAssetLibrary.does_asset_exist(target_phys_path):
                unreal.EditorAssetLibrary.delete_asset(target_phys_path)
            unreal.EditorAssetLibrary.rename_asset(auto_phys_path, target_phys_path)

    # 3. CREATE MATERIAL INSTANCES
    mi_assets = []
    for json_file in config["mi_jsons"]:
        print(f"Creating material instance: {os.path.basename(json_file)}")
        with open(json_file, 'r') as f:
            mi_data = json.load(f)
            
        asset_name = os.path.basename(json_file).replace('.json', '')
        factory = unreal.MaterialInstanceConstantFactoryNew()
        mi_asset = asset_tools.create_asset(asset_name, ue_path, unreal.MaterialInstanceConstant, factory)
        
        is_raw_fmodel = isinstance(mi_data, list) and len(mi_data) > 0 and "Properties" in mi_data[0]
        parent_path = ""

        if is_raw_fmodel and "Parent" in mi_data[0]["Properties"]:
            raw_path = mi_data[0]["Properties"]["Parent"]["ObjectPath"]
            if "Pal/Content/" in raw_path:
                parent_path = "/Game/" + raw_path.split("Pal/Content/")[1].split(".")[0]
        
        if not parent_path:
            lower_name = asset_name.lower()
            if "eye" in lower_name or "mouth" in lower_name:
                parent_path = "/Game/Pal/Material/Character/Common/MI_PalLit_CharacterEyeBase"
            elif "hair" in lower_name:
                parent_path = "/Game/Pal/Material/Character/Common/MI_PalLit_CharacterHairBase"
            else:
                parent_path = "/Game/Pal/Material/Character/Common/MI_PalLit_CharacterBodyBase"

        parent_mat = unreal.EditorAssetLibrary.load_asset(parent_path)
        if parent_mat:
            unreal.MaterialEditingLibrary.set_material_instance_parent(mi_asset, parent_mat)

        if is_raw_fmodel:
            props = mi_data[0]["Properties"]
            for vp in props.get("VectorParameterValues", []):
                name = vp["ParameterInfo"]["Name"]
                val = vp["ParameterValue"]
                color_val = unreal.LinearColor(val.get("R", 0), val.get("G", 0), val.get("B", 0), val.get("A", 1))
                unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(mi_asset, name, color_val)
                
            for sp in props.get("ScalarParameterValues", []):
                name = sp["ParameterInfo"]["Name"]
                val = sp["ParameterValue"]
                unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mi_asset, name, val)
                
            for tp in props.get("TextureParameterValues", []):
                name = tp["ParameterInfo"]["Name"]
                obj_name = tp["ParameterValue"]["ObjectName"]
                tex_asset_name = obj_name.split("'")[1]
                loaded_tex = unreal.EditorAssetLibrary.load_asset(f"{ue_path}/{tex_asset_name}")
                if loaded_tex:
                    unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(mi_asset, name, loaded_tex)
        else:
            colors = mi_data.get("Parameters", {}).get("Colors", {})
            for c_name, rgba in colors.items():
                color_val = unreal.LinearColor(rgba["R"], rgba["G"], rgba["B"], rgba["A"])
                unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(mi_asset, c_name, color_val)
            scalars = mi_data.get("Parameters", {}).get("Scalars", {})
            for s_name, val in scalars.items():
                unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mi_asset, s_name, val)
            textures = mi_data.get("Textures", {})
            for t_name, t_path in textures.items():
                tex_asset_name = t_path.split('.')[-1]
                loaded_tex = unreal.EditorAssetLibrary.load_asset(f"{ue_path}/{tex_asset_name}")
                if loaded_tex:
                    unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(mi_asset, t_name, loaded_tex)

        unreal.EditorAssetLibrary.save_loaded_asset(mi_asset)
        mi_assets.append((asset_name.lower(), mi_asset))

    # 4. ATTACH MATERIALS & PHYSICS TO THE MESH
    if target_asset_path:
        mesh = unreal.EditorAssetLibrary.load_asset(target_asset_path)
        if mesh:
            print("Linking Materials and Physics Asset...")
            
            saved_phys = unreal.EditorAssetLibrary.load_asset(target_phys_path)
            if saved_phys:
                try:
                    mesh.set_editor_property('physics_asset', saved_phys)
                except Exception as e:
                    pass
            
            new_materials = []
            skel_materials = mesh.materials
            
            for skel_mat in skel_materials:
                slot_name = str(skel_mat.material_slot_name).lower()
                assigned = False
                
                for mi_name, mi_asset in mi_assets:
                    if ("body" in mi_name and "body" in slot_name) or \
                       ("eye" in mi_name and "eye" in slot_name) or \
                       ("mouth" in mi_name and "mouth" in slot_name) or \
                       ("hair" in mi_name and "hair" in slot_name):
                        skel_mat.material_interface = mi_asset
                        assigned = True
                        break
                        
                new_materials.append(skel_mat)
            
            mesh.set_editor_property('materials', new_materials)
            unreal.EditorAssetLibrary.save_loaded_asset(mesh)

    print("Flushing all generated assets to disk...")
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(save_map_packages=False, save_content_packages=True)
    print(f"--- IMPORT COMPLETE ---")

run_import()